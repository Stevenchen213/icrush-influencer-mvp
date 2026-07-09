"""
RapidAPI Instagram data fetchers.

Replaces Apify actors for:
- Profile data (ig_get_fb_profile_v3)
- Similar accounts (get_ig_similar_accounts)
"""

import asyncio
import time
from collections import deque
from typing import Any

import httpx

from icrush.config import RAPIDAPI_KEY
from icrush.language import detect_region

RAPIDAPI_HOST = "instagram-scraper-stable-api.p.rapidapi.com"

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type": "application/x-www-form-urlencoded",
}

# Rate limit: 50 req/min sliding window
_RATE_LIMIT = 50
_RATE_WINDOW = 60.0
_req_timestamps: deque[float] = deque()
_rate_lock = asyncio.Lock()


async def _acquire_rate_slot():
    """Wait until a rate slot is available (50 req/min)."""
    while True:
        async with _rate_lock:
            now = time.monotonic()
            while _req_timestamps and _req_timestamps[0] < now - _RATE_WINDOW:
                _req_timestamps.popleft()
            if len(_req_timestamps) < _RATE_LIMIT:
                _req_timestamps.append(now)
                return
            wait = _req_timestamps[0] + _RATE_WINDOW - now + 0.1
        await asyncio.sleep(wait)


async def _fetch_profile_one(
    client: httpx.AsyncClient, username: str, retries: int = 3
) -> dict[str, Any] | None:
    """Fetch one IG profile with rate limiting + retry."""
    last_err = None
    for attempt in range(retries):
        await _acquire_rate_slot()
        try:
            resp = await client.post(
                "https://instagram-scraper-stable-api.p.rapidapi.com/ig_get_fb_profile_v3.php",
                data={"username_or_url": username},
                headers=HEADERS,
                timeout=httpx.Timeout(30.0),
            )
            if resp.status_code == 200:
                result = _map_profile(resp.json())
                if result is None:
                    print(f"    [!] Invalid profile for {username} (private/deleted?)")
                    return None
                return result
            elif resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"    [!] Rate limited on {username}, waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"    [!] HTTP {resp.status_code} for {username}")
                return None
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                await asyncio.sleep(2 * (attempt + 1))
    if last_err:
        print(f"    [!] Failed {username}: {last_err}")
    return None


async def fetch_ig_profiles(
    usernames: list[str], max_concurrent: int = 5
) -> dict[str, dict[str, Any]]:
    """Fetch profiles concurrently via RapidAPI (50 req/min rate limit).

    Returns dict username → profile.
    """
    profiles: dict[str, dict[str, Any]] = {}
    total = len(usernames)
    done = 0
    sem = asyncio.Semaphore(max_concurrent)

    async with httpx.AsyncClient() as client:

        async def _fetch_one(username: str):
            nonlocal done
            async with sem:
                p = await _fetch_profile_one(client, username)
            if p:
                profiles[username] = p
            done += 1
            if total > 10 and done % 50 == 0:
                print(f"  [profile] {done}/{total}")

        tasks = [asyncio.create_task(_fetch_one(u)) for u in usernames]
        await asyncio.gather(*tasks)

    return profiles


def _map_profile(data: dict) -> dict[str, Any]:
    """Map RapidAPI response to Apify-compatible format."""
    # API sometimes returns a list for private/deleted accounts
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict):
            data = data[0]
        else:
            return None

    bio = data.get("biography", "") or ""
    region = detect_region(bio)

    return {
        "username": data.get("username", ""),
        "fullName": data.get("full_name", ""),
        "followersCount": data.get("follower_count", 0),
        "postsCount": data.get("media_count", 0),
        "biography": bio,
        "businessCategoryName": data.get("category"),
        "private": data.get("is_private", False),
        "verified": data.get("is_verified", False),
        "isBusinessAccount": data.get("is_business", False),
        "externalUrl": data.get("external_url", ""),
        "region": region,
    }
