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
| qwen3_5_0_8b_authorizer | qwen2_5_7b | 52.8% | 80.0% | 18.8% | 11.1% | 86.2% | 1.45s | FAIL |
| qwen3_5_0_8b_authorizer | qwen3_5_9b | 52.8% | 75.0% | 25.0% | 13.9% | 96.8% | 1.43s | FAIL |
| qwen3_5_2b_authorizer | qwen2_5_7b | 69.4% | 85.0% | 59.4% | 11.1% | 75.9% | 2.38s | FAIL |
| qwen3_5_2b_authorizer | qwen3_5_9b | 66.7% | 70.0% | 68.8% | 19.4% | 87.1% | 2.33s | FAIL |
| qwen3_5_4b_authorizer_reference | qwen2_5_7b | 80.6% | 95.0% | 71.9% | 2.8% | 100.0% | 3.91s | FAIL |
| qwen3_5_4b_authorizer_reference | qwen3_5_9b | 86.1% | 95.0% | 81.2% | 2.8% | 100.0% | 3.85s | FAIL |

- Selected candidate: `None`
- Decision: `do_not_advance_v35_semantic_authorizer`
- Runtime remains unchanged; a fresh frozen holdout is required after a development pass.
