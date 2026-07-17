# Reflection Hybrid Classifier V4 Independent Holdout

| Condition | Correct | Accuracy |
|---|---:|---:|
| Frozen rules control | 18/32 | 56.25% |
| Rules + frozen qwen3.5:4b tool fallback | 24/32 | 75.00% |

| Candidate class | Correct | Accuracy |
|---|---:|---:|
| semantic | 8/8 | 100.00% |
| procedural | 5/8 | 62.50% |
| interpretive | 3/8 | 37.50% |
| none | 8/8 | 100.00% |

- Delta: +18.75%
- Newly correct: 6
- Regressions: 0
- Critical false positives: 0
- Tool parse success: 100.00%
- Median fallback latency: 2.388s
- Warm p95 fallback latency: 2.557s
- All frozen gates: **FAIL**
- Decision: `freeze_the_negative_result_keep_runtime_typed_reflection_disabled_and_do_not_retest_this_holdout`

This is an ID-disjoint, same-corpus engineering holdout. Tatoeba provides source text, not reflection labels. It does not authorize memory writes or broad human-likeness claims.
