---
name: mvp-pending-next-session
description: 2026-06-23 EOD 状态、已验证的达人发现方法、待解决项
metadata: 
  node_type: memory
  type: project
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

## 2026-06-23 完成的改动

### Codex 新增（已同步到本地，未推 GitHub）
- 3 个新发现模块：`discoverer_hashtag.py`、`discoverer_snowball.py`、`discoverer_suggested.py`
- `discover.py` 重写，支持 4 种方法：wednesday / hashtag / snowball / suggested
- 新增 `DrissionPage` 依赖，一堆探索用 `.mjs` 脚本

### 达人画像学习（已存长期记忆）
- 看了全部历史判定结果 + 朋友标注的好/差名单 + 75 个账号首页截图
- 存入 `influencer_taste_profile.md` 和 `brand_seed_list.md`

## 已验证的达人发现方法

| # | 方法 | 结果 |
|---|------|------|
| 1 | Apify 标签搜达人 | ❌ 结果全是品牌号 |
| 2 | Apify 滚雪球 | ❌ 超时严重，标签不相关 |
| 3 | 谷歌搜榜单 | ❌ 全是大号 >300K |
| 4 | 谷歌搜 Collabstr/UGC 平台 | ✅ 找到 12 个，3 个进备选 |
| 5 | CDP 浏览器抓 IG 关注列表 | ⚠️ 弹窗能打开，但滚动没调好（1331 人只抓到 12） |

## 当前阻塞

- **Apify 月度 $5 额度用完**（7月1日恢复）
- **Wednesday 配额用完**（7月1日恢复）
- **CDP 关注列表滚动加载**待修

## 已测试的达人

Google 搜 Collabstr 跑完 pipeline：
- 🟡 已入库 1 个：aeb.sa
- ❌ 不合适 8 个：帖数 <200（7个）、浏览为 0（1个）
- 🟡 复查 3 个：deiademeny（2K粉/2029帖/文案没德语）、krithiga_kd（2K粉/226帖/缺德语）、modesynthese（37K粉/2182帖/18590浏览/缺商单）

## 下一步（7月1日后）

1. Wednesday + Apify 同时恢复 → 自动搜人 + pipeline 全通
2. 优先修 CDP 关注列表滚动 → 从好号捞出几百个同类
3. 提交 Codex 修改到 GitHub（需先清理 config.py 硬编码 token）
