---
name: ig-similar-accounts-method
description: "Breakthrough: IG similar accounts work via three-step modal-click method, not deprecated"
metadata:
  type: project
---

## Breakthrough Discovery (2026-06-24)

IG's "Similar Accounts" feature is **NOT dead** — it was just moved from a page section to a modal popup. The old extraction methods all failed because they looked for the old UI layout.

## The Three-Step Method

```
1. Navigate to profile: instagram.com/{username}/
2. Click "类似账户" / "Similar accounts" button (role="button")
3. Click "查看全部" / "See all" → full-page grid of similar accounts
4. Scroll aggressively to lazy-load all results (50+ scrolls)
5. Extract all <a href="/username/"> links from the page
```

**Yield**: ~80 similar accounts per seed profile.

## Key Findings

| Finding | Detail |
|---------|--------|
| IG didn't remove similar accounts | Moved from page section → modal → "See all" full page |
| API `include_suggested_users` = false | IG web client deliberately disables it in GraphQL queries |
| `edge_related_profiles` gone | No longer in IG API responses since April 2026 |
| Apify `relatedProfiles` dead | Returns empty since April 2026, IG server-side removal |
| `suggested_users` = null | Field exists in responses but always null |
| Recommendation quality | Based on the **seed account**, not the viewer's profile |
| Main Chrome vs temp profile | Same results — IG doesn't personalize by viewer |

## Verified on 2026-06-24

- @oksana_vibe.de (beauty/fashion) → 80 accounts (mostly Produkttester, seed quality issue)
- @jxlia.albrecht (German lifestyle) → 80 accounts (German young women, good match)
- User confirmed manual match with @jxlia.albrecht results ✅

## Safety Strategy

### Risk Profile
- Uses your own IG account in your own Chrome (not API, not multi-account)
- IG sees human-like behaviour: clicking, scrolling with jitter
- Account age + engagement history = natural protection

### Safe Mode (default)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Seed delay | 30-90s random | Simulates browsing between profiles |
| Max seeds/session | 5 | ~400 candidates, pipeline filters to ~50-80 |
| Max sessions/day | 7-8 | ~2800-3200 candidate/day, ~350-640 after pipeline |
| Scroll jitter | ±400px, ±200ms | Human-like irregular scrolling |
| Micro-pauses | 5% probability | Random 0.5-2s pause mid-scroll |
| Session log | `data/session_log.json` | Tracks daily volume |

### Login
- Normal Chrome close/open preserves cookies
- Session lasts several days to a week
- Re-login only when expired (not every CDP launch)
- **Never** `taskkill /F` Chrome — kills cookies

### Fast Mode (debug only)
```bash
node scripts/fetch_similar_accounts_v3.mjs --fast seed1 seed2
# Skips all safety delays — test only, not for daily use
```

## How to Apply

This method is the new primary influencer discovery channel for ICRUSH.

```bash
# 1. Close Chrome normally, then:
chrome --remote-debugging-port=9222

# 2. Daily workflow (7-8 sessions):
node scripts/fetch_similar_accounts_v3.mjs seed1 seed2 seed3 seed4 seed5

# 3. Feed results to pipeline:
python scripts/run_batch.py data/input_similar_combined.txt
```

The related memory for the user's preferred sourcing method is [[efficient_sourcing_method]].
