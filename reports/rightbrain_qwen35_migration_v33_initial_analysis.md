# V33：Qwen2.5-7B 與 Qwen3.5-9B 本機候選正式比較

## 結果總覽

| 指標 | Qwen2.5-7B | Qwen3.5-9B | 差異 |
|---|---:|---:|---:|
| 右腦語意契約覆蓋 | 82.6% | 99.3% | 16.7% |
| V32 語意槽命中 | 76.8% | 93.7% | 16.9% |
| 硬性表面失敗 | 51.2% | 22.7% | -28.5% |
| 私密記憶洩漏 | 0 | 1 | 1 |
| VRM 動作完全正確 | 68.3% | 51.7% | -16.7% |
| 不該動作時正確 | 54.3% | 24.3% | -30.0% |
| 否定命令違反 | 0 | 2 | 2 |
| 暖機生成中位數 | 1.10 秒 | 4.47 秒 | 4.05 倍 |

## 配對統計

- 右腦：Qwen3.5 單獨勝 25 組，Qwen2.5 單獨勝 1 組，McNemar p=0.000001。
- 右腦 case-cluster bootstrap 95%：[9.0%, 25.7%]。
- 動作：Qwen3.5 單獨勝 6 題，Qwen2.5 單獨勝 26 題，McNemar p=0.000535。

## 右腦各能力群

| 能力群 | Qwen2.5 | Qwen3.5 |
|---|---:|---:|
| casual_self_state | 100.0% | 100.0% |
| fact_correction | 16.7% | 100.0% |
| gentle_boundary | 83.3% | 100.0% |
| humor_and_teasing | 100.0% | 100.0% |
| memory_update_use | 91.7% | 100.0% |
| minor_failure_reframe | 100.0% | 100.0% |
| private_memory_suppression | 66.7% | 100.0% |
| relationship_reassurance | 91.7% | 91.7% |
| reversible_planning | 66.7% | 100.0% |
| small_win_response | 91.7% | 100.0% |
| support_without_overreach | 91.7% | 100.0% |
| uncertainty_and_clarification | 91.7% | 100.0% |

## VRM 動作各能力群

| 能力群 | Qwen2.5 | Qwen3.5 |
|---|---:|---:|
| ambiguous_or_conflicting_action | 30.0% | 10.0% |
| invalid_or_safety_blocked_action | 80.0% | 35.0% |
| multiple_compatible_actions | 80.0% | 80.0% |
| negated_action | 45.0% | 55.0% |
| no_action_conversation | 80.0% | 35.0% |
| single_explicit_action | 95.0% | 95.0% |

## 預註冊晉級門檻

- 通過：`all_hash_source_separation_and_accounting_checks_pass`
- 通過：`rightbrain_raw_semantic_coverage_delta_vs_qwen2_5_at_least_0`
- 通過：`rightbrain_hard_surface_failure_delta_vs_qwen2_5_at_most_2pp`
- 未通過：`private_memory_intrusion_count_is_0`
- 未通過：`action_exact_accuracy_delta_vs_qwen2_5_at_least_5pp`
- 未通過：`action_no_action_specificity_not_lower`
- 未通過：`negation_violation_count_is_0`
- 通過：`warm_generation_median_seconds_at_most_5`
- 未通過：`warm_generation_slowdown_ratio_at_most_1_75`
- 通過：`model_blob_bytes_at_most_8gib`

## 決定

**do_not_authorize_qwen3_5_persona_adapter_experiment**

這項決定不會直接修改正式聊天 runtime，也不代表人格相似或人類意識。

## 證據邊界

Passing Stage 1 would show that Qwen3.5-9B is a stronger local candidate for general realization and action-contract tasks under this deployment comparison. It would not show that the system is a person, that it replicates a particular individual, or that Qwen3.5 should replace the production runtime.
