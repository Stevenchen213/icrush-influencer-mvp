# ICRUSH 达人营销项目

> CLAUDE.md — 供 Claude Code 加载项目上下文
> 完整信息见 AGENT.md（供 Codex）

# ICRUSH AGENT.md

> 椤圭洰绾т笂涓嬫枃鏂囦欢锛屼緵 AI agent锛圕odex / Claude Code锛夋帴鍔涙椂瀵归綈鐘舵€併€?
> doc 鑱岃矗鍒掑垎: AGENT.md=AI涓婁笅鏂?/ README.md=浜虹被姒傝 / docs/rules.md=瀹屾暣瑙勫垯

---

## 椤圭洰姒傚喌

**ICRUSH** -- 鍥藉唴鍔炲叕瀹よ嚜鍔ㄥ寲杈句汉绛涢€夌绾裤€傝緭鍏?Instagram/TikTok 涓婚〉閾炬帴锛屾寜纭€ф潯浠惰嚜鍔ㄥ垽瀹氶€氳繃/娣樻卑/缃崲/澶嶆煡锛岃緭鍑?Markdown 鎶ヨ〃銆?
褰撳墠鐗堟湰锛?*v0.7**
GitHub: https://github.com/Stevenchen213/icrush-influencer-mvp.git

---

## 鐢ㄦ埛瑙掕壊

- **ICRUSH 瀹炰範鐢?*锛屾壘寰峰浗 IG/TT 鐝犲疂鏃跺皻杈句汉
- 浣跨敤 **椋炰功** 鍋氬叡浜煡閲嶈〃
- 浣跨敤 **Wednesday (Upfluence)** 鐪嬪彈浼楃敾鍍忥紝鏈堥厤棰?3000 views
- **棰勭畻鏁忔劅**锛欰pify 鏈堥厤棰濆凡鑰楀敖锛岄渶鍏呭€?
- Python 璺緞锛歚C:\Users\yaxua\AppData\Local\Programs\Python\Python312\python.exe`

---

## 鎶€鏈爤

| 灞?| 閫夊瀷 |
|---|------|
| 璇█ | Python >=3.11 |
| 渚濊禆 | httpx, langdetect, playwright, python-dotenv, drissionpage |
| 鏁版嵁婧?| Apify Actors銆乄ednesday API銆丳laywright stealth銆丏rissionPage |
| 瀹圭伨 | Apify 澶辫触 -> Playwright headless 鍏滃簳 |
| 缁撴灉 | Markdown 琛ㄦ牸杈撳嚭鍒?`results/` |

---

## 鍏抽敭鏂囦欢

```
icrush/
  discoverer_hashtag.py    # Apify hashtag 鎼滅储
  discoverer_snowball.py   # Apify 闆悆娉曪紙绉嶅瓙 -> hashtag锛?
  discoverer_suggested.py  # DrissionPage 鎺ㄨ崘鍙戠幇锛堟柊澧烇級
  discovery.py             # Wednesday 鍙戠幇寮曟搸
  dedup.py                 # KOL 鏌ラ噸 API
  pipeline.py              # 鍥涢樁娈电紪鎺?
  judges.py                # 鐭矾娣樻卑 + caption 鍒ゅ畾
  language.py              # 璇█妫€娴嬨€佸湴鍖恒€佽亴涓氥€佹€у埆
  wordlists.py             # 璇嶅吀
  wednesday.py             # 缂撳瓨璇诲啓 + 瀹炴椂鏌ヨ
  classifier.py            # 鍟嗗崟鍒嗙被
  report.py                # Markdown 琛ㄦ牸杈撳嚭
  airtable.py / feishu.py # 鎺掗櫎鍚嶅崟 fallback
  config.py                # 闃堝€煎父閲?

scripts/
  run_batch.py             # 涓诲叆鍙ｏ紙鐢ㄦ埛璐碪RL鏃舵案杩滅敤杩欎釜锛?
  discover.py              # 缁熶竴鍙戠幇 CLI锛?-method wednesday/hashtag/snowball/suggested锛?
  ig_stealth_search.mjs    # Playwright stealth IG 鎼滅储
