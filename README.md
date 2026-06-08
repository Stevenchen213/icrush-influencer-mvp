# ICRUSH 德国/奥地利达人筛选 MVP

ICRUSH 国内办公室自动化达人调研流水线 —— 输入一批 Instagram / TikTok 主页链接，按硬性条件自动判定"合适 / 不合适 / 置换组 / 需人工核查"，省去手动对照查重表 + 人工核对每个账号的时间。

**当前版本**：v0.4 (2026-06-08)

## 🎯 干啥的

给定 N 个达人主页 URL，自动判定每个达人是否符合品牌合作标准：

| 硬性条件 | 阈值 |
|---------|------|
| 1. 地区 | DE 或 AT（bio 城市 + caption 50% 德语 + 评论 60% 德语，每视频 10 条文字评论）|
| 2. 粉丝数 | TT 10K-500K / IG 10K-300K（<10K 置换组，<1K 直接 pass）|
| 3. 帖数 | TT/IG ≥ 200（私密账户直接 pass）|
| 4. 近 3 月平均浏览 | ≥4000 / 2000-3999 置换组 / <2000 pass |
| 5. 职业 | 律师 / 艺术家 → 直接 pass |
| 6. 男粉占比（二期）| ≤ 40%（粉丝 >100K 时可放宽到 65%）|

详细规则见 [docs/rules_v0.4.md](docs/rules_v0.4.md)。

## 📂 项目结构

```
icrush-influencer-mvp/
├── scripts/                       # 处理脚本
│   ├── fetch_comments.mjs         # 直连 Apify API 抓评论数据
│   ├── analyze.mjs                # 主分析：6 条硬性条件判定
│   ├── analyze_comments.mjs       # 评论语言占比分析
│   ├── extract_urls.mjs           # 从 profile dataset 提取视频/帖子 URL
│   └── final_table.mjs            # 输出最终判定表
├── docs/
│   ├── rules_v0.4.md              # 完整规则文档
│   └── workflow.md                # 流水线说明
├── results/                       # 历次跑的结果
│   └── 2026-06-08_batch23.md      # 最近一次 23 人测试
├── data/                          # 抓回来的原始数据（gitignored）
├── .env.example                   # 环境变量模板（复制成 .env 填 token）
├── .gitignore
├── package.json
└── README.md
```

## 🛠️ 工具栈

- **Apify**：主数据源，靠 Actor 抓 TT/IG 公开数据
  - TT 主页：[`clockworks/tiktok-profile-scraper`](https://apify.com/clockworks/tiktok-profile-scraper)
  - TT 评论：[`thescrapelab/tiktok-comments-scraper`](https://apify.com/thescrapelab/tiktok-comments-scraper)
  - IG 主页：[`apify/instagram-profile-scraper`](https://apify.com/apify/instagram-profile-scraper)
  - IG 帖子：[`apify/instagram-post-scraper`](https://apify.com/apify/instagram-post-scraper)
  - IG 评论：[`apify/instagram-comment-scraper`](https://apify.com/apify/instagram-comment-scraper)
- **Node.js 22+**：跑分析脚本（用了原生 `--env-file` 加载 .env）

## 🚀 怎么用

### 一、首次配置（5 分钟）

```bash
# 1. clone 仓库
git clone <repo-url>
cd icrush-influencer-mvp

# 2. 配置 Apify token
cp .env.example .env
# 编辑 .env，把 your_token_here 换成真实 token

# 3. 装依赖（暂时没用，未来加）
npm install
```

### 二、跑一批达人（典型流程）

> **当前阶段是 MVP**：scripts 里的某些路径是硬编码的 `C:\Users\yaxua\...`，需要你按自己环境调整。下一版会改成参数化。

```bash
# 步骤 1：先用 Claude Code + Apify MCP 抓 profile/post 数据
#         （这部分目前手动通过对话触发，见 docs/workflow.md）

# 步骤 2：抓评论（Apify API 直连，不经 MCP）
npm run fetch-comments

# 步骤 3：分析
npm run analyze

# 步骤 4：输出最终表
npm run final-table
```

### 三、看历次结果

`results/` 目录下每个文件是一次测试的快照。

## ⚠️ 安全

- **永远不要 commit `.env`**（含 Apify token）
- 抓回来的评论/帖子数据按 GDPR 算个人信息，**永远不要 commit `data/`** 下的 JSON
- 仓库设为 **Private**

## 📜 版本演进

- **v0.1** (2026-06-04)：第一版规则，基本指标
- **v0.2** (2026-06-05)：加 1K-10K 置换组分层
- **v0.3** (2026-06-05)：调整粉丝上限到 TT 500K / IG 300K
- **v0.4** (2026-06-08)：加职业筛选（律师/艺术家）+ 平均浏览量分层 + 评论二级检查；修复 TT 语言占比 bug（排除"un"表情视频）
- **v0.4 微调** (2026-06-08 PM)：① caption 阈值 70%→50%；② 评论阈值 70%→60%；明确"每视频抓 10 条文字评论、表情类不计入分母"

## 🤝 协作

修改规则时：
1. 改 `docs/rules_v0.4.md`（描述）
2. 改 `scripts/analyze.mjs`（实现）
3. Commit message 写明"规则变化：XX → YY"
4. Push

PR / Issue 直接在 GitHub 上交流。
