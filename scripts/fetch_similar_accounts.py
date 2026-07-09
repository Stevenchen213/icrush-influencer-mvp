"""
ICRUSH Similar Accounts Extractor (RapidAPI)

Replaces the Playwright-based Node.js v3 extractor with a fast HTTP API.
Calls RapidAPI's instagram-scraper-stable-api to get similar accounts.

Usage:
  python scripts/fetch_similar_accounts.py seed1 [seed2 ...]
  python scripts/fetch_similar_accounts.py --max-seeds 5 jxlia.albrecht ...

Output (same format as v3):
  data/similar_{username}.txt  — per-seed file
  data/input_similar_combined.txt  — combined deduped file
"""

import os
import sys
import json
import time
from pathlib import Path

import requests

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Allow import from icrush package
sys.path.insert(0, str(ROOT))
from icrush.config import RAPIDAPI_KEY

RAPIDAPI_URL = "https://instagram-scraper-stable-api.p.rapidapi.com/get_ig_similar_accounts.php"
RAPIDAPI_HOST = "instagram-scraper-stable-api.p.rapidapi.com"

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type": "application/json",
}

# Small delay between API calls to respect rate limits
DELAY_BETWEEN_SEEDS = 2.0  # seconds


def sanitize_seed(raw: str) -> str:
    """Strip URL/protocol/domain → bare username."""
    s = raw.replace("https://", "").replace("http://", "").replace("www.", "")
    s = s.replace("@", "")
    # instagram.com/username/... → username
    for prefix in ("instagram.com/",):
        if s.lower().startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.split("/")[0].split("?")[0].split("#")[0]
    return s.strip()


def fetch_similar(username: str, retries: int = 3) -> list[str]:
    """Call RapidAPI to get similar accounts for a single username.

    Returns a list of usernames (max ~78 per IG's limit).
    """
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                RAPIDAPI_URL,
                headers=HEADERS,
                params={"username_or_url": username},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return [d["username"] for d in data if "username" in d]
                else:
                    print(f"  [!] Unexpected response: {json.dumps(data, ensure_ascii=False)[:200]}")
                    return []
            elif resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  [!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [!] HTTP {resp.status_code}: {resp.text[:120]}")
                return []
        except requests.RequestException as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    if last_err:
        print(f"  [!] Request failed: {last_err}")
    return []


def main():
    args = sys.argv[1:]
    seeds = [a for a in args if not a.startswith("--")]
    max_seeds = None

    # Parse flags
    i = 0
    while i < len(args):
        if args[i] == "--max-seeds" and i + 1 < len(args):
            max_seeds = int(args[i + 1])
            i += 2
        else:
            i += 1

    if not seeds:
        print("Usage: python scripts/fetch_similar_accounts.py <username1> [username2 ...]")
        sys.exit(1)

    # Sanitize & dedup
    seeds = list(dict.fromkeys([sanitize_seed(s) for s in seeds]).keys())

    if max_seeds and len(seeds) > max_seeds:
        print(f"[!] Limiting to {max_seeds} seeds ({len(seeds)} requested)")
        seeds = seeds[:max_seeds]

    print(f"ICRUSH Similar Accounts (RapidAPI)")
    print(f"Seeds: {len(seeds)} | Est. time: ~{len(seeds) * 3:.0f}s")
    print(f"{'=' * 50}")

    all_accounts: set[str] = set()
    results: dict[str, list[str]] = {}

    for si, seed in enumerate(seeds):
        print(f"\n=== @{seed} ===")
        accounts = fetch_similar(seed)
        results[seed] = accounts
        all_accounts.update(a.lower() for a in accounts)
        print(f"  => {len(accounts)} accounts")

        # Delay between seeds
        if si < len(seeds) - 1:
            time.sleep(DELAY_BETWEEN_SEEDS)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Total unique accounts: {len(all_accounts)}")
    print(f"{'=' * 50}")

    # Save per-seed files
    for seed, accounts in results.items():
        if accounts:
            out_path = DATA_DIR / f"similar_{seed}.txt"
            urls = [f"https://www.instagram.com/{u}/" for u in accounts]
            out_path.write_text("\n".join(urls) + "\n", encoding="utf-8")
            print(f"  {seed}: {len(accounts)} -> similar_{seed}.txt")

    # Save combined file
    if all_accounts:
        combined_path = DATA_DIR / "input_similar_combined.txt"
        all_urls = [f"https://www.instagram.com/{u}/" for u in sorted(all_accounts)]
        combined_path.write_text("\n".join(all_urls) + "\n", encoding="utf-8")
        print(f"  Combined ({len(all_accounts)}) -> input_similar_combined.txt")
    else:
        print("\n⚠️  0 accounts found — skipping pipeline")
        sys.exit(0)


if __name__ == "__main__":
    main()
