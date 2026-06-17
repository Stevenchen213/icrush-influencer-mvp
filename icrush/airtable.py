"""Airtable exclusion list integration.

Base: appmvJMccHqkAUwg8
Table: tbl8G3lCOugPLxNjr (KOL查重-实习生用表, ~5992 records)
"""

import httpx

from icrush.config import AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID, AIRTABLE_TOKEN


async def check_airtable(username: str) -> bool:
    """Check if a username or IG URL exists in the Airtable exclusion list.

    Searches the table using filterByFormula for the username string.
    Returns True if found (should exclude), False if not found or API unavailable.
    """
    if not AIRTABLE_TOKEN:
        return False  # No token → skip check gracefully

    url = (
        f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
        f"?filterByFormula=SEARCH(%22{username}%22%2C%7BInstagram+URL%7D)"
        f"&maxRecords=1"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("records", [])
                return len(records) > 0
            return False
    except Exception:
        return False  # API unavailable → don't block discovery
