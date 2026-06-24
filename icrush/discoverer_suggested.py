#!/usr/bin/env python3
"""Enhanced suggested discoverer: seed from known accounts, dedup against DB.

Usage:
  python scripts/discover.py --method suggested --run
  # Uses seeds from known accounts, dedups via Lambda API

  python scripts/discover.py --method suggested --seeds URL1 URL2 --run
  # Explicit seeds (overrides auto-seed from known accounts)
"""
import asyncio
import glob
import json
import re
import sys
import time
from pathlib import Path

from DrissionPage import ChromiumPage

from icrush.config import DATA_DIR
from icrush.dedup import check_dedup

# ============================================================
# Defaults
# ============================================================

COOKIE_FILE = DATA_DIR / "ig_cookies.json"
DEFAULT_OUTPUT = DATA_DIR / "input_suggested.txt"
PAGE_LOAD_TIMEOUT = 30
SCROLL_WAIT = 2

SUGGESTED_HEADINGS = [
    "\u4e3a\u4f60\u63a8\u8350",
    "Suggested for you",
    "Suggested",
]


# ============================================================
# Load known accounts from project data
# ============================================================

def load_known_accounts() -> set[str]:
    """Load all known IG usernames from input files + comments + profiles."""
    known: set[str] = set()

    # 1. All input_*.txt files
    for f in sorted(glob.glob(str(DATA_DIR / "input_*.txt"))):
        text = Path(f).read_text(encoding="utf-8")
        matches = re.findall(r"instagram\.com/([^/?\s]+)", text)
        known.update(m.lower() for m in matches)

    # 2. ig_profiles.json
    pf = DATA_DIR / "ig_profiles.json"
    if pf.exists():
        try:
            data = json.loads(pf.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if item.get("username"):
                        known.add(item["username"].lower())
            elif isinstance(data, dict):
                known.update(k.lower() for k in data)
        except Exception:
            pass

    # 3. ig_comments.json
    cf = DATA_DIR / "ig_comments.json"
    if cf.exists():
        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
            for item in data if isinstance(data, list) else []:
                for key in ["ownerUsername", "username"]:
                    if item.get(key):
                        known.add(item[key].lower())
        except Exception:
            pass

    # 4. discovery_history.json
    hf = DATA_DIR / "discovery_history.json"
    if hf.exists():
        try:
            data = json.loads(hf.read_text(encoding="utf-8"))
            known.update(u.lower() for u in data.get("processed_usernames", []))
        except Exception:
            pass

    return known


# ============================================================
# Internals
# ============================================================

def _save_cookies(page: ChromiumPage, path: Path):
    """Persist browser cookies to disk."""
    cookies = page.cookies()
    path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [Cookie] saved {len(cookies)} cookies to {path}")


def _load_cookies(path: Path) -> list | None:
    """Load cookies from disk if available."""
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"  [Cookie] loaded {len(data)} cookies from {path}")
        return data
    print("  [Cookie] no cookie file found, need manual login")
    return None


