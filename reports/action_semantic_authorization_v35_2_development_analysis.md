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
| qwen3_5_0_8b_authorizer | qwen2_5_7b | 58.3% | 100.0% | 6.2% | 0.0% | 75.9% | 1.57s | FAIL |
| qwen3_5_0_8b_authorizer | qwen3_5_9b | 58.3% | 95.0% | 12.5% | 2.8% | 67.7% | 1.51s | FAIL |
| qwen3_5_2b_authorizer | qwen2_5_7b | 66.7% | 80.0% | 68.8% | 13.9% | 86.2% | 2.44s | FAIL |
| qwen3_5_2b_authorizer | qwen3_5_9b | 63.9% | 65.0% | 78.1% | 22.2% | 90.3% | 2.38s | FAIL |
| qwen3_5_4b_authorizer_reference | qwen2_5_7b | 75.0% | 95.0% | 59.4% | 2.8% | 100.0% | 4.35s | FAIL |
| qwen3_5_4b_authorizer_reference | qwen3_5_9b | 80.6% | 95.0% | 68.8% | 2.8% | 100.0% | 4.07s | FAIL |

- Selected candidate: `None`
- Decision: `do_not_advance_v35_semantic_authorizer`
- Runtime remains unchanged; a fresh frozen holdout is required after a development pass.
