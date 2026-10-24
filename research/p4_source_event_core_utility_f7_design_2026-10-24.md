# P4 f7：當輪可觀察事件對選中核心的來源覆蓋效用

狀態：**事前 source-only 設計，0 f7 產品碼／0 f7 真模型／0 Safari Send**。f6 結果已在 `analysis/p4_visible_japanese_guard_f6_fresh_product_failure_2026-10-24.md` 凍結：選中核心與最終泡泡都沒提陶藝小碟，M29 卻已辨識明示 `brief_encouragement`。`post_check.did_reply_cover_focus=false` 只是既有焦點詞覆蓋失敗，不能誤稱為陶藝事件辨識；M39 `observable_concepts=[]` 接受泛稱回覆。f5/f6 原題、gold、raw、strict FAIL 均不修改或重送。

## 問題、唯一變因及因果邊界

f7 只在**已通過當輪 User→M29 direct-reply-act 證書、M33 不適用、實際 full compact planner**的候選選擇邊界，加入保守的「observable source event → candidate core」覆蓋效用。真輪固定既有 `--direct-act-arm control`，只開新 utility flag，保留 f6 的 `control_no_handoff`；不能同時開 `treatment` 注入 planner prompt。必須核 `compact_general_plan_p2.completed=true`、`candidate_count=3`、M21 `model_call_completed=true`、`fallback_used=false`，不能僅憑 route 名稱宣稱是同一候選生成條件。

只讀 `cue_span` 前的當輪事件敘述；不把 `今は一言だけ励まして` 這類回覆指令當事件。初版只支援單句、非引述、未否定、直接 User 自述、明確日文受詞與動作的有限構式；不符則 `unverifiable`、維持舊選擇，不猜 actor、情緒或中文/英文翻譯。對每個候選只根據可觀察物件與動作兩個不同來源成分作保守覆蓋檢查；純 `おめでとう`、只提 `今`、只提物件、不提動作、錯 actor／極性／受詞均不能得來源效用。候選的相對 persona/psyche 等舊分數不改，只有有來源證書且 response mode/scene 未衝突的候選可得到額外效用；若三個候選都泛稱，記 `no_grounded_candidate`，**不能憑空造出正確候選、不能改字面 gold 或把 FAIL 當 PASS**。

凍結的有限來源構式是 cue 前**恰一個完整句子**，含直接自述 `自分で{object}を{action}`，`object` 與 `action` 均為非空日文原文 span；開頭可有 `初めて`，但不得把它當候選得分的必要條件。只在候選核心同時含這兩段**原文字面**且沒有引述、否定或明示的非 User actor 時授予 `grounded`；同義改寫／跨語翻譯無法由此證實時一律 `unverifiable`，不硬猜。`scene` 僅 casual/support 且 `response_mode` 僅 direct_answer/direct_answer_with_hedge 可得效用。選擇規則為先在 grounded 候選內沿用原有 Bayes score 順序；若無 grounded 則完全沿用原選擇，等價於只對符合證書的候選加一個固定優先層，絕不重估 persona/psyche。候選 index 固定為**模型原始三候選順序**，hash 為核心 UTF-8 SHA-256；不持久化原文。這個有限字面檢查不能證明 `初めて` 或 `自分で` 已在可見回覆完整表達，故仍以事前 visible gold 另判。

可在同一次生成的三個候選上計算「未加效用的舊選擇」與「加效用後的選擇」，保留 bounded index、hash、覆蓋狀態和原因，不存 raw 候選；這只是共用候選集上的 selection counterfactual，不是 baseline 可見回覆、人評或強 LLM 對照。多 tick critique 可能修訂或重建候選，故**實際操弄**另要求同一最終候選集舊／新 index 不同、最後 selected core hash 等於加效用 winner hash、其後沒有 revision/final-tick repair；否則標 `not_exercised`，不可拿中途 index 變動冒充最終選擇改變。若模型三候選不含 grounded core，這一變因無法改進產品，下一階段才應單獨檢查候選生成；不能在本項同時改 prompt、schema、translation、fallback、M29/M39、final guard、記憶或圖版型。

允許檔案：新 `uruha_source_event_core_utility_p4.py`、`uruha_brain_mac.py` 的當輪證書→full compact 選擇窄接線、`p4_direct_reply_act_m29_priority_detached_control.py` 的 child-only opt-in flag、必要的 focused tests、此設計/題本/manifest/結果和 `CURRENT_TASK.md`。不改 `uruha_compact_planner_p2.py` JSON Schema/prompt、既有 f6 產品 guard 或其他產品路由。測試必須證明 flag off 位元組等價、證書失配/過期、非 full route、安全/記憶路由、中文/英文或不明日文、引述/轉述/否定/矛盾等皆不取得效用；同一候選集的 grounded vs generic 可重選且 actor/polarity 錯誤不加分。來源偵測不得硬編 f7 名詞作答案；對詞形變化不能保證則標 `unverifiable`，不得稱一般日文語義等價。最後若 surface 漏掉選中事件，也必須整體 FAIL，不能只拿 planner score 過關。

## 事前新題、驗收及成本

新作者題／gold 在 `datasets/p4_source_event_core_utility_f7_probe_2026-10-24.json`；對當前 tracked repo 的完整 `庭のベンチ`／`塗り直した` 片語查找 0 命中（單字 `ベンチ` 已見於舊第三人引述題，不能稱詞彙全新），source-only M29 判定 `brief_encouragement`、`cue_span=[18,29]`，位於事件句之後。題不屬正式 temporal holdout。採 7934 新 0700 私有 root、先空 port/官方 ONNX 私有離線 warm/同 PID zero-turn ready-planned stop、T0/Tpre 0600+fsync；靜態檢查先於 Tpre，完整背景 pair 後快照並立即原生 Safari 一次 Send、0 retry，Tpre→arrival ≤10s 且無 interleave、同 opaque ID 完整 delivered。若入場失敗，保存 pre-Send 或 off-gate FAIL，不重送。

code gate：先紅後綠、嚴格注入/陰性契約與完整隔離 RightBrain+fake LeftBrain route、受影響回歸、compile/diff、product SHA。真輪操弄需持久 trace 顯示 `eligible=true`、至少一個 grounded candidate、同一最終候選集的舊 index→新 index 有變化、最終 hash 相符且沒有後續 repair，才可說 selection 被實際改變；否則 `not_exercised` 或 `no_grounded_candidate`。可見 gate：自然短日文同時接住「第一次自己把庭院長椅重新上漆」與只要一句低壓鼓勵，不教學、不追問、不捏造；泡泡＝raw＝guard＝graph UTTERANCE＝隔離 episode。圖上須呈現來源事件證書、候選覆蓋、舊/新選擇、缺證據狀態，以及 input→retrieval→decision→utterance→writeback；native visual 原件若無法保存，明記缺證。上限 1 Safari Send、3 completed generations、2000 provider tokens、20s user wait，另列背景/embedding/Web 未 instrument 成本。任何語義、日文、時序、隔離或證據硬 gate 失敗，整體 strict FAIL。

f7 若通過只能說有限日文直接自述＋明示回覆指令中，選擇器可能更偏好帶有當輪物件/動作證據的**已存在**候選；不證實模型能普遍生成 grounded 候選、跨語意圖、人類理解或優於同模型 LLM。下一步依真結果決定：全泛稱→前瞻研究候選生成；已選 grounded 但 surface 丟失→單獨研究表面保真；證書誤授權→縮窄驗證，不用額外固定答案追分。正式資料、原始 dirty checkout、無關 `output/` 保留。
