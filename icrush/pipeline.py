"""Main pipeline orchestrator — STAGE 1 → 1.5 → 2 → 3 → report."""

import asyncio
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from icrush.apify import ApifyClient
from icrush.classifier import analyze_commercial
from icrush.config import (
    ACTOR_IG_COMMENTS,
    ACTOR_IG_POSTS,
    ACTOR_IG_PROFILE,
    ACTOR_TT_COMMENTS,
    ACTOR_TT_PROFILE,
    COMMENTS_PER_POST,
    DATA_DIR,
    FAN_REPLACE,
    POSTS_LIMIT,
    SKIP_COMMENTS,
    SKIP_DEDUP,
    VIEW_OK,
    VIEW_REPLACE,
)
from icrush.dedup import check_dedup
from icrush.judges import (
    finalize_with_comments,
    judge_from_caption,
    short_circuit,
)
from icrush.language import detect_comment_lang, detect_lang, detect_region, parse_url
from icrush.report import build_markdown_table, build_stats, save_report
from icrush.wednesday import (
    judge_gender,
    judge_wednesday_region,
    live_lookup,
    wednesday_lookup,
)


class Pipeline:
    """Orchestrates the full multi-stage influencer vetting pipeline."""

    def __init__(self, client: ApifyClient) -> None:
        self.client = client
        self.results: dict = {}
        self.survivor_meta: dict = {}

    async def run(self, input_text: str) -> None:
        """Run the complete pipeline from raw input text to saved report."""
        # Parse URLs
        input_order = [p for p in (parse_url(line) for line in input_text.split("\n")) if p]
        if not input_order:
            print("❌ 没解析到任何 profile URL。")
            return

        print(f"📥 输入 {len(input_order)} 条 URL（含重复）")

        unique_tt = list(dict.fromkeys(p["username"] for p in input_order if p["platform"] == "TT"))
        unique_ig = list(dict.fromkeys(p["username"] for p in input_order if p["platform"] == "IG"))
        print(f"🔢 去重 TT={len(unique_tt)}, IG={len(unique_ig)}")

        # === STAGE 0: KOL 查重（入库前检查，省 Apify 费用）===
        if not SKIP_DEDUP:
            dedup_tt, dedup_ig = await self._stage0_dedup(unique_tt, unique_ig)
            if dedup_tt or dedup_ig:
                print(f"🔍 查重拦截: TT {len(dedup_tt)} 人, IG {len(dedup_ig)} 人 → 跳过 pipeline")
                unique_tt = [u for u in unique_tt if u not in dedup_tt]
                unique_ig = [u for u in unique_ig if u not in dedup_ig]
        else:
            print("\n⚠️ SKIP_DEDUP=1，跳过 KOL 查重")

        # === STAGE 1: profile metadata ===
        tt_profiles, ig_profiles = await self._stage1_profiles(unique_tt, unique_ig)

        # === Short circuit ===
        tt_survivors, ig_survivors = self._apply_short_circuit(
            unique_tt, unique_ig, tt_profiles, ig_profiles
        )

        # === STAGE 1.5: Wednesday ===
        wednesday_data = await self._stage1_5_wednesday(
            unique_tt, unique_ig, tt_profiles, ig_profiles,
            tt_survivors, ig_survivors,
        )

        # === STAGE 2: posts ===
        await self._stage2_posts(
            tt_survivors, ig_survivors, tt_profiles, ig_profiles, wednesday_data
        )

        # === STAGE 3: comments ===
        await self._stage3_comments(tt_profiles, ig_profiles)

        # === Commercial review rule ===
        for key, r in self.results.items():
            if r.get("verdict") == "✅ 是" and r.get("commercialStats") and r["commercialStats"]["total"] == 0:
                r["verdict"] = "🟡 复查"
                r["reason"] = "其他条件通过但近3月无商单"

        # === Output ===
        print("\n=== 最终判定（按粘贴顺序）===\n")
        table = build_markdown_table(input_order, self.results)
        print(table)

        stats = build_stats(self.results)
        print("\n=== 统计 ===")
        print(stats)

        total_usd = await self.client.report_cost()
        survivors_tt = len(tt_survivors)
        survivors_ig = len(ig_survivors)
        warn_count = sum(1 for r in self.results.values() if r.get("_pendingComments"))

        filepath = save_report(
            table=table,
            stats=stats,
            batch_size=len(input_order),
            unique_tt=len(unique_tt),
            unique_ig=len(unique_ig),
            survivors_tt=survivors_tt,
            survivors_ig=survivors_ig,
            warn_count=warn_count,
            total_usd=total_usd,
        )
        print(f"\n✓ 存档到 {filepath}")

    # ── helpers ──────────────────────────────────────────────────

    @staticmethod
    def _safe_get(obj: dict, direct_key: str, *nested_path: str):
        """Get a value from a dict that might be at top-level or nested under authorMeta."""
        if direct_key in obj:
            return obj[direct_key]
        for part in nested_path:
            obj = obj.get(part, {})
        return obj if isinstance(obj, (str, int, float, bool, type(None))) else None

    # ── Playwright fallback for Apify failures ───────────────────

    @staticmethod
    def _parse_follower_count(raw: str) -> int:
        """Parse follower count from meta text like '1M' or '273K' or '1,234'."""
        import re
        raw = raw.strip().replace(",", "")
        m = re.match(r"([\d.]+)\s*([KkMm]?)", raw)
        if not m:
            return 0
        num = float(m.group(1))
        unit = m.group(2).upper()
        if unit == "K":
            return int(num * 1_000)
        if unit == "M":
            return int(num * 1_000_000)
        return int(num)

    async def _scrape_ig_fallback(self, username: str) -> dict | None:
        """Use Playwright to scrape IG profile when Apify fails."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    await page.goto(f"https://www.instagram.com/{username}/",
                                    wait_until="domcontentloaded", timeout=20000)
                    # Wait for meta tag to populate (IG blocks headless, may need longer)
                    await page.wait_for_timeout(5000)
                    # Also try waiting for the meta tag itself
                    try:
                        await page.wait_for_selector('meta[name="description"]', timeout=5000)
                    except Exception:
                        pass

                    meta = await page.evaluate("""() => {
                        const m = document.querySelector('meta[name="description"]');
                        return m ? m.getAttribute('content') : '';
                    }""")

                    if not meta or len(meta) < 20:
                        print("❌ meta 为空")
                        return None

                    # Parse meta: handle both Chinese and English locale formats
                    # CN: "1M 位粉丝、已关注 Y 人、 Z 篇帖子 - Instagram 用户 Name (@xxx)："bio""
                    # EN: "1M Followers, 728 Following, 932 Posts - Name (@xxx) on Instagram: "bio""
                    import re

                    followers = 0
                    fm = re.search(r"([\d.,]+[KkMm]?)\s*(?:位粉丝|Followers?)", meta)
                    if fm:
                        followers = self._parse_follower_count(fm.group(1))

                    posts = 0
                    pm = re.search(r"(\d[\d,]*)\s*(?:篇帖子|Posts?)", meta)
                    if pm:
                        posts = int(pm.group(1).replace(",", ""))

                    name = username
                    nm = re.search(r"(?:Instagram 用户 |on Instagram: )(.+?) \(@", meta)
                    if nm:
                        name = nm.group(1).strip()

                    bio = ""
                    bm = re.search(r'\s[："]([^"]+)"$', meta)
                    if bm:
                        bio = bm.group(1).replace("\\n", "\n")

                    if followers == 0 and posts == 0:
                        print(f"⚠️ 解析失败，meta length={len(meta)}, preview={meta[:120]}")
                        return None

                    print(f"     ✅ Playwright 兜底: {followers:,}粉 {posts}帖")

                    return {
                        "username": username,
                        "fullName": name,
                        "followersCount": followers,
                        "postsCount": posts,
                        "biography": bio,
                        "businessCategoryName": None,
                        "private": False,
                        "latestPosts": [],
                    }
                finally:
                    await browser.close()
        except Exception as e:
            print(f"     ⚠️ Playwright 兜底失败: {e}")
            return None

    # ── STAGE 0: KOL 查重 ────────────────────────────────────────

    async def _stage0_dedup(
        self, tt_users: list[str], ig_users: list[str]
    ) -> tuple[set[str], set[str]]:
        """Check KOL 查重 API for all users. Returns sets of usernames to skip."""
        dup_tt: set[str] = set()
        dup_ig: set[str] = set()

        all_users = [(u, "TT", "TikTok") for u in tt_users] + \
                    [(u, "IG", "Instagram") for u in ig_users]

        if not all_users:
            return dup_tt, dup_ig

        print(f"\n=== STAGE 0: KOL 查重（{len(all_users)} 人）===")

        for username, platform, api_platform in all_users:
            sys.stdout.write(f"  → {username} ... ")
            sys.stdout.flush()
            result = await check_dedup(username, api_platform)
            if result["is_duplicate"]:
                print(f"🚫 重复 → {result['summary']}")
                if platform == "TT":
                    dup_tt.add(username)
                else:
                    dup_ig.add(username)
                self.results[f"{platform}:{username}"] = {
                    "platform": platform, "name": username,
                    "fans": None, "posts": None,
                    "regionAccurate": "-", "avgViews": None,
                    "genderFemale": None, "commercialStats": None,
                    "verdict": "🟡 已入库",
                    "reason": f"KOL查重: {result['summary']}",
                }
            elif result.get("error"):
                print(f"⚠️ {result['error']} → 放行")
            else:
                print("✅ 不重复")

        dup_total = len(dup_tt) + len(dup_ig)
        if dup_total:
            print(f"   📋 查重拦截 {dup_total} 人（已入库），跳过后续 pipeline")
        return dup_tt, dup_ig

    # ── STAGE 1 ──────────────────────────────────────────────────

    async def _stage1_profiles(
        self, tt_users: list[str], ig_users: list[str]
    ) -> tuple[dict, dict]:
        """Fetch profile metadata via Apify Actors."""
        print("\n=== STAGE 1: profile metadata（短路用）===")
        tasks: list[asyncio.Task] = []

        if tt_users:
            print(f"  → TT clockworks profile-only (resultsPerPage=1) ×{len(tt_users)}")
            tasks.append(asyncio.create_task(
                self._start_and_fetch(ACTOR_TT_PROFILE, {
                    "profiles": tt_users,
                    "profileScrapeSections": ["videos"],
                    "profileSorting": "latest",
                    "resultsPerPage": 1,
                    "shouldDownloadAvatars": False,
                    "shouldDownloadCovers": False,
                    "shouldDownloadSlideshowImages": False,
                    "shouldDownloadVideos": False,
                }, kind="tt-profile")
            ))

        if ig_users:
            print(f"  → IG profile-scraper ×{len(ig_users)}")
            tasks.append(asyncio.create_task(
                self._start_and_fetch(ACTOR_IG_PROFILE, {
                    "usernames": ig_users,
                    "includeAboutSection": True,
                }, kind="ig-profile")
            ))

        results = await asyncio.gather(*tasks)

        tt_profiles: dict = {}
        ig_profiles: dict = {}

        for kind, items in results:
            if kind == "tt-profile":
                for v in items:
                    name = self._safe_get(v, "authorMeta.name", "authorMeta", "name")
                    if not name or name in tt_profiles:
                        continue
                    bio = self._safe_get(v, "authorMeta.signature", "authorMeta", "signature") or ""
                    category = self._safe_get(v, "authorMeta.commerceUserInfo.category", "authorMeta", "commerceUserInfo", "category") or None
                    tt_profiles[name] = {
                        "name": name,
                        "fullName": self._safe_get(v, "authorMeta.nickName", "authorMeta", "nickName") or name,
                        "fans": self._safe_get(v, "authorMeta.fans", "authorMeta", "fans") or 0,
                        "posts": self._safe_get(v, "authorMeta.video", "authorMeta", "video") or 0,
                        "bio": bio,
                        "category": category,
                        "private": self._safe_get(v, "authorMeta.privateAccount", "authorMeta", "privateAccount") or False,
                        "region": detect_region(bio),
                    }
            else:
                for p in items:
                    username = p.get("username")
                    if not username:
                        continue  # skip malformed entries
                    about_country = (p.get("about") or {}).get("country", "")
                    if about_country == "Germany":
                        region = {"region": "DE", "city": "about.country"}
                    elif about_country == "Austria":
                        region = {"region": "AT", "city": "about.country"}
                    else:
                        region = detect_region(p.get("biography", ""))

                    ig_profiles[username] = {
                        "name": p["username"],
                        "fullName": p.get("fullName", ""),
                        "fans": p.get("followersCount", 0),
                        "posts": p.get("postsCount", 0),
                        "bio": p.get("biography", ""),
                        "category": p.get("businessCategoryName"),
                        "private": p.get("private", False),
                        "region": region,
                        "latestPosts": p.get("latestPosts", []),
                    }

        # Playwright fallback for IG users Apify missed
        missed_ig = [u for u in ig_users if u not in ig_profiles]
        if missed_ig:
            print(f"\n   🔄 Apify 漏了 {len(missed_ig)} 个 IG 账号，Playwright 兜底...")
            for u in missed_ig:
                sys.stdout.write(f"     → {u} ... ")
                sys.stdout.flush()
                fallback = await self._scrape_ig_fallback(u)
                if fallback:
                    about_country = (fallback.get("about") or {}).get("country", "")
                    if about_country == "Germany":
                        region = {"region": "DE", "city": "about.country"}
                    elif about_country == "Austria":
                        region = {"region": "AT", "city": "about.country"}
                    else:
                        region = detect_region(fallback.get("biography", ""))
                    ig_profiles[u] = {
                        "name": fallback["username"],
                        "fullName": fallback.get("fullName", ""),
                        "fans": fallback.get("followersCount", 0),
                        "posts": fallback.get("postsCount", 0),
                        "bio": fallback.get("biography", ""),
                        "category": fallback.get("businessCategoryName"),
                        "private": fallback.get("private", False),
                        "region": region,
                        "latestPosts": fallback.get("latestPosts", []),
                    }
                else:
                    print("❌")

        return tt_profiles, ig_profiles

    async def _start_and_fetch(self, actor: str, input_data: dict, *, kind: str) -> tuple[str, list[dict]]:
        """Start an actor, wait for completion, fetch dataset."""
        run = await self.client.start_actor(actor, input_data)
        await self.client.wait_for_run(run.run_id)
        items = await self.client.fetch_dataset(run.dataset_id)
        return kind, items

    # ── SHORT CIRCUIT ────────────────────────────────────────────

    def _apply_short_circuit(
        self,
        unique_tt: list[str],
        unique_ig: list[str],
        tt_profiles: dict,
        ig_profiles: dict,
    ) -> tuple[list[str], list[str]]:
        """Apply short-circuit logic to all profiles."""
        tt_survivors: list[str] = []
        ig_survivors: list[str] = []

        for u in unique_tt:
            p = tt_profiles.get(u)
            if p is None:
                self.results[f"TT:{u}"] = {
                    "platform": "TT", "name": u, "fans": None, "posts": None,
                    "regionAccurate": "-", "avgViews": None, "genderFemale": None,
                    "commercialStats": None, "verdict": "⚠️ 抓取失败",
                    "reason": "TT profile 抓取无返回",
                }
                continue
            sc = short_circuit("TT", p)
            if sc["fail"]:
                self.results[f"TT:{u}"] = {
                    "platform": "TT", "name": u, "fans": p["fans"], "posts": p["posts"],
                    "regionAccurate": "是" if p.get("region") else "-",
                    "avgViews": None, "genderFemale": None, "commercialStats": None,
                    "verdict": "❌ 否", "reason": sc["reason"],
                }
            else:
                tt_survivors.append(u)

        for u in unique_ig:
            p = ig_profiles.get(u)
            if p is None:
                self.results[f"IG:{u}"] = {
                    "platform": "IG", "name": u, "fans": None, "posts": None,
                    "regionAccurate": "-", "avgViews": None, "genderFemale": None,
                    "commercialStats": None, "verdict": "⚠️ 抓取失败",
                    "reason": "IG profile 抓取无返回",
                }
                continue

            sc = short_circuit("IG", p)
            if sc["fail"]:
                self.results[f"IG:{u}"] = {
                    "platform": "IG", "name": u, "fans": p["fans"], "posts": p["posts"],
                    "regionAccurate": "是" if p.get("region") else "-",
                    "avgViews": None, "genderFemale": None, "commercialStats": None,
                    "verdict": "❌ 否", "reason": sc["reason"],
                }
            else:
                ig_survivors.append(u)

        print(f"\n⚡ 短路淘汰: TT {len(unique_tt) - len(tt_survivors)}/{len(unique_tt)}, "
              f"IG {len(unique_ig) - len(ig_survivors)}/{len(unique_ig)}")
        print(f"   TT 存活: [{', '.join(tt_survivors) or '无'}]")
        print(f"   IG 存活: [{', '.join(ig_survivors) or '无'}]")

        return tt_survivors, ig_survivors

    # ── STAGE 1.5 ────────────────────────────────────────────────

    async def _stage1_5_wednesday(
        self,
        unique_tt: list[str],
        unique_ig: list[str],
        tt_profiles: dict,
        ig_profiles: dict,
        tt_survivors: list[str],
        ig_survivors: list[str],
    ) -> dict:
        """Query Wednesday cache for ALL users. For survivors: apply pass/fail.
        For already short-circuited: only fill in gender/region data.
        Cache misses → auto query Wednesday API live."""
        wednesday_data: dict = {}

        all_tt = list(unique_tt)
        all_ig = list(unique_ig)

        # Collect all users to query
        all_users: list[tuple[str, str]] = []
        for u in unique_tt:
            all_users.append(("TT", u))
        for u in unique_ig:
            all_users.append(("IG", u))

        surv_count = len(tt_survivors) + len(ig_survivors)
        total = len(all_users)
        print(f"\n=== STAGE 1.5: Wednesday 地区+性别查询（{total} 人，{surv_count} 存活 + {total - surv_count} 已淘汰）===")

        # First pass: check cache
        cache_misses: list[str] = []  # usernames not in cache
        for platform, u in all_users:
            p = tt_profiles.get(u) if platform == "TT" else ig_profiles.get(u)
            if p is None:
                continue
            key = f"{platform}:{u}"
            is_short = key in self.results and self.results[key].get("verdict") == "❌ 否"

            detail = wednesday_lookup(u)
            if not detail["found"]:
                if not is_short:
                    cache_misses.append(u)
                continue

        # Auto-query live for cache misses
        if cache_misses:
            print(f"   🔍 {len(cache_misses)} 人无缓存，自动查询 Wednesday API...")
            await live_lookup(cache_misses)
            # Re-read cache after live lookup updated it
            import importlib
            # force reload the module-level cache to pick up new data
            wednesday_module = importlib.import_module("icrush.wednesday")
            wednesday_module._cache = None  # type: ignore[attr-defined]

        # Second pass: now all users should be in cache (or confirmed not found)
        for platform, u in all_users:
            p = tt_profiles.get(u) if platform == "TT" else ig_profiles.get(u)
            if p is None:
                continue
            key = f"{platform}:{u}"
            is_short = key in self.results and self.results[key].get("verdict") == "❌ 否"

            detail = wednesday_lookup(u)
            if not detail["found"]:
                if not is_short:
                    print(f"  → {key}: ❌ 无缓存（Wednesday 未收录）→ 走原流程")
                    wednesday_data[key] = {"found": False}
                continue

            region_r = judge_wednesday_region(detail)
            gender_r = judge_gender(detail, p.get("fans", 0))
            female_str = f"{detail['gender']['female']}%" if detail.get("gender") else "无信息"

            wednesday_data[key] = {
                "found": True,
                "regionPass": region_r["pass"],
                "genderPass": gender_r["pass"],
                "genderFemale": detail.get("gender", {}).get("female") if detail.get("gender") else None,
                "topCountry": detail.get("topCountry"),
                "topCity": detail.get("topCity"),
            }

            if is_short:
                existing = self.results[key]
                existing["genderFemale"] = detail.get("gender", {}).get("female") if detail.get("gender") else None
                if existing["regionAccurate"] == "是" and region_r["pass"]:
                    existing["regionAccurate"] = "是 (Wednesday)"
                print(f"     {key}: 已淘汰但补全数据 → 女粉 {female_str}")
                continue

            if not region_r["pass"]:
                self.results[key] = {
                    "platform": platform, "name": u,
                    "fans": p["fans"], "posts": p["posts"],
                    "regionAccurate": "否 (Wednesday)",
                    "avgViews": None,
                    "genderFemale": detail.get("gender", {}).get("female") if detail.get("gender") else None,
                    "commercialStats": None,
                    "verdict": "❌ 否", "reason": region_r["reason"],
                }
                print(f"     ❌ 地区不通过: {region_r['reason']}")
                if platform == "TT":
                    tt_survivors.remove(u)
                else:
                    ig_survivors.remove(u)
            elif not gender_r["pass"]:
                self.results[key] = {
                    "platform": platform, "name": u,
                    "fans": p["fans"], "posts": p["posts"],
                    "regionAccurate": "是 (Wednesday)",
                    "avgViews": None,
                    "genderFemale": detail.get("gender", {}).get("female") if detail.get("gender") else None,
                    "commercialStats": None,
                    "verdict": "❌ 否", "reason": gender_r["reason"],
                }
                print(f"     ❌ 性别不通过: {gender_r['reason']} (女粉 {female_str})")
                if platform == "TT":
                    tt_survivors.remove(u)
                else:
                    ig_survivors.remove(u)
            else:
                tc = detail.get("topCountry")
                tci = detail.get("topCity")
                print(f"     ✅ 地区=DE {tc['pct']}% + 城市={tci['name'] if tci else '?'} + 女粉 {female_str}")

        return wednesday_data

    # ── STAGE 2 ──────────────────────────────────────────────────

    async def _stage2_posts(
        self,
        tt_survivors: list[str],
        ig_survivors: list[str],
        tt_profiles: dict,
        ig_profiles: dict,
        wednesday_data: dict,
    ) -> None:
        """Scrape 20 posts per survivor."""
        total = len(tt_survivors) + len(ig_survivors)
        if total == 0:
            return

        print(f"\n=== STAGE 2: 抓 survivors 的 posts/videos（{POSTS_LIMIT} 条/人）===")
        tasks: list[asyncio.Task] = []

        if tt_survivors:
            print(f"  → TT clockworks {POSTS_LIMIT} videos ×{len(tt_survivors)}")
            tasks.append(asyncio.create_task(
                self._start_and_fetch(ACTOR_TT_PROFILE, {
                    "profiles": tt_survivors,
                    "profileScrapeSections": ["videos"],
                    "profileSorting": "latest",
                    "resultsPerPage": POSTS_LIMIT,
                    "excludePinnedPosts": True,
                    "shouldDownloadAvatars": False,
                    "shouldDownloadCovers": False,
                    "shouldDownloadSlideshowImages": False,
                    "shouldDownloadVideos": False,
                }, kind="tt-posts")
            ))

        if ig_survivors:
            print(f"  → IG post-scraper detailedData, {POSTS_LIMIT} posts ×{len(ig_survivors)}")
            tasks.append(asyncio.create_task(
                self._start_and_fetch(ACTOR_IG_POSTS, {
                    "username": ig_survivors,
                    "dataDetailLevel": "detailedData",
                    "resultsLimit": POSTS_LIMIT,
                    "skipPinnedPosts": False,
                }, kind="ig-posts")
            ))

        results_list = await asyncio.gather(*tasks)

        # Group posts by user
        tt_posts_by_user: dict[str, list] = {}
        ig_posts_by_user: dict[str, list] = {}

        for kind, items in results_list:
            if kind == "tt-posts":
                for v in items:
                    name = self._safe_get(v, "authorMeta.name", "authorMeta", "name")
                    if not name:
                        continue
                    tt_posts_by_user.setdefault(name, []).append({
                        "lang": v.get("textLanguage"),
                        "createTime": v.get("createTimeISO"),
                        "createTimeRaw": v.get("createTime"),
                        "playCount": v.get("playCount", 0),
                        "url": v.get("webVideoUrl"),
                        "text": v.get("text", ""),
                        "hashtags": v.get("hashtags", []),
                        "isAd": v.get("isAd", False),
                        "isSponsored": v.get("isSponsored", False),
                        "mentions": v.get("mentions", []),
                        "detailedMentions": v.get("detailedMentions", []),
                    })
            else:
                for p in items:
                    owner = p.get("ownerUsername")
                    if owner:
                        ig_posts_by_user.setdefault(owner, []).append(p)

        three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)

        # Process TT survivors
        for u in tt_survivors:
            p = tt_profiles[u]
            posts = tt_posts_by_user.get(u, [])
            wd_key = f"TT:{u}"
            wd = wednesday_data.get(wd_key, {"found": False})

            recent = [x for x in posts if x["createTime"] and
                      datetime.fromisoformat(x["createTime"].replace("Z", "+00:00")) > three_months_ago]
            avg_views = round(sum(x["playCount"] for x in recent) / len(recent)) if recent else 0

            gender_female = wd.get("genderFemale") if wd.get("found") else None
            commercial_stats = analyze_commercial(posts, "TT", three_months_ago)

            if wd.get("found") and wd.get("regionPass") and wd.get("genderPass"):
                region_acc = "是 (Wednesday)"
                is_replace = p["fans"] < FAN_REPLACE
                if avg_views >= VIEW_OK:
                    view_status = "pass"
                elif avg_views >= VIEW_REPLACE:
                    view_status = "replace"
                else:
                    view_status = "fail"

                if view_status == "fail":
                    self.results[wd_key] = {
                        "platform": "TT", "name": u, "fans": p["fans"], "posts": p["posts"],
                        "regionAccurate": region_acc, "avgViews": avg_views,
                        "genderFemale": gender_female, "commercialStats": commercial_stats,
                        "verdict": "❌ 否",
                        "reason": f"近 3 月平均浏览 {avg_views:,}<{VIEW_REPLACE}",
                    }
                elif is_replace or view_status == "replace":
                    rs = []
                    if is_replace: rs.append(f"粉丝 {p['fans']}<10K")
                    if view_status == "replace": rs.append(f"平均浏览 {avg_views:,} 在 2000-4000")
                    self.results[wd_key] = {
                        "platform": "TT", "name": u, "fans": p["fans"], "posts": p["posts"],
                        "regionAccurate": region_acc, "avgViews": avg_views,
                        "genderFemale": gender_female, "commercialStats": commercial_stats,
                        "verdict": "🟡 置换组", "reason": "; ".join(rs),
                    }
                else:
                    self.results[wd_key] = {
                        "platform": "TT", "name": u, "fans": p["fans"], "posts": p["posts"],
                        "regionAccurate": region_acc, "avgViews": avg_views,
                        "genderFemale": gender_female, "commercialStats": commercial_stats,
                        "verdict": "✅ 是", "reason": "-",
                    }
            else:
                de_count = sum(1 for x in posts if x.get("lang") == "de")
                en_count = sum(1 for x in posts if x.get("lang") == "en")
                de_pct = round(de_count * 100 / (de_count + en_count)) if (de_count + en_count) > 0 else None
                j = judge_from_caption("TT", p, de_pct, avg_views)
                self.results[wd_key] = {
                    "platform": "TT", "name": u, "fans": p["fans"], "posts": p["posts"],
                    **j, "avgViews": avg_views, "genderFemale": gender_female,
                    "commercialStats": commercial_stats,
                    "_captionDePct": de_pct,
                }

            self.survivor_meta[wd_key] = {
                "avgViews": avg_views,
                "urls": [x["url"] for x in posts if x.get("url")],
            }

        # Process IG survivors
        for u in ig_survivors:
            p = ig_profiles[u]
            posts = ig_posts_by_user.get(u, [])
            wd_key = f"IG:{u}"
            wd = wednesday_data.get(wd_key, {"found": False})

            recent_videos = [
                x for x in posts
                if (x.get("type") == "Video" or (x.get("videoPlayCount") and x.get("videoPlayCount", 0) > 0))
                and x.get("timestamp")
                and datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")) > three_months_ago
            ]
            if recent_videos:
                views_list = [x.get("videoPlayCount") or x.get("videoViewCount") or 0 for x in recent_videos]
                avg_views = round(sum(views_list) / len(views_list))
            else:
                avg_views = 0

            gender_female = wd.get("genderFemale") if wd.get("found") else None
            commercial_stats = analyze_commercial(posts, "IG", three_months_ago)

            if wd.get("found") and wd.get("regionPass") and wd.get("genderPass"):
                region_acc = "是 (Wednesday)"
                is_replace = p["fans"] < FAN_REPLACE
                if avg_views >= VIEW_OK:
                    view_status = "pass"
                elif avg_views >= VIEW_REPLACE:
                    view_status = "replace"
                else:
                    view_status = "fail"

                if view_status == "fail":
                    self.results[wd_key] = {
                        "platform": "IG", "name": u, "fans": p["fans"], "posts": p["posts"],
                        "regionAccurate": region_acc, "avgViews": avg_views,
                        "genderFemale": gender_female, "commercialStats": commercial_stats,
                        "verdict": "❌ 否",
                        "reason": f"近 3 月平均浏览 {avg_views:,}<{VIEW_REPLACE}",
                    }
                elif is_replace or view_status == "replace":
                    rs = []
                    if is_replace: rs.append(f"粉丝 {p['fans']}<10K")
                    if view_status == "replace": rs.append(f"平均浏览 {avg_views:,} 在 2000-4000")
                    self.results[wd_key] = {
                        "platform": "IG", "name": u, "fans": p["fans"], "posts": p["posts"],
                        "regionAccurate": region_acc, "avgViews": avg_views,
                        "genderFemale": gender_female, "commercialStats": commercial_stats,
                        "verdict": "🟡 置换组", "reason": "; ".join(rs),
                    }
                else:
                    self.results[wd_key] = {
                        "platform": "IG", "name": u, "fans": p["fans"], "posts": p["posts"],
                        "regionAccurate": region_acc, "avgViews": avg_views,
                        "genderFemale": gender_female, "commercialStats": commercial_stats,
                        "verdict": "✅ 是", "reason": "-",
                    }
            else:
                captions = [x for x in posts if x.get("caption") and len(x["caption"].strip()) > 5]
                g = sum(1 for post in captions if detect_lang(post["caption"]) == "de")
                e = sum(1 for post in captions if detect_lang(post["caption"]) == "en")
                de_pct = round(g * 100 / (g + e)) if (g + e) > 0 else None
                j = judge_from_caption("IG", p, de_pct, avg_views)
                self.results[wd_key] = {
                    "platform": "IG", "name": u, "fans": p["fans"], "posts": p["posts"],
                    **j, "avgViews": avg_views, "genderFemale": gender_female,
                    "commercialStats": commercial_stats,
                    "_captionDePct": de_pct,
                }

            self.survivor_meta[wd_key] = {
                "avgViews": avg_views,
                "urls": [x.get("url") for x in posts if x.get("url")],
            }

    # ── STAGE 3 ──────────────────────────────────────────────────

    async def _stage3_comments(
        self, tt_profiles: dict, ig_profiles: dict
    ) -> None:
        """Comment scraping for ⚠️ users."""
        warn_list = [k for k, r in self.results.items() if r.get("_pendingComments")]

        if SKIP_COMMENTS:
            for k in warn_list:
                self.results[k]["verdict"] = "⚠️ 需人工核查"
                self.results[k]["reason"] = "跳过评论检查（需人工判定地区）"
            return

        if not warn_list:
            return

        print(f"\n=== STAGE 3: ⚠️ 评论检查（{len(warn_list)} 人）===")

        tt_warn = [k[3:] for k in warn_list if k.startswith("TT:")]
        ig_warn = [k[3:] for k in warn_list if k.startswith("IG:")]

        tasks: list[asyncio.Task] = []

        if tt_warn:
            urls = []
            for u in tt_warn:
                urls.extend((self.survivor_meta.get(f"TT:{u}", {}).get("urls") or [])[:POSTS_LIMIT])
            print(f"  → TT thescrapelab {len(urls)} videos × {COMMENTS_PER_POST} 评论 ({len(tt_warn)} 人)")
            tasks.append(asyncio.create_task(
                self._start_and_fetch(ACTOR_TT_COMMENTS, {
                    "videoUrls": urls,
                    "maxCommentsPerVideo": COMMENTS_PER_POST,
                    "includeReplies": False,
                }, kind="tt-comments")
            ))

        if ig_warn:
            urls = []
            for u in ig_warn:
                urls.extend((self.survivor_meta.get(f"IG:{u}", {}).get("urls") or [])[:POSTS_LIMIT])
            print(f"  → IG instagram-comment-scraper {len(urls)} posts × {COMMENTS_PER_POST} 评论 ({len(ig_warn)} 人)")
            tasks.append(asyncio.create_task(
                self._start_and_fetch(ACTOR_IG_COMMENTS, {
                    "directUrls": urls,
                    "resultsLimit": COMMENTS_PER_POST,
                }, kind="ig-comments")
            ))

        results_list = await asyncio.gather(*tasks)

        # Analyze comments per user
        tt_comments_by_user: dict[str, dict] = {}
        ig_comments_by_user: dict[str, dict] = {}

        for kind, items in results_list:
            if kind == "tt-comments":
                for c in items:
                    if not c.get("video_url") or not c.get("text"):
                        continue
                    m = re.search(r"@([^/]+)/", c["video_url"])
                    if not m:
                        continue
                    user = m.group(1)
                    if user not in tt_warn:
                        continue
                    s = tt_comments_by_user.setdefault(user, {"de": 0, "en": 0, "total": 0})
                    s["total"] += 1
                    lang = c.get("language") or detect_comment_lang(c["text"])
                    if lang == "de":
                        s["de"] += 1
                    elif lang == "en":
                        s["en"] += 1
            else:
                for c in items:
                    if not c.get("postUrl") or not c.get("text"):
                        continue
                    # Map postUrl → ownerUsername via ig_posts (would need ig_posts loaded)
                    # For now, skip mapping as it requires the full IG posts data
                    # Fallback: use a URL-based heuristic
                    user = None
                    for u in ig_warn:
                        meta_urls = self.survivor_meta.get(f"IG:{u}", {}).get("urls") or []
                        if c["postUrl"] in meta_urls:
                            user = u
                            break
                    if not user:
                        continue
                    s = ig_comments_by_user.setdefault(user, {"de": 0, "en": 0, "total": 0})
                    s["total"] += 1
                    lang = detect_comment_lang(c["text"])
                    if lang == "de":
                        s["de"] += 1
                    elif lang == "en":
                        s["en"] += 1

        # Apply comment-based verdicts
        for k in warn_list:
            platform = k[:2]
            user = k[3:]
            profile = (tt_profiles if platform == "TT" else ig_profiles).get(user, {})
            stats = tt_comments_by_user.get(user) if platform == "TT" else ig_comments_by_user.get(user)
            meta = self.survivor_meta.get(k, {})

            if stats and (stats["de"] + stats["en"]) > 0:
                de_pct = round(stats["de"] * 100 / (stats["de"] + stats["en"]))
            else:
                de_pct = None

            j = finalize_with_comments(profile, meta.get("avgViews", 0), de_pct)
            existing = self.results[k]
            self.results[k] = {
                "platform": platform, "name": user,
                "fans": profile.get("fans"), "posts": profile.get("posts"),
                **j,
                "avgViews": meta.get("avgViews", 0),
                "genderFemale": existing.get("genderFemale"),
                "commercialStats": existing.get("commercialStats"),
            }

            stat_summary = (
                f"(de={stats['de']}, en={stats['en']}, total={stats['total']})"
                if stats else "(无评论数据)"
            )
            print(f"   {k}: 评论 {de_pct if de_pct is not None else '?'}% {stat_summary} → {j['verdict']}")

        # Clean up _pendingComments markers
        for k in self.results:
            self.results[k].pop("_pendingComments", None)
