# ICRUSH AGENT.md

> 项目级上下文文件，供 AI agent（Codex / Claude Code）接力时对齐状态。
> doc 职责划分: AGENT.md=AI上下文 / README.md=人类概览 / docs/rules.md=完整规则

---

## 项目概况

**ICRUSH** -- 国内办公室自动化达人筛选管线。输入 Instagram/TikTok 主页链接，按硬性条件自动判定通过/淘汰/置换/复查，输出 Markdown 报表。
当前版本：**v0.8.3**
GitHub: https://github.com/Stevenchen213/icrush-influencer-mvp.git

---

## 用户角色

- **ICRUSH 实习生**，找德国 IG/TT 珠宝时尚达人
- 使用 **飞书** 做共享查重表
- 使用 **Wednesday (Upfluence)** 看受众画像，月配额 3000 views
- **预算敏感**：Apify 月配额 $300，花费达到阈值需暂停
- Python 路径：`C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe`

---

## 技术栈

| 层 | 选型 |
|---|------|
| 语言 | Python >=3.11 |
| 依赖 | httpx, langdetect, playwright, python-dotenv |
| 达人发现 | Playwright CDP（IG 类似账户）— 唯一发现方法 |
| 筛选数据 | Apify Actors（profile/posts）、Wednesday API（受众画像） |
| 容灾 | Apify 失败 -> Playwright headless 兜底 |
| 结果 | Markdown 表格输出到 `results/` |

---

## 达人获取：唯一方法

### IG 类似账户三步法（2026-06-24 验证）

**这是目前唯一有效的达人发现方式。**

```
种子达人主页 → 点击"类似账户" → 弹窗 → 点击"查看全部" → 滚动加载 → 提取
每个种子 ~80 个关联达人，完全免费
```

脚本：`scripts/fetch_similar_accounts_v3.mjs`
文档：`docs/similar_accounts_guide.md`

### 日常流程（自动 / 手动）

```bash
# === 自动化 ===
# 脚本会自动检测并启动 Chrome CDP（飞书触发时也可以用）
python scripts/ensure_chrome_cdp.py

# === 半自动 ===
# 提取（安全模式，每次最多 5 种子）
node scripts/fetch_similar_accounts_v3.mjs seed1 seed2

# 喂入 pipeline
python scripts/run_batch.py data/input_similar_combined.txt

# === 手动备选 ===
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\Users\yaxua\chrome-debug
```

> ⚠️ **必须用 `--user-data-dir`**：Chrome 136+ 忽略默认目录的 `--remote-debugging-port`（2026-06-25 排查确认）。

### 部署到新机器

1. `git clone` + `pip install -r requirements.txt` + `npm install`
2. 复制 `.env.example` → `.env`，修改路径：
   ```
   CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe
   CHROME_USER_DATA=C:\Users\yaxua\chrome-debug
   CDP_PORT=9222
   ```
3. 手动运行一次 Chrome CDP 启动命令，登录 IG（session 持久化在 chrome-debug 目录）
4. 此后 `ensure_chrome_cdp.py` 自动管理 Chrome 生命周期

### 安全策略

| 参数 | 值 |
|------|-----|
| 种子间隔 | 30-90s 随机 |
| 单次上限 | 5 种子 |
| 每日上限 | 7-8 次会话 |
| 滚动抖动 | ±400px, ±200ms |

---

## 关键文件

```
icrush/
  pipeline.py              # 三阶段编排（STAGE 0→1→1.5→2）
  judges.py                # 短路淘汰 + caption 判定
  language.py              # 语言检测、地区、职业、性别
  wordlists.py             # 词典
  wednesday.py             # 缓存读写 + 实时查询
  classifier.py            # 商单分类
  report.py                # Markdown 表格输出
  dedup.py                 # KOL 查重 API
  feishu.py               # 飞书结果同步 + 二次判断表
  apify.py                 # Apify API 客户端
  apify_cache.py           # Apify 结果文件缓存（崩溃恢复省费用）
  config.py                # 阈值常量

scripts/
  run_batch.py             # 主入口（用户贴URL时永远用这个）
  run_full_workflow.py     # 端到端编排（CDP→提取→pipeline，含重试）
  fetch_similar_accounts_v3.mjs  # 类似账户提取（唯一发现方法）
  ensure_chrome_cdp.py     # 自动管理 Chrome CDP 生命周期
  refresh_wednesday_cache.py     # 手动刷新 Wednesday 缓存
  setup_first_time.bat     # 新机器 IG 登录初始化
  extract_urls.py          # TT 评论 URL 提取器（STAGE 3 已废弃，保留备用）

docs/
  rules.md                 # 完整规则
  similar_accounts_guide.md # 类似账户提取指南
```

---

## Pipeline 速览

| Stage | 做什么 | 淘汰即停 |
|-------|--------|---------|
| STAGE 0 | KOL 查重（阿里云 API 4库 + 飞书结果表） | 已入库则跳过 |
| STAGE 1 | Profile + 短路淘汰（含品牌号检测）+ Apify 缓存 | 命中即终止 |
| STAGE 1.5 | Wednesday 受众查询（@用户名精确优先，fallback all） | - |
| STAGE 2 | IG: 40条Reel（前10浏览+全40商单）/ TT: 20条→3月过滤 | 通过/淘汰/置换/复查 |

完整规则见 `docs/rules.md`

---

## 重要约定

1. **获取达人 -> 永远用 `node scripts/fetch_similar_accounts_v3.mjs`**
2. **用户贴 URL -> 永远用 `python scripts/run_batch.py`**
3. **输出表格保持输入顺序**
4. **Apify 仅用于 pipeline 内 profile/posts 抓取，不用于发现**

### 偏好（非硬性，最终人工选人时在意）
- 白人年轻美女达人，时尚/穿搭/美妆/生活方式类
- 要有口播商单（不只是图文 #ad）
- IG 为主，TT 也可以
- 反目标：民族服饰 / 游戏 / 食物 / 亲子 / 炫富 / 品牌创始人 / 品牌官方号 / 宠物 / DIY

### 查重机制（双重）
- 阿里云 API（主）：`POST {account, platform, developer_name, check_only: true}` → 对比 4 库（KOL总表/KOC红人库/实习生表/AWS KOC），只查不写
- 飞书结果表查重：查询达人筛选结果表已有用户 → 命中则跳过

---

## 当前会话状态（2026-06-30）

### v0.8.3 更新（今日）
- **种子去重**：`run_full_workflow.py` / `run_batch_seeds.py` 批次内+跨批次去重（`data/seeds_processed.txt`），`--force` 强制重跑
- **Scroll 修复**：`fetch_similar_accounts_v3.mjs` 额外懒加载等待（400±300ms）+ 每10次1.5s喘息 + 放弃阈值 4→6
- **二次判断表优化**：排除"🟡 已入库"（原仅排除"❌ 否"），仅同步需人工判断的结果
- **SOP 文档**：`docs/达人二次判断-SOP.md` + `scripts/feishu_create_sop_doc.py` 自动生成飞书文档
- **飞书 App 权限**：新增 `docx:document` 权限
- **批量跑结果**：4 种子 → 251 个 profile → 37 ✅ 是 / 28 🟡 复查 / 12 🟡 推荐置换
- **GitHub push** ✅

### v0.8.2 更新
- 品牌过滤修复 / 抓取失败 bug 修复 / 飞书 token 自动刷新
- Chrome CDP 可靠性 / 人工复查地区检查 / run_batch_seeds.py 通用化

### 待办
- [ ] Wednesday 配额重置后刷新缓存（7/1）
