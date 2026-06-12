"""Constants, thresholds, paths, and environment variable loading."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# === Apify ===
TOKEN: str = os.environ["APIFY_TOKEN"]  # fail fast if missing
SKIP_COMMENTS: bool = os.environ.get("SKIP_COMMENTS", "") == "1"

# === Thresholds ===
CAPTION_THRESHOLD: int = 25
COMMENT_THRESHOLD: int = 60
POSTS_LIMIT: int = 20
COMMENTS_PER_POST: int = 10
POSTS_MIN: int = 200
FAN_MIN: int = 1_000
FAN_MAX: dict[str, int] = {"TT": 500_000, "IG": 300_000}
FAN_REPLACE: int = 10_000
VIEW_REPLACE: int = 2_000
VIEW_OK: int = 4_000
THREE_MONTH_DAYS: int = 90
USD_TO_CNY: float = 7.25

# === Wednesday / Upfluence ===
WEDNESDAY_BASE: str = "https://facade.upfluence.co/api/v1"
WEDNESDAY_EMAIL: str = os.environ.get("WEDNESDAY_EMAIL", "it@icrush.de")
WEDNESDAY_PASSWORD: str = os.environ.get("WEDNESDAY_PASSWORD", "")
GENDER_MALE_MAX: int = 50
GENDER_MALE_MAX_100K: int = 65
WEDNESDAY_COUNTRY_MIN: float = 35.0

# === Apify Actor IDs ===
ACTOR_TT_PROFILE: str = "clockworks/tiktok-profile-scraper"
ACTOR_IG_PROFILE: str = "apify/instagram-profile-scraper"
ACTOR_IG_POSTS: str = "apify/instagram-post-scraper"
ACTOR_TT_COMMENTS: str = "thescrapelab/tiktok-comments-scraper"
ACTOR_IG_COMMENTS: str = "apify/instagram-comment-scraper"

# === Paths ===
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RESULTS_DIR: Path = PROJECT_ROOT / "results"
CACHE_FILE: Path = DATA_DIR / "wednesday_cache.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
