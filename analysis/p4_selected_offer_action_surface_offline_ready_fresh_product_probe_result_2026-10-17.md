# P4 selected food-offer action：離線就緒後第二批 Safari 產品驗收結果

狀態：2026-10-17，依首輪前 commit `4873ead` 凍結的六輪／gold／資源上限，**整批 strict FAIL／REVIEW_REQUIRED**。這是 developer-authored 產品前瞻案例，不是獨立 holdout、同模型 LLM 對照、人評或一般人類語用理解的證明。第一批 T1 Chroma 首載 timeout 的 strict FAIL 另見 `analysis/p4_selected_offer_action_surface_fresh_product_probe_abort_2026-10-17.md`，本次離線預檢與成功啟動不會抹去它，也不能把本批未過的語義門檻改成 PASS。

## 凍結條件與真實程序

- 首輪前原件：`datasets/p4_selected_offer_action_surface_offline_ready_fresh_probe_2026-10-17.json`、`research/p4_selected_offer_action_surface_offline_ready_fresh_probe_plan_2026-10-17.md`、同前綴 `*_freeze_2026-10-17.sha256`；commit `4873ead` 已推既有 PR #435。六題逐字各一次、0 retry、每輪 ≤20 秒、T3 後同隔離 DB planned restart，正例四輪與負控制兩輪按原 gold 判定。
- 使用新私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-wy07nein`。0-turn 離線 ONNX cache readiness 為獨立設施預檢：83,178,821-byte archive 官方 SHA256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，fresh interpreter 封鎖下載後得到 1×384 finite embedding，約 0.405 秒 embedding／0.811 秒子程序；非本批對話成本，也非產品語義 PASS。
- 真 Safari session `20261017_131154_c51dc9c2`／run `dd49e073e31b9762`／PID `25217` 完成 T1–T3；planned stop 核原 PID exited、port vacant。同 root 第二 session `20261017_131455_d61c419d`／run `840b7a6ef7f8d84a`／PID `25634` 完成 T4–T6，`previous_run_id` 指向第一 run；兩 run 均於送題前核同 PID、單一 localhost listener、HTTP 200，第二 run 末亦 planned stop、PID exited／port vacant。舊 Safari 分頁未任意關閉，服務已停，root/raw 保留。
- 兩段同一 DB 的 episode 數序列為 T0 0、T1–T3 1/2/3、重啟後仍 3、T4–T6 4/5/6；六個不同 persisted turn episode。每份快照 profile rows 均為空，六輪 row-ID delta `[0,0,0,0,0,0]`；只支持此隔離 root 未被寫入本人偏好，不外推正式 DB。

## 逐輪對照原 gold

| 輪 | Safari 輸入 | 可見最終日文／實際圖 | 判定 |
|---|---|---|---|
| T1 | `チーズポテト、一口いる？` | `普通に、ポテトなら一口ほしい。今それくらいがちょうどいい。`；selected `food_offer_generic`，新 offer audit `visible_action_preserved` | 直接邀請與物品接受符合有界 gold；graph utterance＝泡泡 |
| T2 | `友人に「抹茶ミルクシェイク、一口いる？」って言われた。` | `先に、ミルクシェイクなら一口ほしい。今それくらいがちょうどいい。`；selected `food_offer_sweet`／`named_offer_light_accept`，無新 audit node | **FAIL**：朋友的引文不是向系統直接邀請；可見回覆卻直接接受。audit 未出現不能算負控制成功 |
| T3 | `バターアップルパイ、一口いる？` | `先に、アップルパイなら一口ほしい。今それくらいがちょうどいい。`；selected `food_offer_sweet`、core `アップルパイなら一口ほしい。甘いのならあり`；**無新 audit node** | **FAIL**：可見接受與物品正確，但事前要求的 `visible_action_preserved` 圖節點缺席 |
| T4 | `焼きおにぎり、一口いる？` | `いや、おにぎりなら一口ほしい。今それくらいがちょうどいい。`；selected `food_offer_generic`，新 audit `visible_action_preserved` | 有界 action／圖通過；`いや` 與接受相鄰，屬自然度警訊，不計作全面人格品質 PASS |
| T5 | `要不要吃一口起司漢堡？` | `ん、バーガーなら一口ほしい。今それくらいがちょうどいい。`；無有界日文 offer audit node | 中文輸入得到日文；窄日文 audit 未越權。此負控制僅依原 gate 判定，不證多語泛化 |
| T6 | `チーズピザ、一口いる？` | `ピザなら一口ほしい。今それくらいがちょうどいい。`；selected `food_offer_generic`，新 audit `visible_action_preserved` | 當前物品與接受／圖通過，未混用前輪物品 |

六輪均有完成的 final、真 Safari 泡泡與 log/graph utterance 逐字相符；六輪可見輸出為日文。四個直接正例中 **3/4** 有要求的新 audit `visible_action_preserved`；兩個負控制中僅 T5 的來源與表面均合原要求，T2 雖無新 node 仍語義錯誤。M19 `user_wait_seconds` 依輪為 `[2.6651,2.8517,2.9595,2.5754,2.7189,2.8207]`，總 16.5913 秒、最大 2.9595 秒，六輪皆低於 20 秒門檻；這是 runtime 指標，不等同於從 Safari 手動觀察到最終泡泡的牆鐘時間。六輪 `bounded_slow_path_m21.route=deterministic_rule_plan` 且 `model_call_attempted=false`，故這批不含可對比的生成模型 token 用量，不能據此主張勝過強 LLM。

## 可反駁的失敗歸因與邊界

- T2 的錯誤先於最終表面：上游 `uruha_leftbrain_rules.py` 的 `_looks_food_offer_query` 對整句找物品、`一口` 與問號，沒有將引號內朋友的話排除；`get_direct_daily_query_plan` 因而選成直接食物邀請。當輪 M39 `speaker_role=unspecified`、`third_party_present=false` 未補足來源。新 selected-offer wrapper 因引用語境不合有界 source contract 而 abstain；**它沒有產生錯誤的 selected plan，也沒有修正上游錯誤**。這是可見錯行動，不只是圖缺欄。
- T3 的 selected/core 與最終接受本身符合該正例語義，缺的是可見稽核：`selected_offer_contract_p4` 會再以 `offer_reply_status_p4(core)` 核 selected core；既有有限文法不接受 `アップルパイなら一口ほしい。甘いのならあり` 的第二句，故 contract 為空，audit 無從出現。這是稽核覆蓋缺口，不能改報為 `visible_action_preserved`，也不可為了過關放寬 gold。
- `今それくらいがちょうどいい` 六輪重複暗示當前主觀合適，來源並未明示；T4 的 `いや` 與正面接受也值得產品自然度觀察。這些是另需檢驗的警訊，不在本次兩個最小客觀反例的因果修正範圍內。

兩個前瞻批次已用完：第一批設施首載失敗、第二批語義／圖雙反例。本 selected-offer 項轉 **REVIEW_REQUIRED**；原題、gold、凍結 manifest、raw 不改、不重播，不做第三批加規則追分。下一個最有意義的**獨立單變因設計審查**先處理「直接使用者邀請與第三者引述的來源作用域」，因它造成實際錯答；應事前界定准入／負控制／自然日文／成本並使用全新未曝光對照。T3 的 sweet-core 有限稽核文法另列後續儀器項，不與 T2 混改。正式同模型比較、人評、temporal holdout、VRM/Function Calling 整合皆 pending，Goal 遠未完成。

## 原始證據完整性

- 本機隔離原件 `web_logs/conversation.jsonl`：六筆，SHA256 `593ae93d1a8a7503b65938b6a004d3690d8d7ead0332e14adb8341c50f82f398`。
- `evidence/snapshot-t0_before.json`：SHA256 `d1b5898291055293a83ce1f9e1327409c477ccb9ed10d8e97d947c45637f0913`；`evidence/snapshot-t6_after.json`：SHA256 `a9b37c32f5d4d1c348d2793241d7adfe75d257ecfb664dbea7c55fe28211577f`。T1–T5 與重啟前後快照留在同一 root，供逐輪反證。
- raw 對話與私有 DB **不進 Git**；本報告只保留必要短例、hash 與可核對的局部路徑。此為同團隊 read-only audit 與因果審查，非獨立盲評。
