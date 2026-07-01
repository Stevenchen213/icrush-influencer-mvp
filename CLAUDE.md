# ICRUSH 达人营销项目

> CLAUDE.md — 供 Claude Code 加载项目上下文
> 完整信息见 AGENT.md

## 项目概况

**ICRUSH v0.9.0** — 国内办公室自动化达人筛选管线。输入 IG/TT 链接，自动判定通过/淘汰/置换/复查，输出 Markdown 报表。

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
  judges.py                # 短路淘汰 + 品类负向词 + 品牌检测（v0.9.0 核心）
  wordlists.py             # BIO_CATEGORY_BLOCKLIST 9类270+词 + 男名库
  language.py              # 语言检测 + 男性识别（含 username/bio 扫描）
  classifier.py / report.py
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
| STAGE 1 | Profile + 短路淘汰（品类负向词 + 品牌检测 + 男性识别 + 硬指标） |
| STAGE 1.5 | Wednesday 受众查询（field:all 全字段搜索） |
| STAGE 2 | IG: Reel Scraper 40条（前10浏览+全40商单）/ TT: 20条→3月过滤 |
| 末尾 | 飞书主结果表 + 二次判断表自动同步 |

## STAGE 1 品类拦截（v0.9.0 新增）

白名单优先 → fashion/beauty/outfit/schmuck 等直接放行

| 类别 | 命中阈值 | 示例关键词 |
|------|---------|-----------|
| 🔴 心理/身心灵 | 1 | psycholog, therap, adhs, meditation, healing |
| 🔴 音乐/DJ/演出 | 1 | dj, festival, booking@, sänger, band |
| 🔴 宗教/教会 | 1 | jesus, kirche, church, gospel, bible |
| 🔴 医疗/健康 | 1 | arzt, medizin, patient, clinic, aerztin |
| 🔴 宠物/动物 | 1 | hund, katze, dog, horse, tierschutz |
| 🔴 家居/DIY | 1 | diy, möbel, interior, cleaning, renovation |
| 🔴 教育 | 1 | lehrerin, kurs, workshop, academy, schule |
| 🟡 母婴 | 2 | mamablog, erziehung, familienblog（不含 mama） |
| 🟡 美食 | 2 | rezept, foodblog, kochen, restaurant, kitchen |

品牌检测：bio 商业信号打分 ≥3 分 → 淘汰（offiziell, hotel, restaurant, kundinnen, bestellung...）
男性检测：名字 + bio + username + 称呼前缀（Mr, Herr, Daddy, Husband...）

## 重要约定

1. **获取达人 → `node scripts/fetch_similar_accounts_v3.mjs`**
2. **用户贴 URL → `python scripts/run_batch.py`**
3. 查重：Lambda API + 飞书结果表 + exclusion_list.json
4. 偏好：白人年轻美女，时尚/穿搭/美妆/生活方式，有口播商单

## 当前状态（2026-07-01）

- ✅ v0.9.0：Bio 品类负向词 9 类 270+ 关键词，基于 270 条人工反馈训练
- ✅ STAGE 1 白名单优先（fashion/beauty → 防误杀）
- ✅ 品牌检测增强 40+ 商业信号
- ✅ 男性检测三重覆盖（名字 + bio + username + 称呼前缀）
- ✅ 旅游类放行，酒店品牌走品牌检测
- ✅ 种子去重：批次内 + 跨批次（`seeds_processed.txt`）
- ⬜ Wednesday 配额重置后刷新缓存（7/1）
- ⬜ 飞书 webhook 集成
