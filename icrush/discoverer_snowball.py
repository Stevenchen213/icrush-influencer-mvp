"""Snowball influencer discovery - from seed profiles, extract hashtags and find similar creators.

Flow: seed IG URL -> profile data -> extract hashtags from bio + recent posts
        -> search those hashtags via Apify -> more creators -> dedup -> pipeline input.
No Wednesday quota consumed.
"""

import asyncio
import sys
import re
from pathlib import Path

from icrush.apify import ApifyClient
from icrush.config import ACTOR_IG_PROFILE, DATA_DIR


async def extract_seed_hashtags(
    seed_urls: list[str],
    client: ApifyClient,
    max_hashtags: int = 30,
) -> list[str]:
    """From seed influencer URLs, extract hashtags from bio and recent posts."""
    hashtag_counter: dict[str, int] = {}
    for url in seed_urls:
        match = re.search(r"instagram\.com/([^/?]+)", url)
        if not match:
            continue
        username = match.group(1).strip("/")
        sys.stdout.write(f"  >> {username} ... ")
        sys.stdout.flush()
        try:
            result = await client.start_actor(ACTOR_IG_PROFILE, {
                "usernames": [username],
                "includeAboutSection": True,
            })
            run = await client.wait_for_run(result.run_id, max_wait_sec=120)
            items = await client.fetch_dataset(run["defaultDatasetId"])
            if not items:
                print("no data")
                continue
            profile = items[0]
            bio = profile.get("biography", "") or ""
            bio_tags = re.findall(r"#(\w+)", bio)
            for tag in bio_tags:
                hashtag_counter[tag.lower()] = hashtag_counter.get(tag.lower(), 0) + 3
            posts = profile.get("latestPosts", []) or profile.get("posts", [])
            post_tag_count = 0
            for post in posts[:12]:
                caption = post.get("caption", "") or post.get("text", "") or ""
                post_tags = re.findall(r"#(\w+)", caption)
                for tag in post_tags:
                    hashtag_counter[tag.lower()] = hashtag_counter.get(tag.lower(), 0) + 1
                    post_tag_count += 1
            print(f"{len(bio_tags)} bio tags, {post_tag_count} post tags")
        except Exception as e:
            print(f"error: {e}")
        await asyncio.sleep(1)

    generic = {"love", "instagood", "fashion", "beautiful", "photooftheday",
               "happy", "cute", "tbt", "follow", "like", "style", "me",
               "photography", "art", "fitness", "travel", "food", "music",
               "model", "beauty", "nature", "life", "smile", "fun",
               "summer", "makeup", "hair", "germany", "deutschland"}

    ranked = sorted([(t, c) for t, c in hashtag_counter.items() if t not in generic], key=lambda x: -x[1])
    result = [t for t, _ in ranked[:max_hashtags]]
    print(f"Extracted {len(result)} unique hashtags from seeds")
    for t, c in ranked[:10]:
        print(f"    #{t} (x{c})")
    return result


async def snowball_discover(
    seed_urls: list[str],
    max_post_hashtag: int = 50,
    max_results: int = 100,
) -> list[str]:
    """Snowball discovery: seeds -> extract hashtags -> search more creators."""
    client = ApifyClient()
    try:
        print("Step 1: Extracting hashtags from seed profiles...")
        hashtags = await extract_seed_hashtags(seed_urls, client)
        if not hashtags:
            return []
        print(f"Step 2: Searching {len(hashtags)} hashtags...")
        from icrush.discoverer_hashtag import search_hashtag
        usernames = await search_hashtag(keywords=[f"#{h}" for h in hashtags], max_posts_per_keyword=max_post_hashtag, client=client)
        seed_users = set()
        for url in seed_urls:
            m = re.search(r"instagram\.com/([^/?]+)", url)
            if m:
                seed_users.add(m.group(1).strip("/").lower())
        filtered = [u for u in usernames if u.lower() not in seed_users]
        print(f"{len(usernames)} found, {len(filtered)} after removing seeds")
        return filtered[:max_results]
    finally:
        await client.close()


async def snowball_and_save(
    seed_urls: list[str],
    max_post_hashtag: int = 50,
    max_results: int = 100,
    output_file: str | Path | None = None,
) -> Path:
    if output_file is None:
        output_file = DATA_DIR / "input_snowball.txt"
    else:
        output_file = Path(output_file)
    usernames = await snowball_discover(seed_urls=seed_urls, max_post_hashtag=max_post_hashtag, max_results=max_results)
    if not usernames:
        print("No new usernames discovered via snowball.")
        return output_file
    lines = [f"https://www.instagram.com/{u}/" for u in usernames]
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} URLs written to {output_file}")
    return output_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("seeds", nargs="+", help="Seed IG URLs")
    parser.add_argument("--max-posts", type=int, default=50)
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    asyncio.run(snowball_and_save(seed_urls=args.seeds, max_post_hashtag=args.max_posts, max_results=args.max_results, output_file=args.output))