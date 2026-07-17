# Consolidation Admission Cascade V1

| Condition | Correct | W / P / N | False / missed | Median | Warm p95 |
|---|---:|---:|---:|---:|---:|
| Direct Qwen3.5 9B | 10/12 (83.33%) | 2 / 4 / 4 | 0 / 2 | 5.713s | 5.959s |
| Conditional 4B to 9B | 9/12 (75.00%) | 1 / 4 / 4 | 0 / 3 | 6.983s | 8.498s |

## Conditional computation

- Stage 1 writes: 6/12
- Stage 2 calls: 6/12
- Newly correct / regressions / net: 0 / 1 / -1
- Total model calls: 30
- All preregistered gates pass: False
- Decision: `fail_stop_qwen35_4b_to_9b_cascade`

This is a Codex-labeled development pilot on one frozen memory-admission contract. It does not test runtime memory writes, retrieval, dialogue quality, or broad human likeness.
