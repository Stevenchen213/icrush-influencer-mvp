# ICRUSH 德国/奥地利达人筛选 MVP

ICRUSH 国内办公室自动化达人调研流水线 —— 输入一批 Instagram / TikTok 主页链接，按硬性条件自动判定"合适 / 不合适 / 置换组 / 需人工核查"，省去手动对照查重表 + 人工核对每个账号的时间。

**当前版本**：v0.5 (2026-06-10)

## 🎯 干啥的

给定 N 个达人主页 URL，自动判定每个达人是否符合品牌合作标准：

| 硬性条件 | 阈值 |
|---------|------|
| 1. 地区 | DE 或 AT（优先 Wednesday 受众国家+城市，fallback caption 25% 德语 + 评论 60% 德语）|
| 2. 粉丝数 | TT 10K-500K / IG 10K-300K（<10K 置换组，<1K 直接 pass）|
| 3. 帖数 | TT/IG ≥ 200（私密账户直接 pass）|
| 4. 近 3 月平均浏览 | ≥4000 / 2000-3999 置换组 / <2000 pass |
| 5. 职业 | 律师 / 艺术家 → 直接 pass |
| 6. 女粉占比 | 男粉 >50% 否决（粉丝 >100K 时放宽到 65%）|

详细规则见 [docs/rules_v0.4.md](docs/rules_v0.4.md)。

## 📂 项目结构

```
icrush-influencer-mvp/
├── scripts/                       # 处理脚本
│   ├── run_batch.mjs              # 主流水线：一键跑完整批（v0.5 Wednesday 集成）
│   ├── analyze_mvp_v4.mjs         # 旧版分析脚本
│   └── ...
├── docs/
│   ├── rules_v0.4.md              # 完整规则文档（已更新至 v0.5）
│   └── workflow.md                # 流水线说明
├── results/                       # 历次跑的结果
├── data/                          # 抓回来的原始数据（gitignored）
├── .env.example                   # 环境变量模板（APIFY_TOKEN + WEDNESDAY_TOKEN）
├── .gitignore
├── package.json
└── README.md
```

## 🛠️ 工具栈

- **Apify**：主数据源，靠 Actor 抓 TT/IG 公开数据
- **Wednesday/Upfluence**：免费受众数据（性别、国家、城市），优先判定地区+男女粉比，节省 Apify 语言检测成本
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
3. **短路淘汰**：帖数<200 / 职业=艺术家律师 / 私密 / 粉丝<1K 或超上限 → 直接 ❌
4. **STAGE 1.5**：Wednesday/Upfluence 查询（免费）— 受众国家+城市判定地区，性别判定男女粉比
5. **STAGE 2**：仅对 survivors 抓 20 posts/videos（IG 用 `detailedData` 拿 view count）；Wednesday 确认者跳过语言检测
6. **caption 判定**（v0.5 规则 caption 25%）；仅 Wednesday 无数据者需检测语言
7. **STAGE 3**（仅当有 ⚠️ 时）：调评论 API，每帖 10 条，按 ≥60% 德语二次判定
8. **输出表格**含女粉占比列，按粘贴顺序，存到 `results/<日期>_batch<N>_<seq>.md`
9. **末尾打印真实 Apify 成本**（USD + ¥ ≈）

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
