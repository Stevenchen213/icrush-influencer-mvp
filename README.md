# ICRUSH 德国/奥地利达人筛选 MVP

ICRUSH 国内办公室自动化达人调研流水线 —— 输入一批 Instagram / TikTok 主页链接，按硬性条件自动判定"合适 / 不合适 / 置换组 / 需人工核查"，省去手动对照查重表 + 人工核对每个账号的时间。

**当前版本**：v0.4 (2026-06-08)

## 🎯 干啥的

给定 N 个达人主页 URL，自动判定每个达人是否符合品牌合作标准：

| 硬性条件 | 阈值 |
|---------|------|
| 1. 地区 | DE 或 AT（bio 城市 / about.country + caption 25% 德语 + 评论 60% 德语，每视频 10 条文字评论）|
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

把 profile URL 一行一个写到 `data/input.txt`（或者用 stdin），然后：

```bash
npm run run-batch data/input.txt
```

这一条命令会自动：

1. **解析 URL**（支持 IG `/<user>/` 和 TT `/@<user>` 两种格式，去重 + 保留输入顺序）
2. **STAGE 1**：抓 profile metadata（IG profile-scraper + TT clockworks `resultsPerPage=1`）
3. **短路淘汰**：帖数<200 / 职业=艺术家律师 / 私密 / 粉丝<1K 或超上限 / bio 地区非 DE/AT → 直接 ❌，不进 STAGE 2
4. **STAGE 2**：仅对 survivors 抓 20 posts/videos（IG 用 `detailedData` 拿 view count，TT clockworks 20 视频）
5. **caption 判定**（v0.4 微调规则 caption 50%）；bio 在 DE/AT 但 caption <50% 的标 ⚠️
6. **STAGE 3**（仅当有 ⚠️ 时）：对 ⚠️ 用户调评论 API（TT `thescrapelab/tiktok-comments-scraper` + IG `apify/instagram-comment-scraper`），每帖 10 条评论，按 ≥60% 德语二次判定
7. **输出表格**按粘贴顺序，存到 `results/<日期>_batch<N>_<seq>.md`
8. **末尾打印真实 Apify 成本**（USD + ¥ ≈）

成本对比（14 unique 达人，9 个短路淘汰，0 个 ⚠️）：

| 方案 | ¥ |
|------|---|
| 旧手动流程 | ~12 |
| run-batch（自动短路 + 20 帖 + detailedData）| **~3-4** |
| run-batch + STAGE 3（每 ⚠️ 约 +¥3-4）| 取决于 ⚠️ 数量 |

### 三、其他单步脚本（按需）

```bash
npm run analyze            # 只跑判定，用 data/ 里已有的 JSON（不调 Apify）
npm run fetch-comments     # 拉一个评论 dataset（需先填 TT_COMMENTS_DATASET / IG_COMMENTS_DATASET 环境变量）
npm run analyze-comments   # 评论语言占比检查（② 评论 60% 规则）
npm run extract-urls       # 从 TT profile dataset 抽视频 URL 喂给评论 scraper
```

### 四、看历次结果

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
- **v0.4 微调 2** (2026-06-09)：① caption 阈值 50%→25%；② IG 地区优先读 `about.country`；③ IG 150–199 帖 reel-heavy 豁免帖数淘汰

## 🤝 协作

修改规则时：
1. 改 `docs/rules_v0.4.md`（描述）
2. 改 `scripts/analyze.mjs`（实现）
3. Commit message 写明"规则变化：XX → YY"
4. Push

PR / Issue 直接在 GitHub 上交流。
