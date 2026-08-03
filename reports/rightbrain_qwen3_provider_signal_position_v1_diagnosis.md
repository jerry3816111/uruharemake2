# Qwen3 provider signal position probe diagnosis

## Formal result

The preregistered outcome is `provider_signal_position_contract_regressed`.
Moving the exact same `persona_expression_brief` object to the first top-level
JSON field is rejected. It authorizes no full-pipeline holdout, training,
adapter save, persona claim, or production change.

## What changed

| Metric | Nested control | Top-level signal | Delta |
|---|---:|---:|---:|
| Provider pairs with different outputs | 1/4 | 3/4 | +2/4 |
| Correct provider-reference direction | 4/8 | 5/8 | +1/8 |
| Provider-reference margin | 0.000470 | -0.005204 | -0.005674 |
| Joint semantic/memory/surface contract | 8/8 | 6/8 | -2/8 |

All three repeats produced exact condition output hashes, including the repeat
that reversed condition order. The result is therefore not an ordering or
sampling artifact.

## Causal interpretation

The model is sensitive to the JSON path: 7/8 outputs changed and provider-pair
diversity increased. That difference was not aligned with the intended provider,
and it damaged protected behavior. Position alone is not the missing mechanism.

The clearest regression occurred in the explicit-memory health case. The nested
target output preserved `八時にまた連絡するよ`; the top-level target changed to
`八時まで...連絡します`, introducing forbidden `ます` and losing the allowed
`八時に` commitment cue. The neutral output also changed `八時に` to `八時まで`.

The current provider object contains abstract labels such as `lazy_short`,
`slightly_bratty`, and placeholder operations such as
`neutral_surface_operation_1`. A base language model has no reliable executable
meaning for these internal labels. Making that object more visible can change
wording without telling the model which concrete transformation is allowed.

## Next falsifiable hypothesis

Before any additional SFT or preference training, test a deterministic compiler
that converts provider state into a short set of concrete surface operations
such as sentence-ending register, directness, hedge strength, and energy. The
compiled signal must explicitly remain subordinate to semantic markers, memory
speakability, forbidden forms, and tool calls.

The next probe must use newly constructed source-disjoint synthetic cases because
all 20 sources in the current curriculum have now participated in at least one
experiment. It should compare the current top-level abstract object against a
compact compiled signal, with the base model, left-brain plan, memory contract,
generation, and scorer fixed. A pass must improve provider-reference direction
without any joint-contract regression.
