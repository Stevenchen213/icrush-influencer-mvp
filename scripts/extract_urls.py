#!/usr/bin/env python3
"""Extract video URLs from TT profile data for comment scraping.

Usage:
    python scripts/extract_urls.py username1 username2 ...
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python scripts/extract_urls.py <username1> <username2> ...")
        sys.exit(1)

    target_users = set(sys.argv[1:])
    tt_file = DATA_DIR / "tt_profiles.json"

    if not tt_file.exists():
        print(f"❌ {tt_file} 不存在")
        sys.exit(1)

    profiles = json.loads(tt_file.read_text(encoding="utf-8"))

    result: dict[str, list[str]] = {}
    for v in profiles:
        name = v.get("authorMeta", {}).get("name") or v.get("authorMeta.name", "")
        if name not in target_users:
            continue

        posts = v.get("videos") or v.get("posts") or []
        urls = [
            p.get("webVideoUrl") or p.get("url", "")
            for p in posts[:20]
            if not p.get("isPinned") and (p.get("webVideoUrl") or p.get("url"))
        ]
        result[name] = urls
        print(f"   {name}: {len(urls)} URLs")

    out_file = DATA_DIR / "comment_urls.json"
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ 写入 {out_file}")


if __name__ == "__main__":
    main()
