---
name: apify-actor-choices
description: Which Apify Actors work for ICRUSH influencer pipeline — verified 2026-06-05 — TT clockworks ✅, apidojo ❌ for German accounts, IG split profile+posts actors needed
metadata:
  node_type: memory
  type: reference
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

Tested 2026-06-05 on real German/Austrian influencer batch. Use these defaults next time, don't re-research.

## TikTok

### ✅ `clockworks/tiktok-profile-scraper` — DEFAULT for TT
- $0.004 per video result
- 98.3% success rate, 26K users — battle-tested
- Returns ALL needed fields: `authorMeta.fans/video/signature/privateAccount`, `textLanguage` (auto-detect!), `playCount`, `locationMeta.countryCode/city`, `isSponsored`, `isAd`, `hashtags.name`, `mentions`, `createTimeISO`
- Input: `profiles: [username, ...]`, `resultsPerPage: 30`, `profileSorting: "latest"`, set all `shouldDownload*` to false to save cost
- ~$0.12/profile for 30 posts

### ❌ `apidojo/tiktok-profile-scraper` — DO NOT USE
- Looked attractive at $0.0003/post (13x cheaper)
- **Tried on 7 German TT accounts → all returned `noResults: true`**
- Either rate-limited on free tier or actor broken for this account profile
- Lost ~30 seconds debugging, switched to clockworks. Don't waste time on this again.

### ✅ `thescrapelab/tiktok-comments-scraper` — for ② comments check
- $0.02 per video + $0.00075 per comment
- Input: `videoUrls: [...]`, `maxCommentsPerVideo: 30`, `includeReplies: false`
- ~$0.85 per influencer (20 videos × 30 comments)
- **One run aborted on 2026-06-05 at ~3 min in — but Apify said `chargedEventCounts: 0` so abort = $0 cost**. Safe to abort early.

## Instagram

### ✅ Two-actor combo for IG (no single actor does both well)

**1. `apify/instagram-profile-scraper`** — for metadata
- $0.0026/profile + $0.007/profile if `includeAboutSection: true` (gets country code)
- 144K users, 99.7% success, official Apify
- Returns: `username, biography, followersCount, postsCount, verified, businessCategoryName, private, externalUrl, latestPosts[~12 items]`
- The latestPosts is only 12 items → not enough for "近30条" rule
- **Do this for metadata + business category (职业判定)**

**2. `apify/instagram-post-scraper`** — for 30 posts
- $0.0017/post basic or $0.001/post details (details is cheaper, oddly)
- Input: `username: [...]`, `resultsLimit: 30`, `skipPinnedPosts: false`
- Returns: `caption, timestamp, type, videoViewCount, videoPlayCount, likesCount, hashtags, mentions, ownerUsername`
- **Note**: schema lists `latestComments.*` fields, **BUT actually-returned data has 0 comments**. Don't try to use this for comments check.

### ⏸️ IG comments scraper — TODO next week
- Have NOT picked one yet. apify/instagram-post-scraper does NOT include comments despite schema suggesting it does.
- When resuming: search "Instagram comments" in apify store, pick highest-rated official one.
- Need it for: emiliajoyyy + jxlia.albrecht (bio在DE但caption<70%德语 → 需查评论)

## Cost reality (per actual runs 2026-06-05)

| Run | What | Actual cost |
|-----|------|-------------|
| Earlier same-day TT tests | 3 small clockworks runs | $0.64 |
| 11 TT profiles × 30 posts | clockworks | $0.84 |
| 12 IG profiles + about | apify/instagram-profile-scraper | $0.116 |
| 12 IG × 30 posts | apify/instagram-post-scraper | ~$0.36 (estimated) |
| TT comments (aborted) | thescrapelab | $0.00 (aborted before charge) |
| **Day total** | | **~$1.96 (≈ ¥14)** |

User's own budget guideline: **约 ¥0.35/达人 抓取** (Apify) for profile-only. Matches reality (~$0.05/达人).

## Pricing notes the user mentioned but I never verified

- "近3月商单数量 (每100条Apify消耗3¥)" — this is for the 商单 query workflow (二期). When she asks about 商单 stats later, budget ~¥3/100条.

## Apify MCP details

- Installed via `claude mcp add --transport http apify ...` — local scope only (works in C:\Users\yaxua which is her primary dir)
- Token in `C:\Users\yaxua\.claude.json` (and exposed in early-conversation chat — user said she'd rotate later but deferred)
- Tools available: `apify_search_actors`, `apify_call_actor`, `apify_fetch_actor_details`, `apify_get_actor_run`, `apify_get_dataset_items`, `apify_abort_actor_run`, `apify_apify_rag_web_browser`, `apify_search_apify_docs`, `apify_fetch_apify_docs`
