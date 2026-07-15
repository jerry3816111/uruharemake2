# V56 fresh holdout result

External exact and controlled compositional results are reported separately.

| condition | commitment | exact calls | false actions |
|---|---:|---:|---:|
| fresh_v51_model_control | 80.25% (65/81) | 79.69% (51/64) | 7 |
| v54_selective_state_with_shared_fresh_v51_fallback | 90.12% (73/81) | 82.81% (53/64) | 7 |
| v56_deterministic_relation_graph_only | 97.53% (79/81) | 93.75% (60/64) | 1 |
| v56_relation_graph_with_shared_fresh_v51_fallback | 98.77% (80/81) | 93.75% (60/64) | 1 |

- External exact V56 commitment: `100.00%`.
- Controlled compositional V56 commitment: `97.73%`.
- V56 coverage / resolved accuracy: `98.77%` / `98.75%`.
- Semantic fixes / regressions vs V54: `7` / `0`.
- State / matched / end-to-end gates: `True` / `True` / `False`.
- Decision: `freeze_v56_state_preregister_compiler_repair`.
- No runtime, shadow, or physical VRM execution is authorized by this report.
