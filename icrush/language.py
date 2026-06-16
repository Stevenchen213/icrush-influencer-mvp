"""Language detection, region detection, occupation detection, URL parsing."""

import re

from icrush.wordlists import (
    AUSTRIAN_CITIES,
    ENGLISH_WORDS,
    GERMAN_CITY_ABBR,
    GERMAN_CITY_LIST,
    GERMAN_WORDS,
)


def _match_boundary(word: str, text: str) -> bool:
    """Check if `word` appears as a whole word in `text`."""
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


def detect_lang(text: str) -> str:
    """Classify short text as 'de', 'en', or 'unknown'.

    Mirrors run_batch.mjs detectLang() exactly.
    """
    if not text or len(text.strip()) < 5:
        return "unknown"

    lower = text.lower()
    clean = re.sub(r"https?://\S+", "", lower)
    clean = re.sub(r"[@#]\w+", "", clean)

    german_char_boost = 0
    if re.search(r"[äöüß]", clean):
        german_char_boost = 3

    words = [w for w in re.split(r"[\s\W]+", clean) if len(w) >= 2]
    if len(words) < 2 and german_char_boost < 2:
        return "unknown"

    g = sum(1 for w in words if w in GERMAN_WORDS)
    e = sum(1 for w in words if w in ENGLISH_WORDS)
    g += german_char_boost

    if g == 0 and e == 0:
        return "unknown"
    if g > e * 1.5:
        return "de"
    if e > g * 1.5:
        return "en"
    if g > e:
        return "de"
    return "en"


def detect_comment_lang(text: str) -> str:
    """Classify short comment text as 'de', 'en', or 'unknown'.

    Mirrors run_batch.mjs detectCommentLang() exactly.
    """
    if not text:
        return "unknown"
    t = text.strip()
    if len(t) < 2:
        return "unknown"
    if re.match(r"^[\W_\s]+$", t):
        return "unknown"  # pure emoji / symbols

    lower = t.lower()
    clean = re.sub(r"https?://\S+", "", lower)
    clean = re.sub(r"[@#]\w+", "", clean)

    if re.search(r"[äöüß]", clean):
        return "de"

    words = [w for w in re.split(r"[\s\W]+", clean) if len(w) >= 2]
    if len(words) < 1:
        return "unknown"

    g = sum(1 for w in words if w in GERMAN_WORDS)
    e = sum(1 for w in words if w in ENGLISH_WORDS)

    if g == 0 and e == 0:
        return "unknown"
    if g >= e * 1.2:
        return "de"
    if e > g * 1.2:
        return "en"
    return "de" if g > 0 else "en"


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
    if "(category|categoryname).*artist" and re.search(
        r"(category|categoryname).*artist", text
    ):
        return "Artist"

    artist_re = re.compile(
        r"\b(künstler|künstlerin|maler|malerin|bildhauer|skulptur|"
        r"schauspielerin|schauspieler)\b"
    )
    if artist_re.search(text):
        return "Artist"

    return None


# ── Male creator detection ──────────────────────────────────────

_MALE_CATEGORY_WORDS = [
    "men's fashion", "männer", "herren", "menswear", "men's clothing",
    "male model", "männermode", "herrenmode", "men's style", "mens fashion",
    "male influencer", "men's lifestyle", "herrenbekleidung",
]


def detect_male_creator(bio: str = "", category: str = "") -> str | None:
    """Check if a profile appears to be a male creator.

    Returns a reason string if the profile is likely male, or None.
    """
    text = f"{bio or ''} {category or ''}".lower()

    for kw in _MALE_CATEGORY_WORDS:
        if kw in text:
            return f"男博主（category: {kw}）"

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
