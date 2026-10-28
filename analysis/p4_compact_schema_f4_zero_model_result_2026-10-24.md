# P4 f4 compact JSON Schema：零模型結果

狀態：**code/contract gate PASS；真模型與 Safari 尚未驗證**。f3 一次真 Safari 回覆品質 strict FAIL 及 compact candidate 缺一個必填欄保留，不改 f3 題、gold 或評判。本項 source-only 計畫／新味噌湯題先以 `bcb7b50` 凍結推至 PR #435；事前十檔 SHA 中兩個刻意修改的產品檔已核 `bcb7b50` Git blob SHA 一致，計畫和題本當前 SHA 亦一致。

唯一產品變因是隔離 product `start --compact-json-schema` 子程序的 compact `response_format`：由原 `json_object` 改成明列三個候選、必填欄、既有 enum、長度與禁額外欄的 JSON Schema。無 flag 的舊 carrier、prompt、模型、生成參數、strict parser、無補欄／無重試、M29/M39、記憶和 Web 均未修改。這是提高格式可靠度的前瞻試驗，不是把已失敗 f3 改判。

新契約修改前紅燈 **2 failed／2 passed**；修改後 f4 schema/控制器/嚴格拒缺欄 **4/4**，真 RightBrain＋假 LeftBrain 的完整 f4 輪次 **1/1**：M29 `brief_encouragement`、M33 not applicable、M21 full/compact completed、support、`direct_chat_answer`、最終回覆等於單筆隔離 episode，假模型只呼叫一次且 request 有 JSON Schema、max_tokens 256、temperature 0.1。新測與相鄰六檔 **37/37 passed**；擴大十四檔受影響回歸 **153/153 passed、9 既有 warnings**（68.16 秒）。`py_compile`、`git diff --check` 均過；產品／測試四 SHA 見 `research/p4_compact_schema_f4_product_2026-10-24.sha256`。獨立只讀 diff 審查無阻擋項，指出實際 detached child 環境與本機模型遵守 schema 尚待真啟動驗證。

本批真 provider calls=0、Safari Send=0、正式 DB writes=0，沒有新的自然日文品質或 node graph 結論。f3/f4 的輸入不同，即使 f4 成功也只能證新題的 schema-arm 可行，**不能單憑兩次結果推斷 carrier 的同題因果效應**。下一步按凍結計畫以 7931／全新私有 root 同 PID zero-turn 與 T0/Tpre admission gate 啟動 f4，原生 Safari 只送一次，依 gold 和成本／graph 硬 gate 如實判 PASS/FAIL；失敗也不重送。
