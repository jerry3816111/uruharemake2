# P4-AX real compound-feedback-to-action delivery: formal FAIL

事前凍結的兩輪 private runtime／Safari gate 正式為 **FAIL**。兩輪在同一隔離 session、port `7889` 各執行一次；題目、gate 與結果永久封存，不重跑也不在結果後改門檻。

## 可見結果

Turn 1：

> 腦中的念頭一波接一波冒出來，怎樣都停不下來。

> いや、寝てないのか、考え事で止まんないのか、まずそこだけどっち？

Turn 2：

> 你先把我想要的回應方向弄清楚，這樣很正確；現在給我一個步驟，要能馬上開始、完成就停止。

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

兩輪都是自然日文、都有隔離的 durable episode，Chroma 恰有 2 筆 embedding。Safari 真實顯示兩輪 node graph，並展開核對 P4-AX、P4-AU 與 M45；沒有關閉任何既有分頁。

## 新能力真正通過的部分

Turn 1 沿用既有已驗證路徑：P4-AW=`authorized_current_user_ellipsis`、P4-AS=`executed_and_committed`、M44 exact receipt=`p1-1-a2d0dce3c511bcd2`、P4-AR=`authorized_executed_product_event`，六個 P4-AG 候選選中 `calibrate_need`，future outcome 被鎖定等待下一輪觀察。

Turn 2 的 P4-AX 在真實產品中得到 `bounded_support_composed`。它把前半句視為對 exact 上一輪澄清的支持，把後半句保留成新的 `solve_regulation`／`practical_help` request。因此：

- exact pending receipt identity=`true`；
- previous outcome 由 predecessor 的 `unknown` 更新為 `supported`；
- `two_independent_acts=true`；
- P4-AT=`closed_supported`，prediction id 精確相同；
- P4-AG previous resolution 也成為 `supported`，而不是把未驗證推測寫成長期事實；
- P4-AX 沒有修改 P4-AT predecessor、沒有繞過 P4-AU、沒有新增 model call 或 factual-memory write，也沒有把原始對話複製進 trace。

P4-AX graph node index=`66`，在 P4-AT `67`、P4-AG `68`、temporal `69`、utterance `70` 前。這是 P4-AX 的 fresh real-product bounded PASS；它只證明該受限複合語用拆分在一條真實產品路徑成立。

## 最早失敗：P4-AU 把回覆形式誤判為新任務

P4-AU 看見一個長度 20 的 `task_clause`，將 Turn 2 的「給我一個步驟、能馬上開始、完成就停止」視為 `current_turn_contains_independent_task_source`，因此 status=`blocked_current_task_replacement`。它能核對 Turn 1 digest=`4ebe80e6d582690d`，但 `prior_source_added=false`；不能把「知道上一輪來源是哪一筆」當成「來源已交給行動生成」。

這裡必須區分兩種情況：

1. 使用者真的換了一個要處理的問題或主題，此時舊來源不應被偷偷帶入；
2. 使用者沒有換問題，只限制回答要「一個步驟、立即開始、有停止條件」，這是 response-form／action-shape constraint。

本輪屬於第二種，但既有 P4-AU 將它判成第一種。這是本次最早、可單獨修正的因果缺口。

## 獨立的後段模型失敗

即使不考慮 P4-AU，後段仍有另一個獨立失敗。M45 做了 1 次完整 model call，記錄 `1001` prompt tokens 與 `360` completion tokens，但回傳不符合契約的資料並引發 `JSONDecodeError`。因此：

- M51=`not_invoked`，候選數 0；
- M46=`plan_unavailable`，content/surface 都未通過；
- P4-AV 與 M53 沒有到達，不能把缺少 unsupported label 誤算成通過；
- M45=`withheld_model_unavailable`；
- M39 對 `practical_action_not_delivered_m45` 正確 fail closed，最後再次澄清而沒有交付動作。

這個 JSON 失敗不會在下一個來源修正裡一起改，否則無法歸因哪一個變因造成結果改變。

## 圖、成本與正式失敗

Turn 2 graph index：P4-AU `53`、M50 `54`、M51 `55`、M46 `56`、M45 `57`、P4-AX `66`、P4-AT `67`、P4-AG `68`、temporal `69`、utterance `70`。P4-AV 與 M53 節點不存在，因此它們的 integrity／ordering gate 都是失敗，不用缺席冒充通過。

Turn 1 latency=`3.776s`，Turn 2=`31.0372s`；只有 1/2 達到 20 秒目標。總 model calls attempted/completed=`1/1`，tokens=`1001+360`，但產物解析失敗，token accounting 仍標為 incomplete。runtime 已停止，隔離 artifacts 保留，Safari 留在結果頁。

正式失敗包括：P4-AU exact prior-source handoff、P4-AV integrity、M53 verified no-unsupported、M45 delivery、M46 verification/content/surface、M39 practical act、禁止再次澄清、兩個缺席節點的 ordering，以及 2/2 latency target。

## 能主張與不能主張

現在可以主張：在一個全新真實 Safari 輪次，P4-AX 能把「支持剛才的澄清方式」與「現在要求實際步驟」分開，精確關閉上一個 observable action outcome，並把修正顯示在 graph。

不能主張：exact prior-problem source 已成功交付、後段 plan 已形成、可見動作已交付、建議對真人有用、使用者真的感到被理解、自然分布泛化、人類方程式，或優於 matched strong LLM。

## 下一個單一變因

本正式 pair 只保留為 exposed negative evidence，不再執行。下一個 P4-AY 只修 P4-AU 的一個邊界：把「回答要一個步驟／立即開始／完成即停」這類 response-form／action-shape constraint，與真正的新問題／新主題分開。

必須先凍結全新的中／英／日正例與 genuine task-replacement controls；保留 exact receipt、direct-user source authority、P4-AT outcome、M45/M46/M39 fail-closed、prompt、model call、memory 與 visible reply 不變。這一變更不能把本次 `JSONDecodeError` 改寫成成功；通過 offline 後仍需另一組全新 Safari pair。