```

---

## Pipeline 閫熻

| Stage | 鍋氫粈涔?| 娣樻卑鍗冲仠 |
|-------|--------|---------|
| STAGE 0 | KOL 鏌ラ噸锛圠ambda API锛?| 宸插叆搴撳垯璺宠繃 |
| STAGE 1 | Profile + 鐭矾娣樻卑 | 鍛戒腑鍗崇粓姝?|
| STAGE 1.5 | Wednesday 鍙椾紬鏌ヨ | - |
| STAGE 2 | 20 鏉?posts + 鍟嗗崟 | - |
| STAGE 3 | 璇勮 + 鍒ゅ畾 | 閫氳繃/娣樻卑/缃崲/澶嶆煡 |

瀹屾暣瑙勫垯瑙?`docs/rules.md`

---

## 鍙戠幇鏂瑰紡瀵规瘮锛?026-06-23 楠岃瘉缁撴灉锛?

| 鏂规硶 | 浠ｇ爜 | 鐘舵€?| 璐圭敤 | 璇存槑 |
|------|------|------|------|------|
| **Playwright stealth IG 鎼滅储** | `ig_stealth_search.mjs` | 宸查獙璇佸彲鐢?| 鍏嶈垂 | 缁曡繃 IG 鍙嶇埇锛岀洿鎼?hashtag 椤?|
| **Playwright bio 楠岃瘉** | `ig_bio_check.mjs` | 宸查獙璇佸彲鐢?| 鍏嶈垂 | 閫愪釜鏌?bio锛屽垽鏂槸鍚﹀痉鍥?|
| **Wednesday 鎼滅储** | `--method wednesday` | 鍙敤锛堥渶閰嶉锛?| Wednesday 鏈堥厤棰?| 7/1 閲嶇疆 |
| **Apify hashtag 鎼滅储** | `--method hashtag` | 鏈哄埗宸查獙璇?| Apify 鎸夐噺璁¤垂 | 闇€鍏呭€?|
| **闆悆娉?* | `--method snowball` | 浠ｇ爜灏辩华 | 鍚屼笂 | 绉嶅瓙 -> hashtag -> 鏇村 |
| **DrissionPage 鎺ㄨ崘鍙戠幇** | `--method suggested` | 浠ｇ爜灏辩华锛堝緟瀹炴祴锛?| 鍏嶈垂 | 绉嶅瓙 -> IG 涓轰綘鎺ㄨ崘 |

---

## 閲嶈绾﹀畾

1. **鐢ㄦ埛璐?URL -> 姘歌繙鐢?`python scripts/run_batch.py`**
2. **杈撳嚭琛ㄦ牸淇濇寔杈撳叆椤哄簭**
3. **鍙戠幇鏂规硶浼樺厛閫夊厤璐圭殑**锛圥laywright / DrissionPage锛夛紝閰嶉鐣欑粰 Wednesday

### 鍋忓ソ锛堥潪纭€э紝鏈€缁堜汉宸ラ€変汉鏃跺湪鎰忥級
- 鐧戒汉骞磋交缇庡コ杈句汉锛屾椂灏?绌挎惌/缇庡/鐢熸椿鏂瑰紡绫?
- 瑕佹湁鍙ｆ挱鍟嗗崟锛堜笉鍙槸鍥炬枃 #ad锛?
- IG 涓轰富锛孴T 涔熷彲浠?
- 鍙嶇洰鏍囷細姘戞棌鏈嶉グ / 娓告垙 / 椋熺墿 / 浜插瓙 / 鐐瘜 / 鍝佺墝鍒涘浜?/ 鍝佺墝瀹樻柟鍙?/ 瀹犵墿 / DIY

### 鏌ラ噸鏈哄埗锛堜笁閲嶏級
- Lambda API锛堜富锛夛細`POST {account, platform}` -> "鏈夐噸澶?鍒欒烦杩?
- Airtable / 椋炰功锛坒allback锛夛細lookup by username
- 鏈湴鏂囦欢 `data/exclusion_list.json`

---

## 当前会话状态（2026-06-24）

### 本会话重大突破
- IG 类似账户三步法验证成功：类似账户 -> 为你推荐 -> 查看全部 -> 滚动 -> 提取
- 每个种子可挖出 ~80 个关联达人，完全免费
- 旧方法全失效原因：IG 把推荐从页面区域改成了弹窗+查看全部
- 生产脚本：scripts/fetch_similar_accounts_v3.mjs

### 本会话验证结论
- Apify relatedProfiles：永久失效（IG 4月起服务端移除）
- Playwright API/HTML（旧版）：全失效，找的是老 UI
- Playwright 弹窗三步法：每个种子 ~80 达人，免费，已验证

### 待办
1. [x] 实测 IG 类似账户抓取 -> 已突破
2. [ ] 将三步法整合进 discoverer_suggested.py
3. [ ] Apify 充值后跑 --method hashtag --run（$4.998 剩余）
4. [ ] Wednesday 配额重置后刷新缓存（7/1）

