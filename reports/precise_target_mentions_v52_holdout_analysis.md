# V52 frozen fresh-holdout result

This is project-fresh evidence with an external exact-text subset. It cannot prove that the base model never encountered Tatoeba during pretraining.

| subset | condition | commitment | call exact | false actions | no-action specificity |
|---|---|---:|---:|---:|---:|
| all | v51_event_map_control | 78.82% (67/85) | 87.50% (56/64) | 2 | 93.94% |
| all | precise_target_mentions_candidate | 77.65% (66/85) | 84.38% (54/64) | 3 | 90.91% |
| external_exact | v51_event_map_control | 84.00% (21/25) | 91.67% (22/24) | 1 | 94.12% |
| external_exact | precise_target_mentions_candidate | 80.00% (20/25) | 87.50% (21/24) | 2 | 88.24% |
| controlled_authored | v51_event_map_control | 76.67% (46/60) | 85.00% (34/40) | 1 | 93.75% |
| controlled_authored | precise_target_mentions_candidate | 76.67% (46/60) | 82.50% (33/40) | 1 | 93.75% |
| controlled_cross_target_precision | v51_event_map_control | 90.00% (9/10) | 80.00% (4/5) | 0 | 0.00% |
| controlled_cross_target_precision | precise_target_mentions_candidate | 80.00% (8/10) | 60.00% (3/5) | 0 | 0.00% |

- Overall commitment/call delta: `-1` / `-2`.
- Cross-target commitment/call delta: `-1` / `-1`.
- Semantic/call regressions: `4` / `2`.
- Exact paired target McNemar p-value: `1.0`.
- Fresh holdout gate passed: `False`.
- Decision: `reject_v52_due_to_fresh_regression_preregister_state_machine`.
- Interpretation: V52 caused a new error on frozen data. Reject runtime advancement and preregister an explicit per-target discourse-state machine instead of tuning on this consumed holdout.
- Runtime and physical VRM execution remain unchanged.
