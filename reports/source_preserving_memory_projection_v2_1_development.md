# Source-preserving Memory Projection V2.1 Development Result

**Decision: development_reject_or_inconclusive**

| Metric | Complete session | Source projection | Difference |
|---|---:|---:|---:|
| Target-only support | 0/8 | 5/8 | +5 |
| Target-removed false support | 0/8 | 0/8 | +0 |
| Intact target support | 0/8 | 0/8 | +0 |

- Exact source projection: 100.0%
- Structured contract: 87.5%
- Exact span grounding: 87.5%
- Mean prompt character reduction: 90.3%

## Failed gates

- `all_48_decisions_present`
- `projected_target_only_answer_support_count_at_least`
- `projected_intact_target_support_count_at_least`
- `structured_contract_rate_equals_one`
- `exact_span_grounding_rate_equals_one`

This is exposed development evidence only. Runtime and production remain disabled.
