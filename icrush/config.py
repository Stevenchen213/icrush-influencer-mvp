"""Constants, thresholds, paths, and environment variable loading."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# === Apify ===
TOKEN: str = os.environ["APIFY_TOKEN"]  # fail fast if missing
SKIP_COMMENTS: bool = os.environ.get("SKIP_COMMENTS", "") == "1"
SKIP_DEDUP: bool = os.environ.get("SKIP_DEDUP", "") == "1"

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

# === Discovery ===
DISCOVERY_KEYWORDS: list[str] = [
    "fashion", "mode", "outfit", "schmuck", "beauty", "lifestyle",
    "style", "jewelry", "accessories", "streetwear", "ootd",
    "lookbook", "modisch", "beauty blogger", "fashion deutschland",
    "mode blogger", "fashionista", "styleblogger", "outfitinspo",
    "fashionblogger", "modetrend", "styling", "influencerfashion",
]

# Discovery pre-filter bounds (stricter than pipeline bounds)
DISCOVERY_FAN_MIN: int = 10_000
DISCOVERY_FAN_MAX_IG: int = 300_000
DISCOVERY_FAN_MAX_TT: int = 500_000
DISCOVERY_GENDER_FEMALE_MIN: float = 50.0

# Wednesday search config
WEDNESDAY_SEARCH_PER_PAGE: int = 50
WEDNESDAY_SEARCH_MAX_PAGES: int = 3
WEDNESDAY_LIST_ID: str = "389827"
WEDNESDAY_VIEW_BUDGET: int = 3000
WEDNESDAY_MIN_REMAINING: int = 100

# IG Hashtag fallback
ACTOR_IG_HASHTAG: str = "apify/instagram-hashtag-scraper"
HASHTAG_KEYWORDS: list[str] = [
    "fashiondeutschland", "modeblogger", "ootdgermany",
    "fashionbloggerde", "streetstylegermany", "styleblogger_de",
    "beautydeutschland", "schmuckliebe", "modetrend",
    "germanfashionblogger", "fashiongermany", "outfitinspiration",
    "berlinfashion", "munichstyle", "hamburgfashion",
]

# Exclusion & history files
EXCLUSION_FILE: Path = DATA_DIR / "exclusion_list.json"
HISTORY_FILE: Path = DATA_DIR / "discovery_history.json"
AUTO_INPUT_FILE: Path = DATA_DIR / "input_auto.txt"

# Airtable exclusion
# Base: appmvJMccHqkAUwg8, Table: tbl8G3lCOugPLxNjr (5992 records)
AIRTABLE_BASE_ID: str = "appmvJMccHqkAUwg8"
AIRTABLE_TABLE_ID: str = "tbl8G3lCOugPLxNjr"
AIRTABLE_TOKEN: str = os.environ.get("AIRTABLE_TOKEN", "")

# 飞书 exclusion
# Base: TgzJbUV0taC8VVsOyndcUp69nEh, Table: tbl0vl4DSF0ChSjg
FEISHU_BASE_ID: str = "TgzJbUV0taC8VVsOyndcUp69nEh"
FEISHU_TABLE_ID: str = "tbl0vl4DSF0ChSjg"
FEISHU_TOKEN: str = os.environ.get("FEISHU_TOKEN", "")

# === KOL 查重 API（实习生部署） ===
DEDUP_API_URL: str = os.environ.get(
    "DEDUP_API_URL",
    "https://xhyngnhrplbfhogbxzw2jz2mpm0uucmp.lambda-url.eu-central-1.on.aws/",
)
DEDUP_API_TOKEN: str = os.environ.get("DEDUP_API_TOKEN", "")
