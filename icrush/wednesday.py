"""Wednesday / Upfluence cache operations and judgment functions."""

import json

from icrush.config import (
    CACHE_FILE,
    GENDER_MALE_MAX,
    GENDER_MALE_MAX_100K,
    WEDNESDAY_COUNTRY_MIN,
)
from icrush.wordlists import AUSTRIAN_CITIES, GERMAN_CITY_ABBR, GERMAN_CITY_LIST

_cache: dict | None = None


def load_wednesday_cache() -> dict:
    """Load and memoize the Wednesday cache file."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        _cache = {}
    return _cache


def wednesday_lookup(username: str) -> dict:
    """Look up a username in the Wednesday cache.

    Returns {'found': True, 'gender': ..., 'topCountry': ..., 'topCity': ...}
    or {'found': False}.
    """
    cache = load_wednesday_cache()
    entry = cache.get(username)
    if not entry or not entry.get("found"):
        return {"found": False}

    # Must have at least one of gender / country / city to be "usable"
    has_data = entry.get("gender") or entry.get("topCountry") or entry.get("topCity")
    if not has_data:
        return {"found": False}

    return {
        "found": True,
        "gender": entry.get("gender"),
        "topCountry": entry.get("topCountry"),
        "topCity": entry.get("topCity"),
    }


def is_german_city(city_name: str | None) -> bool:
    """Check if a city name refers to a German or Austrian city."""
    if not city_name:
        return False
    lower = city_name.lower()

    for c in GERMAN_CITY_LIST:
        if c in lower:
            return True
    for c in AUSTRIAN_CITIES:
        if c in lower:
            return True
    for c in GERMAN_CITY_ABBR:
        if lower.startswith(c.lower() + ","):
            return True
    import re

    if re.search(r", de$", lower) or re.search(r", at$", lower):
        return True
    return False


def judge_wednesday_region(wd: dict) -> dict:
    """Check if Wednesday audience data passes the region test.

    Returns {'pass': bool, 'reason': str}.
    """
    tc = wd.get("topCountry")
    if not tc or tc.get("code") != "DE":
        return {
            "pass": False,
            "reason": f"受众国家#1={tc.get('code', '?') if tc else '?'} 非 DE",
        }
    if tc.get("pct", 0) < WEDNESDAY_COUNTRY_MIN:
        return {
            "pass": False,
            "reason": f"受众 DE 仅 {tc['pct']}%<{WEDNESDAY_COUNTRY_MIN}%",
        }

    top_city = wd.get("topCity")
    if not top_city or not is_german_city(top_city.get("name")):
        return {
            "pass": False,
            "reason": f"受众城市#1={top_city.get('name', '?') if top_city else '?'} 非德城",
        }

    return {"pass": True, "reason": ""}


def judge_gender(wd: dict, fans: int) -> dict:
    """Check if Wednesday audience gender data passes.

    Returns {'pass': bool, 'male_pct': float|None, 'reason': str}.
    """
    gender = wd.get("gender")
    if not gender:
        return {"pass": True, "male_pct": None, "reason": ""}

    male = gender["male"]
    max_male = GENDER_MALE_MAX_100K if fans > 100_000 else GENDER_MALE_MAX
    if male > max_male:
        return {
            "pass": False,
            "male_pct": male,
            "female_pct": gender["female"],
            "reason": f"男粉 {male}%>{max_male}%",
        }

    return {
        "pass": True,
        "male_pct": male,
        "female_pct": gender["female"],
        "reason": "",
    }
