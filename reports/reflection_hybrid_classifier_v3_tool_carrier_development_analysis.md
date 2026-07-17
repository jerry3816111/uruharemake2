# Reflection Hybrid Classifier V3 Tool-Carrier Development Pilot

| Model | Correct | Accuracy | Newly correct | Regressions | Tool parse | Median fallback | Gates |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3.5:0.8b | 18/32 | 56.25% | 2 | 4 | 85.00% | 0.763s | FAIL |
| qwen3.5:2b | 24/32 | 75.00% | 7 | 3 | 100.00% | 1.264s | FAIL |
| qwen3.5:4b | 29/32 | 90.62% | 9 | 0 | 100.00% | 2.386s | PASS |

- Rules-only control: 20/32 (62.50%)
- Selected smallest passing model: **qwen3.5:4b**
- Decision: `authorize_fresh_source_separated_holdout_preregistration_only`
- Parse errors: `{'missing_tool_calls': 3}`

This is a development output-carrier pilot on retired data. It cannot establish generalization or authorize runtime reflection writes.
