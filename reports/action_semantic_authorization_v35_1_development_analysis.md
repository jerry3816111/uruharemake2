# V35 semantic action authorization development result

> Development evidence on the retired V34 confirmation set. It cannot authorize runtime use.

## Baselines

| proposal source | path | exact | no-action | recall | false action |
|---|---|---:|---:|---:|---:|
| qwen2_5_7b | raw_direct | 58.3% | 35.0% | 87.5% | 41.7% |
| qwen2_5_7b | v34_lexical_validator | 80.6% | 100.0% | 59.4% | 0.0% |
| qwen3_5_9b | raw_direct | 55.6% | 25.0% | 93.8% | 44.4% |
| qwen3_5_9b | v34_lexical_validator | 77.8% | 95.0% | 59.4% | 2.8% |

## Semantic authorizers

| authorizer | proposal source | exact | no-action | recall | false action | parse | p50 | gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| qwen3_5_0_8b_authorizer | qwen2_5_7b | 33.3% | 45.0% | 25.0% | 30.6% | 96.5% | 1.42s | FAIL |
| qwen3_5_0_8b_authorizer | qwen3_5_9b | 38.9% | 50.0% | 31.2% | 30.6% | 100.0% | 1.40s | FAIL |
| qwen3_5_2b_authorizer | qwen2_5_7b | 66.7% | 85.0% | 62.5% | 11.1% | 89.7% | 2.33s | FAIL |
| qwen3_5_2b_authorizer | qwen3_5_9b | 63.9% | 70.0% | 71.9% | 19.4% | 90.3% | 2.29s | FAIL |
| qwen3_5_4b_authorizer_reference | qwen2_5_7b | 83.3% | 100.0% | 71.9% | 0.0% | 100.0% | 3.80s | FAIL |
| qwen3_5_4b_authorizer_reference | qwen3_5_9b | 88.9% | 100.0% | 81.2% | 0.0% | 100.0% | 3.76s | FAIL |

- Selected candidate: `None`
- Decision: `do_not_advance_v35_semantic_authorizer`
- Runtime remains unchanged; a fresh frozen holdout is required after a development pass.