def _extract_accounts(page: ChromiumPage) -> list[str]:
    """Extract suggested account usernames from the current profile page.

    Uses three fallback strategies:
      1. Find section heading (e.g. "Suggested for you") and traverse parent.
      2. Find containers via aria-label attributes.
      3. Filter all user-profile links on the page.

    Returns a deduplicated list of Instagram usernames.
    """
    seen: set[str] = set()
    accounts: list[str] = []

    # -- Strategy 1: heading-based
    for heading_text in SUGGESTED_HEADINGS:
        try:
            heading = page.ele(f"tag:h2@@text():{heading_text}", timeout=3)
            if heading:
                print(f"  [locate] found heading: {heading_text}")
                section = heading.parent()
                links = section.eles("tag:a@@href:^/")
                if not links:
                    section = heading.parent(2)
                    links = section.eles("tag:a@@href:^/")
                for link in links:
                    href = link.attr("href")
                    if not href or href.startswith(("/explore/", "/accounts/")):
                        continue
                    username = href.strip("/").split("/")[0]
                    if username and username not in seen and "/" not in username and len(username) <= 30:
                        seen.add(username)
                        accounts.append(username)
                if accounts:
                    return accounts
        except Exception:
            continue

    # -- Strategy 2: attribute-based containers
    for attr_val in ["suggested", "recommended", "follow"]:
        for sel in [
            f'div[aria-label*="{attr_val}" i]',
            f'section[aria-label*="{attr_val}" i]',
        ]:
            try:
                container = page.ele(sel, timeout=2)
                if container:
                    links = container.eles("tag:a@@href:^/")
                    for link in links:
                        href = link.attr("href")
                        if not href or href.startswith(("/explore/", "/accounts/")):
                            continue
                        username = href.strip("/").split("/")[0]
                        if username and username not in seen and "/" not in username and len(username) <= 30:
                            seen.add(username)
                            accounts.append(username)
            except Exception:
                continue

    # -- Strategy 3: blanket filter
    if not accounts:
        print("  [locate] falling back to blanket link filter...")
        all_links = page.eles("tag:a@@href:^/")
        for link in all_links:
            href = link.attr("href")
            if not href:
                continue
            if (href.startswith(("/explore/", "/accounts/", "/p/"))
                    or href == "/" or "/" not in href.strip("/")):
                continue
            username = href.strip("/").split("/")[0]
            if not username or username in seen or len(username) > 30:
                continue
            seen.add(username)
            accounts.append(username)

    return accounts


def _scrape_seed_suggested(
    seed_url: str,
    headless: bool = False,
) -> list[str]:
    """Open one seed profile page and return its suggested account usernames.

    Launches Chrome, handles login via cookie persistence, scrolls to trigger
    lazy-load, extracts accounts, and closes the browser.
    """
    print(f"\n{'=' * 60}")
    print(f"  Seed: {seed_url}")
    print(f"{'=' * 60}")

    page = ChromiumPage()
    page.set.timeouts(PAGE_LOAD_TIMEOUT)

    # -- Cookie restoration --
    saved = _load_cookies(COOKIE_FILE)
    if saved:
        page.get("https://www.instagram.com/")
        time.sleep(2)
        page.set.cookies(saved)
        page.get("https://www.instagram.com/")
        time.sleep(3)
        print("  [login] cookies injected")
    else:
        print("  [login] browser opened -- please log in to Instagram manually")
        page.get("https://www.instagram.com/")
        (__import__("time").sleep(40) or print("  waited 40s for manual login"))

    # -- Navigate to seed profile --
    page.get(seed_url)
    time.sleep(5)

    current_url = page.url
    if "login" in current_url.lower() or "accounts/access" in current_url.lower():
        print("\n  [!] session expired -- please log in again")
        (__import__("time").sleep(40) or print("  waited 40s for manual login"))
        page.get(seed_url)
        time.sleep(5)

    # Save cookies for next time
    _save_cookies(page, COOKIE_FILE)

    # -- Scroll to trigger lazy load --
    print("  [scroll] scrolling to trigger lazy-load...")
    for i in range(4):
        page.scroll.down(500)
        time.sleep(SCROLL_WAIT)
        print(f"    scroll {i + 1}/4")

    # -- Extract accounts --
    print("  [extract] parsing suggested accounts...")
    usernames = _extract_accounts(page)
    page.quit()

    print(f"  [result] {len(usernames)} suggested accounts found for {seed_url}")
    return usernames


# ============================================================
# Public API
# ============================================================

