# V64 左腦意義契約實驗結果

**決策：** `freeze_negative_result_and_stop_structured_meaning_contract_hypothesis`

| 指標 | 精簡計畫 | 結構化意義契約 |
|---|---:|---:|
| 必要意思命中 | 12/28 (42.9%) | 11/28 (39.3%) |
| 整題完整 | 4/14 (28.6%) | 3/14 (21.4%) |
| 禁止意思違反 | 0/14 | 0/14 |
| JSON 解析 | 100.0% | 100.0% |
| 角色關係命中 | 不適用 | 3/14 (21.4%) |
| 記憶新舊判定 | 不適用 | 3/4 (75.0%) |

必要意思差異：-3.6%；95% bootstrap CI [-14.3%, +7.1%]。

## 未通過門檻

- `t1_response_commitment_recall`
- `t1_recall_delta_vs_c0`
- `t1_complete_case_rate`
- `t1_frame_relation_recall`
- `t1_memory_state_accuracy`
- `t1_latency_median`
- `t1_latency_p95`

這份結果只評估左腦內容規劃 schema，不代表右腦輸出、完整聊天或廣義人類相似度。
