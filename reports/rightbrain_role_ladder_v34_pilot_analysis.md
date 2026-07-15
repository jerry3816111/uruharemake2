# V34 RightBrain model ladder development pilot

> This is development evidence. It selects confirmation candidates but cannot change runtime.

| condition | semantic contract | semantic groups | raw gate | hard failure | polite drift | p50 latency | eligible |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3_5_0_8b_lower_bound | 47.2% | 70.5% | 22.2% | 5.6% | 52.8% | 0.78s | no |
| qwen3_5_2b_candidate | 44.4% | 70.5% | 38.9% | 0.0% | 16.7% | 1.25s | no |
| qwen3_5_4b_candidate | 88.9% | 96.2% | 83.3% | 2.8% | 5.6% | 2.42s | no |
| qwen2_5_7b_base_reference | 80.6% | 92.4% | 69.4% | 13.9% | 11.1% | 1.13s | no |
| qwen3_5_9b_upper_reference | 91.7% | 97.1% | 83.3% | 2.8% | 5.6% | 3.93s | no |

## Decision

- `no_model_is_authorized_for_confirmation_or_runtime_change`
- Smallest eligible candidate: `None`

## Failed gates

- `qwen3_5_0_8b_lower_bound`: semantic_contract_pass_rate, semantic_group_recall, raw_surface_gate_pass_rate, polite_or_service_register_rate
- `qwen3_5_2b_candidate`: semantic_contract_pass_rate, semantic_group_recall, raw_surface_gate_pass_rate, polite_or_service_register_rate
- `qwen3_5_4b_candidate`: semantic_contract_pass_rate
- `qwen2_5_7b_base_reference`: semantic_contract_pass_rate, semantic_group_recall, polite_or_service_register_rate
- `qwen3_5_9b_upper_reference`: warm_generation_median_seconds

The pilot may choose which models deserve a fresh confirmation test. It cannot authorize a runtime change, persona training, or a human-likeness claim.
