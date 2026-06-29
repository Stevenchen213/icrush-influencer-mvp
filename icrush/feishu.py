"""飞书 Bitable integration — exclusion list + results sync.

Exclusion table (read-only):
  Base: TgzJbUV0taC8VVsOyndcUp69nEh
  Table: tbl0vl4DSF0ChSjg

Results sync table (write):
  Config via FEISHU_RESULTS_BASE_ID / FEISHU_RESULTS_TABLE_ID env vars.
"""

import calendar
import sys
from datetime import datetime

import httpx

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from icrush.classifier import format_commercial_stats
from icrush.config import (
    FEISHU_BASE_ID,
    FEISHU_RESULTS_BASE_ID,
    FEISHU_RESULTS_TABLE_ID,
    FEISHU_SYNC_ENABLED,
    FEISHU_TABLE_ID,
    FEISHU_TOKEN,
)


# ═══════════════════════════════════════════════════════════════════
#  Exclusion list (keep existing behaviour)
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
#  Results sync — STAGE 0 dedup + pipeline-end append
# ═══════════════════════════════════════════════════════════════════

def _auth_headers(token: str | None = None) -> dict:
    t = token or FEISHU_TOKEN
    return {
        "Authorization": f"Bearer {t}",
        "Content-Type": "application/json",
    }


def _api_url(base_id: str, table_id: str, path: str) -> str:
    return f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/{path}"


async def fetch_all_usernames(
    base_id: str | None = None,
    table_id: str | None = None,
    token: str | None = None,
) -> set[str]:
    """Fetch all usernames from the Feishu results table for STAGE 0 dedup.

    Paginates through all records (500 per page).
    Returns a set of username strings like {"IG:stevenchen", "TT:ayliniz", ...}.
    Returns an empty set on any failure (never blocks the pipeline).
    """
    b_id = base_id or FEISHU_RESULTS_BASE_ID
    t_id = table_id or FEISHU_RESULTS_TABLE_ID
    tkn = token or FEISHU_TOKEN

    if not tkn or not t_id:
        return set()

    headers = _auth_headers(tkn)
    usernames: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            page_token = ""
            while True:
                url = _api_url(b_id, t_id, "records") + f"?page_size=500"
                if page_token:
                    url += f"&page_token={page_token}"

                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return set()

                data = resp.json()
                for item in data.get("data", {}).get("items", []):
                    fields = item.get("fields", {})
                    username = fields.get("用户名", "")
                    platform = fields.get("平台", "")
                    if username:
                        usernames.add(f"{platform}:{username}")

                has_more = data.get("data", {}).get("has_more", False)
                page_token = data.get("data", {}).get("page_token", "")
                if not has_more or not page_token:
                    break

        return usernames

    except Exception:
        return set()


