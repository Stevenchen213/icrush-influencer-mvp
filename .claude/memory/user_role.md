---
name: user-role
description: ICRUSH intern sourcing German+Austrian IG/TT jewelry/fashion influencers; v0.6 rules locked-in 2026-06-16
metadata:
  node_type: memory
  type: user
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

User is an intern at **ICRUSH** (国内办公室). Daily job: sourcing IG + TikTok influencers for German jewelry/fashion brand collaborations. Uses 飞书 for shared dedup table. Uses **Wednesday (Upfluence)** for audience demographics.

## Target market: 德国 + 奥地利 (DE + AT)

## v0.6 hard rules (2026-06-16 定版)

See [[mvp-workflow]] for complete implementation. Quick reference:

1. **男博主直接不要** — 通过 IG fullName 匹配男名列表（DE/EN/TR），情侣名（Anna & Tom）不拒
2. **地区** = DE or AT：
   - Wednesday 有数据 → 完全采信
   - Wednesday 无数据 → bio DE/AT + caption ≥ 25% → ✅ 直接过
   - bio DE/AT + caption < 25% → 🟡 复查
   - bio 无 + caption ≥ 25% → ✅ 语言通过
   - bio 无 + caption < 25% → ❌ 淘汰
3. **粉丝**: TT 10K-500K / IG 10K-300K。 < 10K = 置换组
4. **帖数**: IG/TT ≥ 200（IG reel 占比 >50% 可豁免到 150）
5. **近3月视频平均浏览**: ≥ 4000 OK / 2000-3999 置换组 / < 2000 PASS
6. **职业**: 认证为艺术家/律师 → 直接 PASS
7. **女粉占比**: ≤50% 男粉（>100K 放宽到 ≤65%）

## 偏好筛选（非硬性）

- 白人年轻美女达人
- 时尚/美妆/生活方式类，不要宠物/DIY/品牌官号
- 要有口播商单（不只是图文 #ad）
- IG 为主，TT 也可以

## Anti-targets

- 民族服饰类 / 游戏/食物/风景/ASMR/亲子类
- 奢侈品炫富类 / 首饰品牌创始人（竞品）
- 艺术家/律师（已纳入硬性规则）

See [[mvp-workflow]] for full pipeline, [[always-use-run-batch]] for execution instructions.
