# P4-L cross-language scope delivery acceptance

## 結論

P4-L 的事前凍結 product gate=`pass`，failed gates=`0`。這次使用全新隔離 runtime、兩個不同 product process，以及兩個各只執行一次的 Safari 輪次，驗證繁中明示 scope `飲料` 會被投影成 canonical `drink`，同時保留 alias provenance；真正重啟後，英文 exact-scope query 能使用同一筆 typed record，交付事前固定的自然日文與正確 node graph。

這是 bounded scope-alignment delivery pass。`麦茶` 與較早 P4-I 的 barley-tea 案例有語意重疊，freeze 已在執行前揭露；因此結果不是 novel value semantics，也不證明任意語言 ontology alignment、一般記憶、長對話可靠、felt understanding、優於強 LLM 或人類方程式。

## 真實執行

第一個 product process 在 `127.0.0.1:7864` 使用全新 mode-0700 isolated root。Safari 實際輸入：

> 我喜歡麦茶，請記住這是我現在的飲料偏好。

可見回覆：

> ん、その好みは覚えとく。

P4-H act=`write`；P4-I 寫入 `value=麦茶`；P4-L 將明示繁中 `飲料` 投影成 `scope=drink`，alias id=`drink:zh-Hant:v1`，source alias SHA-256=`7a4d3d287250d8c18c204cca7c8f8c73e074f96555a2d3936402258636fece4d`。active memory id=`c62640d7-ab6a-4edc-8f42-d44f8fd4fa01`。Safari graph 同時顯示 `multilingual_current_preference_p4` 與 `preference_scope_canonicalization_p4` memory nodes。等待 `2.2757s`，planner model call=`0`。

PID `89827` 退出、launcher exit code=`241`，且 listener 確認關閉後，第二個 product process 以同一 runtime root／memory DB 啟動，PID=`90082`、新 session=`20260921_162820_35be9fa3`。在 recall turn 或外部注入前，DB 已有第一程序的同一 active id、canonical scope 與 alias provenance。Safari 再輸入一次凍結問題：

> What is my current drink preference?

可見回覆：

> 今の飲み物の好みは麦茶。前のじゃなくて、今の方ね。

P4-J status=`resolved_unique_active_typed_current_preference`，回答綁定同一 active id，final surface 與事前契約逐字相同。Safari 下方 graph 實際出現 `typed_current_preference_recall_p4` 的 `select` node。等待 `2.2885s`，planner model call=`0`。

## 持久化與非變更證據

- profile count：recall 前 `1`，後 `1`。
- active typed current count：前 `1`，後 `1`；historical count=`0`。
- typed record content hash：前後皆 `a3556037169d72487a98868095039ad98133b354d2e214e0a185503e5db2f1fd`。
- canonical `drink`、`drink:zh-Hant:v1` 與 source alias hash 在重啟後仍存在。
- episode count：`1 -> 2`，兩輪各一筆、episode id 不同。
- recall 的 profile writes=`0`、P4-L canonicalization count=`0`、historical/negative/episode answer use 均=`0`。
- 兩程序、一次真正重啟、兩輪、retry=`0`、fallback=`0`、planner model calls=`0`。
- production memory、paid API、external deployment、Function tool、VRM action 都是 `0`。
- 沿用同一個現存 Uruha Safari tab；觀察到 `51` 個 tab，關閉使用者 tab=`0`。

## P4-L 真正補上的缺口

P4-K 的成功條件是 write 與 query 剛好都使用 canonical `drink`。P4-L 之前，繁中 `飲料`、簡中 `饮料`、日文 `飲み物` 會形成不同 predicate，P4-J 雖然知道 query 是 `drink`，仍因 exact-scope join 找不到紀錄。P4-L 沒有用飲品 value 猜 scope，也沒有放寬 P4-J 的 answer authority；它只對三個事前凍結、language＋surface 都精確相符的明示別名做投影，並留下來源雜湊。這次 pass 表示該單一變因已穿過真實 Web write、持久 DB、process restart、recall、visible Japanese 與 graph。

## 下一個必要缺口

現在只證明「跨語寫入後能回想」。尚未證明同一 canonical scope 在跨語更正時會讓新值成為唯一 active、舊值降為 historical，且重啟後不會把舊值說成現在值。下一步 P4-M 應只處理／驗證 cross-language canonical-scope correction supersession：固定一個 source write、一個另一語言 correction、一個重啟後 answer-absent query，核對 active/historical lineage、alias provenance、日文 surface 與 graph。不得改 value extraction、query authority、baseline、公開 claim，亦不得重跑 P4-L 的 `麦茶` 案例追分。
