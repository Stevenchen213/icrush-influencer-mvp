# ICRUSH AGENT.md

> 项目级上下文文件，供 AI agent（Codex / Claude Code）接力时对齐状态。
> doc 职责划分: AGENT.md=AI上下文 / README.md=人类概览 / docs/rules.md=完整规则

---

## 项目概况

**ICRUSH** -- 国内办公室自动化达人筛选管线。输入 Instagram/TikTok 主页链接，按硬性条件自动判定通过/淘汰/置换/复查，输出 Markdown 报表。
当前版本：**v0.7**
GitHub: https://github.com/Stevenchen213/icrush-influencer-mvp.git

---

## 用户角色

- **ICRUSH 实习生**，找德国 IG/TT 珠宝时尚达人
- 使用 **飞书** 做共享查重表
- 使用 **Wednesday (Upfluence)** 看受众画像，月配额 3000 views
- **预算敏感**：Apify 月配额已耗尽，需充值
- Python 路径：`C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe`

---

## 技术栈

| 层 | 选型 |
|---|------|
| 语言 | Python >=3.11 |
| 依赖 | httpx, langdetect, playwright, python-dotenv, drissionpage |
| 数据源 | Apify Actors、Wednesday API、Playwright stealth、DrissionPage |
| 容灾 | Apify 失败 -> Playwright headless 兜底 |
| 结果 | Markdown 表格输出到 `results/` |

---

## 关键文件

```
icrush/
  discoverer_hashtag.py    # Apify hashtag 搜索
  discoverer_snowball.py   # Apify 雪球法（种子 -> hashtag）
  discoverer_suggested.py  # DrissionPage 推荐发现（新增）
  discovery.py             # Wednesday 发现引擎
  dedup.py                 # KOL 查重 API
  pipeline.py              # 四阶段编排
  judges.py                # 短路淘汰 + caption 判定
  language.py              # 语言检测、地区、职业、性别
  wordlists.py             # 词典
  wednesday.py             # 缓存读写 + 实时查询
  classifier.py            # 商单分类
  report.py                # Markdown 表格输出
  airtable.py / feishu.py # 排除名单 fallback
  config.py                # 阈值常量

scripts/
  run_batch.py             # 主入口（用户贴URL时永远用这个）
  discover.py              # 统一发现 CLI（--method wednesday/hashtag/snowball/suggested）
  ig_stealth_search.mjs    # Playwright stealth IG 搜索
```

---

## Pipeline 速览

| Stage | 做什么 | 淘汰即停 |
|-------|--------|---------|
| STAGE 0 | KOL 查重（Lambda API） | 已入库则跳过 |
| STAGE 1 | Profile + 短路淘汰 | 命中即终止 |
| STAGE 1.5 | Wednesday 受众查询 | - |
| STAGE 2 | 20 条 posts + 商单 | - |
| STAGE 3 | 评论 + 判定 | 通过/淘汰/置换/复查 |

完整规则见 `docs/rules.md`

---

## 发现方式对比（2026-06-23 验证结果）

| 方法 | 代码 | 状态 | 费用 | 说明 |
|------|------|------|------|------|
| **Playwright stealth IG 搜索** | `ig_stealth_search.mjs` | 已验证可用 | 免费 | 绕过 IG 反爬，直搜 hashtag 页 |
| **Playwright bio 验证** | `ig_bio_check.mjs` | 已验证可用 | 免费 | 逐个查 bio，判断是否德国 |
| **Wednesday 搜索** | `--method wednesday` | 可用（需配额） | Wednesday 月配额 | 7/1 重置 |
| **Apify hashtag 搜索** | `--method hashtag` | 机制已验证 | Apify 按量计费 | 需充值 |
| **雪球法** | `--method snowball` | 代码就绪 | 同上 | 种子 -> hashtag -> 更多 |
| **DrissionPage 推荐发现** | `--method suggested` | 代码就绪（待实测） | 免费 | 种子 -> IG 为你推荐 |

---

## 重要约定

1. **用户贴 URL -> 永远用 `python scripts/run_batch.py`**
2. **输出表格保持输入顺序**
3. **发现方法优先选免费的**（Playwright / DrissionPage），配额留给 Wednesday

### 偏好（非硬性，最终人工选人时在意）
- 白人年轻美女达人，时尚/穿搭/美妆/生活方式类
- 要有口播商单（不只是图文 #ad）
- IG 为主，TT 也可以
- 反目标：民族服饰 / 游戏 / 食物 / 亲子 / 炫富 / 品牌创始人 / 品牌官方号 / 宠物 / DIY

### 查重机制（三重）
- Lambda API（主）：`POST {account, platform}` -> "有重复"则跳过
- Airtable / 飞书（fallback）：lookup by username
- 本地文件 `data/exclusion_list.json`

---

## 当前会话状态（2026-06-24）

### 本会话重大突破
- **IG 类似账户三步法验证成功**：类似账户 → 为你推荐 → 查看全部 → 滚动 → 提取
  - 每个种子可挖出 ~80 个关联达人
  - 旧方法全部失效原因：IG 把推荐从页面区域改成了弹窗+查看全部
  - 生产脚本：`scripts/fetch_similar_accounts_v3.mjs`
  - 详细文档：`.claude/memory/ig_similar_accounts_method.md`

### 本会话验证结论
- Apify `relatedProfiles`：❌ 永久失效（IG 4月起服务端移除）
- Playwright API 拦截 `edge_related_profiles`：❌ IG 响应中字段不存在
- Playwright HTML（旧版）：❌ 旧脚本找的是老 UI 布局
- DrissionPage `--method suggested`：❌ 同上 + cookies 过期
- **Playwright 弹窗三步法**：✅ 每个种子 ~80 个达人，免费

### 待办（按优先级）
1. [x] 实测 IG 类似账户抓取 → **已突破：三步弹窗法**
2. [ ] 将三步法整合进 `discoverer_suggested.py` 或新模块
3. [ ] Apify 充值后跑 `--method hashtag --run`（预算 $4.998 剩余）
4. [ ] Wednesday 配额重置后刷新缓存（7/1）
5. [ ] 完善品牌官方号过滤名单（如需）
