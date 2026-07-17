# Reflection Classifier V1 External Holdout

Status: **FAIL**

| Condition | Correct | Accuracy |
|---|---:|---:|
| Frozen legacy | 20/32 | 62.50% |
| Structural candidate | 20/32 | 62.50% |

- Accuracy delta: +0.00%
- Newly correct: 0
- Regressions: 0
- Critical false positives: 0

## Class results

| Class | Legacy | Candidate |
|---|---:|---:|
| semantic | 5/8 | 5/8 |
| procedural | 2/8 | 2/8 |
| interpretive | 5/8 | 5/8 |
| none | 8/8 | 8/8 |

## Frozen gates

- candidate_correct_count_min: FAIL
- candidate_overall_accuracy_min: FAIL
- candidate_semantic_correct_min: FAIL
- candidate_procedural_correct_min: FAIL
- candidate_interpretive_correct_min: FAIL
- candidate_none_correct: PASS
- critical_false_positive_count_max: PASS
- regression_vs_legacy_count_max: PASS
- newly_correct_vs_legacy_count_min: FAIL

## Decision

reject_runtime_advancement_keep_reflection_disabled_and_freeze_failures_as_future_development_evidence

This result measures only source-separated reflection-entry classification. It does not measure extraction quality, memory usefulness, downstream behavioral change, or broad human likeness.
