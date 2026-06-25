# ICRUSH Influencer Vetting Pipeline — v0.7 Rules

> 最后更新: 2026-06-17

## 完整判定流程

### STAGE 0：KOL 查重（新增）
调用实习生部署的 Lambda API (`POST /`)，传入 `{account, platform}`:
- 返回 `summary` 包含 "不重复" → 放行，继续 pipeline
- 返回 `summary` 包含 "有重复" → 🟡 已入库，跳过后续（不消耗 Apify 费用）

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

### STAGE 2：Posts 抓取
对存活者抓 20 条最新 posts，计算 caption 德语率、近3月平均浏览、商单分类。

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
- **品牌官方号过滤**: 当前无代码实现，需人肉判定；欢迎补充品牌名单到 `wordlists.py`
