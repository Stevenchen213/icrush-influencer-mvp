#!/usr/bin/env python3
"""Fetch Apify datasets by ID and save to data/.

Usage:
    python scripts/fetch_batch.py <tt_dataset_id> <ig_profile_dataset_id> <ig_posts_dataset_id>
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from icrush.apify import ApifyClient


async def main() -> None:
    if len(sys.argv) < 4:
        print("用法: python scripts/fetch_batch.py <tt_dataset> <ig_profile_dataset> <ig_posts_dataset>")
        sys.exit(1)

    tt_id, ig_profile_id, ig_posts_id = sys.argv[1], sys.argv[2], sys.argv[3]
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    client = ApifyClient()
    try:
        print("📥 抓取数据集...")
        tt, ig_p, ig_ps = await asyncio.gather(
            client.fetch_dataset(tt_id),
            client.fetch_dataset(ig_profile_id),
            client.fetch_dataset(ig_posts_id),
        )

        (data_dir / "tt_profiles.json").write_text(json.dumps(tt), encoding="utf-8")
        print(f"   ✓ tt_profiles.json ({len(tt)} items)")

        (data_dir / "ig_profiles.json").write_text(json.dumps(ig_p), encoding="utf-8")
        print(f"   ✓ ig_profiles.json ({len(ig_p)} items)")

        (data_dir / "ig_posts.json").write_text(json.dumps(ig_ps), encoding="utf-8")
        print(f"   ✓ ig_posts.json ({len(ig_ps)} items)")

        print("✅ 完成")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
