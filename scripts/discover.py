#!/usr/bin/env python3
"""Automatic influencer discovery and pipeline execution.

Usage:
    # Dry run: search + pre-filter only (0 Wednesday views)
    python scripts/discover.py --dry-run

    # Full discovery: search → filter → pipeline
    python scripts/discover.py --run

    # Search specific keywords only
    python scripts/discover.py --run --keywords "fashion,mode"

    # Limit results
    python scripts/discover.py --run --max-validate 20

    # Force re-run (ignore history)
    python scripts/discover.py --run --force
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Fix Unicode output on Windows GBK terminals
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from icrush.apify import ApifyClient
from icrush.config import DISCOVERY_KEYWORDS
from icrush.discovery import DiscoveryEngine


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="ICRUSH automatic influencer discovery"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Search + pre-filter only (0 views)")
    parser.add_argument("--run", action="store_true",
                        help="Full flow: search → filter → pipeline")
    parser.add_argument("--keywords", type=str, default=None,
                        help="Comma-separated keywords (default: all built-in)")
    parser.add_argument("--max-validate", type=int, default=None,
                        help="Max candidates to feed to pipeline")
    parser.add_argument("--force", action="store_true",
                        help="Re-process even if in history")
    args = parser.parse_args()

    if not args.dry_run and not args.run:
        parser.print_help()
        print("\n请指定 --dry-run 或 --run")
        sys.exit(1)

    # Parse keywords
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    else:
        keywords = DISCOVERY_KEYWORDS

    print("=" * 60)
    print("ICRUSH 自动达人发现系统 v0.1")
    print(f"关键词: {len(keywords)} 个")
    print(f"模式: {'试运行' if args.dry_run else '完整流程'}")
    if args.force:
        print("⚠️ 强制模式：忽略历史记录")
    print("=" * 60)

    client = ApifyClient()
    try:
        engine = DiscoveryEngine(client)

        # Phase 1: search + pre-filter
        stats = await engine.search_and_filter(
            keywords=keywords,
            force=args.force,
        )

        if args.dry_run:
            print("\n--- 试运行结束（0 views 消耗）---")
            if engine.filtered:
                print(f"\n前 {min(10, len(engine.filtered))} 名候选人:")
                for i, inf in enumerate(engine.filtered[:10]):
                    name = inf.get("name", "?")
                    uname = inf.get("username", "?")
                    score = inf.get("score", "-") or "-"
                    country = inf.get("_country_code", "?")
                    female = inf.get("_female_pct", "?")
                    followers = inf.get("_followers_parsed", "?")
                    ig = inf.get("_ig_handles", [])
                    ig_str = ", ".join(
                        h.get("username", "?") if isinstance(h, dict) else str(h)
                        for h in ig[:2]
                    ) or "-"
                    print(f"  #{i+1} {name} (@{ig_str}) | {followers:,}粉 | "
                          f"DE:{country} | 女:{female}% | score:{score}")
            return

        # Phase 2: pipeline
        if args.max_validate and len(engine.filtered) > args.max_validate:
            engine.filtered = engine.filtered[:args.max_validate]
            print(f"\n📋 限制为前 {args.max_validate} 名候选人进入 pipeline")

        await engine.run_pipeline()

    finally:
        await client.close()


def main_cli() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
