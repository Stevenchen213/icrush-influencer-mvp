---
name: superpowers-on-demand
description: "User wants superpowers skills invoked only when actually relevant (dev/code work), not on every conversation turn"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

For this user, **invoke superpowers skills (brainstorming, writing-plans, TDD, frontend-design, debugging, etc.) only when the task is actually software development / coding related** — not on every turn, even though `using-superpowers` says it should be invoked before every response.

**Why:** The user's work (see [[user-role]]) is Instagram/TikTok influencer sourcing and summarization at ICRUSH, not software development. The superpowers skill set is dev-oriented (writing plans, TDD, debugging, frontend, git worktrees, code review). Forcing the full superpowers ritual on every turn is wasted overhead with zero benefit for her actual workflow. The user explicitly chose option B ("按需调用") over A (strict rule-following) and C (uninstall) on 2026-06-04.

**How to apply:**
- Default: skip the superpowers skills for routine conversation, sourcing advice, summarization, German translation, tooling recommendations, etc.
- Invoke `superpowers:brainstorming` only if she explicitly asks to build software, design a system, or write code (e.g. if the "商单 stats tool" idea from earlier conversations becomes real).
- Invoke `superpowers:writing-plans` / `TDD` / `debugging` / `frontend-design` only when actually coding.
- Don't apologize or call out the skipped skill — she already gave the standing instruction.
- If a future task is genuinely dev-related, do invoke the relevant skill.
