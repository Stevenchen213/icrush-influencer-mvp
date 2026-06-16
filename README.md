# ICRUSH 德国/奥地利达人筛选 MVP

ICRUSH 国内办公室自动化达人调研流水线 —— 输入 Instagram / TikTok 主页链接，按硬性条件自动判定 ✅ 是 / ❌ 否 / 🟡 置换组 / 🟡 复查，省去手动核对时间。

**当前版本**：v0.6 (2026-06-16)

## 硬性规则速览

| # | 条件 | 阈值 |
|---|------|------|
| 1 | 男博主 | 名字匹配 DE/EN/TR 男名 → 直接 ❌（情侣名不拒） |
| 2 | 私密账户 | → ❌ |
| 3 | 帖数 | < 200（IG reel 占比 >50% 可豁免到 150） |
| 4 | 粉丝 | IG 1K-300K / TT 1K-500K（<10K 置换组） |
| 6 | 地区 | Wednesday 优先，fallback: bio DE/AT + caption ≥25% |
| 7 | 浏览量 | ≥4000 通过 / 2000-3999 置换 / <2000 否 |
| 8 | 女粉占比 | 男粉 ≤50%（>100K 放宽到 ≤65%） |

完整规则：**[docs/rules.md](docs/rules.md)**

## 语言检测

- 使用 `langdetect` 库（Google 算法）
- 土耳其语、法语等非 DE/EN → 映射为 unknown，不计入 caption 比例
- 已修复：旧词表法会把土耳其语（含 ü/ö）误判为德语

## 三级容灾

```
Apify 失败  →  Playwright headless 自动兜底
Wednesday 缓存未命中  →  自动 Playwright 实时查询 API
任何外部服务挂  →  不阻塞主流程
```

## 项目结构

```
icrush-influencer-mvp/
├── icrush/                     # 核心库
│   ├── config.py               → 阈值常量
│   ├── wordlists.py            → 词典（德语/英语/城市/男名）
│   ├── language.py             → 语言检测(langdetect)、地区、职业、性别
│   ├── judges.py               → 短路淘汰 + caption 判定
│   ├── wednesday.py            → 缓存读写 + 自动实时查询
│   ├── pipeline.py             → 三阶段编排 + Playwright 兜底
│   ├── classifier.py           → 商单分类
│   ├── gender.py               → 头像检测预留（需 API key）
│   └── report.py               → Markdown 表格输出
├── scripts/                    # 入口脚本
│   ├── run_batch.py            → 主流水线
│   └── refresh_wednesday_cache.py → 手动刷新缓存
├── docs/
│   └── rules.md                → 完整规则文档
├── results/                    # 历次跑的结果
├── data/                       # 抓回来的原始数据 + 缓存（gitignored）
├── .env                        # 环境变量（gitignored）
├── .env.example
├── pyproject.toml              # 依赖清单
└── README.md
```

## 安装

```bash
git clone <repo-url>
cd icrush-influencer-mvp
pip install -e .
playwright install chromium
```

配置 `.env`：
```
APIFY_TOKEN=your_token_here
WEDNESDAY_EMAIL=it@icrush.de
WEDNESDAY_PASSWORD=xxx
```

## 使用

```powershell
# Python 路径
$py = "C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe"

# 从文件批量跑
& $py scripts/run_batch.py data/input.txt

# 从 stdin 单条跑
echo "https://www.instagram.com/x/" | & $py scripts/run_batch.py -

# 手动刷新 Wednesday 缓存
& $py scripts/refresh_wednesday_cache.py username1 username2
```

## 流水线步骤

1. **解析 URL**（TT + IG 混排，去重保留顺序）
2. **STAGE 1**：Apify 抓 profile metadata → 短路淘汰（按上述顺序）
3. **STAGE 1.5**：Wednesday 查询（缓存优先，缓存未命中自动 Playwright 实时查询）
4. **STAGE 2**：对存活者抓 20 posts，计算 caption 德语率、均浏览、商单
5. **输出表格**（含 Caption 德语列），存档 `results/<日期>_batch<N>_<seq>.md`
6. **打印 Apify 成本**

## 判定矩阵

| 条件 | 标记 |
|------|------|
| 全通过 + 有商单 | ✅ 是 |
| 全通过 + 无商单 | 🟡 复查 |
| 粉丝 <10K 或浏览 2K-4K | 🟡 置换组 |
| bio DE + caption < 25%（无 Wednesday） | 🟡 复查 |
| 任一硬条件不满足 | ❌ 否 |

## 依赖

```
httpx>=0.27, langdetect>=1.0, playwright>=1.60, python-dotenv>=1.0
```

## 安全

- **永远不要 commit `.env`**（含 Apify token）
- 抓回来的数据属个人信息，**永远不要 commit `data/`**
- 仓库设为 **Private**

## 版本演进

- **v0.1** (2026-06-04)：第一版规则，基本指标
- **v0.2** (2026-06-05)：加 1K-10K 置换组分层
- **v0.3** (2026-06-05)：调整粉丝上限（TT 500K / IG 300K）
- **v0.4** (2026-06-08)：职业筛选 + 浏览量分层 + 评论检查；修复 TT 语言占比 bug
- **v0.5** (2026-06-10)：Wednesday API 集成，男女粉检测，商单分类
- **v0.6** (2026-06-16)：**Python 重写 + 多项规则变更**
  - Node.js → Python（`icrush/` 模块化）
  - 语言检测：词表 → `langdetect`（修复土耳其语误判）
  - 男博主硬规则：名字匹配
  - bio DE + caption < 25% → 🟡 复查（不再调评论 API，省钱）
  - Wednesday 缓存未命中自动实时查询
  - Apify 失败自动 Playwright 兜底
  - 表格新增 Caption 德语列
  - GBK 编码兼容修复

## 协作

修改规则时：
1. 改 `docs/rules.md`（描述）
2. 改 `icrush/` 下对应模块（Python 实现）
3. Commit message 写明规则变化
4. Push