def _build_fields(
    r: dict,
    unique_username: str,
    date_str: str,
    batch_id: str,
) -> dict:
    """Map a single pipeline result dict to Feishu Bitable field values.

    None values are omitted so Feishu shows empty cells (not "0").
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_ms = calendar.timegm(dt.timetuple()) * 1000  # UTC, avoids TZ offset

    fields = {
        "用户名": r.get("name", ""),  # bare username, platform is a separate field
        "平台": r.get("platform", ""),
        "粉丝数量": r.get("fans"),
        "帖数": r.get("posts"),
        "地区准确性": r.get("regionAccurate", ""),
        "近三月平均浏览量": r.get("avgViews"),
        "女粉占比": r.get("genderFemale"),
        "Caption德语占比": r.get("_captionDePct"),
        "达人链接": {"link": f"https://www.instagram.com/{r.get('name', '')}/"} if r.get("platform") == "IG" else {"link": f"https://www.tiktok.com/@{r.get('name', '')}"},
        "近3月商单": format_commercial_stats(r.get("commercialStats")),
        "判定结果": r.get("verdict", ""),
        "原因": r.get("reason", ""),
        "批次ID": batch_id,
        "日期": date_ms,
    }
    # Omit None values → Feishu shows empty cells
    return {k: v for k, v in fields.items() if v is not None}


async def _batch_create(
    client: httpx.AsyncClient,
    base_id: str,
    table_id: str,
    token: str,
    records: list[dict],
) -> bool:
    """Create records in batches of 500 (Feishu API limit)."""
    if not records:
        return True

    headers = _auth_headers(token)
    url = _api_url(base_id, table_id, "records/batch_create")
    all_ok = True

    for i in range(0, len(records), 500):
        chunk = records[i : i + 500]
        payload = {"records": [{"fields": f} for f in chunk]}
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"  ⚠️ Feishu batch_create HTTP {resp.status_code}: {resp.text[:200]}")
                all_ok = False
            else:
                body = resp.json()
                if body.get("code", 0) != 0:
                    print(f"  ⚠️ Feishu API error {body.get('code')}: {body.get('msg','')[:200]}")
                    all_ok = False
        except Exception:
            all_ok = False

    return all_ok


async def sync_to_feishu(
    results: dict,
    batch_size: int,
    file_num: int,
    *,
    base_id: str | None = None,
    table_id: str | None = None,
    token: str | None = None,
) -> bool:
    """Append pipeline results to the Feishu 多维表格.

    Only creates new records — does NOT update existing ones because
    STAGE 0 dedup already filtered out previously-seen usernames.

    Returns True on success, False if skipped or any failure occurred.
    """
    # ── Guards ──
    if not FEISHU_SYNC_ENABLED:
        return False
    b_id = base_id or FEISHU_RESULTS_BASE_ID
    t_id = table_id or FEISHU_RESULTS_TABLE_ID
    tkn = token or FEISHU_TOKEN
    if not tkn or not t_id:
        return False

    # ── Build fields ──
    datestamp = datetime.now().strftime("%Y-%m-%d")
    batch_id = f"{datestamp}_batch{batch_size}_{file_num}"

    records: list[dict] = []
    skipped = 0
    for key, r in results.items():
        # Skip records that are already in the table (dedup survivors)
        if r.get("verdict") == "🟡 已入库":
            skipped += 1
            continue

        platform = r.get("platform", "")
        username = r.get("name", "")
        unique_name = f"{platform}:{username}"
        fields = _build_fields(r, unique_name, datestamp, batch_id)
        records.append(fields)

    if not records:
        print(f"  ℹ️ 飞书: 无新记录需同步（跳过 {skipped} 条已入库）")
        return True

    # ── Execute ──
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            ok = await _batch_create(client, b_id, t_id, tkn, records)

        if ok:
            print(f"  ✓ 飞书: 同步 {len(records)} 条记录（跳过 {skipped} 条已入库）")
        else:
            print(f"  ⚠️ 飞书: 部分同步失败（{len(records)} 条）")

        return ok

    except httpx.TimeoutException:
        print("  ⚠️ 飞书同步超时，跳过")
        return False
    except Exception as e:
        print(f"  ⚠️ 飞书同步异常: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
#  Table creation helper
# ═══════════════════════════════════════════════════════════════════

RESULTS_TABLE_SCHEMA = [
    {"field_name": "用户名", "type": 1},                # 1 = Text
    {"field_name": "平台", "type": 3,                   # 3 = Single Select
     "property": {"options": [{"name": "IG", "color": 0}, {"name": "TT", "color": 1}]}},
    {"field_name": "粉丝数量", "type": 2},               # 2 = Number
    {"field_name": "帖数", "type": 2},
    {"field_name": "地区准确性", "type": 1},
    {"field_name": "近三月平均浏览量", "type": 2},
    {"field_name": "女粉占比", "type": 2},
    {"field_name": "Caption德语占比", "type": 2},
    {"field_name": "近3月商单", "type": 1},
    {"field_name": "判定结果", "type": 3,
     "property": {"options": [
         {"name": "✅ 是", "color": 0},
         {"name": "❌ 否", "color": 1},
         {"name": "🟡 复查", "color": 2},
         {"name": "🟡 置换组", "color": 3},
         {"name": "⚠️ 抓取失败", "color": 4},
         {"name": "🟡 已入库", "color": 5},
     ]}},
    {"field_name": "原因", "type": 1},
    {"field_name": "批次ID", "type": 1},
    {"field_name": "日期", "type": 5},                   # 5 = Date
]


async def create_results_table(
    name: str = "达人筛选结果",
    base_id: str | None = None,
    token: str | None = None,
) -> str | None:
    """Create the results table in the configured Feishu Base.

    Creates the table and all fields. Returns the new table_id on success,
    or None on failure. Does NOT write to .env (caller handles that).
    """
    b_id = base_id or FEISHU_RESULTS_BASE_ID
    tkn = token or FEISHU_TOKEN

    if not tkn:
        print("❌ FEISHU_TOKEN 未设置，无法创建表格")
        return None

    headers = _auth_headers(tkn)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Create table
            create_url = (
                f"https://open.feishu.cn/open-apis/bitable/v1/"
                f"apps/{b_id}/tables"
            )
            resp = await client.post(
                create_url,
                json={"table": {"name": name}},
                headers=headers,
            )
            if resp.status_code != 200:
                print(f"[ERROR] Failed to create table: {resp.status_code} {resp.text}")
                return None

            data = resp.json()
            table_id = data.get("data", {}).get("table_id", "")
            if not table_id:
                print(f"[ERROR] No table_id in response: {resp.text}")
                return None

            print(f"[OK] Table created: {name} ({table_id})")

            # 2. Add fields one by one
            fields_url = (
                f"https://open.feishu.cn/open-apis/bitable/v1/"
                f"apps/{b_id}/tables/{table_id}/fields"
            )
            for field in RESULTS_TABLE_SCHEMA:
                fr = await client.post(
                    fields_url,
                    json={"field_name": field["field_name"], "type": field["type"],
                          "property": field.get("property")},
                    headers=headers,
                )
                if fr.status_code == 200:
                    print(f"  [OK] Field: {field['field_name']}")
                else:
                    print(f"  [WARN] Field {field['field_name']}: {fr.status_code}")

            return table_id

    except Exception as e:
        print(f"[ERROR] Create table failed: {e}")
        return None
