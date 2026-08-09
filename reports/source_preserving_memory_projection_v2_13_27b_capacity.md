# V2.13 Qwen3.5 Model-Capacity Screen

**Decision: `27b_capacity_diagnostic_invalid_or_resource_rejected`**

| Measure | Locked 9B control | Fresh 27B candidate |
|---|---:|---:|
| Mean official F1 | 0.213 | 0.228 |
| Paired delta | - | +0.015 |
| 95% bootstrap CI | - | [-0.048, +0.079] |
| Mean latency | historical qwen3.5:9b | 14.571s |

V2.13 is a model-capacity screen on 57 fully exposed LoCoMo cases. It reuses locked 9B controls and adds only fresh 27B generations with identical complete-session prompts. A pass can authorize only a separate preregistration on a new source-disjoint external dataset; it cannot establish generalization, full-pipeline memory use, persona similarity, runtime safety, or production readiness.
