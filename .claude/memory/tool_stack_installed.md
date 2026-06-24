---
name: tool-stack-installed
description: Complete list of MCP servers, plugins, and Chrome extensions installed on this machine as of 2026-06-05 for ICRUSH influencer pipeline
metadata:
  node_type: memory
  type: reference
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

Snapshot of installed tooling for the influencer-vetting MVP. Before assuming any of these is gone, verify with the listed command first.

## MCP servers (in `C:\Users\yaxua\.claude.json`)

| MCP | Scope | Verify | Purpose |
|-----|-------|--------|---------|
| **apify** | local (project=C:\Users\yaxua) | `claude mcp list` shows `apify: ... ✓ Connected` | Primary scraping for IG/TT |
| **playwright** | user | same | Backup browser automation (clean Chromium, no login state) |

Apify added with: `claude mcp add --transport http apify "https://mcp.apify.com?tools=actors,docs,apify/rag-web-browser" -H "Authorization: Bearer <token>"` — token in `.claude.json`.

Playwright added with: `cmd /c "claude mcp add playwright -s user -- npx -y @playwright/mcp@latest"` (had to use `cmd /c` to bypass PowerShell `-y` parsing).

## Claude Code plugins (in `C:\Users\yaxua\.claude\settings.json` enabledPlugins)

| Plugin | Source | Status | Purpose |
|--------|--------|--------|---------|
| **frontend-design@claude-plugins-official** | official marketplace | enabled (unused for her work) | UI generation — irrelevant to her job; she asked to install it but it's dead weight for influencer sourcing |
| **superpowers@claude-plugins-official** | official marketplace | enabled | On-demand only per [[superpowers-on-demand]] |
| **web-access@web-access** | marketplace add `https://github.com/eze-is/web-access` | enabled | CDP-based browser automation using her existing Chrome (the only way to use the Wednesday extension programmatically) |

Verify with: `claude plugin list`

## Chrome setup (on her laptop)

- **CDP debugging enabled** on her Chrome (toggled at `chrome://inspect/#remote-debugging`, port 9222). Required by web-access skill. Done 2026-06-05 morning.
- **Chrome user profile**: `C:\Users\yaxua\AppData\Local\Google\Chrome\User Data\Profile 7` (only profile she uses)
- **Wednesday extension installed**: Real name = "Influencer Analytics by Wednesday" (purple W logo). User informally calls it "upinfluencer". Injects analytics panel onto TT/IG profile pages — shows audience demographics including male/female split (needed for v0.4 rule 6, 二期).

## web-access skill config

- `WEB_ACCESS_BROWSER=chrome` set in `C:\Users\yaxua\.claude\plugins\cache\web-access\web-access\2.5.2\config.env`
- CDP Proxy: started lazily by `scripts/check-deps.mjs`, listens on `http://localhost:3456`
- Don't kill it between sessions — re-attaching to the user's Chrome requires the user to re-authorize the CDP toggle

## What's NOT installed (deferred)

- **飞书 (Lark) MCP** — user paused this on 2026-06-05 multiple times. Plan was: she creates "Claude MVP 测试" 自建应用 in 飞书开放平台 with `bitable:app` scope, adds it only to a NEW test 多维表格 (NOT the team's main 查重表), gives me App ID + Secret. We can pick this up when she's ready to skip the manual copy-paste step.
- **claude-mem** (https://github.com/thedotmack/claude-mem) — user asked about it 2026-06-05; I recommended skipping because it overlaps with the built-in memory system she's already using (this file).
- **IG comments scraper** — not picked yet. See [[mvp-workflow]] for what we need.

## Settings location reference

- User settings: `C:\Users\yaxua\.claude\settings.json` (contains `ANTHROPIC_API_KEY` in plaintext + `ANTHROPIC_BASE_URL=https://cn.xingsuancode.com`, the Chinese proxy)
- MCP config: `C:\Users\yaxua\.claude.json`
- Plugins cache: `C:\Users\yaxua\.claude\plugins\cache\`
- Memory: `C:\Users\yaxua\.claude\projects\C--Users-yaxua\memory\`
