#!/usr/bin/env python3
"""Refresh Wednesday cache via Playwright browser automation.

Usage:
    python scripts/refresh_wednesday_cache.py username1 username2 ...
    python scripts/refresh_wednesday_cache.py data/input.txt
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

# Fix Unicode output on Windows GBK terminals
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

# Add project root to path for icrush imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from icrush.config import CACHE_FILE, WEDNESDAY_EMAIL, WEDNESDAY_PASSWORD


def load_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def extract_usernames(filepath: str) -> list[str]:
    raw = Path(filepath).read_text(encoding="utf-8")
    users: list[str] = []
    for line in raw.split("\n"):
        u = line.strip()
        if not u or u.startswith("#"):
            continue
        m = re.search(r"tiktok\.com/@([\w._-]+)", u)
        if m:
            users.append(m.group(1))
            continue
        m = re.search(r"instagram\.com/([\w._-]+)", u)
        if m:
            seg = m.group(1)
            if seg.lower() in ("p", "reel", "reels", "tv", "stories", "explore"):
                continue
            users.append(seg.rstrip("/"))
    return list(dict.fromkeys(users))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Wednesday audience data cache")
    parser.add_argument("usernames", nargs="*",
                        help="One or more usernames, or path to input.txt")
    args = parser.parse_args()

    if not args.usernames:
        print("用法: python scripts/refresh_wednesday_cache.py <usernames...>")
        print("  或: python scripts/refresh_wednesday_cache.py data/input.txt")
        sys.exit(1)

    # Resolve usernames
    users: list[str] = []
    for arg in args.usernames:
        if arg.endswith(".txt"):
            users.extend(extract_usernames(arg))
        else:
            users.append(arg)
    users = list(dict.fromkeys(users))

    print(f"🔍 准备查询 {len(users)} 个达人: {', '.join(users)}")

    cache = load_cache()
    to_query = [u for u in users if not (
        cache.get(u, {}).get("found") and (
            cache[u].get("gender") or cache[u].get("topCountry")
        )
    )]

    if not to_query:
        print("✅ 所有达人已缓存，无需查询")
        return

    print(f"   需查询 {len(to_query)} 人（{len(users) - len(to_query)} 人已有缓存）")

    # Start Playwright
    print("\n🚀 启动无头浏览器...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Login
            print("🔑 登录 Wednesday...")
            await page.goto("https://user.wednesday.app/login",
                            wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)

            if "hq.wednesday.app" not in page.url:
                # Wait for form
                try:
                    await page.wait_for_selector(
                        'input[placeholder*="email"], input[id*="ember"]',
                        timeout=10000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)

                # Check form exists
                form_exists = await page.evaluate("""() => {
                    const ins = document.querySelectorAll('input:not([type="hidden"])');
                    return ins.length >= 2;
                }""")

                if not form_exists:
                    print("❌ 登录表单未加载，可能是网络问题")
                    print(f"   页面 URL: {page.url}")
                    await browser.close()
                    sys.exit(1)

                await page.fill('input[placeholder*="email"]', WEDNESDAY_EMAIL)
                await page.fill('input[placeholder*="password"]', WEDNESDAY_PASSWORD)
                await page.click('button:has-text("Log in")')
                print("   ℹ️  等待登录跳转...")
                await page.wait_for_timeout(5000)

                for _ in range(6):
                    if "hq.wednesday.app" in page.url:
                        break
                    await page.wait_for_timeout(2000)

                if "hq.wednesday.app" not in page.url:
                    print(f"❌ 登录失败，URL: {page.url}")
                    await browser.close()
                    sys.exit(1)

            print("   ✅ 登录成功")

            # Extract token from cookie
            token = await page.evaluate("""() => {
                const m = document.cookie.match(/wednesday-production-auth=([^;]+)/);
                if (!m) return null;
                return JSON.parse(decodeURIComponent(m[1])).authenticated.access_token;
            }""")

            if not token:
                print("❌ 无法提取 token")
                await browser.close()
                sys.exit(1)

            # Query each user
            print(f"\n🔎 查询 {len(to_query)} 个达人...")
            for username in to_query:
                sys.stdout.write(f"  → {username} ... ")
                sys.stdout.flush()
                try:
                    # This JS must be preserved verbatim from Node version
                    result = await page.evaluate("""async ({username, token}) => {
                        // Search
                        const sr = await fetch('https://facade.upfluence.co/api/v1/matches?page=1&per_page=10&offset=0', {
                            method: 'POST',
                            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'application/json' },
                            body: JSON.stringify({ current_list: '389827', criterias: [{ value: username, weight: 1, field: 'all', type: 'should' }], filters: [], audience_filters: [], social_media_matching_operator: 'or', should_save: false, track_hits_results: 10000, score_model: 'default' }),
                        });
                        const sd = await sr.json();
                        const infs = sd.influencers || [];

                        // Strategy: fetch detail for each candidate, compare exact IG/TT username
                        const candidates = infs.slice(0, 5);
                        for (const inf of candidates) {
                            try {
                                const dr = await fetch(`https://facade.upfluence.co/api/v1/influencers/${inf.id || inf.influencer_id}`, {
                                    headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
                                });
                                const dd = await dr.json();
                                const igs = dd.instagrams || [];
                                const tts = dd.tiktoks || [];

                                // Exact match on social media username
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
                            } catch (e) { /* skip this candidate */ }
                        }
                        return { found: false, _debug: { searched: candidates.length } };
                    }""", {"username": username, "token": token})

                    cache[username] = result
                    if result.get("found"):
                        g = result.get("gender")
                        g_str = f"女{g['female']}%" if g else "无性别"
                        tc = result.get("topCountry")
                        c_str = f" {tc['code']} {tc['pct']}%" if tc else ""
                        via = result.get("_matchedVia", "?")
                        name = result.get("_matchedName", "?")
                        print(f"✅ {g_str}{c_str} ({via}:{name})")
                    else:
                        print("❌ 无匹配")

                except Exception as e:
                    cache[username] = {"found": False, "error": str(e)}
                    print(f"⚠️ 异常: {e}")

            save_cache(cache)
            print(f"\n💾 缓存已保存: {CACHE_FILE}")
            print(f"   共 {len(cache)} 条记录")

        finally:
            await browser.close()


def main_cli() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
