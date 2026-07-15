# V55 mention-bound discourse operators development result

This is a zero-model replay on consumed V54 evidence, not a fresh holdout.

| condition | commitment | exact calls | false actions |
|---|---:|---:|---:|
| frozen_v54_hybrid_control | 92.11% (70/76) | 93.75% (60/64) | 3 |
| v55_deterministic_operator_only | 89.47% (68/76) | 84.38% (54/64) | 2 |
| v55_selective_operator_with_frozen_v51_fallback | 89.47% (68/76) | 84.38% (54/64) | 2 |

- Coverage / resolved accuracy: `100.00%` / `89.47%`.
- Targeted fixed/correct: `5` / `5` of `6`.
- Commitment / call delta: `-2` / `-6`.
- Semantic / call regressions: `7` / `7`.
- Gate passed: `False`.
- Decision: `reject_v55_due_to_semantic_regression`.
- Interpretation: The structural operators fixed known cases but changed previously correct semantics. Reject V55 and redesign operator binding under a new preregistration.
- No model call, paid API, runtime change, or physical VRM action was used.
