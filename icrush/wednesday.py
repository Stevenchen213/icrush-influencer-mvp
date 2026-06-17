"""Wednesday / Upfluence cache operations and judgment functions."""

import asyncio
import json
import sys

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
        return {"found": False}

    # Must have at least one of gender / country / city to be "usable"
    has_data = entry.get("gender") or entry.get("topCountry") or entry.get("topCity")
    if not has_data:
        return {"found": False}

    return {
        "found": True,
        "gender": entry.get("gender"),
        "topCountry": entry.get("topCountry"),
        "topCity": entry.get("topCity"),
    }


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

    Returns {'pass': bool, 'reason': str}.
    """
    tc = wd.get("topCountry")
    if not tc or tc.get("code") != "DE":
        return {
            "pass": False,
            "reason": f"受众国家#1={tc.get('code', '?') if tc else '?'} 非 DE",
        }
    if tc.get("pct", 0) < WEDNESDAY_COUNTRY_MIN:
        return {
            "pass": False,
            "reason": f"受众 DE 仅 {tc['pct']}%<{WEDNESDAY_COUNTRY_MIN}%",
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
                # Login
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
                        print("   ⚠️ Wednesday 登录表单未加载，跳过实时查询")
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
                        print("   ⚠️ Wednesday 登录失败，跳过实时查询")
                        return results

                # Extract token
                token = await page.evaluate("""() => {
                    const m = document.cookie.match(/wednesday-production-auth=([^;]+)/);
                    if (!m) return null;
                    return JSON.parse(decodeURIComponent(m[1])).authenticated.access_token;
                }""")

                if not token:
                    print("   ⚠️ 无法提取 Wednesday token")
                    return results

                # Query each username
                for username in usernames:
                    sys.stdout.write(f"  → Wednesday 实时查询 {username} ... ")
                    sys.stdout.flush()
                    try:
                        result = await page.evaluate("""async ({username, token}) => {
                            const sr = await fetch('https://facade.upfluence.co/api/v1/matches?page=1&per_page=10&offset=0', {
                                method: 'POST',
                                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'application/json' },
                                body: JSON.stringify({ current_list: '389827', criterias: [{ value: username, weight: 1, field: 'all', type: 'should' }], filters: [], audience_filters: [], social_media_matching_operator: 'or', should_save: false, track_hits_results: 10000, score_model: 'default' }),
                            });
                            const sd = await sr.json();
                            const infs = sd.influencers || [];

                            const candidates = infs.slice(0, 5);
                            for (const inf of candidates) {
                                try {
                                    const dr = await fetch(`https://facade.upfluence.co/api/v1/influencers/${inf.id || inf.influencer_id}`, {
                                        headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
                                    });
                                    const dd = await dr.json();
                                    const igs = dd.instagrams || [];
                                    const tts = dd.tiktoks || [];

                                    const igMatch = igs.find(m => m.username?.toLowerCase() === username.toLowerCase());
                                    const ttMatch = tts.find(m => m.username?.toLowerCase() === username.toLowerCase());

                                    if (igMatch || ttMatch) {
                                        const med = igMatch || ttMatch;
                                        const aud = med?.audience || {};
                                        const g = aud?.gender_image_extractor?.values || null;
                                        const c = aud?.country_last_picture?.values || null;
                                        const ci = aud?.city_last_picture?.values || null;
                                        let tc = null, tcp = 0; if (c) Object.entries(c).forEach(([k, v]) => { if (v > tcp) { tcp = v; tc = k; } });
                                        let tci = null, tcip = 0; if (ci) Object.entries(ci).forEach(([k, v]) => { if (v > tcip) { tcip = v; tci = k; } });
                                        return {
                                            found: true,
                                            gender: g ? { female: Math.round(g.female * 10000) / 100, male: Math.round(g.male * 10000) / 100 } : null,
                                            topCountry: tc ? { code: tc, pct: Math.round(tcp * 10000) / 100 } : null,
                                            topCity: tci ? { name: tci, pct: Math.round(tcip * 10000) / 100 } : null,
                                            _matchedName: inf.name,
                                            _matchedVia: igMatch ? 'IG' : 'TT',
                                        };
                                    }
                                } catch (e) { /* skip */ }
                            }
                            return { found: false };
                        }""", {"username": username, "token": token})

                        results[username] = result
                        if result.get("found"):
                            g = result.get("gender")
                            g_str = f"女{g['female']}%" if g else "?"
                            tc = result.get("topCountry")
                            c_str = f" {tc['code']} {tc['pct']}%" if tc else ""
                            via = result.get("_matchedVia", "?")
                            print(f"✅ {g_str}{c_str} ({via})")
                        else:
                            print("❌ 无匹配")

                    except Exception as e:
                        results[username] = {"found": False, "error": str(e)}
                        print(f"⚠️ {e}")

                # Save updated cache
                cache = load_wednesday_cache()
                cache.update(results)
                save_cache(cache)
                print(f"   💾 缓存已更新（+{sum(1 for r in results.values() if r.get('found'))} 人）")

            finally:
                await browser.close()

    except Exception as e:
        print(f"   ⚠️ Wednesday 实时查询异常: {e}")

    return results


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
                    "current_list": "389827",
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
