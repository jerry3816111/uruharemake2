# V2.2 Local Evidence Extractor Capacity Screen

**Decision: development_reject_or_inconclusive**

| Measure | Frozen 4B | 9B intervention | Difference |
|---|---:|---:|---:|
| Projected target support | 5/8 | 7/8 | +2 |
| Structured contract | 87.5% | 81.2% | -6.2% |
| Exact span grounding | 87.5% | 81.2% | -6.2% |

- 9B complete-session target support: 0/8
- 9B projected hard-negative false support: 0/8
- 9B mean latency (complete / projection): 14.29s / 5.65s

## Failed gates

- `structured_contract_rate_equals_one`
- `exact_span_grounding_rate_equals_one`

This paired exposed-development screen does not authorize runtime or production use.
