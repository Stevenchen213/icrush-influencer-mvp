"""Short-circuit and verdict functions extracted from run_batch.mjs."""

from icrush.config import (
    CAPTION_THRESHOLD,
    FAN_MAX,
    FAN_MIN,
    FAN_REPLACE,
    POSTS_MIN,
    VIEW_OK,
    VIEW_REPLACE,
)
from icrush.language import detect_male_by_name
from icrush.wordlists import BIO_CATEGORY_BLOCKLIST


# Brand detection: scoring-based. Signals split into username-only and bio-only
# to prevent .de/.com email addresses in bio from triggering brand detection.

# Username-only signals (3 pts each — enough alone). TLD/suffix in username = brand.
_BRAND_USERNAME_SIGNALS: list[tuple[str, int]] = [
    ("_deutschland", 3), ("_de", 3), ("_at", 3), ("_ch", 3), ("_dach", 3),
    ("_gmbh", 3), ("_shop", 3), ("_store", 3), ("_official", 3),
    (".de", 3), (".com", 3), (".at", 3), (".rtl", 3), (".tv", 3),
    ("_online", 3), ("_magazin", 3), ("magazine", 3), ("_news", 3),
    ("_label", 3), ("_brand", 3),
    # Removed: jewelry/jewellery/schmuck/bijoux — too aggressive,
    # would false-positive on personal jewelry influencer accounts.
]

# Bio-only signals (lower weight — need combination to cross threshold)
_BRAND_BIO_SIGNALS: list[tuple[str, int]] = [
    ("www.", 2),
    ("online-shop", 2), ("onlineshop", 2), ("online shop", 2),
    ("offiziell", 2), ("offizielle", 2), ("official", 2),
    ("gmbh", 2), ("impressum", 2), ("datenschutz", 2),
    # TV / media
    ("rtl+", 2), ("rtl.de", 2), ("prosieben", 3), ("sat.1", 3),
    ("tv show", 2), ("tv-show", 2), ("fernsehshow", 2),
    ("staffel", 1), ("folge", 1),
    # P1: enhanced commercial signals (missed cases from review feedback)
    ("restock", 2), ("kundinnen", 2), ("zufriedene", 1),
    ("bestellung", 2), ("bestellen", 1), ("versand", 2),
    ("lieferung", 1), ("kollektion", 2), ("filiale", 2),
    ("standort", 2), ("standorte", 2), ("buchung", 1),
    ("termin", 1), ("termin vereinbaren", 2),
    ("geöffnet", 2), ("öffnungszeiten", 2), ("mo-fr", 2),
    ("☎", 2), ("📞", 1),
    # Corporate / institutional language
    ("unser team", 2), ("wir sind", 1), ("besuche uns", 2),
    ("abonniere", 1), ("jetzt anmelden", 2), ("tickets", 2),
    ("vorverkauf", 2), ("veranstaltung", 1),
    # Institutional
    ("institut", 2), ("verein", 2), ("stiftung", 2),
    ("museum", 2), ("stadt ", 1), ("tourismus", 2),
    # Venues / hospitality (clear business signals)
    ("restaurant", 2), ("hotel", 2), ("resort", 2),
    ("hostel", 2), ("beachclub", 2),
    ("eventlocation", 2), ("event location", 2),
    # Brand / shop identities
    ("boutique", 2), ("brand", 2), ("label", 2), ("verlag", 2),
    ("friseur", 1), ("friseurin", 1), ("nagelstudio", 2),
    ("kosmetikstudio", 2), ("beauty studio", 2),
    ("permanent makeup", 2), ("microblading", 2),
    # Weak signals (1 pt — must combine with others)
    ("shop", 1), ("store", 1), ("beauty", 1),
    ("edeka", 2), ("rewe", 2), ("lidl", 2), ("aldi", 2),
    ("geschäft", 1), ("markt", 1), ("bedarf", 1),
    ("eröffnungszeiten", 1), ("filiale", 1),
    ("instagram.com/", -10),   # never penalize bio links
]

_BRAND_THRESHOLD = 3


