# V65 本機左腦模型篩選結果

**決策：** `freeze_negative_result_and_stop_one_call_model_replacement`

| 模型 | 完整計畫 | 欄位正確 | 工具解析 | 中位延遲 | P95 | 峰值 RSS |
|---|---:|---:|---:|---:|---:|---:|
| Qwen2.5 7B | 0/12 (0.0%) | 52/96 (54.2%) | 0/12 | 4.30s | 4.87s | 4.80 GiB |
| Qwen3.5 4B | 2/12 (16.7%) | 78/96 (81.2%) | 12/12 | 6.30s | 6.70s | 4.95 GiB |
| Qwen3.5 9B | 2/12 (16.7%) | 75/96 (78.1%) | 12/12 | 10.91s | 12.41s | 6.48 GiB |

## 候選門檻

- **Qwen3.5 4B**：新增答對 2 題、退步 0 題；未通過。
  - 未通過：exact_case_count, exact_case_accuracy, exact_field_accuracy, selected_evidence, memory_policy, epistemic_control, safety_boundary, nonliteral_pragmatics, median_latency
- **Qwen3.5 9B**：新增答對 2 題、退步 0 題；未通過。
  - 未通過：exact_case_count, exact_case_accuracy, exact_field_accuracy, selected_evidence, memory_policy, actor_binding, epistemic_control, safety_boundary, nonliteral_pragmatics, median_latency, p95_latency

這是精確 function-call 計畫選擇測試，不代表完整聊天、右腦自然度或廣義人類相似度。
