# P4-J 跨程序 typed-current-preference 回溯驗收

日期：2026-09-21  
正式 gate：`fail`  
證據範圍：一個事前凍結、不得重跑的跨程序產品案例

## 結論先講

P4-J 沒有通過。系統確實在重啟後找回第一程序寫入的 active typed record，也在 plan 中形成正確答案：

> 今の飲み物の好みはルイボスティー。前のじゃなくて、今の方ね。

但 Safari 最終顯示的是：

> 前に: 2026-09-21 13:15:5って言ってたろ。そこは忘れてない。

而且 graph 沒有出現 `typed_current_preference_recall_p4` 節點。因此這不是「記憶沒有保存」或「查錯 active id」，而是 P4-J
已得到正確 typed-state plan 後，contract 沒有進入最終 logic／surface／graph；既有 episode-based surface 仍覆寫了答案。

## 事前凍結與真實執行

implementation commit `5900eef` 完成後，cross-restart contract、gate 與新案例由 commit `4027277` 在任何 P4-J 真實產品輪次前凍結。
契約要求兩個不同程序、相同 mode-0700 隔離 runtime root 與 memory DB、兩輪各一次、0 retry、0 planner model call、每輪 20 秒內，
並要求第二程序送出問題前已能只讀看到第一程序的 active typed memory id。

實際 listener 是 `127.0.0.1:7862`。第一程序 PID `85345` 與 session `20260921_131430_6aa046c2` 結束後，
第二程序 PID `85435` 與 session `20260921_131653_9731c1c6` 重用同一個 runtime root 和 DB。沒有手動注入記憶、沒有外部部署、
沒有正式記憶存取，也沒有關閉 Safari 分頁。

## 第一程序：寫入成功

輸入：

> I prefer rooibos tea. Please remember that as my current drink preference.

可見輸出：

> ん、その好みは覚えとく。

這一輪通過既有 P4-H/P4-I：profile 新增唯一 active `drink=rooibos tea`，memory id
`b1ae941d-5120-47c2-81fb-77194545ce78`；episode id 是 `c1c1bdc4-cf26-4c83-a76d-f029b9748723`；
Safari graph 有 P4-H select 與 P4-I memory node。等待 `2.3621s`，0 planner model call。

## 第二程序：回溯失敗但因果位置明確

第二程序啟動、且在使用者輸入前，只讀確認同一 active id 仍存在。輸入不含答案：

> 我現在的飲料偏好是什麼？

P4-J 的 rule plan 使用相同 active id，intent 是 `typed_current_preference_recall`，planner path 是
`typed_current_preference_recall_authority_p4`，正確 core message 明確包含 `ルイボスティー`。這表示 typed-state 讀取、scope join 與日文化值都已成功。

然而 final logic 沒有保存 P4-J contract；`visible_language_guard` 接到的仍是 episode-derived 回覆，最後把時間字串局部日文化後交給 UI。
Safari 與 JSONL 都顯示相同錯誤 surface，且 69 個 runtime nodes 中沒有 P4-J select node。第二輪 episode id 是
`bf10a96f-d8bc-4e25-8db6-1eafac85697c`，等待 `2.4421s`，仍然 0 planner model call。

## 記憶與資源核對

回溯前後 profile 都恰好 1 筆，active id 不變；profile 內容 hash 前後皆為
`b00854b804605590cf09154fc203b224115a2889d49169b792eb209aeb8608de`。episode 由 1 筆增加為 2 筆，符合一次真實對話的正常 writeback。
所以失敗沒有污染或改寫 typed state。

總計 2 次程序啟動、1 次重啟、2 個真實產品輪次、0 retry、0 fallback、0 planner model call、0 paid API、0 external deployment、
0 production-memory access、0 Function tool、0 VRM action。兩輪合計使用者等待 `4.8042s`。

## 這個 fail 改變下一步什麼

不能再把 P4-J 稱為產品可用的 typed-current-preference recall。下一個獨立工作項 P4-K 只修一個已定位的 seam：把 query 階段存在於
`memory_data` 的 P4-J contract，安全地傳給最後 visible guard、logic 與 graph；safety route 仍不得被覆寫，其他 query 仍完整委派舊路徑。
修正必須新增一個模擬「planner normalization 丟掉自訂 plan field」的回歸測試，避免原本只測理想 logic payload 的假綠燈。

P4-K 不得重跑本次 rooibos 案例，也不能更改本次 freeze、預期答案或 gate。完成與回歸通過後，才可另外凍結一個從未執行的新值與新語言案例。

## 證據邊界

本次能證明的是一個具體負結果：跨程序 typed state 可被正確讀進 plan，但目前尚未被可靠地交付到最終 surface 與 node graph。它不能證明
conversational recall、長對話可靠度、felt understanding、相對強 LLM 優勢或人類方程式；也不能用正確的中間 plan 取代使用者真正看到的失敗輸出。
