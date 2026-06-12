#!/usr/bin/env python3
"""Complete batch judgment pipeline.

Usage:
    python scripts/run_batch.py data/input.txt
    echo "https://www.instagram.com/x/" | python scripts/run_batch.py -
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Fix Unicode output on Windows GBK terminals
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Allow running from project root without pip install -e .
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from icrush.apify import ApifyClient
from icrush.pipeline import Pipeline


async def main() -> None:
    parser = argparse.ArgumentParser(description="ICRUSH influencer batch vetting pipeline")
    parser.add_argument("input", nargs="?", default="-",
                        help="Input file path or '-' for stdin")
    parser.add_argument("--skip-comments", action="store_true",
                        help="Skip STAGE 3 comment scraping")
    args = parser.parse_args()

    if args.input == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.input).read_text(encoding="utf-8")

    if args.skip_comments:
        import icrush.config
        icrush.config.SKIP_COMMENTS = True

    client = ApifyClient()
    try:
        pipeline = Pipeline(client)
        await pipeline.run(text)
    finally:
        await client.close()


def main_cli() -> None:
    """Entry point for pyproject.toml [project.scripts]."""
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
