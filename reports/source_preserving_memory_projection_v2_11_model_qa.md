# V2.11 Paired Local-Model QA

**Decision: `model_qa_reject_adjacency_answer_quality_gain`**

| Measure | Isolated Top-3 | Adjacency |
|---|---:|---:|
| Mean official F1 | 0.153 | 0.179 |
| Paired delta | - | +0.026 |
| 95% bootstrap CI | - | [-0.041, +0.097] |

V2.11 evaluates fresh qwen3.5:9b answers on 57 frozen final-reserve questions under two source projections. A pass can support only a separate full-pipeline memory-intervention preregistration. It cannot establish causal production-memory use, persona similarity, runtime safety, or production readiness.
