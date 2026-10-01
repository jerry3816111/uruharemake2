# P3 complete product compute accounting plan

日期：2026-09-09
狀態：在 P3 baseline／新案例／成功門檻與任何比較生成之前凍結

## 問題與研究位置

P2 已凍結一個有限產品 system side，但最後 9 輪 run 的 ledger 只記錄 2 次 OpenAI-compatible chat completion。
實際產品每輪至少做四個 Chroma 文字查詢與一次 episode 文件寫入，另有一條以 native `urllib` 呼叫 Ollama 的
M31 語意驗證路徑。現有帳本因此不能支持「與強 LLM 同資源」或「品質相當但成本更低」。修改前證據固定於
`analysis/p3_prechange_compute_accounting_gap_2026-09-09.json`。

本單元只修正 **product compute observability**。不設計 P3 題目、不打開 holdout、不生成 baseline 或 system 回覆，
也不修改對話策略、記憶內容、人格、prompt、模型、閾值、日文表面或正式 M55–M57 授權。

## 單一變因

在既有 raw-text-free `ComputeLedger` 增加兩類可觀察資源記錄，並把它們接到實際產品入口：

1. native Ollama chat：記錄 stage、model、message shape/hash、options、實際 `prompt_eval_count`／`eval_count`、
   latency、response shape/hash 與 error type；不保存 prompt 或 reply。
2. Chroma collection operation：記錄 collection、operation、文字／ID／embedding 的 count、character count/hash、
   是否需要 collection embedding function、latency、result shape 與 error type；token 不可得時明確為 null，不能用字數冒充 token。

OpenAI-compatible 與 transformers 記錄保持相容。帳本 snapshot 另提供按 resource kind／backend／stage 的 raw-free summary，
並明確區分：生成 token、公用向量操作、整體 wall time。P3 後續比較必須呈現品質—成本 Pareto，不以相同 call count
為必要條件，也不得用未完整的 token ledger 宣稱資源相等。

## 測量邊界

- 初始化與 health check 若發生在 item scope 外，保留為 `unscoped` setup cost；逐輪比較另報 item-scoped cost。
- Chroma `query_texts`／`documents` 代表 embedding expected；caller 已提供 `query_embeddings`／`embeddings` 時不宣稱本地
  embedding 重新執行。
- Chroma timing 是 collection operation 的總時間，無法把 embedding 與 index I/O 精確拆開；報告必須保留此限制。
- process CPU、peak RSS、energy 尚未在本單元新增；後續 P3 harness 需以 process-level telemetry 補足。
- P2 frozen behavior commit 與既有結果不改；新 instrumentation 必須以回歸證明 reply／decision 不受影響。

## 預先成功條件

1. native success/failure 均只記錄 shape/hash，不洩漏 prompt、reply 或 exception message；成功時使用 Ollama 真實 token counts。
2. Chroma query/add/update/get 的操作與是否預期 embedding 可區分；文字、documents、IDs 不以 raw 形式進 snapshot。
3. 產品 `MemoryManager` 在提供 ledger 時使用 instrumentation；未提供 ledger 時完全維持原 collection object 與行為。
4. 隔離 collection contract 至少顯示 Chroma operation；本機產品 probe 顯示 generative 與 vector-memory 兩類成本，且不再宣稱
   只有 OpenAI-compatible accounting。
5. 既有 compute-ledger、產品 P1/P2、memory／persona／visible-Japanese 相鄰測試無新增退步。
6. 0 formal holdout access、0 額外正式模型比較、0 production memory writes、0 VRM/tool actions。

## 失敗與停止條件

- 若包裝 collection 改變 Chroma 行為、query 結果或寫入語意，停止並保留失敗，不以較少測試掩蓋。
- 若 Ollama response 缺 token counts，欄位保持 null 並標示 unavailable；禁止以 character count 推算成實際 token。
- 若無法在不保存 raw text 下識別 operation，寧可標記 unaccounted，不放寬隱私邊界。
- 本單元通過仍不代表 P3 公平比較、產品優勢、human preference 或人類反應方程式成立。

## 後續 P3 gate

完成此單元後，下一個單一工作才是凍結 P3 comparison contract：強 baseline 必須看到相同完整可見歷史、同一
`qwen2.5:7b`、相同 Uruha surface/output contract 與 generation budget；system 的差異只允許是顯式記憶／狀態／
預測—驗證—修正機制。現有 P2 五組仍是 developer controls，不得改名 holdout。
