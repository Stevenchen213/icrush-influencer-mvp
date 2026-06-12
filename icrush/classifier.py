"""Commercial post detection and classification (5 categories)."""

import re
from datetime import datetime, timedelta, timezone

from icrush.wordlists import CAT_LABELS, CATEGORY_KEYWORDS, COMMERCIAL_SIGNALS


def is_commercial(
    text: str,
    hashtags_raw: list | None = None,
    is_ad: bool = False,
    is_sponsored: bool = False,
) -> bool:
    """Check if a single post is commercial based on signals.

    Mirrors run_batch.mjs isCommercial() exactly.
    """
    if is_ad or is_sponsored:
        return True

    hashtags: list[str] = []
    for h in (hashtags_raw or []):
        if isinstance(h, str):
            hashtags.append(h)
        elif isinstance(h, dict):
            hashtags.append(h.get("name", ""))

    combined = ((text or "") + " " + " ".join(hashtags)).lower()

    for signal in COMMERCIAL_SIGNALS:
        if len(signal) <= 4:
            # Short words must match as whole-word or hashtag
            escaped = re.escape(signal)
            if re.search(rf"(?:^|[#\s]){escaped}(?:$|[\s.,!?])", combined):
                return True
        else:
            if signal in combined:
                return True

    return False


def classify_commercial(
    text: str,
    hashtags_raw: list | None = None,
    mentions_raw: list | None = None,
    tagged_users: list | None = None,
) -> str:
    """Classify a commercial post into a category based on brand/keyword scoring.

    Returns a category key ('food', 'tech', etc.) or '其他'.
    """
    hashtags: list[str] = []
    for h in (hashtags_raw or []):
        if isinstance(h, str):
            hashtags.append(h)
        elif isinstance(h, dict):
            hashtags.append(h.get("name", ""))

    mentions: list[str] = []
    for m in (mentions_raw or []):
        if isinstance(m, str):
            mentions.append(m)
        elif isinstance(m, dict):
            mentions.append(m.get("name", ""))

    tagged_names = [
        (t.get("username") or t.get("full_name") or "").lower()
        for t in (tagged_users or [])
    ]

    combined = (
        (text or "").lower()
        + " "
        + " ".join(hashtags).lower()
        + " "
        + " ".join(mentions).lower()
        + " "
        + " ".join(tagged_names)
    )

    scores: dict[str, int] = {}
    for cat, data in CATEGORY_KEYWORDS.items():
        score = 0
        for brand in data["brands"]:
            if brand.lower() in combined:
                score += 3
        for kw in data["keywords"]:
            if kw.lower() in combined:
                score += 1
        scores[cat] = score

    entries = [(k, v) for k, v in scores.items() if v > 0]
    entries.sort(key=lambda x: -x[1])

    if not entries:
        return "其他"

    top = entries[:2]
    if len(top) == 2 and top[0][1] >= 3 and top[0][1] >= top[1][1] * 2:
        return top[0][0]
    if len(top) == 2 and top[0][1] <= top[1][1] * 1.5:
        return f"{top[0][0]}+{top[1][0]}"
    return top[0][0]


def analyze_commercial(
    posts: list[dict], platform: str, three_months_ago: datetime
) -> dict:
    """Analyze all posts for commercial content within 3 months.

    Returns a stats dict with total + per-category counts.
    """
    recent: list[dict] = []
    for x in posts:
        ts = x.get("timestamp") or x.get("createTime") or x.get("createTimeRaw")
        if ts is None:
            continue
        # Try ISO string first (most IG timestamps)
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, OverflowError):
                continue
        elif isinstance(ts, (int, float)):
            # TT createTimeRaw may be Unix seconds (< 10^10)
            if ts < 10_000_000_000:
                ts = ts * 1000
            try:
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            except (OSError, ValueError, OverflowError):
                continue
        else:
            continue
        if dt > three_months_ago:
            recent.append(x)

    stats: dict = {
        "total": 0,
        "food": 0,
        "tech": 0,
        "beauty": 0,
        "fashion": 0,
        "jewelry": 0,
        "其他": 0,
    }

    for p in recent:
        text = p.get("caption") or p.get("text") or ""
        hashtags = p.get("hashtags") or []
        is_ad = p.get("isAd") or False
        is_sponsored = p.get("isSponsored") or False

        mentions_raw = p.get("mentions") or []
        detailed = p.get("detailedMentions") or []
        mentions = mentions_raw or [
            m.get("name", "") for m in detailed if m.get("name")
        ]

        tagged = p.get("taggedUsers") or []

        if not is_commercial(text, hashtags, is_ad, is_sponsored):
            continue

        stats["total"] += 1
        cat = classify_commercial(text, hashtags, mentions, tagged)
        if cat in stats:
            stats[cat] += 1
        else:
            stats["其他"] += 1

    return stats


def format_commercial_stats(stats: dict | None) -> str:
    """Format commercial stats dict into display string.

    Returns '-' for None, '无' for zero, or e.g. '食品×2, 美妆×1 | 共3条'.
    """
    if stats is None:
        return "-"
    if stats["total"] == 0:
        return "无"

    parts: list[str] = []
    for cat, label in CAT_LABELS.items():
        if stats.get(cat, 0) > 0:
            parts.append(f"{label}×{stats[cat]}")
    if stats.get("其他", 0) > 0:
        parts.append(f"其他×{stats['其他']}")

    return f"{', '.join(parts)} | 共{stats['total']}条"
