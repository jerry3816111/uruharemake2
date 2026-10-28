# P4-AE 修正後 fresh ambiguity generalization 驗收

日期：2026-09-23  
狀態：**FAIL（唯一一次事前凍結執行）**，failed gates=`3`，不重跑。

## 實驗位置

P4-AD 的第一次 validation 為 `5/9`，修正後同題 `9/9` 只能算開發回歸。P4-AE 因此在修正固定後另寫六個全新中／英／日
ambiguity paraphrases，以及六個只共享部分詞彙的 near-miss controls；資料、P4-AD module hash、gate 與一次執行限制先 commit，
才讀第一次結果。

## 結果

- 真 ambiguity：status=`6/6`、selected low-pressure clarification=`6/6`、required candidate modes=`6/6`、private reason
  unknown=`6/6`。
- near-miss controls：`5/6` 正確 abstain，false positive=`1/6`，因此正式 gate FAIL。
- 唯一反例：`風扇一直轉，但我已經把報告寫完了。` 被錯誤建立六個 response candidates，並選擇 low-pressure clarification。
- retry／fallback／case change／gate change／implementation change=`0`；可見回覆、model call、fact/profile/episode write、
  private truth commitment 也全為 `0`。

## 為什麼失敗

由凍結結果與既有程式碼可定位到：這句沒有「腦袋／想法」作為 cognitive-overactivity 主體，因此 P4-AD 新 bridge 本身不應啟動；
但舊 `_explicit_atom_assignments` 只要看到 `報告` 就建立 `task_pressure`，而 `build_current_state` 又把任何 explicit atom 當成
desired-response 啟動理由。也就是「提到一個任務」被誤當成「正在要求某種回應形式」。此外，句中的 `已經…寫完` 是完成狀態，
現有 task cue 沒有做 polarity／completion binding。

這不是模型回答內容的問題，而是原腦架構中 **topic cue → need activation** 的因果邊界太寬。它說明只把候選列出來還不夠，
必須先確認當輪真的構成需要選 desired response 的互動事件。

## 下一步邊界

P4-AE 已關閉，不能改實作後用同 12 題追分。下一個 development task 應把這個反例加入已曝光案例，單一修改 P4-AD 的 eligibility：
只有 typed cognitive-overactivity、明示 response-form authority、或既有受支援 emotional cue 可以建立 ambiguity ledger；純 task-topic atom
不能單獨啟動。修正要另配 task ongoing／task completed／物體持續運動／真正 task-pressure request 的對照，之後再用另一組全新 sealed
cases 做第一次泛化結果。

此結果仍不涉及真人偏好、felt understanding、自然分布、強 LLM 對照或人類方程式證明。
