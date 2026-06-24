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


def short_circuit(platform: str, profile: dict) -> dict:
    """Apply STAGE 1 short-circuit checks to a profile.

    Returns {'fail': bool, 'reason': str}.
    """
    # Male creator check — by name (hard rule)
    male_reason = detect_male_by_name(profile.get("fullName", ""))
    if male_reason:
        return {"fail": True, "reason": male_reason}

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
            "verdict": "🟡 置换组",
            "reason": "; ".join(rs),
            "regionAccurate": region_accurate,
        }

    return {"verdict": "✅ 是", "reason": "-", "regionAccurate": region_accurate}
