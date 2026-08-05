# Semantic memory recall support V1 development result

- Decision: `development_pass_requires_fresh_holdout`
- Scope: known eight-case mechanism fixture; not fresh generalization evidence.

| Measure | Original planner | Rejected score-only V1 | Semantic-support V1 |
|---|---:|---:|---:|
| LeftBrain model calls | 24 | 8 | 6 |
| Fast-path rows | 0 | 19 | 21 |
| Median latency | 60.009s | 0.009s | 0.009s |
| Target-removed false fast paths | 0 | 8 | 0 |

## Causal conditions

| Condition | Plan marker rate |
|---|---:|
| Intact target | 87.5% |
| Target removed | 0.0% |
| Target replaced | 87.5% |
| Irrelevant removed | 87.5% |

## Gates

- complete_32_rows: PASS
- intact_target_plan_preserved: PASS
- removed_target_does_not_leak: PASS
- replacement_steers_plan: PASS
- irrelevant_removal_preserves_target: PASS
- no_target_removed_fast_path: PASS
- valid_fast_path_coverage: PASS
- model_call_budget: PASS
- all_fast_paths_have_support: PASS
- no_sensitive_fast_path: PASS
- no_non_recall_fast_path: PASS
- no_ambiguous_fast_path: PASS
- boundary_preflight: PASS
- no_transport_errors: PASS
- no_production_writes: PASS
- no_vrm_actions: PASS

## Evidence boundary

A pass authorizes only a disjoint fresh holdout. Production remains disabled.
