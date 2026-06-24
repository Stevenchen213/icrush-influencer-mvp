"""Hashtag-based influencer discovery via Apify Instagram hashtag scraper.

Flow: hashtag keywords -> Apify -> usernames -> IG URLs -> pipeline input.
No Wednesday quota consumed.
"""

import asyncio
import sys
from pathlib import Path

from icrush.apify import ApifyClient
from icrush.config import ACTOR_IG_HASHTAG, HASHTAG_KEYWORDS, DATA_DIR


async def search_hashtag(
    keywords: list[str] | None = None,
    max_posts_per_keyword: int = 100,
    client: ApifyClient | None = None,
) -> list[str]:
    """Search Instagram by hashtag keywords and return unique usernames."""
    if keywords is None:
        keywords = HASHTAG_KEYWORDS
    own_client = client is None
    if own_client:
        client = ApifyClient()
    seen: set[str] = set()
    all_usernames: list[str] = []
    try:
        for kw in keywords:
            hashtag = kw.lstrip("#").strip()
            if not hashtag:
                continue
            sys.stdout.write(f"  >>> #{hashtag} ... ")
            sys.stdout.flush()
            try:
                result = await client.start_actor(ACTOR_IG_HASHTAG, {
                    "hashtags": [hashtag],
                    "resultsPerPage": min(max_posts_per_keyword, 50),
                    "maxPosts": max_posts_per_keyword,
                    "shouldDownloadVideos": False,
                    "shouldDownloadCovers": False,
                })
                run = await client.wait_for_run(result.run_id, max_wait_sec=300)
                items = await client.fetch_dataset(run["defaultDatasetId"])
                new_count = 0
                for item in items:
                    username = item.get("ownerUsername", "")
                    if not username or username.lower() in seen:
                        continue
                    seen.add(username.lower())
                    all_usernames.append(username)
                    new_count += 1
                print(f"{len(items)} posts, {new_count} new users")
            except Exception as e:
                print(f"error: {e}")
            await asyncio.sleep(1)
    finally:
        if own_client:
            await client.close()
    return all_usernames


async def search_hashtag_and_save(
    keywords: list[str] | None = None,
    max_posts_per_keyword: int = 100,
    output_file: str | Path | None = None,
) -> Path:
    if output_file is None:
        output_file = DATA_DIR / "input_hashtag.txt"
    else:
        output_file = Path(output_file)
    usernames = await search_hashtag(keywords=keywords, max_posts_per_keyword=max_posts_per_keyword)
    if not usernames:
        print("No usernames found via hashtag search.")
        return output_file
    lines = [f"https://www.instagram.com/{u}/" for u in usernames]
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} URLs written to {output_file}")
    return output_file


if __name__ == "__main__":
    asyncio.run(search_hashtag_and_save())