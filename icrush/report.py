"""Markdown table generation and report file output."""

from datetime import datetime
from pathlib import Path

from icrush.classifier import format_commercial_stats
from icrush.config import RESULTS_DIR


def build_markdown_table(input_order: list[dict], results: dict) -> str:
    """Build the final verdict Markdown table.

    Args:
        input_order: list of {'platform','username'} in display order.
        results: dict keyed by 'TT:user'/'IG:user' → verdict entry.

    Returns:
        Full table as a multi-line markdown string.
    """
    header = (
        "| # | 平台 | 用户名 | 粉丝数量 | 帖数 | 地区是否准确 "
        "| 近三月平均浏览量 | 女粉占比 | Caption 德语 | 近3月商单 | 是否合适 | 原因 |"
    )
    sep = (
        "|---|------|--------|---------|------|-------------"
        "|-----------------|---------|-------------|---------|---------|------|"
    )

    rows: list[str] = []
    for i, u in enumerate(input_order, start=1):
        key = f"{u['platform']}:{u['username']}"
        r = results.get(key)
        if r is None:
            rows.append(
                f"| {i} | {u['platform']} | {u['username']} "
                "| - | - | - | - | - | - | ⚠️ 抓取失败 | - |"
            )
            continue

        fans_str = f"{r['fans']:,}" if r.get("fans") is not None else "-"
        posts_str = str(r["posts"]) if r.get("posts") is not None else "-"
        views_str = f"{r['avgViews']:,}" if r.get("avgViews") is not None else "-"
        gender_str = (
            f"{r['genderFemale']}%"
            if r.get("genderFemale") is not None
            else "无信息"
        )
        caption_str = f"{r['_captionDePct']}%" if r.get("_captionDePct") is not None else "-"
        commercial_str = format_commercial_stats(r.get("commercialStats"))

        rows.append(
            f"| {i} | {r['platform']} | {r['name']} "
            f"| {fans_str} | {posts_str} "
            f"| {r.get('regionAccurate', '-')} "
            f"| {views_str} "
            f"| {gender_str} "
            f"| {caption_str} "
            f"| {commercial_str} "
            f"| {r['verdict']} | {r.get('reason', '-')} |"
        )

    return "\n".join([header, sep, *rows])


def build_stats(results: dict) -> str:
    """Build verdict statistics summary."""
    counts: dict[str, int] = {}
    for r in results.values():
        v = r["verdict"]
        counts[v] = counts.get(v, 0) + 1

    lines = [f"- {k}: {v}" for k, v in counts.items()]
    return "\n".join(lines)


def next_report_filename(batch_size: int) -> tuple[Path, int]:
    """Return (filepath, file_num) for the next non-colliding report file."""
    datestamp = datetime.now().strftime("%Y-%m-%d")
    file_num = 1
    while True:
        filepath = RESULTS_DIR / f"{datestamp}_batch{batch_size}_{file_num}.md"
        if not filepath.exists():
            return filepath, file_num
        file_num += 1


def save_report(
    table: str,
    stats: str,
    batch_size: int,
    unique_tt: int,
    unique_ig: int,
    survivors_tt: int,
    survivors_ig: int,
    warn_count: int,
    total_usd: float,
    usd_to_cny: float = 7.25,
    *,
    filepath: Path | None = None,
) -> Path:
    """Save the full report to a timestamped file in results/.

    Returns the path where the report was saved.
    """
    if filepath is None:
        filepath, _ = next_report_filename(batch_size)

    datestamp = datetime.now().strftime("%Y-%m-%d")
    short_circuited = (unique_tt + unique_ig) - (survivors_tt + survivors_ig)

    lines = [
        f"# {datestamp} 批次 ({batch_size} URL / 去重 {unique_tt}TT+{unique_ig}IG)",
        "",
        f"> 规则: v0.5 Wednesday 集成 (caption 25% / 评论 60% / 男粉≤50% or >100K≤65%)",
        f"> 抓取量: 20 posts/videos per survivor (短路淘汰 {short_circuited}/{unique_tt + unique_ig})",
    ]

    if warn_count > 0:
        lines.append(f"> STAGE 3 评论检查: {warn_count} 人")
    else:
        lines.append("> STAGE 3 评论检查: 无 ⚠️，跳过")

    lines.extend([
        f"> Apify 成本: ${total_usd:.4f} (~¥{total_usd * usd_to_cny:.2f})",
        "",
        "## 最终判定表",
        "",
        table,
        "",
        "## 统计",
        "",
        stats,
    ])

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return filepath
