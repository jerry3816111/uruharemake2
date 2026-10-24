# P4-AF desired-response eligibility 因果邊界驗收

日期：2026-09-23  
狀態：**PASS（frozen deterministic development + fresh developer-authored cases）**。

## 從哪個錯誤開始

P4-AE 的唯一 fresh 結果中，`風扇一直轉，但我已經把報告寫完了。` 被錯誤建立六個回應候選。根因不是「轉」這個字，
而是舊 M18 將 `報告` 映射為 `task_pressure`，再把任何 explicit atom 當成 desired-response path 的啟動理由。也就是系統把
「話題是任務」錯當成「使用者正在要求解法／傾聽／吐槽等特定回法」。

## 單一修正

P4-AF 沒有修改舊 M18、P4-AD、候選分數或可見回覆，而是在 ledger 外加 eligibility guard。只有下列 current-turn authority
可以建立候選：

1. M37 已抽出的 typed `cognitive_overactivity`；
2. 使用者明示想要哪種 response form／明示修正；
3. 受限的 emotional/support signal；
4. 當輪真的匹配已驗證 trigger relation。

`task topic`、`task_pressure atom`、domain label 或未驗證歷史偏好單獨出現，一律沒有 authority。

## 結果

- 4 個 development：status／authority／selected action exact=`4/4`；P4-AE 反例從 6 candidates 變成 0。
- 6 個全新 positive（中／英／日 cognitive ambiguity、明示傾聽、明示吐槽）：status／authority／selected action=`6/6`。
- 6 個全新 negative（單純提任務、物理上卡在筆記本下面）：status／authority=`6/6`，topic-only authorization=`0`。
- 8 個有合法 authority 的案例 candidate policy/order/score 全數逐字保持=`8/8`，所以修的只是 eligibility，沒有偷偷改 ranking。
- visible reply／model call／fact/profile/episode write=`0`；additive product entry 與單一 graph node integration 通過。

## 現在能說什麼

可以說：這個架構現在不只列出多種「使用者可能想要的回法」，還先檢查是否真的有足夠的當輪互動證據值得建立這些候選；
單純話題詞不再自動等於需要。

不能說：候選中選到的那個一定是使用者真正想要的、回覆已讓人感到被理解、自然分布也有同樣 precision、已優於強 LLM，或已解出
人類方程式。下一個必要步驟是多輪 outcome binding：第一輪候選必須在第二輪被接受、否定或保持未知，且更新應連回同一 prediction，
不能只在下一輪重新產生另一份看似合理的分析。
