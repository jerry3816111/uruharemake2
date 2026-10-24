# P4-H 多語偏好記憶行為 plan-level authority 驗收

日期：2026-09-21  
正式 gate：`pass`  
證據範圍：bounded product plan／surface；不是完整偏好語意或研究優勢

## 這一步修正了什麼

P4-G 的真實負結果證明，只在最後看到 `了解しました` 才換成 casual 日文不夠：模型可能回 allowlist 外的句子，更正輪也可能先被舊規則
誤判成 `ask_like_me`。P4-H 沒有擴大制式回覆 allowlist，而是讓已凍結的明示第一人稱偏好分類器，在 general planner 與舊 intent
碰撞之前取得 deterministic plan；同一個 typed act 再取得最後 surface authority。

這個設計只處理兩種可觀察行為：使用者明確要求記住目前偏好，以及明確否定舊偏好並提出現在偏好。普通聊天、第三人稱、假設、引文、
自傷風險、Function command 與 VRM command 都會 fail closed，交回原路由。沒有改 general persona prompt、episode schema、memory ranking
或 P4-F recall。

## 事前凍結與執行

P4-H implementation commit `7d4e8d8` 在真實執行前已通過 207 項受影響回歸。接著 acceptance contract、gate 與全新案例以
commit `e8e617a` 先提交；凍結要求 1 個新隔離 process、兩輪各送一次、0 planner model call、0 retry、20 秒內、兩個不同 episode、
graph node 必須在 `select` stage 且 exact-match audit 必須為 true。

舊 P4-G 的茉莉花茶／冰咖啡案例沒有重跑。P4-H 使用全新 mode-0700 root
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-qcds63tm`，repository write sandbox 開啟，
production memory 未讀取。Safari 沿用既有 Uruha 分頁；沒有關閉觀察到的 50 個分頁。

## 真實兩輪結果

第一輪 English write：

> I prefer sparkling water. Please remember that as my current drink preference.

可見回覆：

> ん、その好みは覚えとく。

結果為 `explicit_preference_memory_write`、`en/write`、`deterministic_rule_plan`，graph 顯示
`explicit_preference_acknowledgement_p4` 的 `select` node；planner model call 0，episode
`f4e13c9b-c223-4c72-a656-eca83a178b1a`，使用者等待 `2.1027s`。

第二輪 Chinese correction：

> 更正：我現在不喜歡氣泡水了，現在比較喜歡熱可可。

可見回覆：

> ん、訂正の内容はそのまま覚えとく。

結果為 `explicit_preference_memory_correction`、`zh/correction`、`deterministic_rule_plan`，同一 graph node 仍位於 `select`，
沒有再落入 `ask_like_me`；planner model call 0，episode `79c430c2-e004-4998-9c94-025fca2ed4bb`，使用者等待
`11.2373s`。

frozen gate 重新計算為 `pass`，failed gates 0。兩輪合計等待 `13.34s`，0 retry／fallback／paid API／external deployment／
production memory／Function tool／VRM action。兩輪各有 69 個 runtime nodes，visible surface、act、language、intent、plan/surface authority、
graph stage、episode write、exact-match 與 latency 都符合事前契約。

## 不能隱藏的語意缺口

這個 pass 不代表多語偏好已完整寫進 typed profile。第二輪後實際 profile 是：

- `likes=[]`
- `dislikes=[氣泡水]`

也就是舊項目「氣泡水」被抽成 dislike，但新項目「熱可可」沒有進入 likes。兩輪原始互動都有以 episode 保存，所以 P4-H 能誠實確認
「這輪被記錄」，但目前不能把 surface 的「訂正內容はそのまま覚えとく」外推成完整 typed current-preference semantics 或 cross-restart
recall。下一個必要工作應從這個觀察出發，單獨修驗多語 typed preference write／supersession，不再改本輪已通過的表達層。

## 結論邊界

P4-H 證明一個窄但真實的產品改善：明示偏好寫入／更正不再依賴任意模型措辭，也不再被已知舊 intent 規則搶走；使用者看到固定、自然、
短的日文，圖上可看見 act→plan→surface，且不花 general planner call。它不證明 complete multilingual memory semantics、重啟後 recall、
一般人格品質、felt understanding、人類偏好或相對強 LLM 的研究優勢。
