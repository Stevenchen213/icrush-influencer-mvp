"""Wednesday / Upfluence cache operations and judgment functions."""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone

from icrush.config import (
    CACHE_FILE,
    GENDER_MALE_MAX,
    GENDER_MALE_MAX_100K,
    WEDNESDAY_COUNTRY_MIN,
    WEDNESDAY_EMAIL,
    WEDNESDAY_PASSWORD,
)
from icrush.wordlists import AUSTRIAN_CITIES, GERMAN_CITY_ABBR, GERMAN_CITY_LIST

_cache: dict | None = None

# "found: false" cache entries expire after N days — re-query next time
WEDNESDAY_CACHE_TTL_DAYS = 7


def load_wednesday_cache() -> dict:
    """Load and memoize the Wednesday cache file."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        _cache = {}
    return _cache


def wednesday_lookup(username: str) -> dict:
    """Look up a username in the Wednesday cache.

    Returns {'found': True, 'gender': ..., 'topCountry': ..., 'topCity': ...}
    or {'found': False}.
    """
    cache = load_wednesday_cache()
    entry = cache.get(username)
    if not entry or not entry.get("found"):
        return _recheck_if_stale(username, cache)

    # login failure entries → re-query (don't serve stale error)
    if entry.get("_wednesdayFailed"):
        return {"found": False}

    # Must have at least one of gender / country / city / dePct to be "usable"
    has_data = entry.get("gender") or entry.get("topCountry") or entry.get("topCity") or entry.get("dePct")
    if not has_data:
        return {"found": False}

    # Null protection: if dePct is None (old cache format), need re-query
    if entry.get("dePct") is None and entry.get("atPct") is None:
        return {"found": False}

    return {
        "found": True,
        "gender": entry.get("gender"),
        "topCountry": entry.get("topCountry"),
        "topCity": entry.get("topCity"),
        "dePct": entry.get("dePct") or 0,
        "atPct": entry.get("atPct") or 0,
    }


def _recheck_if_stale(username: str, cache: dict) -> dict:
    """Return {'found': False} unless the cached 'found: false' is older than TTL."""
    entry = cache.get(username, {})
    if not isinstance(entry, dict):
        return {"found": False}

    last_attempt = entry.get("_lastAttempt")
    if last_attempt:
        try:
            age_days = (time.time() - last_attempt) / 86400
            if age_days < WEDNESDAY_CACHE_TTL_DAYS:
                return {"found": False}  # still fresh, don't re-query
        except (TypeError, ValueError):
            pass

    # Stale or no timestamp → clear entry so live_lookup re-queries
    cache.pop(username, None)
    return {"found": False}


def is_german_city(city_name: str | None) -> bool:
    """Check if a city name refers to a German or Austrian city."""
    if not city_name:
        return False
    lower = city_name.lower()

    for c in GERMAN_CITY_LIST:
        if c in lower:
            return True
    for c in AUSTRIAN_CITIES:
        if c in lower:
            return True
    for c in GERMAN_CITY_ABBR:
        if lower.startswith(c.lower() + ","):
            return True
    import re

    if re.search(r", de$", lower) or re.search(r", at$", lower):
        return True
    return False


def judge_wednesday_region(wd: dict) -> dict:
    """Check if Wednesday audience data passes the region test.

    DE + AT combined >= WEDNESDAY_COUNTRY_MIN (35%).

    Returns {'pass': bool, 'reason': str}.
    """
    de_pct = wd.get("dePct", 0) or 0
    at_pct = wd.get("atPct", 0) or 0
    combined = de_pct + at_pct

    if combined < WEDNESDAY_COUNTRY_MIN:
        tc = wd.get("topCountry")
        top_code = tc.get("code", "?") if tc else "?"
        return {
            "pass": False,
            "reason": f"受众 DE+AT 仅 {combined}%<{WEDNESDAY_COUNTRY_MIN}%（#1={top_code}）",
        }

    top_city = wd.get("topCity")
    if not top_city or not is_german_city(top_city.get("name")):
        return {
            "pass": False,
            "reason": f"受众城市#1={top_city.get('name', '?') if top_city else '?'} 非德城",
        }

    return {"pass": True, "reason": ""}


def judge_gender(wd: dict, fans: int) -> dict:
    """Check if Wednesday audience gender data passes.

    Returns {'pass': bool, 'male_pct': float|None, 'reason': str}.
    """
    gender = wd.get("gender")
    if not gender:
        return {"pass": True, "male_pct": None, "reason": ""}

    male = gender["male"]
    max_male = GENDER_MALE_MAX_100K if fans > 100_000 else GENDER_MALE_MAX
    if male > max_male:
        return {
            "pass": False,
            "male_pct": male,
            "female_pct": gender["female"],
            "reason": f"男粉 {male}%>{max_male}%",
        }

    return {
        "pass": True,
        "male_pct": male,
        "female_pct": gender["female"],
        "reason": "",
    }


def save_cache(cache: dict) -> None:
    """Persist cache to disk."""
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


async def _wednesday_login(page, *, max_retries: int = 3) -> str | None:
    """Log into Wednesday and return an access token, or None on failure.

    Retries up to max_retries times with escalating delays (5s / 10s / 20s).
    """
    for attempt in range(1, max_retries + 1):
        try:
            await page.goto("https://user.wednesday.app/login",
                            wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            if "hq.wednesday.app" not in page.url:
                # Already logged in? Check cookie
                token = await _extract_token(page)
                if token:
                    return token

                # Wait for login form
                try:
                    await page.wait_for_selector(
                        'input[placeholder*="email"], input[id*="ember"]',
                        timeout=10000)
                except Exception:
                    pass
                await asyncio.sleep(2)

                form_exists = await page.evaluate("""() => {
                    const ins = document.querySelectorAll('input:not([type="hidden"])');
                    return ins.length >= 2;
                }""")

                if not form_exists:
                    if attempt < max_retries:
                        print(f"   ⚠️ Wednesday 登录表单未加载，重试 {attempt}/{max_retries}...")
                        await asyncio.sleep(attempt * 5)
                        continue
                    print("   ⚠️ Wednesday 登录表单未加载，放弃")
                    return None

                await page.fill('input[placeholder*="email"]', WEDNESDAY_EMAIL)
                await page.fill('input[placeholder*="password"]', WEDNESDAY_PASSWORD)
                await page.click('button:has-text("Log in")')
                await asyncio.sleep(5)

                for _ in range(6):
                    if "hq.wednesday.app" in page.url:
                        break
                    await asyncio.sleep(2)

                if "hq.wednesday.app" not in page.url:
                    if attempt < max_retries:
                        print(f"   ⚠️ Wednesday 登录跳转失败，重试 {attempt}/{max_retries}...")
                        await asyncio.sleep(attempt * 5)
                        continue
                    print("   ⚠️ Wednesday 登录失败，放弃")
                    return None

            # Extract token
            token = await _extract_token(page)
            if token:
                return token

            if attempt < max_retries:
                print(f"   ⚠️ 无法提取 Wednesday token，重试 {attempt}/{max_retries}...")
                await asyncio.sleep(attempt * 5)
            else:
                print("   ⚠️ 无法提取 Wednesday token，放弃")

        except Exception as e:
            if attempt < max_retries:
                print(f"   ⚠️ Wednesday 登录异常 ({e})，重试 {attempt}/{max_retries}...")
                await asyncio.sleep(attempt * 5)
            else:
                print(f"   ⚠️ Wednesday 登录异常 ({e})，放弃")

    return None


async def _extract_token(page) -> str | None:
    """Extract the Bearer token from Wednesday's auth cookie."""
    try:
        return await page.evaluate("""() => {
            const m = document.cookie.match(/wednesday-production-auth=([^;]+)/);
            if (!m) return null;
            return JSON.parse(decodeURIComponent(m[1])).authenticated.access_token;
        }""")
    except Exception:
        return None