async def suggested_discover(
    seed_urls: list[str] | None = None,
    headless: bool = False,
    auto_seed: bool = True,
    dedup: bool = True,
) -> list[str]:
    """Discover suggested accounts from seed Instagram profile URLs,
    with dedup against known accounts and the dedup API.

    Parameters
    ----------
    seed_urls : list[str] | None
        Instagram profile URLs for seeds. If None and auto_seed=True,
        seeds are loaded from known accounts.
    headless : bool
        Whether to run Chrome in headless mode.
    auto_seed : bool
        If True and no seed_urls given, use known accounts as seeds.
    dedup : bool
        If True, check each discovered account against the dedup API.

    Returns
    -------
    list[str]
        New (not previously known) IG usernames.
    """
    known = load_known_accounts() if (auto_seed or dedup) else set()
    print(f"[known] loaded {len(known)} known accounts from project data")

    # Determine seeds
    if seed_urls and len(seed_urls) > 0:
        final_seeds = seed_urls
        print(f"[seed] using {len(final_seeds)} explicit seed URLs")
    elif auto_seed:
        # Use known accounts as seeds
        final_seeds = [f"https://www.instagram.com/{u}/" for u in list(known)[:5]]
        print(f"[seed] auto-selected {len(final_seeds)} known accounts as seeds (max 5)")
    else:
        print("[seed] no seeds provided and auto_seed=False")
        return []

    all_new: list[str] = []
    seen: set[str] = set()

    for url in final_seeds:
        m = re.search(r"instagram\.com/([^/?]+)", url)
        if not m:
            print(f"  [skip] not a valid IG URL: {url}")
            continue
        seed_username = m.group(1).strip("/").lower()

        found = _scrape_seed_suggested(url, headless=headless)

        for username in found:
            u = username.lower()
            if u == seed_username or u in seen:
                continue

            # Check against known accounts
            if dedup and u in known:
                print(f"    [dedup] {u} is in local known set, skipping")
                seen.add(u)
                continue

            # Check against Lambda dedup API
            if dedup:
                try:
                    result = await check_dedup(u, platform="Instagram")
                    if result.get("is_duplicate"):
                        print(f"    [dedup] {u} is in dedup DB, skipping ({result.get('summary')})")
                        seen.add(u)
                        continue
                    print(f"    [dedup] {u} is new (API: {result.get('summary')})")
                except Exception as e:
                    print(f"    [dedup] API check failed for {u}: {e}, including anyway")

            seen.add(u)
            all_new.append(username)

    return all_new


async def suggested_and_save(
    seed_urls: list[str] | None = None,
    headless: bool = False,
    auto_seed: bool = True,
    dedup: bool = True,
    output_file: str | Path | None = None,
) -> Path:
    """Discover new suggested accounts and save to pipeline input file.

    Parameters
    ----------
    seed_urls : list[str] | None
        Explicit seed URLs. If None and auto_seed=True, use known accounts.
    headless : bool
        Whether to run Chrome in headless mode.
    auto_seed : bool
        Auto-select seeds from known accounts.
    dedup : bool
        Dedup against the Lambda API and local known set.
    output_file : str | Path | None
        Output path (default: data/input_suggested.txt).

    Returns
    -------
    Path
        Path to the saved output file.
    """
    if output_file is None:
        output_file = DEFAULT_OUTPUT
    else:
        output_file = Path(output_file)

    usernames = await suggested_discover(
        seed_urls=seed_urls,
        headless=headless,
        auto_seed=auto_seed,
        dedup=dedup,
    )

    if not usernames:
        print("No NEW suggested accounts discovered.")
        return output_file

    lines = [f"https://www.instagram.com/{u}/" for u in usernames]
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} NEW URLs written to {output_file}")
    return output_file


if __name__ == "__main__":
    async def cli():
        import argparse
        parser = argparse.ArgumentParser(description="Discover IG suggested accounts with dedup")
        parser.add_argument("--seeds", nargs="*", default=None, help="Seed IG URLs (optional)")
        parser.add_argument("--headless", action="store_true", help="Run Chrome headless")
        parser.add_argument("--no-auto-seed", action="store_true", help="Disable auto-seeding from known accounts")
        parser.add_argument("--no-dedup", action="store_true", help="Skip dedup check")
        parser.add_argument("--output", type=str, default=None, help="Output file path")
        args = parser.parse_args()

        await suggested_and_save(
            seed_urls=args.seeds,
            headless=args.headless,
            auto_seed=not args.no_auto_seed,
            dedup=not args.no_dedup,
            output_file=args.output,
        )

    asyncio.run(cli())
