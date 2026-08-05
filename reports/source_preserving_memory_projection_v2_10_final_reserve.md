# V2.10 Final Reserve Evidence-ID Result

**Decision: `final_reserve_pass_authorize_independent_model_preregistration_only`**

The unchanged adjacency projection replicated its official evidence-turn
retention advantage on the final two LoCoMo reserve conversations.

| Measure | Isolated Top-3 | Adjacency | Difference |
|---|---:|---:|---:|
| Official evidence turns retained | 37/57 | 47/57 | +10 |
| Micro evidence recall | 64.9% | 82.5% | +17.5 pp |
| Cases with all evidence retained | 37/57 | 47/57 | +10 |
| Mean source character ratio | 17.1% | 27.3% | +10.2 pp |

## Paired case transitions

| Same question | Cases |
|---|---:|
| Both projections retained all evidence | 35 |
| Only isolated Top-3 retained all evidence | 2 |
| Only adjacency retained all evidence | 12 |
| Neither retained all evidence | 8 |

Both final reserve conversations improved: 65.0% to 90.0% and 64.9% to
78.4% evidence recall. The run consumed both final reserve payloads exactly
once and committed only aliases, hashes, source indices, and metrics.

No model was called. This result proves deterministic source-evidence
retention, not that a model reads or causally uses the retained evidence. It
authorizes only a separate independent model-evaluation preregistration, not
runtime shadowing or production enablement.
