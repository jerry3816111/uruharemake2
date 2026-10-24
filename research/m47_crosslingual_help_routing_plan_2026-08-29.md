# M47 下一步：跨語言「要方法／不要方法」先正確到達路由

狀態：M46 後只讀問題定義，尚未實作。先讀交接 §7.60 與 M46 acceptance；M45–M46
程式、首次 Web、正式八輪與 post-fix 結果一律保留，不重跑成績覆寫。

## 單一核心變因

只修 explicit desired-response routing 的跨語言授權與否定範圍，不改 M46 goal/progress
生成、review prompt、34秒預算或效用標準：

- 中文／日文「現在給我一個步驟」應穩定選 practical help，讓原任務內容到達 M46；
- 中文／日文「不要方法／方法はいらない」應明確禁止 practical help，不可先選 solve 再由
  M46 猜不到任務而問作業；
- 同句同時有內容與回覆形式時，task clause 與 desired-response clause 的原始 span 都保留，
  不能用題型白名單、報告／書架答案或 M46 成功與否反推 route。

## 最小驗收

1. 先定位 M25/M36 對 `手順を一つだけ教えて`、`給我一個現在能做的步驟`、
   `不要給我方法` 的 token/span/negation 行為；保留失敗 fixture，不改舊 reserve。
2. 新 overlay 只輸出 current explicit route authority／negated policy 與 source spans；安全、身分、
   傾聽不退化。普通談到「方法」但沒有請求，不得誤觸。
3. 選定回歸後，用新隔離 Safari 至少跑：日文要一步、中文要一步、日文不要、中文不要、
   英文既有正例、含「方法」但不是請求的反例。逐輪核對 M47 route node 與 M46是否應介入。
4. 成功只代表 route 到達／避開正確；M46 若仍拒絕中文 action，必須另列生成失敗，不能把
   route pass 寫成實用建議 pass。

## 仍不在 M47 範圍

澄清後銜接、25秒級延遲、長對話跨 session、獨立 holdout、人類被理解感、persona
provenance 與全圖可讀性。M47 也不是人腦方程式完成。
