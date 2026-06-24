#!/usr/bin/env python3
"""Unified ICRUSH influencer discovery CLI.

Supports multiple discovery backends:
    --method wednesday   : Wednesday/Upfluence keyword search (default, needs quota)
    --method hashtag     : Apify Instagram hashtag scraper (no quota)
    --method snowball    : Seed profile -> hashtag -> snowball (no quota)
    --method suggested   : DrissionPage browser -> "Suggested for you" accounts (no quota)
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from icrush.apify import ApifyClient
from icrush.config import DISCOVERY_KEYWORDS, HASHTAG_KEYWORDS


async def main() -> None:
    parser = argparse.ArgumentParser(description="ICRUSH unified influencer discovery")
    parser.add_argument("--method", type=str, default="wednesday",
                        choices=["wednesday", "hashtag", "snowball", "suggested"],
                        help="Discovery backend (default: wednesday)")
    parser.add_argument("--dry-run", action="store_true", help="Search + list only, no pipeline")
    parser.add_argument("--run", action="store_true", help="Full flow: search -> pipeline")
    parser.add_argument("--keywords", type=str, default=None, help="Keywords/hashtags (comma-separated)")
    parser.add_argument("--seeds", type=str, nargs="*", default=None, help="Seed IG URLs for snowball")
    parser.add_argument("--max-posts", type=int, default=100, help="Max posts per hashtag/keyword")
    parser.add_argument("--max-results", type=int, default=100, help="Max candidates to pipeline")
    parser.add_argument("--force", action="store_true", help="Re-process even if in history")
    parser.add_argument("--output", type=str, default=None, help="Output input file path")
    parser.add_argument("--headless", action="store_true", help="Run Chrome headless (suggested method)")
    args = parser.parse_args()

    if not args.dry_run and not args.run:
        parser.print_help()
        print("\nPlease specify --dry-run or --run")
        sys.exit(1)

    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    print("=" * 60)
    print(f"ICRUSH Discovery v0.2  |  Method: {args.method}")
    print("=" * 60)

    if args.method == "wednesday":
        await run_wednesday(args, keywords)
    elif args.method == "hashtag":
        await run_hashtag(args, keywords)
    elif args.method == "snowball":
        await run_snowball(args)
    elif args.method == "suggested":
        await run_suggested(args)


async def run_wednesday(args: argparse.Namespace, keywords: list[str] | None) -> None:
    from icrush.discovery import DiscoveryEngine
    if keywords is None:
        keywords = DISCOVERY_KEYWORDS
    client = ApifyClient()
    try:
        engine = DiscoveryEngine(client)
        stats = await engine.search_and_filter(keywords=keywords, force=args.force)
        if args.dry_run:
            print("\n--- Dry run complete (0 Wednesday views used) ---")
            if engine.filtered:
                print(f"Top {min(10, len(engine.filtered))} candidates:")
                for i, inf in enumerate(engine.filtered[:10]):
                    name = inf.get("name", "?")
                    uname = inf.get("username", "?")
                    country = inf.get("_country_code", "?")
                    female = inf.get("_female_pct", "?")
                    f2 = inf.get("_followers_parsed", "?")
                    ig = inf.get("_ig_handles", [])
                    ig_str = ", ".join(h.get("username", "?") if isinstance(h, dict) else str(h) for h in ig[:2]) or "-"
                    print(f"  #{i+1} {name} (@{ig_str}) | {f2:,} fans | DE:{country} | F{female}%")
            return
        if args.max_results and len(engine.filtered) > args.max_results:
            engine.filtered = engine.filtered[:args.max_results]
        await engine.run_pipeline()
    finally:
        await client.close()


async def run_hashtag(args: argparse.Namespace, keywords: list[str] | None) -> None:
    from icrush.discoverer_hashtag import search_hashtag_and_save
    if keywords is None:
        keywords = HASHTAG_KEYWORDS
    print(f"Keywords: {len(keywords)} hashtags")
    print(f"Max posts/keyword: {args.max_posts}")
    input_file = await search_hashtag_and_save(keywords=keywords, max_posts_per_keyword=args.max_posts, output_file=args.output)
    if args.dry_run:
        print("\n--- Dry run complete ---")
        if input_file.stat().st_size > 0:
            lines = input_file.read_text(encoding="utf-8").strip().split("\n")
            print(f"Would feed {len(lines)} URLs into pipeline")
        return
    if input_file.stat().st_size > 0:
        print("\n--- Feeding into pipeline ---")
        from icrush.pipeline import Pipeline
        client = ApifyClient()
        try:
            text = input_file.read_text(encoding="utf-8")
            pipeline = Pipeline(client)
            await pipeline.run(text)
        finally:
            await client.close()
    else:
        print("No candidates to pipeline.")


async def run_snowball(args: argparse.Namespace) -> None:
    from icrush.discoverer_snowball import snowball_and_save
    seeds = args.seeds
    if not seeds:
        print("Error: --seeds required for snowball method")
        print("Example: --seeds https://www.instagram.com/oksana_vibe.de/")
        sys.exit(1)
    print(f"Seeds: {len(seeds)} URLs")
    print(f"Max posts per hashtag: {args.max_posts}")
    print(f"Max results: {args.max_results}")
    input_file = await snowball_and_save(seed_urls=seeds, max_post_hashtag=args.max_posts, max_results=args.max_results, output_file=args.output)
    if args.dry_run:
        print("\n--- Dry run complete ---")
        if input_file.stat().st_size > 0:
            lines = input_file.read_text(encoding="utf-8").strip().split("\n")
            print(f"Would feed {len(lines)} URLs into pipeline")
        return
    if input_file.stat().st_size > 0:
        print("\n--- Feeding into pipeline ---")
        from icrush.pipeline import Pipeline
        client = ApifyClient()
        try:
            text = input_file.read_text(encoding="utf-8")
            pipeline = Pipeline(client)
            await pipeline.run(text)
        finally:
            await client.close()
    else:
        print("No candidates to pipeline.")



async def run_suggested(args: argparse.Namespace) -> None:
    from icrush.discoverer_suggested import suggested_and_save
    seeds = args.seeds
    if seeds:
        print(f"Seeds: {len(seeds)} URLs")
    else:
        print("No explicit seeds, using auto_seed (known accounts)")
    print(f"Headless: {args.headless}")
    print("Dedup: enabled via Lambda API")
    print("(First run opens browser for manual Instagram login)")
    print("(Cookies saved for subsequent runs)")
    input_file = await suggested_and_save(
        seed_urls=seeds if seeds else None,
        headless=args.headless,
        auto_seed=seeds is None,
        dedup=True,
        output_file=args.output,
    )
    if args.dry_run:
        print("\n--- Dry run complete ---")
        if input_file.stat().st_size > 0:
            clines = input_file.read_text(encoding="utf-8").strip().split("\n")
            print(f"Would feed {len(clines)} URLs into pipeline")
        return
    if input_file.stat().st_size > 0:
        print("\n--- Feeding into pipeline ---")
        from icrush.pipeline import Pipeline
        from icrush.apify import ApifyClient
        client = ApifyClient()
        try:
            text = input_file.read_text(encoding="utf-8")
            pipeline = Pipeline(client)
            await pipeline.run(text)
        finally:
            await client.close()
    else:
        print("No candidates to pipeline.")

def main_cli() -> None:
    asyncio.run(main())

if __name__ == "__main__":
    main_cli()
