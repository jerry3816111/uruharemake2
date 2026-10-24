# P4 時序句的行為者／作用域：單變因設計審查

狀態：2026-10-17，同團隊、非獨立的只讀審查；**尚未實作或前瞻驗收**。前批七輪與五輪 strict FAIL、首輪前資料／gold／SHA／raw 均保留，不重播舊題追分。本項只處理「誰先做哪個動作」的當輪證據准入；未知偏好句尾自然度是另一個表達風險，不能合包。

## Before：錯在規劃前，不在日文前綴

前批七輪 raw SHA-256 `77b0a8cc138b73176a4a1f47369442b5407d10ca88511da6f41d15d7552016b8`，隔離 Safari T3：`先に予定を確認して、それから返事してもいい？` → `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？`。使用者詢問能否**自己**先確認再答覆，並未要求助手先問想要的回覆形式。原報告 `analysis/p4_hash_prefix_provenance_fresh_product_probe_result_2026-10-17.md` 已將這一輪列為 strict FAIL；它只能作開發診斷，不能回填為新批 PASS。

持久 trace：M25 的 `selected_policy=calibrate_need`、`authority=current_explicit_desired_response`、M36 日文 cue `calibrate_need:ja:m36:1`；P4-AT 把同一錯誤繼承為 `p4_at_current_request:calibrate_need:ja:0` 並給 0.97 confidence；M18 的 selected core 已是上述錯句，fast path 直接交付，graph UTTERANCE 與它相同。`uruha_adaptive_person_model.py:872,1042,1093-1160` 的 `先に…確認して` 不分行為者／受詞；`uruha_executed_action_outcome_closure_p4.py:123-152,173-212` 在自己沒有新 cue 時又以 `released_m25` 繼承；`decide_response` 依明確請求選澄清。只改最後句、只刪一個 regex、或只看 final bubble 均不能證明修正。

一次**純 in-process 的曝光題診斷**暫時撤回 M25 的該明確請求（不寫檔、不跑 Safari／模型）：`state.active=False`，M18 `status=not_applied`、無 selected core；隔離的假 memory/brain runtime 只回 `分かった。`，M21 `completed_without_general_model`。這避免搶問，但仍未明確承接「使用者先查、稍後回覆」，所以**只阻斷誤升權並不足夠**；不能把該診斷當新產品成功。原 raw 的 `ordinary_selected_policy=calibrate_need` 是在錯 cue 已提升 uncertainty 後計算，亦不能推斷撤回後仍會選同一策略。

## 要凍結的唯一因果變因

在回覆形式取得權限**以前**，將當輪「先查／先問」證據分解為 `source`（直接使用者／第三者引述／不明）、`actor`（使用者自做／助手受託／不明）、`action`（自行檢查後答覆／要求助手先問／其他）與 temporal relation。只有有足夠當輪證據指向**助手受託先問使用者回覆形式**，才能以該 cue 授權 `calibrate_need`；使用者自行先查再答覆不得被升為助手提問。引述及不明行為者不因字面 `先に確認して` 取得明確請求權限；不明仍可因別的合法證據自然澄清，不應偽稱已辨識主語。若同句另有明確、獨立指向助手的請求，該後句仍可授權，不能以全句否定。

對已辨識的使用者自行延後答覆，最終行動須尊重「使用者先做、稍後回覆」，而不是搶問回覆類型。可依既有 chat/planner 路線承接；若零模型開發輪仍不能產生這個行動，需在**首輪前**提出同一 actor/scope 合約下的有界行動交付修正，並重做設計審查，不可送新題後補固定句追分。不得假裝已解析任意日文省略主語，也不把當輪暫緩變成穩定偏好或事實性長期記憶。

```text
文字／來源證據 → actor+action+time（含 unknown） → M25/P4-AT 權限
                                        ↘ M18/一般規劃 → selected action → 日文 utterance
                     graph 逐項核 actor、授權、selected、final；後續回饋仍須綁實際行動
```

