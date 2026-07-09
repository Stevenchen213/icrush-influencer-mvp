"""Constants, thresholds, paths, and environment variable loading."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# === Apify ===
TOKEN: str = os.environ["APIFY_TOKEN"]  # fail fast if missing
SKIP_DEDUP: bool = os.environ.get("SKIP_DEDUP", "") == "1"

# === Apify Cache ===
APIFY_CACHE_ENABLED: bool = os.environ.get("APIFY_CACHE_ENABLED", "1") == "1"
APIFY_CACHE_TTL_HOURS: int = int(os.environ.get("APIFY_CACHE_TTL_HOURS", "24"))

# === Thresholds ===
CAPTION_THRESHOLD: int = 25
POSTS_LIMIT: int = 10
REELS_LIMIT: int = 40  # for commercial detection (larger sample)
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
ACTOR_IG_REELS: str = "apify/instagram-reel-scraper"

# === Paths ===
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RESULTS_DIR: Path = PROJECT_ROOT / "results"
CACHE_FILE: Path = DATA_DIR / "wednesday_cache.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Exclusion file
EXCLUSION_FILE: Path = DATA_DIR / "exclusion_list.json"

# 飞书 exclusion
# Base/Table: 通过环境变量配置，硬编码值仅作 fallback
FEISHU_BASE_ID: str = os.environ.get("FEISHU_BASE_ID", "TgzJbUV0taC8VVsOyndcUp69nEh")
FEISHU_TABLE_ID: str = os.environ.get("FEISHU_TABLE_ID", "tbl0vl4DSF0ChSjg")
FEISHU_TOKEN: str = os.environ.get("FEISHU_TOKEN", "")
FEISHU_APP_ID: str = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET: str = os.environ.get("FEISHU_APP_SECRET", "")

# 飞书 results sync（需 FEISHU_SYNC_ENABLED=1 + FEISHU_RESULTS_TABLE_ID）
FEISHU_SYNC_ENABLED: bool = os.environ.get("FEISHU_SYNC_ENABLED", "0") == "1"
FEISHU_RESULTS_BASE_ID: str = os.environ.get("FEISHU_RESULTS_BASE_ID", FEISHU_BASE_ID)
FEISHU_RESULTS_TABLE_ID: str = os.environ.get("FEISHU_RESULTS_TABLE_ID", "")

# 飞书 review table — "✅ 是" 结果二次人工判断
FEISHU_REVIEW_SYNC_ENABLED: bool = os.environ.get(
    "FEISHU_REVIEW_SYNC_ENABLED", str(FEISHU_SYNC_ENABLED)
).lower() in ("1", "true")
FEISHU_REVIEW_BASE_ID: str = os.environ.get("FEISHU_REVIEW_BASE_ID", FEISHU_RESULTS_BASE_ID)
FEISHU_REVIEW_TABLE_ID: str = os.environ.get("FEISHU_REVIEW_TABLE_ID", "")

# === KOL 查重 API（实习生部署） ===
RAPIDAPI_KEY: str = os.environ.get("RAPIDAPI_KEY", "")

# === KOL 查重 API（实习生部署） ===
DEDUP_API_URL: str = os.environ.get(
    "DEDUP_API_URL",
    "https://fc-toolplatform-wlmnvexxpg.cn-hangzhou.fcapp.run/api/koc-dedup",
)
DEDUP_API_TOKEN: str = os.environ.get("DEDUP_API_TOKEN", "")
