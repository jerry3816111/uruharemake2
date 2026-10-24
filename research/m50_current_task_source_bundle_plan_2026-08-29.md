# M50 下一步：同一輪任務片段必須以完整 source bundle 進 planner

狀態：M49 exact handoff contract PASS 後的新修正；M47 route、M48 surface、M46 reviewer 凍結。

## 單一核心變因

只修 **current-turn task source composition**。M49 已讓 task spans 到達 M46，但 planner 仍可只選
「桌上有紅紙和藍紙」而漏掉「依顏色分」，或任選一段後把完整任務拆散。M50 將同一 current-user
turn、通過 M45.1/M49、offset 不重疊且沒有 observable correction 的片段，依原順序組成唯一
`current_task_bundle_m50`。bundle text 只由 exact 原文片段加明確換行組成，不翻譯、不補語意。

## 最小驗收

1. 多片段日文 report／color case 在 M46 schema 只剩一個 bundle source；component ID、offset、
   digest 可回到原文，trace 不保存 raw dialogue。
2. 單一來源、linked previous user、純 request、no-method、correction、tampered origin 不強行合併。
3. M46 plan/review 必須引用完整 bundle；M50 graph/card 分開顯示「組成 bundle」與「模型是否使用／交付」。
4. 隔離 Safari 重跑 report、color、單一英文、純 request、no-method。成功只代表完整來源送達；
   planner 或 same-model reviewer 仍可失敗，不冒算 usefulness。

## 不在 M50 範圍

不做語意相容性的通用證明、不修單一英文 source 的理解、不改 progress taxonomy、不加物件／數量
白名單、不改日文 surface、人評、長對話、延遲或正式 DB。
