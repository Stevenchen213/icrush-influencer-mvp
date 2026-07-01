# ICRUSH 德国/奥地利达人筛选 MVP

ICRUSH 国内办公室自动化达人调研流水线 —— 输入种子达人，自动发现类似达人 → Pipeline 硬性筛选 → 输出判定报表。

**当前版本**：v0.9.0 (2026-07-01)

## 完整工作流

```bash
# 批量种子（直接贴 URL）
python scripts/run_full_workflow.py seed1 seed2 seed3

# 强制重跑已处理种子（忽略历史）
python scripts/run_full_workflow.py --force seed1

# 从文件批量读取（带预算控制）
python scripts/run_batch_seeds.py data/seeds.txt --budget 40

# 输出：results/YYYY-MM-DD_batchN_seq.md（Markdown 报表）
```

### 种子去重

- **批次内去重**：相同种子自动合并
- **跨批次去重**：处理后写入 `data/seeds_processed.txt`，下次自动跳过
- **强制重跑**：`--force` 忽略历史记录

### 分步说明

| 步骤 | 命令 | 费用 |
|------|------|------|
| 1. 启动 Chrome CDP | `python scripts/ensure_chrome_cdp.py`（自动） | 免费 |
| 2. 提取类似达人 | `node scripts/fetch_similar_accounts_v3.mjs seed1 seed2` | 免费 |
| 3. 筛选 | `python scripts/run_batch.py data/input_similar_combined.txt` | Apify 按量 |

详细方法见 **[docs/similar_accounts_guide.md](docs/similar_accounts_guide.md)**

## 硬性规则（STAGE 1 短路淘汰）

| # | 条件 | 阈值 |
|---|------|------|
| 1 | 白名单 | fashion/beauty/outfit/schmuck → 优先放行 |
| 2 | 品类不符 | 9 类 270+ 负向关键词扫描（见下表） |
| 3 | 男博主 | 名字 + bio + username + 称呼前缀三重检测 |
| 4 | 品牌/商业号 | bio 商业信号打分 ≥3（offiziell, hotel, restaurant, kundinnen...） |
| 5 | 私密账户 | → ❌ |
| 6 | 帖数 | < 200（IG reel >50% 可豁免到 150） |
| 7 | 粉丝 | IG 1K-300K / TT 1K-500K（<10K 置换组） |
| 8 | Caption 德语 | ≥ 25%（bio DE 时），不足则 🟡 复查 |
| 9 | 地区 | Wednesday 优先，fallback: bio DE/AT + caption ≥25% |
| 10 | 浏览量 | ≥4000 / 2000-3999 / <2000（仅计 Reel/Video） |
| 11 | 男粉占比 | ≤50%（>100K 放宽到 ≤65%） |

### 品类拦截矩阵

| 类别 | 触发数 | 示例 |
|------|--------|------|
| 🔴 心理/身心灵 | 1 命中 | psycholog, therap, adhs, meditation, healing |
| 🔴 音乐/DJ/演出 | 1 命中 | dj, festival, booking@, sänger, band |
| 🔴 宗教/教会 | 1 命中 | jesus, kirche, church, gospel, bible |
| 🔴 医疗/健康 | 1 命中 | arzt, medizin, patient, clinic, aerztin |
| 🔴 宠物/动物 | 1 命中 | hund, katze, dog, horse, tierschutz |
| 🔴 家居/DIY | 1 命中 | diy, möbel, interior, cleaning |
| 🔴 教育 | 1 命中 | lehrerin, kurs, workshop, academy |
| 🟡 母婴 | 2 命中 | mamablog, erziehung, familienblog（不含 mama） |
| 🟡 美食 | 2 命中 | rezept, foodblog, kochen, restaurant |
| ✅ 旅游 | 放行 | 旅行博主不拦，酒店走品牌检测 |

> 基于 270 条人工反馈训练，预期拦截 60-70% 第一轮被拒案例。

完整规则：**[docs/rules.md](docs/rules.md)**

## Pipeline 流程

```
STAGE 0  → KOL 查重（阿里云 API 4库 + 飞书结果表，check_only 只查不写）
STAGE 1  → Apify 抓 Profile → 品类负向词 + 品牌检测 + 男性识别 + 硬指标
        → 白名单优先：fashion/beauty 等美学词直接放行
STAGE 1.5 → Wednesday 受众查询（@用户名精确优先，fallback: all 全字段搜索）
STAGE 2  → IG: Reel Scraper 抓 40 条 Reel（近3月）/ TT: 20 条 → 3 月过滤
         → 浏览量 + caption 德语率 + 近3月商单 → 最终判定
         → 飞书自动同步: 主结果表 + 二次判断表
```

## 飞书多维表格自动同步

开启 `FEISHU_SYNC_ENABLED=1` 后，管道跑完自动同步到两张飞书表：

**主结果表**（`FEISHU_RESULTS_TABLE_ID`）：
- STAGE 0 查重命中 → 标记"已入库"跳过
- 全量结果 append（排除已入库）

**二次判断表**（`FEISHU_REVIEW_TABLE_ID`）：
- 排除"❌ 否"和"🟡 已入库"，仅同步需人工判断的结果
- 提供"总结反馈"和"二次判定"两列供人工填写
- 审核 SOP：[飞书文档](https://icrush.feishu.cn/docx/IIdpdBoF8oDgaexKco1cIeoFnzb) | [Markdown](docs/达人二次判断-SOP.md)

同步失败不阻塞管道，关掉 `FEISHU_SYNC_ENABLED=0` 即可

## 判定矩阵

| 条件 | 标记 |
|------|------|
| 全通过 + 有商单 | ✅ 是 |
| 全通过 + 无商单 | 🟡 复查 |
| 粉丝 <10K 或 浏览 2K-4K | 🟡 推荐置换 |
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
│   ├── wordlists.py            → 词典（9类品类负向词270+ / 城市 / 男名191）
│   ├── wednesday.py            → 缓存读写 + 自动实时查询
│   ├── dedup.py                → KOL 查重 API
│   ├── apify.py                → Apify API 客户端
│   ├── report.py               → Markdown 表格输出
│   ├── config.py               → 阈值常量
│   └── feishu.py               → 飞书结果同步 + 二次判断表
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
│   ├── rules.md                     → 完整规则文档
│   ├── similar_accounts_guide.md    → 类似账户提取指南
│   └── 达人二次判断-SOP.md          → 人工审核操作规范
├── results/                    # 历次跑的结果
├── data/                       # 抓取数据 + 缓存 + 种子历史（gitignored）
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
- **v0.9.0** (2026-07-01)：**智能品类拦截**
  - Bio 品类负向词过滤：9 类别 270+ 关键词，白名单优先防误杀
  - 基于 270 条人工反馈训练，预期拦截 60-70% 第一轮被拒案例
  - 品牌检测增强 40+ 商业信号，男性检测三重覆盖
  - 旅游类放行，酒店品牌走品牌检测
- **v0.8.3** (2026-06-30)：种子去重 / Scroll 修复 / 二次判断表优化 / SOP 文档
