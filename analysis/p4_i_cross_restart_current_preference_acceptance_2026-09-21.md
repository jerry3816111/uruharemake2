# P4-I 跨程序目前偏好 typed-state 驗收

日期：2026-09-21  
正式 gate：`pass`  
證據範圍：一個事前凍結的跨程序產品案例；不是開放世界記憶或研究優勢

## 這一步真正改變了什麼

P4-H 已讓英文偏好寫入與中文偏好更正取得 deterministic plan 和自然日文 surface，但它留下了不能忽略的資料缺口：新偏好沒有完整進入
typed profile。P4-I 沒有重跑或調整那兩個舊案例，而是把 P4-H 已選中的明示第一人稱「目前偏好」投影成 scope-aware typed state。

每一筆狀態保存來源語言、輸入 hash、行為種類、scope、分類 cue、時間與 epistemic status。相同 scope 的新正向值使用既有
single-cardinality validity resolver，讓舊正向值成為歷史而不是刪除；只有使用者明確否定舊值時，才另寫一筆 active dislike。這個 typed
state 仍是 observation-only，`answer_use_authorized=false`，沒有偷偷塞進回答 prompt。

## 事前凍結與實際執行

implementation commit `e5e6f74` 先完成並通過受影響回歸。接著 cross-restart contract、gate 和全新案例以 commit `49761fa` 在實際執行前
凍結。契約要求兩個不同程序、相同 mode-0700 隔離 root 與 memory DB、不同 PID 與 product session、兩輪各送一次、0 retry、0 planner
model call、每輪 20 秒內，且第二程序在送出更正前必須已看得到第一程序留下的 active typed record。

實際 root 是
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-uxhbq70y`，listener 是
`127.0.0.1:7861`。第一程序 PID `75313` 結束後確認 listener 消失；第二程序 PID `75432` 重用同一 root 與 DB，沒有手動注入記憶。
Safari 沿用既有 Uruha 分頁，沒有關閉觀察到的 50 個分頁。

## 兩個程序的真實結果

第一程序 English write：

> I prefer oolong tea. Please remember that as my current drink preference.

可見日文：

> ん、その好みは覚えとく。

產品寫入 active current preference `oolong tea`，scope `drink`，memory id
`48c580fb-2e4d-4a82-bed2-ec2fe0e17e7a`。Safari graph 同時顯示 P4-H 的 `select` node 與 P4-I 的 `memory` node；
episode id 是 `4611fe56-4416-4669-a7c8-6b3624f3f8fb`，使用者等待 `2.3411s`。

第二程序啟動時先只讀確認前述 id 仍是 active，再送出 Chinese correction：

> 更正：我現在不喜歡oolong tea了，現在比較喜歡barley tea。

可見日文：

> ん、訂正の内容はそのまま覚えとく。

產品從唯一 active 舊值繼承 scope `drink`，新建 active positive `barley tea`，memory id
`9aacdcae-fb3f-4115-908c-b2a3f5a12e39`；另建立 active negative `oolong tea`，memory id
`dacf1004-a2c1-446f-8fb8-0a1591ee663c`。舊 positive 沒有刪除或改寫，由同一 predicate 的 single-cardinality resolver 判為
`historical/newer_single_value`。第二個 episode id 是 `08f94170-1c2d-42ef-8567-36a2fe8ab9bb`，等待 `16.2815s`，仍在 20 秒契約內。

最終 DB 恰好有 3 筆 profile record、2 筆 episode；profile surface state 是 `likes=[barley tea]`、`dislikes=[oolong tea]`。兩輪各有
69 個 runtime node，0 retry／fallback／planner model call／paid API／external deployment／production memory／Function tool／VRM action。
frozen gate 重新計算為 `pass`，failed gates 0；24 項 P4-I result／gate／freeze／typed-state 測試全數通過。

## 這個 pass 能證明與不能證明的事

它能證明一個窄而真實的產品能力：程序重啟後，明示目前偏好沒有只剩聊天文字；相同 scope 的跨語更正能產生可追溯的新 current state，
保留舊 state 的歷史，並把明確否定分開記錄。使用者仍只看到自然日文回覆，研究者才在 graph／trace 看到 typed update。

它還不能證明系統會用 typed state 回答「我現在喜歡什麼？」。目前 profile shadow 明確維持
`answer_use_authorized=false`、`affects_working_memory=false`；P4-F 的 episode recall 也不能替代 typed-current-state recall。因此下一個必要項目
是 P4-J：只對明確第一人稱「目前偏好」查詢開放一條 read-only、scope-exact、active-only 的回答路徑；scope 不明或有多個 active 候選時要拒絕
猜測。這仍需另一份事前凍結與全新跨重啟案例，不能沿用本次案例直接宣稱通過。

## 結論邊界

P4-I 是 typed current-preference persistence／supersession 的 bounded cross-process pass。它不是 open-world multilingual understanding、長對話記憶
可靠度、felt understanding、人類偏好、相對強 LLM 優勢或「人類方程式」證據。
