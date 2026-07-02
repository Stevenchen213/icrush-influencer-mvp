# ICRUSH Influencer Vetting Pipeline — v0.9.2 Rules

> 最后更新: 2026-07-02

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
| 1 | **男博主** | `detect_male_by_name(fullName, bio, username)` 四重覆盖：名字 + bio + username（含复合用户名子串检测≥5字符男名）+ 称呼前缀，情侣名不拒 | ❌ 男博主 |
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

**IG**：Reel Scraper 抓取近 3 月最近 40 条 Reel（服务端 `onlyPostsNewerThan: "3 months"`）
- 平均浏览量：基于前 10 条 Reel 的播放量计算
- 商单分类：基于全部 40 条 Reel 的 caption 分析
- 如近 3 月无 Reel → 🟡 人工复查

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
| 粉丝 <10K 或浏览 2K-4K | 🟡 推荐置换 |
| bio DE+caption<25%（无 Wednesday） | 🟡 复查 |
| 任一硬条件不满足 | ❌ 否 |

## 男博主检测

- 方法：四重覆盖 —— `fullName` token + `bio` + `username`（含复合用户名子串检测，≥5字符男名）+ 称呼前缀
- 复合用户名：如 `createdbytaavi` 中 `taavi` 通过子串匹配识别
- 词库位置：`icrush/wordlists.py` `MALE_FIRST_NAMES`
- 覆盖语言：German + English + Turkish + Finnish/Estonian
- 情侣名（含 & / und）→ 不拒，按女博主处理

## 备注

- **偏好筛选 / Anti-targets**: 见 `AGENT.md`「重要约定」章节，非硬性规则，人工选人时参考
- **运行方式 / 依赖 / 语言检测**: 见项目 `README.md`
- **版本演进**: 见 `README.md`「版本演进」
- **品牌/媒体号过滤**: STAGE 1 打分制自动检测（域名后缀、官方号标识、商业词、协会/俱乐部/球队信号、狂欢节信号、用户名前后缀），命中 → ❌ 品牌官方号，详见 `icrush/judges.py` `is_brand_account()`
- **品牌检测 v0.9.2 新增信号**：
  - 协会：verein(3), e.V.(3), burschenverein(3), traditionsverein(3), sportverein(3)
  - 旅游公司：jugendreisen(3), jugendreise(3)
  - 狂欢节：karneval(3), karnevalsverein(3), karnevalsclub(3), fasching(3), faschingsverein(3), närrisch(2), narren(2)
  - 体育俱乐部用户名前缀：sv, fc, tsv, sc, vfl, vfb, sg（startswith + ≥2后缀字符 → +3）
  - 用户名后缀：新增 reisen
- **商单分类器** (v0.9.2)：词边界阈值 ≤5 字符统一整词匹配，与品类检测对齐，消除 "ringe"→"dringend" 等子串误伤
