import sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx, asyncio
from icrush.config import FEISHU_REVIEW_BASE_ID, FEISHU_REVIEW_TABLE_ID
from icrush.feishu import _get_feishu_token

async def main():
    tkn = _get_feishu_token()
    headers = {'Authorization': f'Bearer {tkn}', 'Content-Type': 'application/json'}
    base = FEISHU_REVIEW_BASE_ID
    tid = FEISHU_REVIEW_TABLE_ID

    total = 0
    cnt_72 = 0
    page_token = ''

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{base}/tables/{tid}/records?page_size=500'
            if page_token:
                url += f'&page_token={page_token}'
            resp = await client.get(url, headers=headers)
            data = resp.json()
            items = data.get('data', {}).get('items', [])
            total += len(items)
            for item in items:
                bid = item.get('fields', {}).get('批次ID', '')
                if bid.startswith('2026-07-02'):
                    cnt_72 += 1
            if not data.get('data', {}).get('has_more', False):
                break
            page_token = data.get('data', {}).get('page_token', '')

    print(f'7/2 批次: {cnt_72} 条')
    print(f'全表总计: {total} 条')

asyncio.run(main())
