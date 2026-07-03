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


def detect_male_by_name(full_name: str = "", bio: str = "", username: str = "") -> str | None:
    """Check fullName, bio, and username for male signals.

    Returns a reason string if likely male, or None.
    Couple names (e.g. 'Anna & Tom') are NOT rejected — only solo male names.
    """
    if not full_name and not bio and not username:
        return None

    name_lower = full_name.lower().strip()
    bio_lower = (bio or "").lower()
    user_lower = (username or "").lower()

    # Title/honorific-based male detection (full_name, bio, username)
    _male_titles = ["mr ", "mr.", "herr ", "papa ", "vater ", "ehemann ",
                    "bruder ", "onkel ", "sohn ", "husband", "father ",
                    "dad ", "daddy", "trans mann"]
    for title in _male_titles:
        if name_lower.startswith(title) or title in name_lower:
            return f"男博主（称呼: {title.strip()}）"
        if title in bio_lower:
            return f"男博主（bio 含: {title.strip()}）"
        if title in user_lower:
            return f"男博主（username 含: {title.strip()}）"

    # Scan full_name + username for male first names
    scan_text = name_lower + " " + user_lower
    tokens = re.split(r"[^a-zA-ZäöüÄÖÜß]+", scan_text)

    male_hits = [t for t in tokens if t in MALE_FIRST_NAMES]
    # Female guard: tokens ending in a/e, >1 char, <=5 chars
    # (excludes single chars like "e" from "germain_e", longer surnames like "Fossa")
    female_candidates = [t for t in tokens
                         if (t.endswith("a") or t.endswith("e")) and 2 <= len(t) <= 4]

    if not male_hits:
        # v0.9.2: compound username detection (e.g. "createdbytaavi")
        # When username is a single glued-together word, check if any male
        # name (len >= 5 to avoid false positives like "ali" in "alice")
        # appears as a substring within the username.
        _long_male_names = [n for n in MALE_FIRST_NAMES if len(n) >= 5]
        for mn in _long_male_names:
            if mn in user_lower:
                return f"男博主（用户名含: {mn}）"
        return None

    # If there's a female name present (e.g. "Anna & Tom"), treat as couple → pass.
    # v0.9.3: only skip if BOTH adjacent tokens around &/und are short (≤12 chars).
    # Prevents "Flo | Reisetipps & Ausflugsziele" being treated as couple.
    _is_couple = False
    for _sep in [" & ", " und "]:
        if _sep in name_lower:
            _parts = name_lower.rsplit(_sep, 1)
            if len(_parts) == 2:
                _left_tokens = _parts[0].strip().split()
                _right_tokens = _parts[1].strip().split()
                _left_word = _left_tokens[-1] if _left_tokens else ""
                _right_word = _right_tokens[0] if _right_tokens else ""
                if len(_left_word) <= 12 and len(_right_word) <= 12:
                    _is_couple = True
            break
    if _is_couple:
        return None

    # Only one token and it's male → likely male
    if len(tokens) == 1 and male_hits:
        first = tokens[0]
        return f"男博主（名字: {first}）"

    # Male hits dominate female candidates → male
    if male_hits and len(male_hits) >= len(female_candidates):
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
