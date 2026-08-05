# Answer-bearing memory span V1 development result

## Decision

**development_reject_or_inconclusive**

This is exposed development evidence only. It cannot authorize runtime or production.

## Causal comparison

| Measure | Lexical gate V1 | Answer-span gate V1 | Change |
|---|---:|---:|---:|
| Wrong trace selections | 9 | 0 | -9 |
| Target-removed selections | 6 | 0 | -6 |
| Intact safe outcome | 87.5% | 12.5% | -75.0% |
| Replacement safe outcome | 37.5% | 12.5% | -25.0% |
| Target-only safe outcome | 75.0% | 12.5% | -62.5% |

## Contract and local cost

- Structured contract validity: 100.0%.
- Exact source grounding: 100.0% (6/6).
- Mean / p95 local latency: 5.339s / 9.431s per intervention.
- Transport errors: 0.

## Condition results

| Condition | Safe | Selected | Wrong trace | Statuses |
|---|---:|---:|---:|---|
| c0_intact_target_and_hard_negative | 1/8 (12.5%) | 1 | 0 | {"selected": 1, "suppressed": 1, "unsupported": 6} |
| t1_remove_exact_target | 8/8 (100.0%) | 0 | 0 | {"unsupported": 8} |
| t2_replace_exact_target | 1/8 (12.5%) | 1 | 0 | {"selected": 1, "suppressed": 1, "unsupported": 6} |
| n1_remove_exact_hard_negative | 1/8 (12.5%) | 1 | 0 | {"selected": 1, "suppressed": 1, "unsupported": 6} |

## Gate failures

- `intact_safe_outcome_rate_not_lower_than_baseline`
- `replacement_safe_outcome_rate_strictly_higher_than_baseline`
- `irrelevant_removed_target_selection_rate_not_lower_than_baseline`

## Evidence boundary

A pass permits only a new disjoint holdout. A failure rejects this version or localizes the next single-variable experiment. No persona, benchmark, human-memory, or production claim is allowed.
