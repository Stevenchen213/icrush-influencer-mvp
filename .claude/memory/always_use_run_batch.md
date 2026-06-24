---
name: always-use-run-batch
description: "When user pastes ICRUSH influencer URLs, ALWAYS use `python scripts/run_batch.py` (Python pipeline), never ad-hoc Apify MCP calls"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

When the user pastes a batch of profile URLs for the ICRUSH MVP vetting pipeline, **ALWAYS run them through `python scripts/run_batch.py`** — never reach for the Apify MCP tools directly.

**Why:** The script encodes the optimal flow:
1. STAGE 1: cheap profile metadata (IG profile-scraper + TT clockworks)
2. Short-circuit: 男博主/职业/私密/帖数/粉丝 → ❌ without paying
3. STAGE 1.5: Wednesday 缓存优先，缓存未命中自动实时查询
4. STAGE 2: 20 posts per survivor only
5. Judge from caption; Wednesday 有数据直接采信，无数据走 fallback 规则
6. 输出表格按粘贴顺序；存档到 `results/<date>_batchN_seq.md`
7. Report Apify USD + ¥ cost

**How to apply:**
- Write URLs to `data/input_<name>.txt`
- Run: `$py = "C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe"; cd C:\Users\yaxua\icrush-influencer-mvp; & $py scripts/run_batch.py data/input_<name>.txt`
- Show markdown table from stdout
- Commit results to GitHub

**注意**: Notebook（Jupyter）环境下用 PowerShell 执行，不用 Bash（路径格式不同）。

See [[mvp-workflow]] for complete rules and [[output-table-preserves-input-order]] for ordering rule.
