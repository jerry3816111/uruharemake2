# Reflection Hybrid Classifier V2 Development Pilot

| Model | Correct | Accuracy | Newly correct | Regressions | Median fallback | Gates |
|---|---:|---:|---:|---:|---:|---:|
| qwen3.5:0.8b | 20/32 | 62.50% | 0 | 0 | 0.468s | FAIL |
| qwen3.5:2b | 20/32 | 62.50% | 0 | 0 | 1.080s | FAIL |
| qwen3.5:4b | 20/32 | 62.50% | 0 | 0 | 1.113s | FAIL |
| qwen3.5:9b | 20/32 | 62.50% | 0 | 0 | 1.749s | FAIL |

- Rules-only control: 20/32 (62.50%)
- Selected smallest passing model: **none**
- Decision: `reject_local_semantic_fallback_and_reconsider_classifier_architecture`

This is a development capacity pilot on a retired failed holdout. It cannot establish generalization or authorize runtime reflection writes.
