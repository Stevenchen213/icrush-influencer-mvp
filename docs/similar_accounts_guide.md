# IG 类似账户自动提取指南

> **2026-06-24 重大突破** — IG 的"类似账户"功能并未消失，只是 UI 从页面区域改成了弹窗。

## 概述

从种子 Instagram 达人主页出发，自动点击"类似账户"→"查看全部"，提取 IG 推荐的所有关联达人。每个种子可获取 **~80 个相关账号**，完全免费，不消耗任何 API 配额。

## 原理

IG 在 2026 年 4 月调整了推荐功能的 UI 布局：

```
旧 UI（已失效）:
  达人主页 → 页面底部"为你推荐"区域 → 横向滚动

新 UI（当前有效）:
  达人主页 → 点击"类似账户"按钮 → 弹窗 → 点击"查看全部" → 全量列表
```

所有旧的提取方式（Apify `relatedProfiles`、Playwright API 拦截 `edge_related_profiles`、页面 HTML 解析）都因为 IG 的这次 UI 变更而失效。本方法直接模拟真实用户的点击操作，不受 API 变更影响。

## 前提条件

1. **Chrome 浏览器** 以调试模式启动：
   ```powershell
   # Windows: 先正常关闭 Chrome，然后
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```

2. **Instagram 已登录** — 在 Chrome 中登录你的 IG 账号

3. **Node.js** 和 **Playwright** 已安装

## 使用方法

### 基本用法

```bash
# 提取 1-5 个种子的类似账户（安全模式）
node scripts/fetch_similar_accounts_v3.mjs jxlia.albrecht emmaleinswelt

# 输出文件：
#   data/similar_jxlia.albrecht.txt    — 单种子结果
#   data/similar_emmaleinswelt.txt
#   data/input_similar_combined.txt     — 合并去重结果
```

### 喂入 Pipeline

```bash
# 提取完成后直接跑筛选
python scripts/run_batch.py data/input_similar_combined.txt
```

### 调试模式

```bash
# 跳过安全延迟（仅测试用，不要日常使用）
node scripts/fetch_similar_accounts_v3.mjs --fast seed1
```

## 安全策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 种子间延迟 | 30-90 秒随机 | 模拟人类浏览节奏 |
| 单次会话上限 | 5 个种子 | ~400 候选，pipeline 后 ~50-80 |
| 每日会话建议 | 7-8 次 | 2000-2800 候选/天，pipeline 后 ~300-500 |
| 滚动抖动 | ±400px, ±200ms | 避免机械匀速滚动 |
| 微停顿 | 5% 概率 0.5-2s | 模拟人类不规律操作 |
| 会话日志 | `data/session_log.json` | 自动记录每日用量 |

### 封号风险评估

- ✅ 使用**你自己的 IG 账号 + 你自己的 Chrome**
- ✅ 操作模式**模拟真人点击和滚动**
- ✅ 请求频率**控制在人类合理范围**
- ✅ IG 看到的是正常的浏览行为，非 API/机器人行为

### 注意事项

- **不要**在同一会话中跑超过 5 个种子
- **不要**用 `--fast` 模式日常跑（仅调试）
- **不要**凌晨批量跑（正常工作时间操作）
- Chrome 正常关闭重启不会丢失 IG 登录态
- **不要**用 `taskkill /F` 强杀 Chrome（会丢 cookies）

## 验证记录

| 日期 | 种子 | 结果 | 质量 |
|------|------|------|------|
| 2026-06-24 | @jxlia.albrecht | 80 个 | ✅ 德国年轻女性，匹配良好 |
| 2026-06-24 | @oksana_vibe.de | 80 个 | ⚠️ 多为 Produkttester，种子质量决定结果 |

## 技术细节

### 为什么旧方法失效

| 方法 | 状态 | 原因 |
|------|------|------|
| Apify `relatedProfiles` | ❌ | IG 4月服务端移除此字段 |
| `edge_related_profiles` API | ❌ | IG GraphQL 中字段不存在 |
| HTML 区域解析 | ❌ | "为你推荐"不再渲染为页面区域 |
| DrissionPage | ❌ | 寻找的是旧 UI 布局 |
| **三步弹窗法（本方法）** | ✅ | 模拟真实点击，不受 API 限制 |

### IG API 发现

- `include_suggested_users` 在 Web 端 GraphQL 查询中**被设为 false**
- `suggested_users` 字段存在于响应中但**值始终为 null**
- 类似账户数据不再通过 API 返回，而是通过弹窗的独立渲染获取

## 相关文件

- 生产脚本：`scripts/fetch_similar_accounts_v3.mjs`
- 项目上下文：`CLAUDE.md` / `AGENT.md`
- 完整规则：`docs/rules.md`
- Pipeline 入口：`scripts/run_batch.py`
