"""KOL 查重 API — 实习生部署的 Lambda 服务。

POST https://<lambda>/
Headers: Content-Type: application/json, x-api-token: <token>
Body:   {"account": "username", "platform": "Instagram"}

Returns summary: "不重复" = 可以录入, "有重复" = 库里已有
"""

import httpx

from icrush.config import DEDUP_API_TOKEN, DEDUP_API_URL


async def check_dedup(username: str, platform: str = "Instagram") -> dict:
    """Check if a KOL username already exists in the database.

    Args:
        username: The social media account name (without @)
        platform: "Instagram" or "TikTok"

    Returns:
        {
            "is_duplicate": True/False,  # True = already in DB, skip
            "summary": str,              # raw summary from API
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
                json={"account": username, "platform": platform},
            )

            if resp.status_code == 200:
                data = resp.json()
                summary = data.get("summary", "")
                # "不重复" = no duplicate found → can proceed
                # anything else (e.g. "有重复") = duplicate exists
                is_dup = "不重复" not in summary
                return {
                    "is_duplicate": is_dup,
                    "summary": summary,
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