## 實作邊界與優先方案

- 新 opt-in 產品層可新增一個共用 typed actor/scope gate，先於 M25 基層判定被 P4-AT 繼承的證據 seam 施行，並將不存原文的 cue ID／input digest、來源、行為者、動作、權限理由帶至 runtime node graph。安裝時須核 P4-AT 的原 classifier capture：它在 import 時保存 `_ORIGINAL_CLASSIFIER_P4_AT`，只在最末端包 `adaptive.classify_explicit_desired_response_m25` 可能造成顯示與 feedback/outcome 看到不同證據。應以新的產品入口與隔離 controller 啟用，不全域改既有入口。
- 不直接編修凍結的 `uruha_adaptive_person_model.py`、`uruha_executed_action_outcome_closure_p4.py`、`uruha_pragmatic_annotation_integrity_m36.py`、前批 overlay、舊 dataset/gold/freeze/raw；M36 離線標註正則也可能對同形字面誤報，須列為評測範圍風險，不能事後改舊 benchmark 標籤。若共用 seam 無法由 opt-in 層維持 consumer 一致，先回審查，不偷改 frozen code。
- 不改基礎模型、生成參數、來源／人格資料、記憶寫入、日文 guard、hash-prefix 已保存結果或 T3 之外的固定表達。新 actor gate 不以完整題句查表，不為特定物品／行程名稱設規則；可拒絕不充分證據，不能假報開放域理解。

## 分層成功／失敗判準與成本

1. 開發期零模型：先用**與 Safari 前瞻句不同**的自造控制核使用者自做、助手受託、第三者引述、主語不明、獨立混合子句；中英日既有明確請求、否定、protected-risk、P4-AT 前輪 outcome identity 不退化。診斷曝光 T3 只能核機制，不計新 PASS。所有 consumer 的 actor/M25/P4-AT/M18 selected/feedback 權限一致；使用者自做 case 的最終行動與 utterance 不搶問。回歸只跑受影響測試，舊 SHA manifest 不變。
2. 首輪前另寫全新、未執行的開發者前瞻題與逐句 gold，涵蓋至少 self-defer、真正助手先問、引述、不明／混合，以及中英日；避免和開發 fixture exact 重複。將程式／資料／計畫／成功閾值做 SHA manifest，commit、push、核 PR #435 head 後才送 Safari。這不是獨立 holdout。
3. 使用新 0700 隔離 root、localhost、0-turn 同 PID/單 listener/HTTP 200、私有官方 SHA ONNX 離線預熱和顯式空 profile setup；成本各列。Safari 一次性逐字 0 retry，每輪最多 20 秒，至少一次同 DB planned restart、兩個 session；逐輪核泡泡＝graph UTTERANCE、actor node→M25→P4-AT→M18 selected→final、episode distinct、全 profile status/count/content digest 不變、model calls/tokens/等待，最後核 PID exited／port vacant。無操作錄影時 browser bubble 與 0 retry 只能報當輪目視，不稱 raw 可獨立重算。
4. strict PASS 需所有新輪程序、typed actor/action/authority 與可見日文語義均符合事前 gold，負例不由同一 cue 冒充明確助手提問，正例不被誤擋；人格、來源、未知不編與自然日文是必要 gate。任一失敗整批 FAIL，保留原件與前置判準；最多兩批有理由修正，不能換題／放寬 gate 追分。可量化 before 是曝光 T3 1/1 actor/action 錯，前瞻 after 只能由首輪後新案例另報，不可將兩者相減當因果率。

即使本項通過，證明的也只是有限時序／行為者來源邊界在本機產品路徑可用；仍不等於 fresh model generation、同模型優勢、人類被理解感、正式 temporal holdout 或人類反應方程式成立。預算上限為一次 0-turn 預檢、一批最多 8 輪 ×20 秒等待加 planned restart／ONNX 預熱與完整快照；若首輪前零模型未能交付 user-defer action，**不消耗**新 Safari 題，回設計審查。
