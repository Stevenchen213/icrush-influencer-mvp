# ICRUSH 德国/奥地利达人筛选 MVP

ICRUSH 国内办公室自动化达人调研流水线 —— 输入种子达人，自动发现类似达人 → Pipeline 硬性筛选 → 输出判定报表。

**当前版本**：v0.8.0 (2026-06-29)

## 完整工作流

```bash
# 批量种子（逐个安全模式）
python scripts/_run_seeds_one_by_one.py  # 读取 data/batch_72.txt，逐个跑完

# 单个种子
python scripts/run_full_workflow.py seed1

# 输出：results/YYYY-MM-DD_batchN_seq.md（Markdown 报表）
```

### 分步说明

| 步骤 | 命令 | 费用 |
|------|------|------|
| 1. 启动 Chrome CDP | `python scripts/ensure_chrome_cdp.py`（自动） | 免费 |
| 2. 提取类似达人 | `node scripts/fetch_similar_accounts_v3.mjs seed1 seed2` | 免费 |
| 3. 筛选 | `python scripts/run_batch.py data/input_similar_combined.txt` | Apify 按量 |

详细方法见 **[docs/similar_accounts_guide.md](docs/similar_accounts_guide.md)**

## 硬性规则

| # | 条件 | 阈值 |
|---|------|------|
| 1 | 男博主 | 名字匹配 DE/EN/TR 男名 → ❌（情侣名不拒） |
| 2 | 品牌/媒体号 | 用户名/简介含品牌标识（_de, .de, official, shop 等）→ ❌ |
| 3 | 私密账户 | → ❌ |
| 4 | 帖数 | < 200（IG reel >50% 可豁免到 150） |
| 5 | 粉丝 | IG 1K-300K / TT 1K-500K（<10K 置换组） |
| 6 | Caption 德语 | ≥ 25%（bio DE 时），不足则 🟡 复查 |
| 7 | 地区 | Wednesday 优先，fallback: bio DE/AT + caption ≥25% |
| 8 | 浏览量 | ≥4000 / 2000-3999 / <2000（仅计 Reel/Video；无视频帖 → 🟡 人工复查） |
| 9 | 男粉占比 | ≤50%（>100K 放宽到 ≤65%） |

完整规则：**[docs/rules.md](docs/rules.md)**

## Pipeline 流程

```
STAGE 0  → KOL 查重（阿里云 API 4库 + 飞书结果表，check_only 只查不写）+ 本地排除名单
STAGE 1  → Apify 抓 Profile → 短路淘汰（含品牌号检测）+ Apify 结果缓存
STAGE 1.5 → Wednesday 受众查询（@用户名 + social_media.username 精确匹配，fallback: all 全字段搜索）
STAGE 2  → IG: 抓 20 条 → 过滤 Reel/Video 算平均浏览 / TT: 20 条 → 3 月过滤
         → 浏览量 + caption 德语率 + 近3月商单 → 最终判定 ✅/❌/🟡置换/🟡复查
         → 飞书多维表格自动同步（需 FEISHU_SYNC_ENABLED=1）
```

## 飞书多维表格自动同步

开启 `FEISHU_SYNC_ENABLED=1` 后，管道跑完自动同步结果到飞书：
- **STAGE 0**：查询飞书结果表已有用户 → 命中则"已入库"跳过
- **管道末尾**：新结果 append 到多维表格（13 字段：用户名/平台/粉丝/帖数/地区/浏览量/女粉/Caption/商单/判定/原因/批次/日期/链接）
- 同步失败不阻塞管道，关掉 `FEISHU_SYNC_ENABLED=0` 即可

## 判定矩阵

