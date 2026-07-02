"""Re-run STAGE 1 short-circuit on Feishu review table entries for 7/2.
Delete accounts that now fail with v0.9.2 code.

Usage:
  python scripts/rejudge_review_table.py          # dry-run (show what would be deleted)
  python scripts/rejudge_review_table.py --apply  # actually delete from Feishu
"""
import asyncio, sys, os, re, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx
from icrush.config import FEISHU_REVIEW_BASE_ID, FEISHU_REVIEW_TABLE_ID
from icrush.judges import short_circuit
from icrush.apify_cache import get_cached, cache_key, is_cache_enabled

APPLY = "--apply" in sys.argv

if not FEISHU_REVIEW_TABLE_ID:
    print("❌ FEISHU_REVIEW_TABLE_ID not set in .env")
    sys.exit(1)


# ── Feishu helpers ──

def _get_token() -> str:
    from icrush.feishu import _get_feishu_token
    return _get_feishu_token()


def _headers(tkn: str) -> dict:
    return {"Authorization": f"Bearer {tkn}", "Content-Type": "application/json"}


def _api_url(path: str) -> str:
    return f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_REVIEW_BASE_ID}/tables/{FEISHU_REVIEW_TABLE_ID}/{path}"


async def fetch_review_records(client: httpx.AsyncClient, headers: dict) -> list[dict]:
    """Fetch all records from the review table, filtering for 7/2 batch."""
    records = []
    page_token = ""
    while True:
        url = _api_url("records") + "?page_size=500"
        if page_token:
            url += f"&page_token={page_token}"
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"❌ Fetch failed: {resp.status_code} {resp.text[:200]}")
            break
        data = resp.json()
        items = data.get("data", {}).get("items", [])
        for item in items:
            fields = item.get("fields", {})
            batch_id = fields.get("批次ID", "")
            if batch_id and batch_id.startswith("2026-07-02"):
                records.append({
                    "record_id": item.get("record_id"),
                    "username": fields.get("用户名", ""),
                    "platform": fields.get("平台", "IG"),
                    "batch_id": batch_id,
                    "verdict": fields.get("判定结果", ""),
                    "reason": fields.get("原因", ""),
                })

        has_more = data.get("data", {}).get("has_more", False)
        page_token = data.get("data", {}).get("page_token", "")
        if not has_more or not page_token:
            break
    return records


async def delete_record(client: httpx.AsyncClient, headers: dict, record_id: str, username: str) -> bool:
    """Delete a single record from the review table."""
    url = _api_url(f"records/{record_id}")
    resp = await client.delete(url, headers=headers)
    if resp.status_code == 200:
        print(f"  🗑️  Deleted: {username}")
        return True
    else:
        print(f"  ❌ Delete failed for {username}: {resp.status_code} {resp.text[:150]}")
        return False


async def scrape_ig_profile(username: str) -> dict | None:
    """Quick Playwright scrape of IG profile meta."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(f"https://www.instagram.com/{username}/",
                            wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(4000)
            try:
                await page.wait_for_selector('meta[name="description"]', timeout=6000)
            except Exception:
                pass

            meta = await page.evaluate("""() => {
                const m = document.querySelector('meta[name="description"]');
                return m ? m.getAttribute('content') : '';
            }""")
            if not meta or len(meta) < 20:
                return None

            followers = 0
            fm = re.search(r"([\d.,]+[KkMm]?)\s*(?:位粉丝|Followers?)", meta)
            if fm:
                raw = fm.group(1).strip().replace(",", "")
                m2 = re.match(r"([\d.]+)\s*([KkMm]?)", raw)
                if m2:
                    num = float(m2.group(1))
                    unit = m2.group(2).upper()
                    followers = int(num * 1_000) if unit == "K" else (int(num * 1_000_000) if unit == "M" else int(num))

            posts = 0
            pm = re.search(r"(\d[\d,]*)\s*(?:篇帖子|Posts?)", meta)
            if pm:
                posts = int(pm.group(1).replace(",", ""))

            title = await page.title()
            full_name = username
            tm = re.match(r"(.+?) \(@", title)
            if tm:
                full_name = tm.group(1).strip()

            nm = re.search(r"(?:Instagram 用户 |on Instagram: )(.+?) \(@", meta)
            if nm:
                full_name = nm.group(1).strip()

            bio = ""
            bm = re.search(r'\s[："]([^"]+)"$', meta)
            if bm:
                bio = bm.group(1).replace("\\n", "\n")

            return {
                "name": username,
                "fullName": full_name,
                "fans": followers,
                "posts": posts,
                "bio": bio,
                "category": None,
                "private": False,
                "latestPosts": [],
            }
        finally:
            await browser.close()


async def main():
    tkn = _get_token()
    headers = _headers(tkn)

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Fetch records
        print(f"📋 Fetching review table records for 2026-07-02...")
        records = await fetch_review_records(client, headers)
        print(f"   Found {len(records)} records\n")

        if not records:
            return

        usernames = list(dict.fromkeys(r["username"] for r in records))
        print(f"   Unique usernames: {len(usernames)}")

        # 2. For each username, get profile and run short_circuit
        to_delete = []
        keep = []

        for i, username in enumerate(usernames):
            print(f"\n[{i+1}/{len(usernames)}] 🔍 @{username}")

            profile = None
            if is_cache_enabled():
                profile = get_cached(cache_key("profile", "IG", username))

            if profile:
                fc = profile.get('fans', 0)
                pc = profile.get('posts', 0)
                print(f"   [cache] {fc:,} fans, {pc} posts")
                p = {
                    "name": profile.get("name", username),
                    "fullName": profile.get("fullName", ""),
                    "fans": fc,
                    "posts": pc,
                    "bio": profile.get("bio", ""),
                    "category": profile.get("category"),
                    "private": profile.get("private", False),
                    "latestPosts": profile.get("latestPosts", []),
                }
            else:
                print(f"   [scraping] Playwright...")
                profile = await scrape_ig_profile(username)
                if not profile:
                    print(f"   ❌ Could not scrape, skipping")
                    keep.append(username)
                    continue
                p = profile

            sc = short_circuit("IG", p)
            if sc["fail"]:
                print(f"   🛑 FAIL: {sc['reason']}")
                for rec in records:
                    if rec["username"] == username:
                        to_delete.append((rec["record_id"], username, sc["reason"]))
            else:
                print(f"   ✅ PASS")
                keep.append(username)

        # 3. Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY: {len(to_delete)} to DELETE, {len(keep)} to KEEP")
        print(f"{'='*60}")
        if to_delete:
            print(f"\n🚫 To delete:")
            for rid, uname, reason in to_delete:
                print(f"   {uname} → {reason}")

        if not APPLY:
            print(f"\n⚠️  DRY RUN — use --apply to actually delete from Feishu")
            return

        # 4. Delete
        if to_delete:
            print(f"\n🗑️  Deleting {len(to_delete)} records...")
            deleted = 0
            failed = 0
            for rid, uname, reason in to_delete:
                if await delete_record(client, headers, rid, uname):
                    deleted += 1
                else:
                    failed += 1
                await asyncio.sleep(0.3)
            print(f"\n   Done: {deleted} deleted, {failed} failed")
        else:
            print("\n   Nothing to delete.")


if __name__ == "__main__":
    asyncio.run(main())
