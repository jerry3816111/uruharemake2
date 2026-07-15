# V34 VRM action isolation development result

> Development evidence only. The 120 V33 cases and model calls were already observed.

| condition | path | exact | no-action | required recall | false action | negation violations |
|---|---|---:|---:|---:|---:|---:|
| qwen2_5_7b_quantized_control | raw | 68.3% | 54.3% | 95.3% | 30.8% | 0 |
| qwen2_5_7b_quantized_control | validated | 97.5% | 100.0% | 95.3% | 0.0% | 0 |
| qwen3_5_9b_quantized_treatment | raw | 51.7% | 24.3% | 96.7% | 47.5% | 2 |
| qwen3_5_9b_quantized_treatment | validated | 98.3% | 100.0% | 96.7% | 0.0% | 0 |

## Decision

- `freeze_policy_and_author_fresh_action_confirmation_holdout`
- The validator never creates a positive action; it only enforces authorization and grounding.
- Runtime remains unchanged until a fresh frozen holdout passes.