| 条件 | 标记 |
|------|------|
| 全通过 + 有商单 | ✅ 是 |
| 全通过 + 无商单 | 🟡 复查 |
| 粉丝 <10K 或 浏览 2K-4K | 🟡 置换组 |
| bio DE + caption <25% | 🟡 复查 |
| 查重命中（KOL API / 飞书结果表） | 🟡 已入库 |
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
│   ├── gender.py               → 头像性别检测（Claude Vision）
│   └── airtable.py / feishu.py → 排除名单 fallback
├── scripts/
│   ├── run_batch.py            → Pipeline 主入口
│   ├── run_full_workflow.py    → 端到端编排（CDP→提取→pipeline，含重试）
│   ├── fetch_similar_accounts_v3.mjs  → 类似账户提取（Node.js）
│   ├── ensure_chrome_cdp.py    → Chrome CDP 自动生命周期管理
│   ├── refresh_wednesday_cache.py     → 手动刷新缓存
│   ├── setup_first_time.bat    → 新机器 IG 登录初始化
│   ├── fetch_batch.py          → 手动抓取 Apify dataset（旧，保留备用）
│   ├── fetch_comments.py       → 手动抓取评论（旧，保留备用）
│   └── extract_urls.py         → TT 评论 URL 提取器（旧，保留备用）
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

### 1. 克隆 + 依赖

```bash
git clone https://github.com/Stevenchen213/icrush-influencer-mvp.git
cd icrush-influencer-mvp
pip install -e .
playwright install chromium
npm install
```

### 2. 配置 `.env`

复制 `.env.example`（如没有则新建），填入：

```bash
# === API Token ===
APIFY_TOKEN=your_token_here
WEDNESDAY_EMAIL=it@icrush.de
WEDNESDAY_PASSWORD=xxx
DEDUP_API_TOKEN=xxx
DEDUP_API_URL=xxx

# === Chrome CDP 路径（部署到新机器必须改） ===
# Chrome 安装位置
CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe
# 独立用户数据目录（存放 IG 登录态，Chrome 136+ 必须用独立目录）
CHROME_USER_DATA=C:\Users\yaxua\chrome-debug
# CDP 调试端口（默认 9222 即可）
CDP_PORT=9222
```

> | 变量 | 说明 | 部署到新机器 |
> |------|------|-------------|
> | `CHROME_EXE` | Chrome 可执行文件路径 | **必须改**（路径不同） |
> | `CHROME_USER_DATA` | 存放 IG 登录 session 的目录 | **必须改**（用户名不同） |
> | `CDP_PORT` | 远程调试端口 | 一般不用改 |

### 3. 初始化 IG 登录（新机器只需一次）

```bash
# 自动启动 Chrome CDP
python scripts/ensure_chrome_cdp.py

# 手动在打开的 Chrome 中登录 IG，session 自动持久化到 CHROME_USER_DATA
# 此后每次运行 ensure_chrome_cdp.py 自动恢复 Chrome + 登录态
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
- **v0.8.0** (2026-06-29)：
  - 品牌/媒体号自动过滤：STAGE 1 打分制检测，用户名/简介含品牌标识（`_de`、`.de`、官方号、媒体/综艺模式等）→ ❌ 品牌官方号
  - Wednesday 搜索修复：`@用户名 + social_media.username` 精确优先，fallback `all` 全字段，慢路径 5→20 条
  - Apify 结果缓存：`data/apify_cache/` 文件缓存，崩溃重跑不重复花费
  - IG 帖子优化：抓 20 条（非 100），仅 Reel/Video 计浏览，无视频 → 🟡 人工复查
  - 飞书同步 STAGE 0 查重 + 结果自动同步
  - Apify 超时 900→1800s、GBK 编码全项目修复
- **v0.7.2** (2026-06-26)：
  - Chrome CDP 根因修复：`--user-data-dir` 替代 `--profile-directory`（Chrome 136+ 兼容）
  - 提取脚本三修复：See all 选择器 / 滚动容器 / 提前停止
  - 新增 `ensure_chrome_cdp.py`：自动检测/启动/恢复 Chrome CDP
  - 部署配置文档：README 安装步骤 + 路径变量说明
  - 无 See all 时快速跳过（≤3 账号 → 6 次滚动后放弃）
