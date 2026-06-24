---
name: mvp-workflow
description: v0.6 automated influencer-vetting pipeline — complete region/gender/caption rules as of 2026-06-16
metadata:
  node_type: memory
  type: project
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

## 项目位置

`C:\Users\yaxua\icrush-influencer-mvp\` — GitHub: https://github.com/Stevenchen213/icrush-influencer-mvp.git

Python 路径: `C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe`（不用 Windows Store 版）

## 运行方式

```
python scripts/run_batch.py data/input.txt          # 从文件读取
echo "https://www.instagram.com/x/" | python scripts/run_batch.py -  # 从 stdin
```

## 完整判定流程（v0.6，2026-06-16 定版）

### STAGE 0：解析 URL
- 提取 IG / TT 用户名，去重

### STAGE 1：Profile 抓取 + 短路淘汰（按顺序）

| # | 检查项 | 条件 | 失败→ |
|---|--------|------|-------|
| 1 | **男博主** | `detect_male_by_name(fullName)` 匹配男名列表（DE/EN/TR），情侣名（Anna & Tom）不拒 | ❌ 男博主 |
| 2 | **职业** | Lawyer / Artist → 直接拒 | ❌ 职业 |
| 3 | **私密账户** | private = true | ❌ 私密 |
| 4 | **帖数** | < 200（IG reel 占比 >50% 可豁免到 150） | ❌ 帖数 |
| 5 | **粉丝** | < 1K 或 IG > 300K / TT > 500K | ❌ 粉丝 |

### STAGE 1.5：Wednesday 受众查询

```
首先读本地缓存（data/wednesday_cache.json）
  → 缓存命中 → 直接用 ✅
  → 缓存未命中 → 自动启动 Playwright 实时查询 Wednesday API
    → 查到 → 存入缓存 ✅
    → 查不到 → 走 fallback
```

**Wednesday 有数据时**：
- 统一判定：地区 + 性别（≤50% 男粉，>100K 放宽到 ≤65%）
- 完全跳过 caption 和评论检查（最省钱）

**Wednesday 无数据时 → fallback**：

| bio/about | caption 德语 | 结果 | 调评论API |
|-----------|-------------|------|-----------|
| DE/AT | ≥ 25% | ✅ 直接过 | ❌ |
| DE/AT | < 25% | 🟡 复查 | ❌ |
| 无 | ≥ 25% | ✅ 语言通过 | ❌ |
| 无 | < 25% | ❌ 淘汰 | ❌ |

**重要**：评论 STAGE 3 已完全移除（2026-06-16 改为 bio DE+caption<25% → 🟡 复查），节省 ~$0.44/人。

### STAGE 2：Posts 抓取
- 对存活者抓 20 条最新 posts
- 计算 caption 德语率、近3月平均浏览、商单分类

### 阈值总览

| 参数 | 值 |
|------|-----|
| IG 粉丝 | 1K - 300K |
| TT 粉丝 | 1K - 500K |
| 帖数下限 | 200（reel 型 150） |
| Caption 德语 | ≥ 25%（bio DE 时） |
| 评论德语 | ≥ 60%（不再使用） |
| 均浏览 | ≥ 4000 通过 / 2000-3999 置换 / <2000 否 |
| 男粉上限 | ≤50%（>100K 放宽到 65%） |
| Wednesday DE | ≥ 35% |

### 最终判定

| 条件 | 标记 |
|------|------|
| 全通过 + 有商单 | ✅ 是 |
| 全通过 + 无商单 | 🟡 复查 |
| 粉丝 <10K 或浏览 2K-4K | 🟡 置换组 |
| bio DE+caption<25%（无 Wednesday） | 🟡 复查 |
| 任一硬条件不满足 | ❌ 否 |

### 男博主检测

- 方法：匹配 IG `fullName` 首 token 到 `MALE_FIRST_NAMES` 词库
- 词库：`icrush/wordlists.py` — German + English + Turkish 男名
- 情侣名（含 & / und）→ 不拒，按女博主处理

## 代码结构

```
icrush/
  config.py      → 阈值常量
  wordlists.py   → 词典（德语/英语/城市/男名/品牌）
  language.py    → 语言检测、地区检测、职业检测、性别检测、URL解析
  judges.py      → 短路淘汰 + caption 判定
  wednesday.py   → 缓存读写 + 实时查询（Playwright）
  pipeline.py    → 三阶段编排
  classifier.py  → 商单分类
  report.py      → Markdown 表格输出

scripts/
  run_batch.py               → 主入口
  refresh_wednesday_cache.py  → 手动刷新缓存
  fetch_batch.py / fetch_comments.py / extract_urls.py  → 辅助
```

## 已知限制

- Wednesday 月度 3000 views 配额（2026-06-16 已耗尽，7月1日重置）
- GitHub 从中国常无法连接（需 VPN）
- Windows 终端必须用 UTF-8 编码（所有脚本已加 `sys.stdout.reconfigure`）
