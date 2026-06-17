"""飞书 Bitable exclusion list integration.

Base: TgzJbUV0taC8VVsOyndcUp69nEh
Table: tbl0vl4DSF0ChSjg
"""

import httpx

from icrush.config import FEISHU_BASE_ID, FEISHU_TABLE_ID, FEISHU_TOKEN


async def check_feishu(username: str) -> bool:
    """Check if a username exists in the 飞书 exclusion table.

    Uses 飞书 Bitable API to search records.
    Returns True if found (should exclude), False if not found or API unavailable.
    """
    if not FEISHU_TOKEN:
        return False  # No token → skip check gracefully

    # 飞书 Bitable List Records API
    url = (
        f"https://open.feishu.cn/open-apis/bitable/v1/"
        f"apps/{FEISHU_BASE_ID}/tables/{FEISHU_TABLE_ID}/records"
        f"?page_size=20"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {FEISHU_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", {}).get("items", [])
                # Search for username in record fields
                for record in records:
                    fields = record.get("fields", {})
                    for val in fields.values():
                        if isinstance(val, str) and username.lower() in val.lower():
                            return True
                return False
            return False
    except Exception:
        return False  # API unavailable → don't block discovery
