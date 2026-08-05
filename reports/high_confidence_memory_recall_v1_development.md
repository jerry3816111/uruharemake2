# High-confidence memory recall V1 development result

- Decision: `development_reject_or_inconclusive`
- Scope: known eight-case mechanism fixture; this is not fresh generalization evidence.
- LeftBrain model calls: 24 -> 8
- Zero-model-call rate: 25.0% -> 75.0%
- Median latency: 60.009s -> 0.009s
- Total latency: 1456.570s -> 487.872s
- Post-hoc target-removed false fast paths: 8/8

## Causal conditions

| Condition | Baseline plan rate | Candidate plan rate |
|---|---:|---:|
| intact target | 87.5% | 100.0% |
| target removed | 0.0% | 0.0% |
| target replaced | 87.5% | 100.0% |
| irrelevant removed | 87.5% | 100.0% |

## Gates

- complete_32_rows: PASS
- intact_target_plan_preserved: PASS
- removed_target_does_not_leak: PASS
- replacement_steers_plan: PASS
- irrelevant_removal_preserves_target: PASS
- model_call_budget: FAIL
- boundary_preflight: PASS
- no_transport_errors: PASS
- no_production_writes: PASS
- no_vrm_actions: PASS

## Evidence boundary

A pass authorizes only a disjoint fresh holdout. It does not authorize production, benchmark, human-memory, or persona-similarity claims.
