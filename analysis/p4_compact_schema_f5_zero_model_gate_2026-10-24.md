# P4 f5 新題：零模型 go/no-go

狀態：**f5 full-route contract PASS，真 provider／Safari 尚未執行**。新題、gold、前瞻時序與十檔 source SHA 已以 `cecb10b` 先推 PR #435，未改 f3/f4 判定；十 SHA 核對 10/10。source-only M29 把新襯衫鈕扣句分類為 `brief_encouragement`，未聲稱私下心理。

隔離真 RightBrain＋假 LeftBrain 的完整輪次：M29 `brief_encouragement`、`projection_required=false`，M33 not applicable、M18 不接管、M21 full/compact completed、scene support、`direct_chat_answer`，最終回覆與唯一隔離 episode 一致；fake model 恰一呼叫，request `response_format=json_schema`、max_tokens 256、temperature 0.1。新 test SHA `65015457d503b1c8cad4ec0bca9fe5840d25504b93809306c4240977084d72c0`。新題及 f4 carrier 相鄰測試 **6/6 passed**（13.95 秒）；f4 較廣受影響 153/153 已先驗且產品碼未再改，不重跑無關大套件。`py_compile`／diff check 另核。

這只證路由與載體在假模型下可達；不能證真 `qwen2.5:7b` 遵 schema、自然日文品質、原生圖、記憶或成本。下一步按凍結計畫建 7932 新 root，先靜態核對再 Tpre→一次 Safari Send；前置時序 gate 不合不送，也不重試。
