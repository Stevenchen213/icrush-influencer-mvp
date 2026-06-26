"""Language detection, region detection, occupation detection, URL parsing."""

import re

from langdetect import DetectorFactory, detect as _detect_langdetect

from icrush.wordlists import (
    AUSTRIAN_CITIES,
    GERMAN_CITY_ABBR,
    GERMAN_CITY_LIST,
    MALE_FIRST_NAMES,
)

# Force consistent results across runs
DetectorFactory.seed = 0


def _detect_lang_impl(text: str) -> str:
    """Classify short text using langdetect library.

    Returns 'de', 'en', 'tr', or 'unknown'.
    """
    if not text or len(text.strip()) < 5:
        return "unknown"

    # Remove URLs and @mentions to reduce noise
    clean = re.sub(r"https?://\S+", "", text)
    clean = re.sub(r"[@#]\w+", " ", clean)

    if len(clean.strip()) < 3:
        return "unknown"

    try:
        lang = _detect_langdetect(clean)
        return lang
    except Exception:
        return "unknown"


def detect_lang(text: str) -> str:
    """Classify caption text using langdetect.

    Returns 'de', 'en', or 'unknown' (tr and other non-DE/EN → unknown).
    """
    result = _detect_lang_impl(text)
    if result in ("de", "en"):
        return result
    return "unknown"


def _match_boundary(word: str, text: str) -> bool:
    """Match word with word-boundary awareness (e.g. 'essen' won't match 'accessories')."""
    return bool(re.search(r'(?<![a-z])' + re.escape(word) + r'(?![a-z])', text))


def detect_region(bio_text: str) -> dict | None:
    """Check a bio string for a German or Austrian city.

    Returns {'region': 'DE'|'AT', 'city': <matched_city>} or None.
    """
    if not bio_text:
        return None
    lower = bio_text.lower()

    for c in AUSTRIAN_CITIES:
        if _match_boundary(c, lower):
            return {"region": "AT", "city": c}
    for c in GERMAN_CITY_LIST:
        if _match_boundary(c, lower):
            return {"region": "DE", "city": c}
    for c in GERMAN_CITY_ABBR:
        if _match_boundary(c, lower):
            return {"region": "DE", "city": c}
    return None


def detect_occupation(bio: str, category: str | None) -> str | None:
    """Detect if this profile is a lawyer or artist.

    Returns 'Lawyer', 'Artist', or None.
    """
    text = f"{bio or ''} {category or ''}".lower()

    lawyer_re = re.compile(
        r"\b(lawyer|attorney|anwalt|anwältin|anwalts|notar|notarin|"
        r"rechtsanwalt|rechtsanwältin|kanzlei|advokat)\b"
    )
    if lawyer_re.search(text):
        return "Lawyer"

    if category and "artist" in (category.lower().split(",")[0] if category else ""):
        return "Artist"

    artist_re = re.compile(
        r"\b(künstler|künstlerin|maler|malerin|bildhauer|skulptur|"
        r"schauspielerin|schauspieler)\b"
    )
    if artist_re.search(text):
        return "Artist"

    return None


def detect_male_by_name(full_name: str = "") -> str | None:
    """Check if the first token of a fullName matches known male first names.

    Returns a reason string if likely male, or None.
    Couple names (e.g. 'Anna & Tom') are NOT rejected — only solo male names.
    """
    if not full_name:
        return None

    # Remove non-alpha characters, split into tokens
    tokens = re.split(r"[^a-zA-ZäöüÄÖÜß]+", full_name.lower().strip())

    male_hits = [t for t in tokens if t in MALE_FIRST_NAMES]
    female_candidates = [t for t in tokens if t.endswith("a") or t.endswith("e")]

    if not male_hits:
        return None

    # If there's a female name present (e.g. "Anna & Tom"), treat as couple → pass
    if "&" in full_name or "und" in full_name.lower():
        return None

    # Only one token and it's male → likely male
    if len(tokens) == 1 and male_hits:
        first = tokens[0]
        return f"男博主（名字: {first}）"

    # Multiple tokens, all identified names are male, no female indicators
    if male_hits and not female_candidates:
        return f"男博主（名字: {', '.join(male_hits)}）"

    return None


def parse_url(url: str) -> dict | None:
    """Parse an Instagram or TikTok profile URL.

    Returns {'platform': 'IG'|'TT', 'username': 'xxx'} or None.
    """
    u = url.strip()
    if not u or u.startswith("#"):
        return None

    m = re.search(r"tiktok\.com/@([\w._-]+)", u)
    if m:
        return {"platform": "TT", "username": m.group(1)}

    m = re.search(r"instagram\.com/([\w._-]+)", u)
    if m:
        seg = m.group(1)
        if seg.lower() in ("p", "reel", "reels", "tv", "stories", "explore"):
            return None
        return {"platform": "IG", "username": seg.rstrip("/")}

    return None
