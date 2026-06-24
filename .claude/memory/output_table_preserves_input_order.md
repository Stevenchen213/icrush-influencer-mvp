---
name: output-table-preserves-input-order
description: "When outputting batch verdict tables for ICRUSH influencer vetting, preserve the user's original URL paste order — do NOT sort by verdict"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

When producing the final verdict table for an influencer batch, list rows in the **exact order the user pasted the URLs**, NOT sorted by verdict (✅ → ⚠️ → 🟡 → ❌).

**Why:** User stated 2026-06-08 PM: "最后罗列的时候就按照原本的顺序罗列". Likely so she can cross-check the output against her source list (飞书 / browser tabs / sourcing notes) line-by-line without re-mapping.

**How to apply:**
- Tracks back to [[mvp-workflow]]: the current `scripts/analyze.mjs` sorts by `verdict` priority. When she sends a new batch, either:
  1. Update `analyze.mjs` to skip the sort (delete the `order` map + `allResults.sort(...)` block, line ~293), OR
  2. Post-process: re-order the analyze output by the user's input URL list before showing it
- Feed Apify `startUrls` in user's order so dataset ordering helps too
- Applies to ALL future batches by default, not just the next one
