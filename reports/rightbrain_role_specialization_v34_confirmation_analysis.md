# V34 fresh role-specialization confirmation

## RightBrain

| condition | semantic contract | raw gate | private leaks | p50 | p95 |
|---|---:|---:|---:|---:|---:|
| qwen2_5_7b_single_reference | 75.0% | 54.2% | 0 | 1.36s | 2.82s |
| qwen3_5_9b_single_upper_reference | 95.8% | 90.3% | 0 | 3.87s | 4.68s |
| qwen3_5_4b_single_ablation | 79.2% | 72.2% | 0 | 2.39s | 2.88s |
| qwen3_5_4b_guarded_candidate | 98.6% | 90.3% | 0 | 2.54s | 4.98s |

- RightBrain gate: FAIL
- RightBrain decision: `do_not_integrate_4b_guarded_rightbrain_from_v34`

## VRM action validation

| condition | path | exact | no-action | recall | false action |
|---|---|---:|---:|---:|---:|
| qwen2_5_7b | raw | 58.3% | 35.0% | 87.5% | 41.7% |
| qwen2_5_7b | validated | 80.6% | 100.0% | 59.4% | 0.0% |
| qwen3_5_9b | raw | 55.6% | 25.0% | 93.8% | 44.4% |
| qwen3_5_9b | validated | 77.8% | 95.0% | 59.4% | 2.8% |

- Action gate: FAIL
- Action decision: `do_not_integrate_action_validator_from_v34`

No production replacement, persona claim, or human-likeness claim is authorized by this test.