async def live_lookup(usernames: list[str], *, timeout: int = 60000) -> dict[str, dict]:
    """Query Wednesday API directly via Playwright for usernames not in cache.

    Returns a dict mapping username → wednesday_detail dict.
    Gracefully returns empty dict on failure (no playwright, login fail, quota, etc).
    """
    if not usernames:
        return {}

    results: dict[str, dict] = {}

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠️ playwright 未安装，跳过 Wednesday 实时查询")
        return {}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Login (with 3 retries)
                token = await _wednesday_login(page, max_retries=3)

                if not token:
                    # Login failed after all retries → mark all as needs-review
                    print("   ⚠️ Wednesday 登录失败，所有用户标记为需人工复查")
                    for username in usernames:
                        results[username] = {
                            "found": False,
                            "_wednesdayFailed": True,
                            "_reason": "Wednesday 登录失败需人工复查",
                        }
                    return results

                # Query all usernames in ONE page.evaluate with Promise.all
                print(f"   🔍 并发查询 {len(usernames)} 人...")
                batch_results = await page.evaluate("""async ({usernames, token}) => {
                    // Reusable search logic for a single username
                    async function searchOne(username) {
                        try {
                            const uLower = username.toLowerCase();
                            const baseBody = { filters: [], audience_filters: [], social_media_matching_operator: 'or', should_save: false, track_hits_results: 10000, score_model: 'default' };

                            // Try exact social_media.username match first (fast, precise)
                            let sr = await fetch('https://facade.upfluence.co/api/v1/matches?page=1&per_page=50&offset=0', {
                                method: 'POST',
                                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'application/json' },
                                body: JSON.stringify({ ...baseBody, criterias: [{ value: '@' + username, weight: 1, field: 'social_media.username', type: 'should' }] }),
                            });
                            let sd = await sr.json();
                            let infs = sd.influencers || [];

                            // Fallback: if no hits, try broad 'all' field search
                            if (infs.length === 0) {
                                sr = await fetch('https://facade.upfluence.co/api/v1/matches?page=1&per_page=50&offset=0', {
                                    method: 'POST',
                                    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'application/json' },
                                    body: JSON.stringify({ ...baseBody, criterias: [{ value: username, weight: 1, field: 'all', type: 'should' }] }),
                                });
                                sd = await sr.json();
                                infs = sd.influencers || [];
                            }

                            // Fast path: match from search results' embedded instagrams/tiktoks
                            for (const inf of infs) {
                                for (const ig of (inf.instagrams || [])) {
                                    if (ig.username?.toLowerCase() === uLower) {
                                        return await fetchAudience(inf.id || inf.influencer_id, uLower, 'IG', token);
                                    }
                                }
                                for (const tt of (inf.tiktoks || [])) {
                                    if (tt.username?.toLowerCase() === uLower) {
                                        return await fetchAudience(inf.id || inf.influencer_id, uLower, 'TT', token);
                                    }
                                }
                            }

                            // Slow path: fetch full profile for top results (up to 20)
                            for (const inf of infs.slice(0, 20)) {
                                try {
                                    const dr = await fetch(`https://facade.upfluence.co/api/v1/influencers/${inf.id || inf.influencer_id}`, {
                                        headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
                                    });
                                    const dd = await dr.json();
                                    for (const ig of (dd.instagrams || [])) {
                                        if (ig.username?.toLowerCase() === uLower) return extractAudience(ig, inf.name, 'IG');
                                    }
                                    for (const tt of (dd.tiktoks || [])) {
                                        if (tt.username?.toLowerCase() === uLower) return extractAudience(tt, inf.name, 'TT');
                                    }
                                } catch (e) { /* try next */ }
                            }

                            return { found: false };
                        } catch (e) {
                            return { found: false, error: e.message };
                        }
                    }

                    async function fetchAudience(infId, uLower, via, token) {
                        try {
                            const dr = await fetch(`https://facade.upfluence.co/api/v1/influencers/${infId}`, {
                                headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
                            });
                            const dd = await dr.json();
                            for (const ig of (dd.instagrams || [])) {
                                if (ig.username?.toLowerCase() === uLower) return extractAudience(ig, dd.name, 'IG');
                            }
                            for (const tt of (dd.tiktoks || [])) {
                                if (tt.username?.toLowerCase() === uLower) return extractAudience(tt, dd.name, 'TT');
                            }
                            return { found: true, gender: null, topCountry: null, topCity: null, dePct: 0, atPct: 0, _matchedName: dd.name, _matchedVia: via };
                        } catch (e) {
                            return { found: true, gender: null, topCountry: null, topCity: null, dePct: 0, atPct: 0, _matchedName: null, _matchedVia: via };
                        }
                    }

                    function extractAudience(med, name, via) {
                        const aud = med?.audience || {};
                        const g = aud?.gender_image_extractor?.values || null;
                        const c = aud?.country_last_picture?.values || null;
                        const ci = aud?.city_last_picture?.values || null;
                        let tc = null, tcp = 0; if (c) Object.entries(c).forEach(([k, v]) => { if (v > tcp) { tcp = v; tc = k; } });
                        let tci = null, tcip = 0; if (ci) Object.entries(ci).forEach(([k, v]) => { if (v > tcip) { tcip = v; tci = k; } });
                        let dePct = 0, atPct = 0;
                        if (c) {
                            if (c.DE) dePct = Math.round(c.DE * 10000) / 100;
                            if (c.AT) atPct = Math.round(c.AT * 10000) / 100;
                        }
                        return {
                            found: true,
                            gender: g ? { female: Math.round(g.female * 10000) / 100, male: Math.round(g.male * 10000) / 100 } : null,
                            topCountry: tc ? { code: tc, pct: Math.round(tcp * 10000) / 100 } : null,
                            topCity: tci ? { name: tci, pct: Math.round(tcip * 10000) / 100 } : null,
                            dePct: dePct, atPct: atPct,
                            _matchedName: name, _matchedVia: via,
                        };
                    }

                    // Run all searches in parallel
                    const results = {};
                    await Promise.all(usernames.map(async (username) => {
                        results[username] = await searchOne(username);
                    }));
                    return results;
                }""", {"usernames": usernames, "token": token})

                # Process results
                for username in usernames:
                    result = batch_results.get(username, {"found": False})
                    results[username] = result
                    if result.get("found"):
                        g = result.get("gender")
                        g_str = f"女{g['female']}%" if g else "?"
                        de_pct = result.get("dePct", 0) or 0
                        at_pct = result.get("atPct", 0) or 0
                        combined = de_pct + at_pct
                        c_str = f" DE+AT={combined}%"
                        via = result.get("_matchedVia", "?")
                        print(f"  ✅ {username}: {g_str}{c_str} ({via})")
                    else:
                        print(f"  ❌ {username}: 无匹配")

                # Save updated cache (stamp _lastAttempt on all entries for TTL)
                now_ts = time.time()
                for r in results.values():
                    if isinstance(r, dict) and "_lastAttempt" not in r:
                        r["_lastAttempt"] = now_ts
                cache = load_wednesday_cache()
                cache.update(results)
                save_cache(cache)
                found_count = sum(1 for r in results.values() if r.get("found"))
                fail_count = sum(1 for r in results.values() if r.get("_wednesdayFailed"))
                print(f"   💾 缓存已更新（+{found_count} 人{f'，{fail_count} 登录失败' if fail_count else ''}）")

            finally:
                await browser.close()

    except Exception as e:
        print(f"   ⚠️ Wednesday 实时查询异常: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════
#  已废弃 — v0.7.1 移除的 Wednesday 关键词发现功能
#  仅保留作为代码参考，不用于达人获取
# ═══════════════════════════════════════════════════════════════════

async def search_keyword(
    keyword: str,
    *,
    page: int = 1,
    per_page: int = 50,
    audience_filters: list[dict] | None = None,
) -> list[dict]:
    """Search Wednesday for influencers matching a KEYWORD (not exact username).

    Uses Playwright for auth (same as live_lookup), but calls /api/v1/matches
    with keyword criteria. Returns audience data at ZERO view cost.

    Args:
        keyword: Search term (e.g. "fashion", "mode blogger")
        page: Page number (1-indexed)
        per_page: Results per page
        audience_filters: Optional pre-filters (e.g. country=DE)

    Returns:
        List of influencer dicts, each containing:
        id, name, username, followers, gender, topCountry, topCity,
        instagrams, tiktoks, score, categories, tags, _keyword
    """
    if audience_filters is None:
        audience_filters = []

    results: list[dict] = []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("   ⚠️ playwright 未安装，跳过 Wednesday 关键词搜索")
        return results

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Login flow (same as live_lookup)
                await page.goto("https://user.wednesday.app/login",
                                wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(5)

                if "hq.wednesday.app" not in page.url:
                    try:
                        await page.wait_for_selector(
                            'input[placeholder*="email"], input[id*="ember"]',
                            timeout=10000)
                    except Exception:
                        pass
                    await asyncio.sleep(2)

                    form_exists = await page.evaluate("""() => {
                        const ins = document.querySelectorAll('input:not([type="hidden"])');
                        return ins.length >= 2;
                    }""")
                    if not form_exists:
                        return results
                    await page.fill('input[placeholder*="email"]', WEDNESDAY_EMAIL)
                    await page.fill('input[placeholder*="password"]', WEDNESDAY_PASSWORD)
                    await page.click('button:has-text("Log in")')
                    await asyncio.sleep(5)
                    for _ in range(6):
                        if "hq.wednesday.app" in page.url:
                            break
                        await asyncio.sleep(2)
                    if "hq.wednesday.app" not in page.url:
                        return results

                # Extract token
                token = await page.evaluate("""() => {
                    const m = document.cookie.match(/wednesday-production-auth=([^;]+)/);
                    if (!m) return null;
                    return JSON.parse(decodeURIComponent(m[1])).authenticated.access_token;
                }""")
                if not token:
                    return results

                # Build search body with keyword criteria
                offset = (page - 1) * per_page
                body = {
                    "criterias": [{
                        "value": keyword,
                        "weight": 1,
                        "field": "all",
                        "type": "should",
                    }],
                    "filters": [],
                    "audience_filters": audience_filters,
                    "social_media_matching_operator": "or",
                    "should_save": False,
                    "track_hits_results": per_page,
                    "score_model": "default",
                }

                # Execute search
                result = await page.evaluate("""async ({body, per_page, offset, token}) => {
                    const sr = await fetch(`https://facade.upfluence.co/api/v1/matches?page=1&per_page=${per_page}&offset=${offset}`, {
                        method: 'POST',
                        headers: {
                            Authorization: `Bearer ${token}`,
                            'Content-Type': 'application/json',
                            Accept: 'application/json',
                        },
                        body: JSON.stringify(body),
                    });
                    const data = await sr.json();
                    const infs = data.influencers || [];
                    return infs.map(inf => ({
                        id: inf.id || inf.influencer_id,
                        name: inf.name,
                        username: inf.username,
                        followers: inf.followers || inf.followers_count,
                        score: inf.score || inf._score,
                        gender: inf.gender || inf.audience_gender || null,
                        topCountry: inf.topCountry || inf.audience_top_country || null,
                        topCity: inf.topCity || inf.audience_top_city || null,
                        instagrams: inf.instagrams?.map(ig => ({username: ig.username, followers: ig.followers})) || [],
                        tiktoks: inf.tiktoks?.map(tt => ({username: tt.username, followers: tt.followers})) || [],
                        categories: inf.categories || [],
                        tags: inf.tags || [],
                        _keyword: null,
                    }));
                }""", {"body": body, "per_page": per_page, "offset": offset, "token": token})

                # Tag each result with the keyword that found it
                for r in result:
                    r["_keyword"] = keyword

                results = result

            finally:
                await browser.close()

    except Exception as e:
        print(f"   ⚠️ Wednesday 搜索异常 ({keyword}): {e}")

    return results


async def search_all_keywords(
    keywords: list[str],
    *,
    per_page: int = 50,
    max_pages: int = 3,
    audience_filters: list[dict] | None = None,
) -> list[dict]:
    """Search Wednesday for multiple keywords and return deduplicated results.

    Args:
        keywords: List of search terms
        per_page: Results per page per keyword
        max_pages: Max pages per keyword
        audience_filters: Optional audience pre-filters

    Returns:
        Deduplicated list of influencers, sorted by score descending.
    """
    seen_ids: set[int] = set()
    seen_usernames: set[str] = set()
    all_results: list[dict] = []

    for kw in keywords:
        sys.stdout.write(f"  🔍 \"{kw}\" ... ")
        sys.stdout.flush()

        keyword_results: list[dict] = []
        for p in range(1, max_pages + 1):
            page_results = await search_keyword(
                kw, page=p, per_page=per_page,
                audience_filters=audience_filters,
            )
            if not page_results:
                break
            keyword_results.extend(page_results)

        new_count = 0
        for inf in keyword_results:
            uid = inf.get("id")
            uname = (inf.get("username") or "").lower()
            if uid and uid in seen_ids:
                continue
            if uname and uname in seen_usernames:
                continue
            if uid:
                seen_ids.add(uid)
            if uname:
                seen_usernames.add(uname)
            all_results.append(inf)
            new_count += 1

        print(f"{len(keyword_results)} 条 ({new_count} 新)")
        await asyncio.sleep(0.5)  # Rate limit between keywords

    # Sort by score descending
    all_results.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)
    return all_results
