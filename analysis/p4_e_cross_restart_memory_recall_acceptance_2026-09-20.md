# P4-E 隔離產品跨 process 重啟記憶回溯驗收

日期：2026-09-20
結論：`pass`

## 這一步真正驗證什麼

P4-B 以前只證明隔離產品能啟動與聊天，沒有證明「關掉程式再開」後還找得到先前經驗。P4-E 把唯一案例、兩輪原句、答案、
owner 錯置反例、PID／session／memory ID 證據與 0-retry 規則先 commit，才執行真實 Safari 輪次。

第一個全新隔離 process 收到：

> My colleague Rina likes black coffee, but I prefer herbal tea. Please remember who likes which drink.

Safari 顯示自然日文 `記憶に残すよ`。這輪走正常 full planner、1 次本機模型呼叫，寫入一個 episodic turn；端到端
`11.7658s`。然後 child PID `62778` 被真正停止，確認 process 已退出且 `7860` port 已釋放。

## 重啟不是換一個空資料夾

第二次啟動使用同一個 launcher manifest、同一 runtime root 與同一 memory DB，但 product PID 變成 `62949`、session 從
`20260920_220019_fd41d761` 變成 `20260920_220242_5dcd5b90`。因此不是同一個 Python process，也不是只在前端保留聊天內容。
重啟之間沒有 memory seed、手動 DB 修改或 server-side injection。

新 Safari page 的 chat 是空的；同時 Local VRM Stage 回到 `waiting_for_local_vrm` 與
`NEUTRAL STAGE · NOT URUHA`。這也是一個重要邊界：文字記憶可由 server 持久化，但使用者前一個分頁選的 VRM 檔仍只是 browser-local，
server 沒有偷偷保存模型檔。

## 不含答案的第二題與實際回答

第二個 session 只問：

> What kind of tea did I say I prefer?

這句沒有 `herbal`。Safari 實際回覆：

> あんたが好みって言ってたのはハーブティー。

系統沒有把 Rina 的 black coffee 錯算給使用者。trace 顯示：

- contract=`resolved_unique_user_preference`
- selected speaker=`user`
- candidate=`1`
- graph node=`speaker_qualified_fact_p3`
- persisted trace=`stored:episode:b992ec7e-cea9-4dca-81eb-e0760050b140`
- retrieved source timestamp=`22:01:43`，早於新 process `22:02:40`
- deterministic rule plan，general planner model call=`0`
- 端到端=`2.2708s`

同一 memory ID 同時存在於 retrieved candidate、selected working memory 與 passed-to-leftbrain trace。frozen gate 重新計算為
`pass`、failed gates=`[]`；不是只看一句回答字面相同。

## 成本、限制與下一步

整個 P4-E 為 2 個 product processes、2 個真實 Safari turns、1 次本機 planner model call、0 retry、0 Function tool、0 VRM action、
0 paid API、0 external deployment、0 production memory access；兩輪使用者等待合計 `14.0366s`。server 留在
`127.0.0.1:7860`，使用者可直接查看第二輪與圖。

這只證明既有 bounded preference recall 在一次真正產品重啟後成立，不是新的研究 holdout，也不是 open-domain、人類式自傳記憶或
長對話可靠性證明。下一個必要缺口是「更正／撤銷」：如果使用者後來明確改掉同一類偏好，重啟後系統必須回覆最新已確認值並保留舊值
為歷史，而不是把兩個值都當現在、任選一個或永久回答 ambiguous。
