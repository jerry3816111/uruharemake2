# P4-D-G zero-model result before fresh Safari

日期：2026-10-23。設計／兩個 source-disjoint 合成來源／13 種結構負控已先於程式以 `8c17b68` 推 PR #435。此報告只記錄**圖表投影與零模型證據**，不改 D0–D10 首批 strict FAIL。

## 原因與唯一改動

D 真產品舊 trace 的四個准入輪次已有 D terminal cert，然而 generic graph signal 選 inherited `intent=deterministic_semantic_commit_m32`，D row 只顯示 `36 fields`。`uruha_memory_observatory.py` 現僅在 result 的當輪 raw/reply、D 純函式重算來源 binding、logic/trace/blackboard cert、cycle、route、guard、history、utterance、selected-plan 與 terminal status 互相一致時，**只覆蓋 D row 與 selected-plan row 的 signal**；其餘 node/edge/detail/raw trace、回覆、DB、D gate、Web 程式保持原樣。可見訊號分別為「使用者本人決定／訂正｜來源與回覆核對」與「已選：當輪決定／訂正承接（D）」。這不是重新驗證 episode；Web observatory payload 可不帶 episode document，terminal status 是由 D 交付時產生。

## 證據

- `test_p4_current_decision_graph_authority_projection.py`：兩個新來源的正例可見圖與 HTML；凍結 13/13 負控均不提升 D 權限；另測低路由、布林 cycle、可見失敗／history／guard／頂層計畫矛盾；正例除了兩個 signal 外 node/edge/trace_id/detail/budget 均與基準相等，result 原件不變；其他 gate marker 的 graph 完全等價。這是零模型合成契約，不是 fresh generation 或盲 holdout。
- `.venv/product_checks/bin/python -m pytest -q` 對此測試與 D gate、M24 graph、P4 producer/atomic、browser hydration、Web final graph 六個相鄰檔：**178 passed**，9 個環境／依賴 warning。`py_compile`、`git diff --check` 通過；未新增模型呼叫。
- 額外 `test_p4_ab_source_proposition_graph_summary.py`：**3 passed、1 failed**。失敗是歷史測試第 117 行硬編 graph 檔 SHA `c95e...`，而本次實作前已凍結的 HEAD SHA 為 `c7168b30...`，故本次之前已不符合；不改舊測試／凍結追綠。此處不能宣稱完整 test suite 全綠。

## 限制與下一 gate

尚未在新隔離真模型／原生 Safari 觀察圖或 reload；現階段不稱產品 PASS。下一步在 product SHA 與 commit/push/PR exact head 核對後，用新 0700 root／官方 ONNX 私有複本，先 zero-turn ready/planned stop、T0 空資料，再用 frozen source `dg0`/`dg1` 各送一次、0 retry；核當輪與 reload 圖、bubble/raw/guard/episode、DB、延遲與成本。若未能保存原生 Safari PNG/AX 或完整 token ledger，需分列未達；D2 日文自然度、D5 衝突值、正式同模型比較／人評／temporal holdout／VRM/Function Calling 均仍未解。
