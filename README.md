# ICRUSH 德国/奥地利达人筛选 MVP

ICRUSH 国内办公室自动化达人调研流水线 —— 输入种子达人，自动发现类似达人 → Pipeline 硬性筛选 → 输出判定报表。

**当前版本**：v0.7 (2026-06-24)

## 完整工作流

```bash
# 一条命令：发现 + 筛选全自动
node scripts/fetch_similar_accounts_v3.mjs --auto-pipeline seed1 seed2 seed3

# 输出：results/YYYY-MM-DD_batchN_seq.md（Markdown 报表）
```

### 分步说明

| 步骤 | 命令 | 费用 |
|------|------|------|
| 1. 启动 Chrome CDP | `chrome --remote-debugging-port=9222` | 免费 |
| 2. 提取类似达人 | `node scripts/fetch_similar_accounts_v3.mjs seed1 seed2` | 免费 |
| 3. 筛选 | `python scripts/run_batch.py data/input_similar_combined.txt` | Apify 按量 |

详细方法见 **[docs/similar_accounts_guide.md](docs/similar_accounts_guide.md)**

## 硬性规则

| # | 条件 | 阈值 |
|---|------|------|
| 1 | 男博主 | 名字匹配 DE/EN/TR 男名 → ❌（情侣名不拒） |
| 2 | 私密账户 | → ❌ |
| 3 | 帖数 | < 200（IG reel >50% 可豁免到 150） |
| 4 | 粉丝 | IG 1K-300K / TT 1K-500K（<10K 置换组） |
| 5 | Caption 德语 | ≥ 25%（bio DE 时），不足则 🟡 复查 |
| 6 | 地区 | Wednesday 优先，fallback: bio DE/AT + caption ≥25% |
| 7 | 浏览量 | ≥4000 / 2000-3999 / <2000 |
| 8 | 男粉占比 | ≤50%（>100K 放宽到 ≤65%） |

完整规则：**[docs/rules.md](docs/rules.md)**

## Pipeline 流程

```
STAGE 0  → KOL 查重（Lambda API + 飞书 + 本地）
STAGE 1  → Apify 抓 Profile → 短路淘汰
STAGE 1.5 → Wednesday 受众查询（缓存优先，未命中自动实时查询）
STAGE 2  → Apify 抓 20 posts → 浏览量 + caption 德语率 + 近3月商单
         → 最终判定 ✅/❌/🟡置换/🟡复查
```

## 判定矩阵

| 条件 | 标记 |
|------|------|
| 全通过 + 有商单 | ✅ 是 |
| 全通过 + 无商单 | 🟡 复查 |
| 粉丝 <10K 或 浏览 2K-4K | 🟡 置换组 |
| bio DE + caption <25% | 🟡 复查 |
| 查重命中 | 🟡 已入库 |
| 任一硬条件不满足 | ❌ 否 |

## 项目结构

```
icrush-influencer-mvp/
├── icrush/                     # 核心 Python 库
│   ├── pipeline.py             → 三阶段编排
│   ├── judges.py               → 短路淘汰 + caption 判定
│   ├── classifier.py           → 商单分类（美妆/服饰/珠宝/食品/科技）
│   ├── language.py             → 语言检测 + 地区识别 + 性别判断
│   ├── wordlists.py            → 词典（城市/男名）
│   ├── wednesday.py            → 缓存读写 + 自动实时查询
│   ├── dedup.py                → KOL 查重 API
│   ├── apify.py                → Apify API 客户端
│   ├── report.py               → Markdown 表格输出
│   ├── config.py               → 阈值常量
│   └── airtable.py / feishu.py → 排除名单 fallback
├── scripts/
│   ├── run_batch.py            → Pipeline 主入口
│   ├── fetch_similar_accounts_v3.mjs  → 类似账户提取（Node.js）
│   ├── refresh_wednesday_cache.py     → 手动刷新缓存
│   ├── fetch_batch.py          → 手动抓取 Apify dataset
│   └── fetch_comments.py       → 手动抓取评论
├── docs/
│   ├── rules.md                → 完整规则文档
│   └── similar_accounts_guide.md → 类似账户提取指南
├── results/                    # 历次跑的结果
├── data/                       # 抓取数据 + 缓存（gitignored）
├── .claude/memory/             # AI agent 上下文
├── AGENT.md / CLAUDE.md        # AI agent 入口
├── pyproject.toml
└── README.md
```

## 安装

```bash
git clone https://github.com/Stevenchen213/icrush-influencer-mvp.git
cd icrush-influencer-mvp
pip install -e .
playwright install chromium
npm install
```

配置 `.env`：
```
APIFY_TOKEN=your_token_here
WEDNESDAY_EMAIL=it@icrush.de
WEDNESDAY_PASSWORD=xxx
DEDUP_API_TOKEN=xxx
DEDUP_API_URL=xxx
```

## 依赖

```
httpx>=0.27, langdetect>=1.0, playwright>=1.60, python-dotenv>=1.0
```

## 安全

- **永远不要 commit `.env`**（含 API token）
- **永远不要 commit `data/`**（含个人信息）
- 仓库设为 **Private**

## 版本演进

- **v0.1-v0.6** (2026-06-04~16)：Python 重写、规则迭代、Wednesday 集成
- **v0.7** (2026-06-17)：KOL 查重 API 集成
- **v0.7.1** (2026-06-24)：**重大更新**
  - 发现 IG 类似账户新方法（三步弹窗法），每种子 ~80 达人，免费
  - 删除所有旧发现方式（hashtag/snowball/suggested/Wednesday discovery）
  - 删除 STAGE 3 评论检查（死代码）
  - 新增 `--auto-pipeline` 一键全自动
  - 删除 drissionpage 依赖
  - 配置文件精简
