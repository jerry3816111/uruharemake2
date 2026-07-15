# V54 independent holdout result

The dataset and gates were frozen before any model inference.

| condition | commitment | exact calls | false actions |
|---|---:|---:|---:|
| fresh_v51_model_control | 78.95% (60/76) | 87.50% (56/64) | 4 |
| v54_deterministic_state_machine_only | 81.58% (62/76) | 89.06% (57/64) | 2 |
| v54_selective_state_machine_with_fresh_v51_fallback | 92.11% (70/76) | 93.75% (60/64) | 3 |

- Deterministic coverage / resolved accuracy: `86.84%` / `93.94%`.
- Fallback targets / accuracy: `10` / `80.00%`.
- Commitment / exact-call delta vs fresh V51: `+10` / `+4`.
- Semantic / call regressions: `1` / `1`.
- Resolved-state / fallback-model / compiler-only failures: `4` / `2` / `1`.
- State / matched / end-to-end gates: `False` / `False` / `False`.
- Decision: `preregister_local_model_size_comparison_on_frozen_abstentions`.
- Interpretation: Errors concentrate in cases where the state machine abstains. Compare smaller and larger free local models only on this frozen unresolved subset; do not change rules or examples first.
- No paid API, runtime change, shadow actuation, or physical VRM action was used.
