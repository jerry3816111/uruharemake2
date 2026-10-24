# P3 成本記錄修正驗收

2026-09-09。判定：記錄接線與開發控制通過；P3 比較尚未執行，Safari pending。

## 改變與結果

原帳本只包含 OpenAI-compatible 生成。現在 `MemoryManager` 可選擇把 Chroma collection 操作接入
`ComputeLedger`；M31 native Ollama 成功／失敗也會記錄。未提供 ledger 時仍使用原 collection。
記錄保留 shape/hash、實際生成 token、耗時與錯誤類型；沒有把對話或例外訊息原文複製入 ledger。
產品 probe 增加逐 session／turn scope，舊 OpenAI-only 視圖保留。

| 證據 | 修改前 P2 run2 | P3 run2 |
|---|---:|---:|
| sessions／turns | 5／9 | 5／9 |
| OpenAI-compatible 生成 | 2 | 2 |
| 已記錄 Chroma 操作 | 未記錄 | 130 |
| query／add／update／get | 未記錄 | 90／9／26／5 |
| 預期需要 embedding 的操作 | 未記錄 | 99 |
| 逐輪／初始化事件 | 未區分 | 127／5 |
| 已記錄生成 token | 2,900 | 2,901 |
| 整體 wall seconds | 28.973048 | 30.834245 |
| 四項結構 checks | 4／4 | 4／4 |
| 可見輸入／回覆相同 | reference | 9／9 逐字相同 |

130 個記憶操作不等於 130 次 LLM 生成。`embedding_expected` 是依呼叫參數推得，不能稱為已測得的
embedding token／kernel 次數。帳本 operation latency 合計 25.907306 秒不是整體 wall time；兩次非隨機化
run 的時間差不能歸因為 instrumentation overhead。P3 尚無品質—成本優勢結論。

## 檢查證據

- 最終受影響組：121 passed／0 failed／8 dependency warnings，38.97 秒；JUnit：
  `analysis/p3_compute_accounting_final_tests_2026-09-09.xml`。
- 編譯與 `git diff --check` 通過。測試覆蓋 native transport 接線、provider 真實計數欄位、失敗記錄與重拋、
  query/add 的 embedding 判別、原文不洩漏、MemoryManager 接線及 P1/P2 相鄰行為。
- 本機 run2：`analysis/p3_complete_compute_accounting_local_run2_2026-09-09.json`；同名 HTML 是該次真實
  runtime 的既有 node graph。它是離線產物，不是 Safari screenshot，也不是 Web 操作驗收。
- run1 曾移至 `/tmp/uruha-p3-superseded.DcANAs`，本次收尾已恢復到 `analysis/`。保留兩次結果，run2 才是最終
  source 對應結果。前後均為開發控制，不是 holdout；沒有為追分重抽案例。

## 限制及下一步

本機九輪沒有觸發 native M31 路徑；該路徑目前是 mocked transport／契約證據。Chroma token、embedding/index
各自時間、Ollama daemon 的 CPU/RSS/energy 尚不可得。初始化 health check、collection creation 也不在 collection
operation 記錄中；`unscoped` 僅代表已被記錄的初始化事件，不能聲稱所有 setup 都已入帳。
RightBrain transformer 未載入，依既有 P2 runtime probe 設定；正式 DB、真人資料與 holdout 均未使用。
121 項是受影響子集，不能稱整個 repository 全綠。歷史 source freeze 仍指向其原 commit，不能以新工作樹
直接重算歷史正式結果。Safari 已知存取限制保持 pending。

下一步僅依 P3 前瞻規格建立比較 harness。需同時限制所有生成模型（M31 預設另用 qwen3.5:9b）、完整歷史、
共同資源上限、失敗處理與獨立評分。沒有這些檢查，不得因新的 ledger 較完整就宣稱同資源或更省成本。
