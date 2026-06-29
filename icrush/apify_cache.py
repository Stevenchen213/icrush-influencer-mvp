"""File-based Apify result cache.

Stores fetched profile/post data per-username so that pipeline crashes
don't force expensive re-fetches. TTL: 24 hours by default.

Cache directory layout:
  data/apify_cache/
    profile/
      IG/  {username}.json
      TT/  {username}.json
    posts/
      IG/  {username}.json
      TT/  {username}.json
"""

import json
import time
import re
from pathlib import Path

from icrush.config import APIFY_CACHE_ENABLED, APIFY_CACHE_TTL_HOURS, DATA_DIR

_CACHE_ROOT = DATA_DIR / "apify_cache"

# Characters illegal in Windows filenames
_FS_BAD = re.compile(r'[\\/:*?"<>|]')


def is_cache_enabled() -> bool:
    return APIFY_CACHE_ENABLED


def cache_key(actor: str, platform: str, username: str) -> Path:
    """Build the filesystem path for a cached result.

    Args:
        actor: "profile" or "posts"
        platform: "IG" or "TT"
        username: bare handle (sanitized for filesystem)
    """
    safe = _FS_BAD.sub("_", username)
    return _CACHE_ROOT / actor / platform / f"{safe}.json"


def get_cached(key: Path) -> dict | None:
    """Read cached data if it exists and is fresh.

    Returns the inner ``data`` dict on hit, or None on miss / error / stale.
    """
    if not is_cache_enabled():
        return None
    try:
        raw = key.read_text("utf-8")
        entry = json.loads(raw)
        age_hours = (time.time() - entry["cached_at"]) / 3600
        if APIFY_CACHE_TTL_HOURS > 0 and age_hours > APIFY_CACHE_TTL_HOURS:
            return None  # stale
        return entry["data"]
    except Exception:
        return None


def set_cache(key: Path, data: dict) -> None:
    """Persist data to the cache.

    Failures are silently ignored — cache is best-effort, not critical.
    """
    if not is_cache_enabled():
        return
    try:
        key.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "username": key.stem,
            "cached_at": time.time(),
            "data": data,
        }
        key.write_text(json.dumps(entry, ensure_ascii=False), "utf-8")
    except Exception as e:
        print(f"  [cache] WARN: write failed for {key.stem}: {e}")
