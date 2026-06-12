"""Short-circuit and verdict functions extracted from run_batch.mjs."""

from icrush.config import (
    CAPTION_THRESHOLD,
    COMMENT_THRESHOLD,
    FAN_MAX,
    FAN_MIN,
    FAN_REPLACE,
    POSTS_MIN,
    VIEW_OK,
    VIEW_REPLACE,
)


def short_circuit(platform: str, profile: dict) -> dict:
    """Apply STAGE 1 short-circuit checks to a profile.

    Returns {'fail': bool, 'reason': str}.
    """
    # Occupation check
    occ = profile.get("occupation")
    if occ:
        label = "律师" if occ == "Lawyer" else "艺术家"
        return {"fail": True, "reason": f"职业={label}（直接 PASS）"}

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
        extra = (
            f"；粉丝 {profile['fans']}<10K（如评论通过则置换组）"
            if is_replace_by_fans
            else ""
        )
        return {
            "verdict": "⚠️ 需人工核查",
            "reason": (
                f"caption {de_pct}%<{CAPTION_THRESHOLD}% "
                f"但 bio 在 {profile['region']['region']} → 待 STAGE 3 调评论 API{extra}"
            ),
            "regionAccurate": region_accurate,
            "_pendingComments": True,
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


def finalize_with_comments(
    profile: dict, avg_views: int, de_pct_comments: int | None
) -> dict:
    """Final verdict after STAGE 3 comment analysis.

    Returns a dict suitable for merging into the results entry.
    """
    if de_pct_comments is None:
        return {
            "verdict": "⚠️ 需人工核查",
            "reason": "评论数据不足（de+en 评论太少无法判定）",
            "regionAccurate": "是 (评论)",
        }

    if de_pct_comments < COMMENT_THRESHOLD:
        return {
            "verdict": "❌ 否",
            "reason": f"② 评论 {de_pct_comments}%<{COMMENT_THRESHOLD}%",
            "regionAccurate": "是 (评论)",
        }

    is_replace_by_fans = profile.get("fans", 0) < FAN_REPLACE

    if avg_views >= VIEW_OK:
        view_status = "pass"
    elif avg_views >= VIEW_REPLACE:
        view_status = "replace"
    else:
        view_status = "fail"

    if view_status == "fail":
        return {
            "verdict": "❌ 否",
            "reason": f"② 评论 {de_pct_comments}% 通过 但近 3 月平均浏览 {avg_views:,}<{VIEW_REPLACE}",
            "regionAccurate": "是 (评论)",
        }

    if is_replace_by_fans or view_status == "replace":
        rs: list[str] = []
        if is_replace_by_fans:
            rs.append(f"粉丝 {profile['fans']}<10K")
        if view_status == "replace":
            rs.append(f"平均浏览 {avg_views:,} 在 2000-4000")
        return {
            "verdict": "🟡 置换组",
            "reason": f"② 评论 {de_pct_comments}% 通过；{'；'.join(rs)}",
            "regionAccurate": "是 (评论)",
        }

    return {
        "verdict": "✅ 是",
        "reason": "-",
        "regionAccurate": "是 (评论)",
    }
