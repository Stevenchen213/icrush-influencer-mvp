"""KOL 查重 API — 已迁移到阿里云（含 KOL 总表 / KOC 红人库 / 实习生查重表 / AWS KOC 数据库）。

POST https://fc-toolplatform-wlmnvexxpg.cn-hangzhou.fcapp.run/api/koc-dedup
Headers: Content-Type: application/json, x-api-token: <token>
Body:   {"account": "username", "platform": "Instagram", "developer_name": "陈铭嵩"}

查重表范围（4 库）：
  - KOL博主记录总表
  - KOC红人库
  - 实习生KOL查重表
  - AWS KOC数据库

Returns summary: "不重复，已录入" = 新账号已写入 KOL 总表, "有重复" = 库里已有
"""

import httpx

from icrush.config import DEDUP_API_TOKEN, DEDUP_API_URL


async def check_dedup(username: str, platform: str = "Instagram") -> dict:
    """Check if a KOL username already exists across 4 dedup tables.

    The API auto-writes new accounts to the KOL 总表 on first check.

    Args:
        username: The social media account name (without @)
        platform: "Instagram" or "TikTok"

    Returns:
        {
            "is_duplicate": True/False,  # True = already in DB, skip
            "summary": str,              # raw summary from API
            "detail": str | None,        # per-table comparison results
            "error": str | None,         # error message if call failed
        }
    """
    if not DEDUP_API_URL or not DEDUP_API_TOKEN:
        return {"is_duplicate": False, "summary": "API 未配置", "error": "missing config"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                DEDUP_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-token": DEDUP_API_TOKEN,
                },
                json={
                    "account": username,
                    "platform": platform,
                    "developer_name": "陈铭嵩",
                    "check_only": True,  # 只查重，不写入 KOL 总表
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                summary = data.get("summary", "")
                # "不重复" / "不重复，已录入" = no duplicate → proceed
                # "有重复" = duplicate exists
                is_dup = "有重复" in summary
                return {
                    "is_duplicate": is_dup,
                    "summary": summary,
                    "detail": data.get("detail"),
                    "error": None,
                }

            return {
                "is_duplicate": False,
                "summary": f"HTTP {resp.status_code}",
                "error": f"API returned {resp.status_code}",
            }

    except httpx.TimeoutException:
        return {"is_duplicate": False, "summary": "超时", "error": "timeout"}
    except Exception as e:
        return {"is_duplicate": False, "summary": "异常", "error": str(e)}
