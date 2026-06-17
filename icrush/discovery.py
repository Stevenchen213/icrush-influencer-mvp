"""Automatic influencer discovery engine.

Orchestrates: Wednesday keyword search → pre-filter → pipeline feed.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from icrush.airtable import check_airtable
from icrush.apify import ApifyClient
from icrush.config import (
    DISCOVERY_FAN_MAX_IG,
    DISCOVERY_FAN_MAX_TT,
    DISCOVERY_FAN_MIN,
    DISCOVERY_GENDER_FEMALE_MIN,
    DISCOVERY_KEYWORDS,
    EXCLUSION_FILE,
    HASHTAG_KEYWORDS,
    HISTORY_FILE,
    AUTO_INPUT_FILE,
    WEDNESDAY_COUNTRY_MIN,
    WEDNESDAY_MIN_REMAINING,
    WEDNESDAY_VIEW_BUDGET,
)
from icrush.feishu import check_feishu
from icrush.language import detect_male_by_name
from icrush.wednesday import (
    is_german_city,
    live_lookup,
    search_all_keywords,
)


class DiscoveryEngine:
    """Orchestrates auto-discovery of influencers via Wednesday + Apify."""

    def __init__(self, client: ApifyClient) -> None:
        self.client = client
        self.candidates: list[dict] = []
        self.filtered: list[dict] = []
        self.validated: list[dict] = []
        self.exclusion_usernames: set[str] = set()
        self.exclusion_ids: set[int] = set()
        self.history_usernames: set[str] = set()
        self.history_ids: set[int] = set()
        self.quota_used: int = 0
        self.history_data: dict = {}

        self._load_files()

    def _load_files(self) -> None:
        """Load exclusion and history from disk."""
        try:
            excl = json.loads(EXCLUSION_FILE.read_text(encoding="utf-8"))
            self.exclusion_usernames = set(
                u.lower() for u in excl.get("usernames", [])
            )
            self.exclusion_ids = set(excl.get("ids", []))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        try:
            self.history_data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            self.history_usernames = set(
                u.lower() for u in self.history_data.get("processed_usernames", [])
            )
            self.history_ids = set(self.history_data.get("processed_ids", []))
        except (FileNotFoundError, json.JSONDecodeError):
            self.history_data = self._empty_history()

    @staticmethod
    def _empty_history() -> dict:
        return {
            "last_run": None,
            "total_discovered": 0,
            "processed_usernames": [],
            "processed_ids": [],
            "runs": [],
            "quota_used_total": 0,
        }

    def _parse_followers(self, val: int | None) -> int:
        """Safely parse follower count."""
        if val is None:
            return 0
        return int(val)

    def is_excluded(self, username: str = "", influencer_id: int = 0) -> bool:
        """Check if an influencer is in exclusion or history."""
        if username.lower() in self.exclusion_usernames:
            return True
        if influencer_id and influencer_id in self.exclusion_ids:
            return True
        if username.lower() in self.history_usernames:
            return True
        if influencer_id and influencer_id in self.history_ids:
            return True
        return False

    def pre_filter_single(self, inf: dict) -> dict | None:
        """Apply pre-filters to one candidate. Returns rejection reason or None if pass."""
        username = (inf.get("username") or "").lower()
        inf_id = inf.get("id") or 0

        # 1. Exclusion check
        if self.is_excluded(username=username, influencer_id=inf_id):
            return {"reason": "excluded"}

        # 2. Male name check
        name = inf.get("name", "")
        if detect_male_by_name(name):
            return {"reason": "male_name"}

        # 3. Follower range
        followers = self._parse_followers(inf.get("followers"))
        # Determine platform: check IG handles first, then TT
        ig_handles = inf.get("instagrams") or []
        tt_handles = inf.get("tiktoks") or []
        is_ig = len(ig_handles) > 0
        is_tt = len(tt_handles) > 0

        if is_ig and (followers < DISCOVERY_FAN_MIN or followers > DISCOVERY_FAN_MAX_IG):
            return {"reason": "fans_out_of_range"}
        if is_tt and (followers < DISCOVERY_FAN_MIN or followers > DISCOVERY_FAN_MAX_TT):
            return {"reason": "fans_out_of_range"}
        if not is_ig and not is_tt and followers > 0:
            return {"reason": "no_social_handles"}

        # 4. Country check
        tc = inf.get("topCountry") or {}
        tc_code = (tc.get("code") or "").upper()
        tc_pct = tc.get("pct", 0)
        if tc_code not in ("DE", "AT") or tc_pct < WEDNESDAY_COUNTRY_MIN:
            return {"reason": "wrong_country"}

        # 5. City check
        tci = inf.get("topCity") or {}
        tci_name = tci.get("name", "")
        if not is_german_city(tci_name):
            # Loose: if no city but country is DE, still pass
            pass

        # 6. Gender check
        gender = inf.get("gender") or {}
        female_pct = gender.get("female", gender.get("f", 0)) or 0
        if female_pct < DISCOVERY_GENDER_FEMALE_MIN:
            return {"reason": "too_male_audience"}

        # All filters passed — enrich with parsed data
        inf["_followers_parsed"] = followers
        inf["_country_code"] = tc_code
        inf["_female_pct"] = female_pct
        inf["_ig_handles"] = ig_handles
        inf["_tt_handles"] = tt_handles
        return None  # Passed

    def pre_filter_all(self) -> tuple[list[dict], dict]:
        """Apply pre-filter to all candidates. Returns (passed, stats)."""
        passed: list[dict] = []
        stats: dict = {}

        for inf in self.candidates:
            fail = self.pre_filter_single(inf)
            if fail:
                reason = fail["reason"]
                stats[reason] = stats.get(reason, 0) + 1
            else:
                passed.append(inf)

        self.filtered = passed
        return passed, stats

    def generate_input_file(self) -> Path:
        """Generate data/input_auto.txt with profile URLs for pipeline."""
        lines: list[str] = []
        for inf in self.filtered:
            # Prefer IG handles
            ig_handles = inf.get("_ig_handles") or inf.get("instagrams") or []
            tt_handles = inf.get("_tt_handles") or inf.get("tiktoks") or []

            has_url = False
            for ig in ig_handles:
                uname = ig.get("username") if isinstance(ig, dict) else str(ig)
                if uname:
                    lines.append(f"https://www.instagram.com/{uname}/")
                    has_url = True
            if not has_url:
                for tt in tt_handles:
                    uname = tt.get("username") if isinstance(tt, dict) else str(tt)
                    if uname:
                        lines.append(f"https://www.tiktok.com/@{uname}/")
                        has_url = True

        AUTO_INPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return AUTO_INPUT_FILE

    def _save_history(self) -> None:
        """Persist discovery history to disk."""
        self.history_data["last_run"] = datetime.now(timezone.utc).isoformat()
        self.history_data["total_discovered"] += len(self.filtered)
        for inf in self.filtered:
            uname = (inf.get("username") or "").lower()
            uid = inf.get("id") or 0
            if uname and uname not in self.history_usernames:
                self.history_data["processed_usernames"].append(uname)
            if uid and uid not in self.history_ids:
                self.history_data["processed_ids"].append(uid)
        self.history_data["runs"].append({
            "date": self.history_data["last_run"],
            "candidates": len(self.candidates),
            "filtered": len(self.filtered),
            "keywords_used": len(DISCOVERY_KEYWORDS),
            "quota_used": self.quota_used,
        })
        self.history_data["quota_used_total"] += self.quota_used
        HISTORY_FILE.write_text(
            json.dumps(self.history_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    async def search_and_filter(
        self,
        *,
        keywords: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        """Phase 1: Search Wednesday and pre-filter. Zero views consumed.

        Returns stats dict.
        """
        if keywords is None:
            keywords = DISCOVERY_KEYWORDS

        print(f"\n🔎 周三关键词搜索 ({len(keywords)} 个关键词)...")
        self.candidates = await search_all_keywords(keywords)
        print(f"   📊 去重后共 {len(self.candidates)} 个唯一候选人")

        print(f"\n🔬 预筛选（DE≥{WEDNESDAY_COUNTRY_MIN}%, 女≥{DISCOVERY_GENDER_FEMALE_MIN}%, "
              f"粉 {DISCOVERY_FAN_MIN}-{DISCOVERY_FAN_MAX_IG}K, 男名, 排除）...")
        passed, stats = self.pre_filter_all()
        print(f"   ✅ {len(passed)} 人通过预筛选")
        for reason, count in sorted(stats.items()):
            labels = {
                "excluded": "排除列表/历史",
                "male_name": "男博主名字",
                "fans_out_of_range": "粉丝不在范围",
                "no_social_handles": "无社交媒体账号",
                "wrong_country": f"受众非 DE/AT 或 <{WEDNESDAY_COUNTRY_MIN}%",
                "too_male_audience": f"女粉 <{DISCOVERY_GENDER_FEMALE_MIN}%",
            }
            print(f"   ❌ {labels.get(reason, reason)}: {count} 人")

        return {"candidates": len(self.candidates), "passed": len(passed), "stats": stats}

    async def run_pipeline(self) -> None:
        """Feed discovered candidates into the vetting pipeline."""
        from icrush.pipeline import Pipeline

        # Check Airtable + 飞书 for final dedup before pipeline
        print(f"\n🔗 最终查重（Airtable + 飞书）...")
        final_candidates = []
        for inf in self.filtered:
            username = (inf.get("username") or "").lower()
            ig_handles = inf.get("_ig_handles") or []

            # Check all IG handles against Airtable and 飞书
            excluded = False
            for ig in ig_handles:
                uname = ig.get("username") if isinstance(ig, dict) else str(ig)
                if await check_airtable(uname):
                    print(f"   🚫 {uname}: Airtable 查重命中")
                    excluded = True
                    break
                if await check_feishu(uname):
                    print(f"   🚫 {uname}: 飞书查重命中")
                    excluded = True
                    break
            if not excluded and username:
                if await check_airtable(username):
                    print(f"   🚫 {username}: Airtable 查重命中")
                    excluded = True
                elif await check_feishu(username):
                    print(f"   🚫 {username}: 飞书查重命中")
                    excluded = True

            if not excluded:
                final_candidates.append(inf)
            else:
                self.exclusion_usernames.add(username)

        self.filtered = final_candidates
        print(f"   ✅ 最终 {len(self.filtered)} 人通过所有检查")

        if not self.filtered:
            print("\n⚠️ 没有候选人需要 pipeline 验证")
            return

        # Generate input file and run pipeline
        input_path = self.generate_input_file()
        print(f"\n📄 输入文件: {input_path} ({len(self.filtered)} 条 URL)")

        text = input_path.read_text(encoding="utf-8")
        pipeline = Pipeline(self.client)
        await pipeline.run(text)

        self._save_history()

    async def run(
        self,
        *,
        keywords: list[str] | None = None,
        force: bool = False,
    ) -> None:
        """Full discovery flow: search → filter → pipeline."""
        await self.search_and_filter(keywords=keywords, force=force)

        if self.filtered:
            await self.run_pipeline()
        else:
            print("\n⚠️ 预筛选后无候选人，跳过 pipeline")
