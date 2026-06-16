# ICRUSH Influencer Vetting Pipeline — v0.6 Rules

> 最后更新: 2026-06-16

## 完整判定流程

### STAGE 0：解析 URL
提取 IG / TT 用户名，去重。

### STAGE 0.5：Resilience
- Apify IG profile 抓取失败 → 自动 Playwright 兜底（headless 浏览器解析 meta 标签）
- Wednesday 缓存未命中 → 自动 Playwright 实时查询 API
- 任何外部服务挂了都不阻塞主流程

### STAGE 1：Profile 抓取 + 短路淘汰

按以下顺序检查，命中即停止（省钱优先）：

| # | 检查项 | 条件 | 失败→ |
|---|--------|------|-------|
| 1 | **男博主** | `detect_male_by_name(fullName)` 匹配男名列表（DE/EN/TR），情侣名（Anna & Tom）不拒 | ❌ 男博主 |
| 2 | **职业** | Lawyer / Artist → 直接拒 | ❌ 职业 |
| 3 | **私密账户** | private = true | ❌ 私密 |
| 4 | **帖数** | < 200（IG reel 占比 >50% 可豁免到 150） | ❌ 帖数 |
| 5 | **粉丝** | < 1K 或 IG > 300K / TT > 500K | ❌ 粉丝 |

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
| Wednesday DE 受众 | ≥ 35% |

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

## 偏好筛选（非硬性）

- 白人年轻美女达人
- 时尚/美妆/生活方式类，不要宠物/DIY/品牌官号
- 要有口播商单（不只是图文 #ad）
- IG 为主，TT 也可以

## Anti-targets

- 民族服饰类 / 游戏/食物/风景/ASMR/亲子类
- 奢侈品炫富类 / 首饰品牌创始人（竞品）
- 艺术家/律师（已纳入硬性规则）

## 运行方式

```bash
# Python 路径（不用 Windows Store 版）
$py = "C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe"

# 从文件批量跑
& $py scripts/run_batch.py data/input.txt

# 从 stdin 单条跑
echo "https://www.instagram.com/x/" | & $py scripts/run_batch.py -
```

## 代码结构

```
icrush/
  config.py      → 阈值常量
  wordlists.py   → 词典（德语/英语/城市/男名/品牌）
  language.py    → 语言检测（langdetect 库）、地区检测、职业检测、性别检测、URL解析
  judges.py      → 短路淘汰 + caption 判定
  wednesday.py   → 缓存读写 + 实时查询（Playwright）
  pipeline.py    → 三阶段编排
  classifier.py  → 商单分类
  report.py      → Markdown 表格输出

scripts/
  run_batch.py               → 主入口
  refresh_wednesday_cache.py  → 手动刷新缓存
```

## 语言检测

- 使用 `langdetect` 库（Google 语言检测算法）
- 土耳其语、法语等非 DE/EN 语言 → 映射为 unknown，不计入 caption 比例分母
- 已修复：之前词表检测会把土耳其语（含 ü/ö）误判为德语

## 依赖

```
httpx>=0.27, langdetect>=1.0, playwright>=1.60, python-dotenv>=1.0
```

## 已知限制

- Wednesday 月度 3000 views 配额（2026-06-16 已耗尽，7月1日重置）
- GitHub 从中国推送不稳（需 VPN）
- Windows 终端需 UTF-8 编码
