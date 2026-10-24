# P4-Q 更正生命週期 protocol 修正版：offline pass

## 可操作結果

P4-Q 依事前 freeze 執行唯一一次、零重試的兩 process Persistent Chroma 診斷，gate 為 **pass / 0 failed**。

實際序列：

1. 中文寫入：`我喜歡洛神花茶，請記住這是我現在的飲料偏好。`
2. 日文更正：`訂正。もう洛神花茶は好みじゃない。今ははと麦茶が好き。今の飲み物の好みとして覚えといて。`
3. 真正結束 process 1，process 2 以相同 Persistent Chroma DB 啟動。
4. 英文、不含答案提問：`What is my current drink preference?`
5. 回傳：`今の飲み物の好みははと麦茶。前のじゃなくて、今の方ね。`

## 這次真正證明的機制

- 中文與日文 scope aliases 都投影到同一個 canonical `drink` predicate；
- 新值 `はと麦茶` 是唯一 active positive；
- 舊值 `洛神花茶` 沒被刪除，而是唯一 historical positive；
- 另有一筆 linked explicit negative，指向新 active record；
- process PID `14814 → 14815`，session ID 不同，同一 DB；
- 三筆 record IDs 與 canonical hashes 在重啟前、重啟後、recall 後完全相同；
- recall 只使用新 active ID，historical/negative answer-use 都是 0；
- surface strategy=`bounded_japanese_identity`，0 retry/model/fallback/paid API/production memory。

## P4-P → P4-Q 的因果判讀

兩者共用完全相同的 write/recall phase functions，產品碼沒有改。唯一預定差異是把 P4-P 的未來 `valid_from`
改成已經過去的時間。P4-P 得到 `no_active`，P4-Q 正確取得 active 並逐字回覆，因此可以把 P4-P 的失敗歸因到
測試 protocol 時間錯誤，而不是跨 process 記憶遺失。

## 尚未達成

這仍是 offline mechanism evidence；尚未證明三個真實 Web/Safari turn、runtime node graph 的逐輪 lineage，
也不能外推任意多語更正、長對話、被理解感、優於 LLM 或人類方程式。下一步 P4-Q-REAL 使用全新值與新隔離 DB，
事前凍結後跑 Safari 三輪／兩 process，不需要產品實作。
