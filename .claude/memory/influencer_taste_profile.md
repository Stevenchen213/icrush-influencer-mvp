---
name: influencer-taste-profile
description: 审核者真实口味三档（很好/一般/no）的判据 —— 脚本规则之外的隐性标准，来自 2026-06-17 人工标注名单
metadata: 
  node_type: memory
  type: project
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

ICRUSH 审核者对达人的真实口味，从 2026-06-17 人工标注的三档名单（很好/一般/no，带批注）提炼。这些是**脚本测不出的隐性标准**，与 [[mvp-workflow]] 的硬性规则互补。

**重要前提（用户 2026-06-17 强调）**：名单里的「很好/一般」很可能**只是夸风格/颜值**，审核者当时**未必核对了帖子数等硬指标**。所以硬标准（帖数≥200、受众德国、reel活跃等）**仍必须满足**，不因「很好」标签放宽。帖子数门槛**不下调**。

## 🔴 硬性淘汰（no 档，按语气强弱）
1. **受众非德国 / 评论英语·阿拉伯语占主导** —— 头号硬伤，原话「这样的情况不要再发生」「德国受众得超50%」
2. **不是德国面孔** —— 客户明确「要找德国面孔的博主」（这是其选品 brief 的市场匹配偏好，如实记录）
3. **reel 太少** —— 「我们主要跟博主合作 reel」，reel 少直接淘汰
4. **职业=艺术家/律师** —— 艺术家 IG 不允许投广告；律师没法带单
5. **跳舞号 / 暗黑系·非主流审美**
6. **主页杂乱 / 封面乱 / 数据不稳**（很多视频点赞<100）
7. **画质差·上古画质** —— 要明亮清晰
8. **首饰浮夸 或 很少戴首饰**（无首饰露出空间）

## 🟡 「一般」= 有亮点但有风险 → C 类备选池（常可免费/置换合作，不淘汰）
几乎都卡在**商单维度**：商单无 code / 商单无口播 / 时尚类商单太少 / 商单都是线下。
其他：播放量太少、互动太少、品类偏移（居家/烹饪/DIY/家具/健身为主，首饰露出少）、太贵、年纪偏大（受众最好 20-35）、夹杂英语。

## 🟢 「很好」= A 类
年轻貌美 + 主页干净 + 封面统一好看 + 带货感强 + 商单多有 code + 双平台(IG+TT) + 首饰露出好。bio 写「时尚｜美丽」是强信号。审美锚点：ksushakhimiy、oksana_vibe.de、xemilyxrie、amadea.pauline。

## 👁️ 视觉风格 DNA（2026-06-17 实地看 75 个代表账号，脚本测不出）

### ✅ 很好的视觉特征（正例：oksana_vibe.de / clarafelinee / elina.amaniii / christinexxe / finjamartha / joanakathyy / leonie_bartsch / yanaclare / melikee.zdn / emi.frais）
- **明亮、干净、暖色自然光**；「邻家美女」亲和感，不浓妆不暗黑
- **内容类型**：镜子 OOTD 自拍、穿搭 inspo、咖啡馆/生活方式、近脸美妆、轻健身穿搭
- **bio 公式**：**德国城市（Hamburg/Berlin/München/Köln/Düsseldorf）+ Content Creator/UGC/Beauty/Lifestyle/Fashion + 经纪/合作邮箱 + 品牌 highlights + TikTok 引流**
- 画质清晰现代，网格封面统一好看
- 首饰露出空间判断：OOTD（脖子/手）、近脸特写（耳朵/脸）、轻健身穿搭（全身/手）

### ⚠️ 「一般」的典型问题（为什么不是很好）
按频率排序：
1. **赛道偏移**（最常见）：纯健身/素食烹饪/孕期/旅行/家居/美妆-only/作家/播客——而非穿搭+首饰组合
2. **商单弱**：无 code、无口播、时尚商单太少（<3个/近2月）、商单都是线下
3. **粉丝太低**：<4K 直接降级，即使画风好
4. **内容太杂**：无清晰 niche（如 "all my sides" / "visual diary"）
5. **非种草型**：模特 portfolio 型（非穿搭 KOL）、curve model、agency 签约模特

### ❌ no 的视觉/内容特征（75个全量反例提炼）
| 硬伤大类 | 具体表现 | 典型案例 |
|---------|---------|---------|
| **审美不符** | 暗黑系妆容、重金属链⛓️emoji、alt aesthetic | minasmakeupmood（Extra Make-up Looks ⛓️） |
| **画质差** | 上古画质/低清，商单再多也救不了 | _emilysbeauty_welt（全是 Rabattcodes 但画质劝退） |
| **赛道完全不匹配** | 户外运动/孕期母婴/纯旅游/跳舞/喜剧/美妆-only/健身-only | ms_nadineslife(377K母婴)、annawillfrt(151K户外)、hannah.hofinger(137K旅行) |
| **非原创 KOL** | 搬运号/deal 聚合号，无种草能力 | shopping.mp3（220K 但全是 repost） |
| **职业硬伤** | IG 分类艺术家/律师，无法投广告 | didemercin_(演员)、fraunotarin(Notarin) |
| **受众非德国** | 阿拉伯语/英语/土耳其语评论主导 | danabnjk_(阿拉伯语)、missaljel(英语+美国并列) |
| **首饰不搭** | 首饰浮夸/极少戴/珠宝偏奢华 | bylorey(浮夸珠宝) |
| **主页杂乱** | 封面不统一、网格乱、数据不稳 | viktoriabuchbrgr(Dating Comedy维也纳) |
| **reel 太少** | 1400+帖仅3-4个reel，过气博主 | alenaarosalie(3reel/240帖) |
| **品牌冲突** | 自有首饰/珠宝品牌、竞品创始人 | heartblood(自有@atelierrenardnoir) |

### 🔑 铁律（实地看后确认）
1. **视觉质量 + 审美对味是第一道门**，先于商单/数据。画质要明亮清晰。
2. **大粉丝量不改变赛道判断**：151K/377K/137K 照样淘汰，赛道不对一切免谈
3. **美妆 ≠ 时尚 ≠ 首饰**：细分赛道要区分，需要的是「戴首饰出镜的穿搭/生活方式号」
4. **reel 比例是隐性指标**：大量发图不发 reel = 过气或非商业号
5. **bio 里有经纪邮箱是强正信号**（ambassador-agency / franklyagency / evolvemgmt / vanthom-management）

## 核心业务事实
- **ICRUSH 主要合作「口播 + 折扣码」的视频商单**（纯展示类可少量合作）
- **商单黄金量化线**（来自 ameliewagnr 批注）：近两个月 >3 个时尚商单 + 2/3 的视频播放量 >6k
- 粉丝下限其实可到 **4K+**（6-8K 小博主内容好也要），但这是「可考虑」非「优先」
- 「很贵/涨价/不回复/被别人联系了」≠ 质量差，是够不着；学画像算正例，但联系优先级低
- TikTok 完全欢迎，IG/TT 并重（非「IG 为主」）
