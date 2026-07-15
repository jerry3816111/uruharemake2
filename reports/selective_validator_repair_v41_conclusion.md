# V41 selective validator-repair conclusion

## Result

V41 replayed the frozen V39 4B primary outputs and invoked a repair specialist only for the four validator-flagged traces. All repair models received the same original input, previous output, and validator errors, with no gold answer or benchmark identity.

| repair model | exact calls | trace wellformed | frame exact | repair accepted | calls/case | effective p95 | passed |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5 0.8B | **100.0%** | 88.9% | 52.8% | 0.0% | 0.111 | 6.11s | no |
| Qwen3.5 2B | **100.0%** | 88.9% | 52.8% | 0.0% | 0.111 | 7.45s | no |
| Qwen3.5 4B | **100.0%** | 94.4% | 55.6% | 50.0% | 0.111 | 7.23s | no |

No model passed every preregistered gate. No fresh holdout was created or consumed, and no runtime change is authorized.

## What the repair experiment established

- The 0.8B and 2B specialists could not produce one accepted repair across four attempts.
- The 4B specialist produced two structurally valid, call-preserving repairs.
- One 4B repair correctly canonicalized an unsupported camera request.
- One 4B repair preserved the empty call set but added a semantically unnecessary negated frame. Call preservation alone is therefore not enough to prove trace correctness.
- External validator feedback improved structure more than blind resampling, but it did not solve the underlying semantic representation problem.

## Deeper diagnosis

The unchanged V39 primary had perfect compiled calls on these retired cases but only 52.8% joint frame exactness before accepted 4B repairs. Sixteen cases still contained missing, extra, or mislabeled non-executed frames. Common failures were:

- replacing a supported negated or ambiguous value with `unsupported`;
- omitting a negated frame while keeping the later requested frame;
- confusing `mentioned`, `hypothetical`, `negated`, and `cancelled`;
- inventing an unrelated frame from ordinary conversation;
- assigning an unsupported action to `other` when its natural domain was known.

The V39 ontology/compiler can still recover the final executable action, but that recovery is not evidence that the model built a complete human-like intermediate representation.

## Next hypothesis

Do not ask a small model to generate complete frames. Use the project action ontology to enumerate exact supported action candidates from the utterance, then give a model only the narrower task of classifying the final commitment for each grounded candidate. This separates value grounding from pragmatic judgment and makes the model output contract much smaller.

Before model inference, first audit how much of the retired and fresh target space the ontology can cover. Unsupported-action detection must remain a separately measured open-set task rather than being hidden inside the supported commitment classifier.
