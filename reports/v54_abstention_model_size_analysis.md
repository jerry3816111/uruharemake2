# V54 abstention model-size diagnostic

This is a diagnostic on 10 consumed V54 abstentions, not an independent model benchmark, right-brain evaluation, or full-system result.

| model condition | correct | requested false positives | median / p95 | gate |
|---|---:|---:|---:|---:|
| qwen35_0_8b | 5/10 (50.0%) | 0 | 0.71s / 2.66s | False |
| qwen35_2b | 6/10 (60.0%) | 4 | 1.09s / 4.15s | False |
| qwen35_4b_frozen_control | 8/10 (80.0%) | 1 | 2.27s / 2.64s | control |
| qwen35_9b | 6/10 (60.0%) | 4 | 3.58s / 10.93s | False |

- Selected candidate: `None`.
- Decision: `reject_model_size_substitution_for_v54_fallback`.
- Interpretation: No alternative model met the locked accuracy, false-request, fix, and zero-regression boundary. Keep model size out of the next architecture change.
- Even a perfect fallback leaves four structural V54 errors; full-set ceiling: `72/76 (94.74%)`.
- No paid API, runtime replacement, shadow actuation, or physical VRM action was used.
