# P4 f6：真 Safari 無混語，但來源承接仍 strict FAIL

狀態：**完整產品 strict FAIL；日文表面與入場／成本狹義 PASS；f6 guard 在此真輪 `not_exercised`**。f6 事前題本及單變因計畫在 `dff1efa`、紅綠/隔離假模型證據在 `7a1ffb1` 已推既有 PR #435；本報告不重判 f5，也不把不同題的 f5→f6 當成因果 A/B。唯一產品變因仍只是共用 `AUDITED_NONSTANDARD_CJK_RE` 新增 `继/续`；模型、prompt、候選排序、M29/M39、fallback、記憶及題本未改。

## 實際一輪與事前 gold

在原生 Safari 的全新本機 `127.0.0.1:7933/`、session `20261024_074129_c50c045d`，只送一次 `初めて自分で陶芸の小皿を焼き上げた。今は一言だけ励まして。`，**1 Send／0 retry**。最終泡泡、私有 JSONL `assistant_reply`、最終 guard、圖上 UTTERANCE 以及隔離 Chroma 唯一 episode 的回覆都是：`おめでとう！これからもがんばろう！そのくらいでいいだろ。`。這句沒有簡體中文或英文，也有一般性的祝賀；但沒有具體承接「第一次自己燒好陶藝小碟」，`これからもがんばろう` 只是泛稱勉勵，未達事前 `visible_gold.must`。因此**可見語義品質 FAIL**；不因純日文而改判。沒有教學、追問或可辨識的私密經歷捏造；本題不驗正向 self-identity。

本輪 `M29` 從當前 User cue 辨識 `brief_encouragement`，但 `direct_reply_act_planner_handoff_p4` 是事前凍結的 `control_no_handoff`／`full_planner`，沒有注入 planner prompt。compact JSON schema `completed=true`、3 candidates、無 parser fallback；selected `core_message_jp=おめでとう！これからもがんばろう！`，`grounding.topic_terms=[今]`。`M39` 的 `source_frame.observable_concepts=[]`、`selected_policy_id=null`，卻 `accepted_verified_surface`；`post_check.did_reply_cover_focus=false`。該 post-check 的 false 只記錄既有焦點覆蓋未過，**不是**獨立辨認出陶藝事件的證書。具體事件在選中核心已丟失，現有來源覆蓋檢查沒有擋住；不是 Safari 翻譯或字元 guard 可修復的部分。未持久化的另兩候選原文不可推斷。

`visible_language_guard.changed=false`、`initial_rejection_reasons=[]`，M49 `not_required`；selected core 與可見回覆原本就是純日文，持久 trace 未見候選因 `nonstandard_cjk_surface` 被拒，最終 guard 也沒有觸發。其他兩個原始候選不持久化，不能推斷其字面內容。因此按事前持久證據判準，f6 的**真模型操弄檢查是 `not_exercised`**，不能說新增 `继/续` 在此輪帶來產品改善。已通過的紅→綠、shared candidate/guard/episode 契約只證「若出現這兩字就能攔」，f5 deterministic replay 的退化泛稱回覆亦仍是品質 FAIL。

## 隔離、入場與圖表原件

- 新 0700 私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-ps4d1a64`；官方 ONNX archive SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`、83,178,821 bytes 的私有複本 inode 49380167（host 4160298），離線 warm 1×384、下載嘗試 0。zero-turn run `7e0231c7158a7d09`／PID 36220 同 PID ready、planned stop；正式 opt-in run `5d12964312db5fa4`／PID 36445 同 PID HTTP ready。正式 DB/原始 dirty checkout 未碰。
- T0 `evidence/db-t0.json` SHA `fb09a62b821a31c28f254e43118d98df0732abd9420269d9f08e2f70a19872c4`（journal 0）；Tpre SHA `f66f57d0b2d4ef631dc57186c177bcc71f357d937e1ad3f714c59248798df25f`，receipt 為同 PID/session、reset0、human finish0、tick5，journal seq1–26 是 13 對完整 background，0 reported/vector writes、0 error/unknown worker。T0/Tpre 的唯一 DB 檔 `chroma.sqlite3` 176,128 bytes、SHA 均 `89c0d864c80e0ffe71bbe0bfd55b251247d20ce5e8592d09c983eb32c7a0261f`。
- Tpre monotonic end `1798956222344791` → seq27 human arrival `1798959368152916`，間隔 **3.145808125 秒**，中間 0 background/proactive 事件；seq27 arrival→28 admission ready→29 cognition start→30 cognition end→31 terminal delivered 均同 opaque ID `727278ee833c9d9425e17ac2a8b174b4`、PID36445、reset0。Tpost SHA `d5c609ec8740b5c5b6317326a19a2fa32c24123d95c009b3883cf1ea95676d7a`，在 seq33 完成後；最終 receipt finish1、reset0，journal 49 events／22 完整 background pair，其背景 pair 0 mutation/error（human turn 另有 1 筆合法 episodic add），SHA `7fc53997e42dab62a1981c3dad3563e2d05184a0f818f8a8c8cfbf66160a12e8`。
- 私有 Web JSONL **1 行**、SHA `8ac31ccc527e85d0f2f30c1a311081880c61aad05b027b4b49da6d8cabba37ce`。原生 Safari 目視泡泡與大型 node graph，AX 核對 USER SIGNAL、空檢索 `retrieved_candidate_count=0`、3 candidate plans、selected plan、M29/M39/guard、UTTERANCE、`memory_updates`/episodic writeback 與本輪相符；圖上 UTTERANCE 同泡泡，flow 有真節點/連線，並沒有憑空畫出已驗證的過去/未來。隔離 DB `episodic_memory=1`、`user_profile=0`、其他三集合 0；唯一 episode id `0497fee3-8d6b-489c-b03e-5e94fa3395c8` 的 document 同時保留來源句與回覆，並非只儲存裸回覆。Safari 截圖/AX **只在工具畫面目視，未有可持久重核 native PNG/AX 原件**；圖很寬、部分節點標籤被截短，外行可讀性不能由這一輪證明，saved-visual gate 未達。
- 正式 PID36445 exact planned stop、port7933 vacant；stop record SHA `84107cb377aec2f1e6b683d3cb6acc151160395e657f4f00e70e4304f6ee471b`。只關本次新 Safari tab，原先 52 個分頁保留；私有失敗 episode 留於隔離 root 供稽核，未混入正式長期記憶。

## 成本、可主張範圍、下一步

本輪 receipt `captured`，1 次本機 `qwen2.5:7b` 生成（prompt **1,042**＋completion **83**＝**1,125 provider tokens**；模型 call **8.43256s**）、11 次 instrumented Chroma vector ops（10 query、1 episode add）、failed 0；user wait **10.9233s**，低於 20s cap。Tpre 前背景完成 pair 的讀取與 turn 後背景事件不算在 user receipt；embedding token、CPU/RSS/energy、Web 額外成本和真人被理解感仍 unavailable。3 completed generations／2,000 tokens／20s／1 Send 上限均未超。

結論只能說：特定簡體字漏檢已有可測試的共用 guard 修補；本次 fresh 產品回覆沒有混語，但**並未實際觸發此修補，也未達來源具體承接**。不能據此說系統勝過強 LLM、具有人類理解、完整日文保障、正式 temporal holdout 或人評通過。下一個必要變因應先讓 selected core 對當輪可觀察事件有來源對齊與失敗可追溯驗證；先做前瞻 source-only 設計／新題／單變因審查，再紅綠與隔離真 Safari。不可回頭改 f5/f6 gold、重送同題，亦不可再用加字元清單冒充語義修復。Goal active。
