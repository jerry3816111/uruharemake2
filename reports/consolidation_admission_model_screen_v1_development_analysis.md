# Consolidation Admission Model Screen V1

| Model | Correct | W / P / N | Frame | Evidence | Parse / index | False / missed | Median / warm p95 | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 7B control | 6/12 (50.00%) | 2 / 1 / 3 | 3/12 | 7/12 | 9/12 / 8/12 | 1 / 5 | 2.482s / 2.577s | - |
| Qwen3.5 4B | 8/12 (66.67%) | 1 / 4 / 3 | 8/12 | 9/12 | 12/12 / 12/12 | 1 / 0 | 3.644s / 3.804s | False |
| Qwen3.5 9B | 10/12 (83.33%) | 3 / 4 / 3 | 10/12 | 11/12 | 12/12 / 12/12 | 1 / 1 | 5.896s / 5.993s | False |

## Paired changes versus Qwen2.5 7B

| Candidate | Newly correct | Regressions | Net gain |
|---|---:|---:|---:|
| Qwen3.5 4B | 4 | 2 | +2 |
| Qwen3.5 9B | 5 | 1 | +4 |

- Exact model calls: 36
- Exact transport attempts: 36
- Selected condition: `None`
- Decision: `reject_model_replacement_and_proceed_to_two_stage_architecture`

This is a Codex-labeled development model screen on one frozen memory-admission contract. It is not an official benchmark, runtime-memory test, or evidence of broad human-like memory.
