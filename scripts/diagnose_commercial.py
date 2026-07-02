"""Diagnose commercial classification for a specific IG user."""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from icrush.apify_cache import get_cached, cache_key
from icrush.classifier import is_commercial, classify_commercial
from icrush.wordlists import COMMERCIAL_SIGNALS, CATEGORY_KEYWORDS

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "jeannetteharttung"

data = get_cached(cache_key('posts', 'IG', USERNAME))
if not data:
    print(f'No cached posts for {USERNAME}')
    sys.exit(1)

print(f"Analyzing {len(data)} posts for @{USERNAME}")
print(f"{'='*60}")

for i, p in enumerate(data):
    caption = p.get('caption', '') or ''
    hashtags_raw = p.get('hashtags', [])
    hashtags = [h.get('name','') if isinstance(h,dict) else str(h) for h in hashtags_raw]
    mentions_raw = p.get('mentions', []) or p.get('detailedMentions', []) or []
    mentions = [m.get('name','') if isinstance(m,dict) else str(m) for m in mentions_raw]

    is_comm = is_commercial(caption, hashtags, False, False)
    if is_comm:
        cat = classify_commercial(caption, hashtags, mentions, [])
        combined = (caption + ' ' + ' '.join(hashtags)).lower()
        matched_signals = []
        for sig in COMMERCIAL_SIGNALS:
            if len(sig) <= 4:
                escaped = re.escape(sig)
                if re.search(rf'(?:^|[#\s]){escaped}(?:$|[\s.,!?])', combined):
                    matched_signals.append(sig)
            else:
                if sig in combined:
                    matched_signals.append(sig)
        print(f'\nPost {i+1}: CAT={cat}')
        print(f'  Caption: {caption[:250]}')
        print(f'  Hashtags: {hashtags}')
        print(f'  Mentions: {mentions}')
        print(f'  Signals: {matched_signals}')

print(f'\n=== All COMMERCIAL_SIGNALS ({len(COMMERCIAL_SIGNALS)}) ===')
print(sorted(COMMERCIAL_SIGNALS))
