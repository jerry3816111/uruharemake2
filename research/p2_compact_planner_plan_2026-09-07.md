# P2 第二批：有限的一般規劃輸出

實作前固定。第一批無根據澄清已被撤回，但本機 fallback 仍讓對話失敗。
診斷：1,828 prompt tokens；一般 planner 要三份重複的大 JSON，45 秒產生逾 1,000 tokens 仍未完結。
因此不再重試相同請求。只縮小產品的一般 planner 輸出契約，保留原模型、輸入、記憶／人格規則及三候選。

- 三候選只傳 `scene`、`core_message_jp`、`response_mode`，共同欄位由既有 normalization 處理。
- 保留原 system prompt 的 Memory／Hard rules；只替換 Output JSON schema 區域，不讀取測試答案。
- JSON 必須恰有三個不同的有效候選；截斷、缺欄、錯型別明確失敗，不能用假候選補齊。
- actual request/response 先過原 compute ledger，轉換回既有 bundle 僅發生在 adapter；不偽造 usage。
- 產品專屬 20 秒上限、256 output tokens，0 retries；20 秒亦含冷啟動，不保證所有電腦達標。
  這是新的產品資源契約，**不是與原 8 秒版本同預算的公平研究比較**；凍結研究入口仍原樣。
- 確切驗證：compact request／解析／超界／非一般路徑／成本帳本 tests，P1/P2 鄰接回歸，隔離本機兩輪。
  若通過才跑六輪；若再次逾時或答非所問，保留失敗，停止本 P2 的追加 patch，回到架構取捨。
- 通過只代表模型生成路徑可運作；第一批控制發現的錯題澄清、撤回與記憶問題不因此自動通過。

允許新增 `uruha_compact_planner_p2.py`、其測試及修改產品入口／探測器，結果置於 `analysis/p2_*`。
不改 frozen 模組／正式 holdout／原始 dirty checkout，不外部部署、不改 Ollama 設定。
