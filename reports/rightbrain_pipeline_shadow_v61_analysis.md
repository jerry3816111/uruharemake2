# V61 matched RightBrain pipeline shadow

All three conditions reused one captured LeftBrain plan per case. No production memory or VRM action was used.

| Metric | Current deterministic | Qwen2.5 7B | Qwen3.5 9B |
|---|---:|---:|---:|
| Raw plan-semantic pass | n/a | 10.0% | 10.0% |
| Raw surface-gate pass | n/a | 80.0% | 96.7% |
| Raw holdout meaning recall | n/a | 33.8% | 46.2% |
| Final plan-semantic pass | 13.3% | 13.3% | 13.3% |
| Model takeover | n/a | 26.7% | 33.3% |
| Final duplicate rate | 3.3% | 3.3% | 3.3% |
| Median model latency | n/a | 2.098s | 3.240s |
| P95 model latency | n/a | 2.598s | 4.497s |

- Automatic gate: FAIL
- Decision: `freeze_negative_result_and_stop_v61_hypothesis`
- Failed checks: t1_raw_semantic_contract_pass_rate_at_least, t1_raw_meaning_proposition_recall_at_least, t1_raw_forbidden_proposition_violation_rate_at_most, t1_model_takeover_rate_at_least, t1_final_semantic_contract_pass_rate_at_least, t1_final_surface_gate_pass_rate_at_least, t1_final_self_monitor_pass_rate_at_least, t1_raw_semantic_delta_vs_c1_at_least

This result estimates only RightBrain realization after one shared cognitive-plan capture. It does not establish whole-system human likeness.
