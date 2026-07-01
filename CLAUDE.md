# ICRUSH 达人营销项目

> CLAUDE.md — 供 Claude Code 加载项目上下文
> 完整信息见 AGENT.md

## 项目概况

**ICRUSH v0.8.3** — 国内办公室自动化达人筛选管线。输入 IG/TT 链接，自动判定通过/淘汰/置换/复查，输出 Markdown 报表。

GitHub: https://github.com/Stevenchen213/icrush-influencer-mvp.git

## 用户角色

- ICRUSH 实习生，找德国 IG/TT 珠宝时尚达人
- 飞书共享查重表 + Wednesday (Upfluence) 受众画像
- 预算敏感：Apify 月配额已耗尽
- Python: `C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe`

## 达人获取：唯一方法

**IG 类似账户三步法**（2026-06-24 验证，详见 `docs/similar_accounts_guide.md`）

```bash
# 1. 启动 Chrome CDP
chrome --remote-debugging-port=9222

# 2. 提取类似达人
node scripts/fetch_similar_accounts_v3.mjs seed1 seed2 seed3

# 3. 喂入 pipeline
python scripts/run_batch.py data/input_similar_combined.txt
```

安全：种子间隔 30-90s，每次 ≤5 种子，每天 7-8 次。

## 技术栈

Python >=3.11 | httpx, langdetect, playwright, python-dotenv
发现: Playwright CDP (IG 类似账户) | 筛选: Apify Actors, Wednesday API

## 关键文件

```
icrush/
  pipeline.py              # 三阶段编排（STAGE 0→1→1.5→2）
  judges.py / language.py / classifier.py / report.py
  wednesday.py / dedup.py / apify.py / config.py
  feishu.py                # 飞书结果同步 + 二次判断表

scripts/
  run_batch.py                     # Pipeline 主入口
  run_full_workflow.py             # 端到端编排（CDP→提取→pipeline，含种子去重）
  run_batch_seeds.py               # 批量种子（含 Apify 预算控制）
  fetch_similar_accounts_v3.mjs    # 类似账户提取（唯一发现方法）
  ensure_chrome_cdp.py             # Chrome CDP 生命周期管理
  feishu_create_sop_doc.py         # 生成飞书 SOP 文档
  setup_first_time.bat             # 新机器 IG 登录初始化

docs/
  rules.md                         # 完整规则
  similar_accounts_guide.md        # 类似账户提取指南
  达人二次判断-SOP.md              # 人工审核操作规范
```

## Pipeline

| Stage | 做什么 |
|-------|--------|
| STAGE 0 | KOL 查重（阿里云 4 库，check_only）+ 飞书结果表查重 |
| STAGE 1 | Profile + 短路淘汰 |
| STAGE 1.5 | Wednesday 受众查询（field:all 全字段搜索） |
| STAGE 2 | IG: Reel Scraper 40条（前10浏览+全40商单）/ TT: 20条→3月过滤 |
| 末尾 | 飞书主结果表 + 二次判断表自动同步 |

## 重要约定

1. **获取达人 → `node scripts/fetch_similar_accounts_v3.mjs`**
2. **用户贴 URL → `python scripts/run_batch.py`**
3. 查重：Lambda API + 飞书结果表 + Airtable/飞书 + exclusion_list.json
4. 偏好：白人年轻美女，时尚/穿搭/美妆/生活方式，有口播商单

## 当前状态（2026-06-30）

- ✅ 种子去重：批次内 + 跨批次（`seeds_processed.txt`），`--force` 强制重跑
- ✅ Scroll 懒加载修复：额外等待 + 放弃阈值 4→6
- ✅ 飞书二次判断表：排除"已入库"和"❌ 否"
- ✅ 达人二次判断 SOP 文档 + 飞书文档生成脚本
- ✅ GitHub push 恢复
- ✅ 飞书 token 自动刷新 / Chrome CDP 可靠性
- ⬜ Wednesday 配额重置后刷新缓存（7/1）
- ⬜ 飞书 webhook 集成
