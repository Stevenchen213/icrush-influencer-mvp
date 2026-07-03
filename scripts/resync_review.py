"""Re-sync specific report files to the review table."""
import sys,io,httpx,asyncio; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import datetime
from icrush.feishu import _get_feishu_token, _api_url, _build_review_fields, _safe_int
from icrush.config import FEISHU_REVIEW_BASE_ID, FEISHU_REVIEW_TABLE_ID

def parse_report(fp):
    records=[]
    in_table=False
    for line in open(fp,encoding='utf-8').read().split('\n'):
        line=line.strip()
        if line.startswith('| # |'): in_table=True; continue
        if line.startswith('|---'): continue
        if not in_table or not line.startswith('|'): continue
        cells=[c.strip() for c in line.split('|')[1:-1]]
        if len(cells)<11: continue
        if '已入库' in cells[10]: continue
        if '❌ 否' in cells[10]: continue
        records.append({
            'name':cells[2],'platform':cells[1],'fans':_safe_int(cells[3]),'posts':_safe_int(cells[4]),
            'regionAccurate':cells[5],'avgViews':_safe_int(cells[6]),
            'genderFemale':_safe_int(cells[7].replace('%','')) if cells[7]!='无信息' else None,
            '_captionDePct':_safe_int(cells[8]) if cells[8]!='-' else None,
            'commercialStats':None,'verdict':cells[10],'reason':cells[11],
        })
    return records

async def main():
    files = sys.argv[1:] if len(sys.argv)>1 else []
    if not files:
        print("Usage: python scripts/resync_review.py <report_files>...")
        return
    all_r=[]
    for fp in files:
        r=parse_report(fp); all_r.extend(r); print(f'{fp}: {len(r)} records')
    if not all_r: return
    tkn=_get_feishu_token()
    h={'Authorization':f'Bearer {tkn}','Content-Type':'application/json'}
    ds=datetime.now().strftime('%Y-%m-%d')
    fl=[_build_review_fields(r,f'{r["platform"]}:{r["name"]}',ds,'resync') for r in all_r]
    async with httpx.AsyncClient(timeout=30) as c:
        url=_api_url(FEISHU_REVIEW_BASE_ID,FEISHU_REVIEW_TABLE_ID,'records/batch_create')
        for i in range(0,len(fl),500):
            chunk=fl[i:i+500]
            resp=await c.post(url,json={'records':[{'fields':f} for f in chunk]},headers=h)
            if resp.status_code==200 and resp.json().get('code',0)==0:
                print(f'  {len(chunk)}/{len(all_r)} synced ✅')
            else:
                body = resp.json()
                print(f'  FAIL: {body.get("code")} {body.get("msg","")[:120]}')
asyncio.run(main())
