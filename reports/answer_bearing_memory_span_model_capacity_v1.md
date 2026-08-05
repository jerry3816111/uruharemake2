# Answer-bearing memory span model-capacity V1 result

## Decision

**model_capacity_not_sufficient**

Selected model: `none`.

This is consumed development evidence only. It cannot authorize runtime.

## Staged comparison

| Model | Phase 1 target-only | Removed-target selections | Full run | Intact | Replacement | Target-only | Wrong traces | Contract | Grounding | Mean new-call latency | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3.5:0.8b | 2/8 | 2 | 16/32 | 0.0% | 0.0% | 25.0% | 2 | 31.2% | 56.2% | 2.085s | no |
| qwen3.5:2b | 1/8 | 0 | 16/32 | 0.0% | 0.0% | 12.5% | 0 | 25.0% | 71.4% | 2.772s | no |
| qwen3.5:4b | 1/8 | 0 | 32/32 | 12.5% | 12.5% | 12.5% | 0 | 100.0% | 100.0% | reused | no |
| qwen3.5:9b | 4/8 | 0 | 16/32 | 0.0% | 0.0% | 50.0% | 0 | 100.0% | 100.0% | 7.896s | no |

## Interpretation boundary

The screen isolates model size under one frozen contract. If no model passes, increasing model capacity is not a sufficient repair on this slice. If one passes, only a new disjoint holdout is authorized; runtime remains unchanged.
