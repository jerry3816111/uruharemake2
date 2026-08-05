# Answer-bearing memory span V1 development result

## Decision

**development_reject_or_inconclusive**

This is exposed development evidence only. It cannot authorize runtime or production.

## Causal comparison

| Measure | Lexical gate V1 | Answer-span gate V1 | Change |
|---|---:|---:|---:|
| Wrong trace selections | 9 | 0 | -9 |
| Target-removed selections | 6 | 0 | -6 |
| Intact safe outcome | 87.5% | 0.0% | -87.5% |
| Replacement safe outcome | 37.5% | 0.0% | -37.5% |
| Target-only safe outcome | 75.0% | 0.0% | -75.0% |

## Contract and local cost

- Structured contract validity: 0.0%.
- Exact source grounding: 0.0% (0/0).
- Mean / p95 local latency: 13.137s / 17.027s per intervention.
- Transport errors: 0.

## Condition results

| Condition | Safe | Selected | Wrong trace | Statuses |
|---|---:|---:|---:|---|
| c0_intact_target_and_hard_negative | 0/8 (0.0%) | 0 | 0 | {"invalid_evidence_contract": 8} |
| t1_remove_exact_target | 8/8 (100.0%) | 0 | 0 | {"invalid_evidence_contract": 8} |
| t2_replace_exact_target | 0/8 (0.0%) | 0 | 0 | {"invalid_evidence_contract": 8} |
| n1_remove_exact_hard_negative | 0/8 (0.0%) | 0 | 0 | {"invalid_evidence_contract": 8} |

## Gate failures

- `structured_parse_rate_equals_one`
- `exact_span_grounding_rate_equals_one`
- `intact_safe_outcome_rate_not_lower_than_baseline`
- `replacement_safe_outcome_rate_strictly_higher_than_baseline`
- `irrelevant_removed_target_selection_rate_not_lower_than_baseline`

## Evidence boundary

A pass permits only a new disjoint holdout. A failure rejects this version or localizes the next single-variable experiment. No persona, benchmark, human-memory, or production claim is allowed.
