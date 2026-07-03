import sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from icrush.apify_cache import get_cached, cache_key
from icrush.judges import is_brand_account, is_wrong_category, _BRAND_BIO_SIGNALS
from icrush.language import detect_male_by_name

# Check endthesilencede
data = get_cached(cache_key('profile','IG','endthesilencede'))
bio = (data.get('bio','') or '').lower()
print(f'endthesilencede bio: {repr(bio[:250])}')
print(f'"mitgliedschaft" in bio: {"mitgliedschaft" in bio}')

# Check dianadelic
data2 = get_cached(cache_key('profile','IG','dianadelic'))
bio2 = (data2.get('bio','') or '').lower()
fn2 = (data2.get('fullName','') or '').lower()
print(f'\ndianadelic bio: {repr(bio2[:250])}')
# Show which 母婴 keywords match
from icrush.wordlists import BIO_CATEGORY_BLOCKLIST
muying = BIO_CATEGORY_BLOCKLIST.get('母婴/育儿', [])
combined = bio2 + ' ' + fn2 + ' ' + 'dianadelic'
hits = []
for kw in muying:
    if len(kw) <= 5:
        tokens = set(combined.replace(',',' ').replace('.',' ').replace('|',' ').replace('/',' ').split())
        if kw in tokens:
            hits.append(kw)
    else:
        if kw in combined:
            hits.append(kw)
print(f'母婴 hits: {hits} ({len(hits)})')

# Check abicrew_nrw
data3 = get_cached(cache_key('profile','IG','abicrew_nrw'))
bio3 = (data3.get('bio','') or '').lower()
fn3 = (data3.get('fullName','') or '').lower()
print(f'\nabicrew_nrw bio: {repr(bio3[:200])}')
# Check brand score
p = {'name':'abicrew_nrw','fullName':data3.get('fullName',''),'fans':0,'posts':0,'bio':bio3,'category':None,'private':False,'latestPosts':[]}
print(f'bicrew brand: {is_brand_account(p)}')

# Check little_travel_society
data4 = get_cached(cache_key('profile','IG','little_travel_society'))
bio4 = (data4.get('bio','') or '').lower()
fn4 = (data4.get('fullName','') or '').lower()
print(f'\nlittle_travel_society bio: {repr(bio4[:200])}')
p4 = {'name':'little_travel_society','fullName':fn4,'fans':0,'posts':0,'bio':bio4,'category':None,'private':False,'latestPosts':[]}
print(f'lts brand: {is_brand_account(p4)}')
