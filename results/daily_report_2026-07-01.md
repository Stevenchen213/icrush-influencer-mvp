# ICRUSH 日报 — 2026-07-01 (周三)

## 今日工作

### 1. 全流程验证：babsiboeck 种子
- 用 `run_full_workflow.py --force babsiboeck` 跑通完整流程
- **种子发现**：81 个类似达人
- **STAGE 0 查重**：拦截 30 人（28 KOL + 2 飞书）
- **STAGE 1 短路**：38 人淘汰（品类不符 x15 / 品牌号 x5 / 男博主 x4 / 帖数不足等）
- **STAGE 2 最终**：9 ✅ + 2 🟡复查 + 1 🟡人工复查 + 1 🟡推荐置换
- Apify 费用：$0.44 (~¥3.20)
- 耗时：275 秒

### 2. 发现 STAGE 1 漏网问题
人工复查发现 4 个应被拦截但通过的账号：

| 账号 | 应属类别 | 漏网原因 |
|------|---------|---------|
| eatwithsarah_ | 美食 | 美食类需 2 命中，bio 只有 "Rezepte" 1 个命中 |
| eigenheimliebe | 家居 | 待查 bio |
| karokauerlabel | 品牌号 | "label" 不在品牌关键词中 |
| lisla.living | 家居 | bio 含 "DIY" + "Home Creator" + "Hausbau"，待确认 |

### 3. 流程问题确认
- `run_batch.py` vs `run_full_workflow.py` 使用场景已理清
- 手动指定种子 → 用 `run_full_workflow.py`
- 已有达人列表 → 用 `run_batch.py`
- KOL 查重仅针对提取出的类似达人，不针对种子本身 ✅

## 待办
- [ ] 补齐美食、家居类漏网关键词
- [ ] 品牌检测加 "label" 等信号
- [ ] 跑剩余 32 个种子
