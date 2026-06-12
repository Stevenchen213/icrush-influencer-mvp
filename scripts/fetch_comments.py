#!/usr/bin/env python3
"""Fetch comment datasets from Apify and save to data/.

Usage:
    python scripts/fetch_comments.py
    python scripts/fetch_comments.py <tt_dataset_id> <ig_dataset_id>
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from icrush.apify import ApifyClient


async def main() -> None:
    tt_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TT_COMMENTS_DATASET", "")
    ig_id = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("IG_COMMENTS_DATASET", "")

    if not tt_id and not ig_id:
        print("用法: python scripts/fetch_comments.py <tt_dataset_id> <ig_dataset_id>")
        print("  或设置环境变量 TT_COMMENTS_DATASET / IG_COMMENTS_DATASET")
        sys.exit(1)

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    client = ApifyClient()
    try:
        if tt_id:
            print(f"📥 抓取 TT 评论 dataset {tt_id}...")
            items = await client.fetch_dataset(tt_id)
            (data_dir / "tt_comments.json").write_text(json.dumps(items), encoding="utf-8")
            print(f"   ✓ tt_comments.json ({len(items)} items)")

        if ig_id:
            print(f"📥 抓取 IG 评论 dataset {ig_id}...")
            items = await client.fetch_dataset(ig_id)
            (data_dir / "ig_comments.json").write_text(json.dumps(items), encoding="utf-8")
            print(f"   ✓ ig_comments.json ({len(items)} items)")

        print("✅ 完成")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
