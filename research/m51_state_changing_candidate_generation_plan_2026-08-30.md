# M51 下一步：從完整任務產生真正改變狀態的候選，不再只重述任務

狀態：M50 bundle contract PASS 後的新修正；M46 rejection gate、M47 route、M48 surface 凍結。

## 單一核心變因

只修 **bounded candidate generation before M46 acceptance**。同一 qwen3.5:9b 對完整 source 先提出
最多三個彼此不同、來源綁定的候選操作，每個都要說明 action 如何造成 observable state change；
再讓 M46 既有 structural＋counterfactual review 審核唯一候選。若全是 task restatement、未知、
隨機移動或缺條件，仍 fail closed。

## 最小驗收

1. report／color／English heading 能生成可區分候選；禁止同義重述灌三次。
2. 候選只能引用 M50/M49 最終 allowed source，不補工具、期限、私人狀態或風險行動。
3. M46 的 allowed progress mechanisms、surface、reviewer 與 final guard 不放寬；M51 不直接交付。
4. 圖卡顯示候選數、去重、被選理由、M46 最終結果；candidate raw 不進長期 person model。
5. 新隔離 Safari 重跑 M50 三個正向與兩個安全負例；成功仍只算工程機制，不算人類偏好。

## 不在 M51 範圍

不做通用世界模型、不加 task/object 白名單、不修改 no-method、不做 holdout/human rating、不處理
長對話、正式部署或延遲最佳化。
