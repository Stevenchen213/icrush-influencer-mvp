# ICRUSH AGENT.md

> 项目级上下文文件，供 AI agent（Codex / Claude Code）接力时对齐状态。
> 每次切换工具前更新本节，让下一个 agent 直接进入状态。

---

## 项目概览

**ICRUSH** — 德国/奥地利 KOL 自动化筛选管线。输入 Instagram / TikTok 主页链接，按硬性条件自动判定 ✓ 通过 / ✗ 淘汰 / 🔄 置换组 / 🔍 复查，输出 Markdown 报表。

当前版本：v0.7（2026-06-17）

---

## 技术栈

| 层 | 选型 |
|---|------|
| 语言 | Python >=3.11 |
| 依赖 | httpx, langdetect, playwright, python-dotenv |
| 数据源 | Apify Actors（IG/TT profile + posts + comments）、Wednesday API |
| 容灾 | Apify 失败 -> Playwright headless 兜底；Wednesday 缓存未命中 -> Playwright 实时查询 |
| 结果 | Markdown 表格输出到 results/ |

---

## 项目结构

```
icrush-influencer-mvp/
├── icrush/              # 核心库
│   ├── config.py        # 阈值常量 + API key
│   ├── wordlists.py     # 字典（德/英/城市/男名）
│   ├── language.py      # 语言检测(langdetect)、地区、性别、URL 解析
│   ├── judges.py        # 短路淘汰 + caption 判定
│   ├── pipeline.py      # 四阶段编排 + Playwright 兜底（主线入口）
│   ├── discovery.py     # 自动发现引擎（Phase 2）
│   ├── classifier.py    # 商单分类
│   ├── dedup.py         # KOL 查重 API 客户端
│   ├── gender.py        # 头像检测预留（需 API key）
│   ├── apify.py         # Apify HTTP 客户端
│   ├── wednesday.py     # Wednesday 缓存 + 实时查询 + 关键词搜索
│   ├── airtable.py      # Airtable 排除名单
│   ├── feishu.py        # 飞书排除名单
│   └── report.py        # Markdown 表格输出
├── scripts/             # CLI 入口
│   ├── run_batch.py     # icrush-batch 主入口
│   ├── discover.py      # 自动发现入口
│   └── ...
├── docs/
│   └── rules.md         # 完整判定规则（最新 v0.7）
├── data/                # 缓存 + 输入文件（gitignored）
├── results/             # 批次输出报表
├── AGENT.md             # 当前文件
├── pyproject.toml       # 项目元信息
└── README.md            # 用户端说明
```

---

## Pipeline 阶段速览

| Stage | 做什么 | 淘汰即停 |
|-------|--------|----------|
| STAGE 0 | KOL 查重（调用 Lambda API） | 已入库则跳过 |
| STAGE 0.5 | 解析 URL，去重 | - |
| STAGE 1 | 抓取 Profile + 短路淘汰（男博主/私密/帖数/粉丝） | 命中即终止 |
| STAGE 1.5 | Wednesday 受众查询（命中则完全采信） | - |
| STAGE 2 | 抓取 20 条 posts + 商单分类 | - |
| STAGE 3 | 评论分析 + 女粉占比 + 最终判定 | 通过/淘汰/置换/复查 |

---

## 当前会话状态

> 使用前更新此节 - 记录当前在做什么、做到哪了、有什么决策和待办。

### 活跃工作
（无）

### 最近改动（未提交）
- .env.example / README.md / docs/rules.md - 文档更新
- icrush/config.py / discovery.py / language.py / pipeline.py - 代码修改
- icrush/dedup.py - 新增去重模块
- results/2026-06-17_batch1_*.md - 今天批次结果

### 关键决策记录
- 语言检测用 langdetect 库（Google 算法），不用词表法
- 土耳其语映射为 unknown，不计入 caption 德语比例
- 女粉占比：男粉 <= 20%（>100K 放宽到 <= 35%）
- 不使用 asyncio 并发，保持同步处理
- IG reel 占比 >50% 时帖数下限放宽到 150

### 待办
- pipeline.py 加失败重试
- 写简单的 benchmark 脚本

---

## 开发约定

- 语言：全部用 ASCII 写代码，文件名、变量名、注释用英文，字符串内容可以是中文
- 配置：敏感信息放 .env（已 gitignored），示例放 .env.example
- git：功能完整时 commit，commit message 用英文，前缀规范（feat/fix/docs/refactor/remove）
- 容灾：外部服务挂了不阻塞主流程，必须有兜底
- 不要：引入新的大依赖、动 .env、改 gitignore 已涵盖的规则

---

## 我在用哪个工具

- [ ] **Codex**（桌面版）
- [ ] **Claude Code CLI**（终端）