def is_brand_account(profile: dict) -> bool:
    """Score-based brand / corporate account detection.

    Username signals (TLDs, suffixes) are checked against username only.
    Bio signals (shop, impressum, etc.) are checked against bio + full_name only.
    This prevents .de email addresses in bios from triggering false positives.
    """
    username: str = (profile.get("name") or "").lower()
    bio: str = (profile.get("bio") or "").lower()
    full_name: str = (profile.get("fullName") or "").lower()

    score = 0

    # Username suffix check (e.g. lascanaofficial, weleda_deutschland)
    _brand_username_suffixes = [
        "official", "deutschland", "germany", "gmbh",
        "shop", "store", "hotel", "restaurant", "festival",
        "agency", "studio", "clinic", "center", "company",
        "magazin", "verlag", "apotheke", "praxis",
        "label", "brand",
    ]
    for sfx in _brand_username_suffixes:
        if username.endswith(sfx) and not username.endswith("_" + sfx):
            score += 3

    # Username-only signals
    for pat, weight in _BRAND_USERNAME_SIGNALS:
        if pat in (".de", ".com", ".at") and pat in username:
            if not username.endswith(pat):
                continue  # skip mid-name: "jenna.depner"
        if pat in username:
            score += weight

    # Bio + full_name only signals (NOT username)
    for pat, weight in _BRAND_BIO_SIGNALS:
        if pat in bio or pat in full_name:
            score += weight

    # Known chain brands in full_name → strong signal (3 pts each)
    # Personal accounts don't have supermarket/pharmacy names as their display name.
    # Pad full_name with spaces for word-boundary matching of short names.
    _fn_padded = " " + full_name + " "
    _chain_brands = ["edeka", "rewe", "aldi", "lidl", " dm ", "rossmann",
                     "müller", "netto", "penny", "kaufland", "norma"]
    for cb in _chain_brands:
        if cb.startswith(" ") and cb.endswith(" "):
            if cb in _fn_padded:
                score += 3
        elif cb in full_name:
            score += 3

    return score >= _BRAND_THRESHOLD


def is_wrong_category(profile: dict) -> tuple[bool, str]:
    """Check if the profile belongs to an excluded category based on bio text.

    Scans bio + full_name against BIO_CATEGORY_BLOCKLIST keyword groups.
    Returns (is_wrong, category_name) — e.g. (True, "母婴/育儿").

    A category matches when >= 2 keywords from that group appear in the text
    (or >= 1 for high-specificity keywords that rarely false-positive).
    """
    bio: str = (profile.get("bio") or "").lower()
    full_name: str = (profile.get("fullName") or "").lower()
    username: str = (profile.get("name") or "").lower()
    # Scan bio + full_name + username (usernames like "psychologin.marie" are strong signals)
    combined = bio + " " + full_name + " " + username

    # Whitelist: fashion/beauty/jewelry/lifestyle keywords take priority.
    # If bio clearly signals fashion/beauty niche, skip category blocking
    # even if it also contains psych/parenting/food keywords.
    # Only fashion/beauty/jewelry-specific keywords. Generic terms like
    # "creator", "influencer", "blogger", "lifestyle", "model", "pflege"
    # are REMOVED — they appear in ALL niches and were preventing legitimate
    # category blocking (e.g. "Home Creator" skipped 家居 detection).
    FASHION_SAFE_WORDS = {
        "fashion", "beauty", "makeup", "make-up", "skincare", "hautpflege",
        "schmuck", "jewelry", "jewellery", "outfit", "outfits", "ootd",
        "mode", "style", "styling", "lookbook", "streetstyle",
        "nagel", "nails", "nägel", "friseur", "friseurin", "haare", "hair",
        "cosmetic", "kosmetik", "parfüm", "duft", "fragrance",
        "gold", "silber", "silver", "kette", "halskette", "ohrringe",
        "armband", "bracelet", "ring", "ringe",
        "lippenstift", "mascara", "foundation", "nagellack",
        "augenbrauen", "brows", "lashes", "haircare",
    }
    # Word-boundary match: split combined text into tokens and check set
    # intersection. This prevents substrings like "mode" in "modern" or
    # "ring" in "bring" from falsely triggering the fashion whitelist.
    _fashion_tokens = set(combined.replace(",", " ").replace(".", " ").replace("|", " ").replace("/", " ").split())
    if _fashion_tokens & FASHION_SAFE_WORDS:
        return (False, "")

    # High-specificity keywords: single match is enough
    HIGH_SPECIFICITY: set[str] = {
        # these almost never appear in a genuine fashion/lifestyle bio
        "psycholog", "therapeut", "paartherap", "narzissmus",
        "hebamme", "stillberatung", "familienbett", "wochenbett",
        "drilling", "adoption",
        "gospel", "pastor", "predigt", "evangelium",
        "booking@", "bookings@",
        "vanlife", "wohnmobil",
        "grundschullehrerin",
        "tierschutz", "tierheim",     # animal protection/shelter
        "zahnarzt", "zahnärztin", "zahnaerztin",   # dentist
        "ärztin", "aerztin", "arzt",                # doctor/physician
        "heilpraktiker", "heilpraktikerin",         # alternative medicine
        "autoimmun", "chronisch krank",             # chronic illness
        # v0.9.1: from false-negative review
        "grundschullehrerin", "klassenlehrerin",    # elementary teacher
        "energetiker", "energetikerin",              # energy healer
        "humanenergetiker", "humanenergetikerin",   # human energetics
        "tierkommunikator", "tierkommunikatorin",   # animal communicator
        "endometriose", "adenomyose",                # medical conditions
        "lipödem",                                    # medical condition
        "darmerkrankung",                             # gut disease
    }

    # Categories where a single keyword match is enough (high-noise categories)
    # 母婴 and 美食 stay conservative (2 hits) to avoid false positives
    AGGRESSIVE_CATEGORIES = {
        "心理/咨询/治疗", "音乐/演出", "宗教/教会",
        "医疗/健康", "家居/DIY/清洁",
        "教育/知识付费", "美食/烹饪",
    }

    for category, keywords in BIO_CATEGORY_BLOCKLIST.items():
        hits = 0
        threshold = 1 if category in AGGRESSIVE_CATEGORIES else 2
        for kw in keywords:
            if kw in combined:
                if kw in HIGH_SPECIFICITY:
                    hits += 3  # instant match
                else:
                    hits += 1
        if hits >= threshold:
            return (True, f"品类不符：{category}")

    return (False, "")


