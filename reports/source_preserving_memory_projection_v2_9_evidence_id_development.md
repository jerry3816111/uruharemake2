# V2.9 Official Evidence-ID Development Result

**Decision: `development_pass_authorize_final_reserve_preregistration_only`**

LoCoMo's official `evidence` dialogue IDs replaced the exact-answer-string
development oracle. The projection algorithms were unchanged.

| Measure | Isolated Top-3 | Adjacency | Difference |
|---|---:|---:|---:|
| Official evidence turns retained | 65/122 | 84/122 | +19 |
| Micro evidence recall | 53.3% | 68.9% | +15.6 pp |
| Cases with all evidence retained | 59/115 | 77/115 | +18 |
| Mean source character ratio | 15.8% | 27.3% | +11.5 pp |

## Paired case transitions

| Same question | Cases |
|---|---:|
| Both projections retained all evidence | 55 |
| Only isolated Top-3 retained all evidence | 4 |
| Only adjacency retained all evidence | 22 |
| Neither retained all evidence | 34 |

All four exposed conversations improved in evidence-turn recall. This is an
exposed-data deterministic development result, not an independent holdout.

No model was called. No runtime, production memory, or VRM state changed. The
result authorizes only a separate preregistration for the final two reserve
conversations; it does not authorize accessing them now, model generation,
runtime shadowing, or production enablement.
