# ICRUSH Influencer Vetting Pipeline — v0.8.2 Rules

> 最后更新: 2026-06-26

## 完整判定流程

### STAGE 0：KOL 查重

**主路径**：调用阿里云查重 API，传入 `{account, platform, developer_name, check_only: true}`：
- `check_only: true` → 只查不写，不会自动录入 KOL 总表
- 内部对比 4 个库：KOL博主记录总表 / KOC红人库 / 实习生KOL查重表 / AWS KOC数据库
- 返回 `summary` 包含 "不重复" → 放行，继续 pipeline
- 返回 `summary` 包含 "有重复" → 🟡 已入库，跳过后续（不消耗 Apify 费用）

**补充路径**：飞书结果表查重（需 `FEISHU_SYNC_ENABLED=1`）
- 拉取飞书"达人筛选结果"表中全部用户名，匹配命中 → 🟡 已入库

### STAGE 0.5：解析 URL
提取 IG / TT 用户名，去重。

### STAGE 0.6：Resilience
- Apify IG profile 抓取失败 → 自动 Playwright 兜底（headless 浏览器解析 meta 标签）
- Wednesday 缓存未命中 → 自动 Playwright 实时查询 API
- 任何外部服务挂了都不阻塞主流程

### STAGE 1：Profile 抓取 + 短路淘汰

按以下顺序检查，命中即停止（省钱优先）：

| # | 检查项 | 条件 | 失败→ |
|---|--------|------|-------|
| 1 | **男博主** | `detect_male_by_name(fullName)` 匹配男名列表（DE/EN/TR），情侣名（Anna & Tom）不拒 | ❌ 男博主 |
| 2 | **私密账户** | private = true | ❌ 私密 |
| 3 | **帖数** | < 200（IG reel 占比 >50% 可豁免到 150） | ❌ 帖数 |
| 4 | **粉丝** | < 1K 或 IG > 300K / TT > 500K | ❌ 粉丝 |

### STAGE 1.5：Wednesday 受众查询

搜索策略：`field: 'all'` 全字段搜索（用户名/显示名均可命中）
```
缓存命中 → 直接用 ✅
缓存未命中 → 自动 Playwright 实时查询 → 存入缓存
```

**Wednesday 有数据 → 完全采信**（跳过 caption + 评论检查）

**Wednesday 无数据 → fallback**：

| bio/about | caption 德语 | 结果 |
|-----------|-------------|------|
| DE/AT | ≥ 25% | ✅ 直接过 |
| DE/AT | < 25% | 🟡 复查 |
| 无 | ≥ 25% | ✅ 语言通过 |
| 无 | < 25% | ❌ 淘汰 |

### STAGE 2：Posts 抓取 + 最终判定

**IG**：Reel Scraper 抓取近 3 月最近 10 条 Reel（服务端 `onlyPostsNewerThan: "3 months"`）
- 平均浏览量：基于这 10 条 Reel 的播放量计算
- 商单分类：基于同一批 Reel 的 caption 分析
- 如近 3 月无 Reel，avgViews=None → 🟡 人工复查

**TT**：抓取 20 条视频 → 近 3 月内视频优先 → 不足则 fallback 到全部
- 平均浏览量：基于筛选后视频的 playCount

→ 输出最终判定（✅/❌/🟡置换/🟡复查）。

> **STAGE 3（评论检查）已于 v0.7.1 移除** — 无实际价值，浪费 Apify 费用。

## 阈值

| 参数 | 值 |
|------|-----|
| IG 粉丝 | 1K - 300K |
| TT 粉丝 | 1K - 500K |
| 帖数下限 | 200（reel 型 150） |
| Caption 德语 | ≥ 25%（bio DE 时） |
| 均浏览 | ≥ 4000 通过 / 2000-3999 置换 / <2000 否 |
| 男粉上限 | ≤50%（>100K 放宽到 65%） |
| Wednesday DE+AT 受众合计 | ≥ 35% |

## 最终判定

| 条件 | 标记 |
|------|------|
| 全通过 + 有商单 | ✅ 是 |
| 全通过 + 无商单 | 🟡 复查 |
| 粉丝 <10K 或浏览 2K-4K | 🟡 置换组 |
| bio DE+caption<25%（无 Wednesday） | 🟡 复查 |
| 任一硬条件不满足 | ❌ 否 |

## 男博主检测

- 方法：匹配 IG `fullName` 首 token 到 `MALE_FIRST_NAMES` 词库
- 词库位置：`icrush/wordlists.py`
- 覆盖语言：German + English + Turkish
- 情侣名（含 & / und）→ 不拒，按女博主处理

## 备注

- **偏好筛选 / Anti-targets**: 见 `AGENT.md`「重要约定」章节，非硬性规则，人工选人时参考
- **运行方式 / 依赖 / 语言检测**: 见项目 `README.md`
- **版本演进**: 见 `README.md`「版本演进」
- **品牌/媒体号过滤**: STAGE 1 打分制自动检测（域名后缀、官方号标识、商业词、媒体/综艺模式），命中 → ❌ 品牌官方号，详见 `icrush/judges.py` `is_brand_account()`