def short_circuit(platform: str, profile: dict) -> dict:
    """Apply STAGE 1 short-circuit checks to a profile.

    Returns {'fail': bool, 'reason': str}.
    """
    # Male creator check — by name + bio + username (hard rule)
    male_reason = detect_male_by_name(
        profile.get("fullName", ""), profile.get("bio", ""), profile.get("name", "")
    )
    if male_reason:
        return {"fail": True, "reason": male_reason}

    # Wrong category — bio keyword scan (P0 fix)
    is_wrong, cat_reason = is_wrong_category(profile)
    if is_wrong:
        return {"fail": True, "reason": cat_reason}

    # Brand / corporate account
    if is_brand_account(profile):
        return {"fail": True, "reason": "品牌官方号"}

    # Private account
    if profile.get("private"):
        return {"fail": True, "reason": "私密账户"}

    # Post count
    posts = profile.get("posts", 0)
    if posts < POSTS_MIN:
        if (
            platform == "IG"
            and posts >= 150
            and profile.get("latestPosts")
            and len(profile["latestPosts"]) > 0
        ):
            latest = profile["latestPosts"]
            reels_count = sum(1 for x in latest if x.get("type") == "Video")
            reels_ratio = reels_count / len(latest) if latest else 0
            if reels_ratio < 0.5:
                return {"fail": True, "reason": f"帖数 {posts}<{POSTS_MIN}"}
            # reel-heavy → exempt
        else:
            return {"fail": True, "reason": f"帖数 {posts}<{POSTS_MIN}"}

    # Fan count
    fans = profile.get("fans", 0)
    if fans == 0 and posts > 0:
        return {"fail": True, "reason": "粉丝数据抓取异常（fans=0）"}
    if fans < FAN_MIN:
        return {"fail": True, "reason": f"粉丝 {fans}<1K"}
    max_fans = FAN_MAX.get(platform, 500_000)
    if fans > max_fans:
        return {"fail": True, "reason": f"粉丝 {fans:,}>{max_fans:,}"}

    return {"fail": False, "reason": ""}


def judge_from_caption(
    platform: str, profile: dict, de_pct: int | None, avg_views: int
) -> dict:
    """Evaluate profile based on caption language analysis (STAGE 2).

    Returns a dict suitable for merging into the results entry.
    """
    sc = short_circuit(platform, profile)
    if sc["fail"]:
        region_str = "是" if profile.get("region") else "-"
        return {
            "verdict": "❌ 否",
            "reason": sc["reason"],
            "regionAccurate": region_str,
        }

    is_replace_by_fans = profile.get("fans", 0) < FAN_REPLACE

    region_accurate: str
    lang_status: str

    if profile.get("region"):
        region_accurate = "是"
        if de_pct is not None and de_pct >= CAPTION_THRESHOLD:
            lang_status = "pass"
        else:
            lang_status = "need-comments"
    else:
        region_accurate = "-"
        if de_pct is not None and de_pct >= CAPTION_THRESHOLD:
            lang_status = "pass"
            region_accurate = "是 (语言)"
        else:
            return {
                "verdict": "❌ 否",
                "reason": f"bio 无地区 + 语言 {de_pct if de_pct is not None else '?'}%<{CAPTION_THRESHOLD}%",
                "regionAccurate": region_accurate,
            }

    if lang_status == "need-comments":
        return {
            "verdict": "🟡 复查",
            "reason": f"bio 在 {profile['region']['region']} 但 caption {de_pct}%<{CAPTION_THRESHOLD}% → 人工复查",
            "regionAccurate": region_accurate,
        }

    # Determine view status
    if avg_views >= VIEW_OK:
        view_status = "pass"
    elif avg_views >= VIEW_REPLACE:
        view_status = "replace"
    else:
        view_status = "fail"

    if view_status == "fail":
        return {
            "verdict": "❌ 否",
            "reason": f"近 3 月平均浏览 {avg_views:,}<{VIEW_REPLACE}",
            "regionAccurate": region_accurate,
        }

    if is_replace_by_fans or view_status == "replace":
        rs: list[str] = []
        if is_replace_by_fans:
            rs.append(f"粉丝 {profile['fans']}<10K")
        if view_status == "replace":
            rs.append(f"平均浏览 {avg_views:,} 在 2000-4000")
        return {
            "verdict": "🟡 推荐置换",
            "reason": "; ".join(rs),
            "regionAccurate": region_accurate,
        }

    return {"verdict": "✅ 是", "reason": "-", "regionAccurate": region_accurate}
