# V56 relation-bound event graph development result

This is a zero-model replay on consumed V54 evidence, not a fresh holdout.

| condition | commitment | exact calls | false actions |
|---|---:|---:|---:|
| frozen_v54_hybrid_control | 92.11% (70/76) | 93.75% (60/64) | 3 |
| frozen_rejected_v55_hybrid | 89.47% (68/76) | 84.38% (54/64) | 2 |
| v56_deterministic_relation_graph_only | 100.00% (76/76) | 96.88% (62/64) | 0 |
| v56_selective_relation_graph_with_frozen_v51_fallback | 100.00% (76/76) | 96.88% (62/64) | 0 |

- Coverage / resolved accuracy: `100.00%` / `100.00%`.
- Prespecified V54 fixed/correct: `6` / `6` of `6`.
- Rejected V55 regression cases correct: `7` of `7`.
- Commitment / call delta vs V54: `+6` / `+2`.
- Semantic / call regressions vs V54: `0` / `0`.
- Gate passed: `True`.
- Decision: `authorize_independent_v56_holdout_and_compiler_repair_design`.
- Interpretation: Typed event relations repaired the consumed V54 failures and all rejected V55 regressions without changing a correct V54 semantic target. This authorizes only a new independent holdout and separate compiler repair.
- No model call, paid API, runtime change, or physical VRM action was used.
