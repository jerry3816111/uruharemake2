# V36 action-intent frame development result

> Retired V34 cases are used for development only. Runtime and VRM execution remain disabled.

## Direct-call baselines

| model | path | exact | no-action | recall | false action |
|---|---|---:|---:|---:|---:|
| qwen2_5_7b | v34_direct_function_call | 58.3% | 35.0% | 87.5% | 41.7% |
| qwen2_5_7b | v34_lexical_validator | 80.6% | 100.0% | 59.4% | 0.0% |
| qwen3_5_9b | v34_direct_function_call | 55.6% | 25.0% | 93.8% | 44.4% |
| qwen3_5_9b | v34_lexical_validator | 77.8% | 95.0% | 59.4% | 2.8% |

## V36 frame parsers

| condition | call exact | no-action | call recall | state | frame exact | frame F1 | parse | p50 | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| qwen3_5_0_8b_lower_bound | 58.3% | 100.0% | 9.4% | 8.3% | 2.8% | 8.2% | 8.3% | 1.41s | FAIL |
| qwen3_5_2b_candidate | 55.6% | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2.33s | FAIL |
| qwen3_5_4b_candidate | 94.4% | 95.0% | 93.8% | 52.8% | 33.3% | 56.4% | 72.2% | 4.02s | FAIL |
| qwen2_5_7b_matched_reference | 75.0% | 80.0% | 75.0% | 44.4% | 27.8% | 54.3% | 55.6% | 3.09s | FAIL |
| qwen3_5_9b_matched_upper_reference | 91.7% | 95.0% | 93.8% | 69.4% | 36.1% | 59.8% | 75.0% | 8.28s | FAIL |

## Matched representation deltas

| V36 condition | same-model V34 baseline | exact delta | no-action delta | recall delta | false-action delta |
|---|---|---:|---:|---:|---:|
| qwen2_5_7b_matched_reference | qwen2_5_7b | +16.7 pp | +45.0 pp | -12.5 pp | -27.8 pp |
| qwen3_5_9b_matched_upper_reference | qwen3_5_9b | +36.1 pp | +70.0 pp | +0.0 pp | -38.9 pp |

- Passing candidates: `[]`
- Selected candidate: `None`
- Decision: `do_not_advance_v36_action_intent_frame`
- Passing development permits only a new frozen holdout, never direct runtime integration.
