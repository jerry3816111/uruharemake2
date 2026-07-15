# V42 grounded commitment-classifier conclusion

## Result

The unchanged ontology grounded all 38 supported development targets with no extra targets. Each local model then classified one target at a time using only the full utterance, target identity, and numbered exact anchor spans.

| condition | parse | commitment | requested precision / recall | supported frame exact | call exact | false action | p95 | passed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V39 full-frame control | 88.9% trace | 65.8% | **100.0% / 100.0%** | 63.9% | **100.0%** | **0.0%** | 5.05s | control |
| Qwen3.5 0.8B | 2.6% | 0.0% | 0.0% / 0.0% | 27.8% | 55.6% | **0.0%** | **2.42s** | no |
| Qwen3.5 2B | 68.4% | 21.1% | **100.0% / 22.7%** | 38.9% | 63.9% | **0.0%** | **2.16s** | no |
| Qwen3.5 4B | 94.7% | **78.9%** | **100.0% / 72.7%** | **80.6%** | 86.1% | **0.0%** | 3.52s | no |

No model passed every preregistered gate. No fresh holdout was created or consumed, and no runtime change is authorized.

## What improved

Compared with V39 full-frame generation, the 4B grounded classifier improved:

- commitment accuracy from 65.8% to 78.9%;
- supported-frame case exactness from 63.9% to 80.6%;
- selected-evidence support from 60.5% to 89.5%;
- p95 case latency from 5.05 seconds to 3.52 seconds.

The decomposition therefore improved the completeness of the observable intermediate representation, even though it did not meet deployment gates.

## Why it still failed

The 4B condition missed eight of 38 commitments:

- two commitments were semantically correct but rejected because the model chose an out-of-range evidence index;
- three coordinated expression states were labeled `mentioned` instead of inheriting the utterance's direct request;
- two replacement actions were mislabeled because negation from a neighboring target was applied too broadly;
- one cancelled request was labeled `negated`.

The whole-utterance fail-closed rule prevented false actions, but requested-action recall fell to 72.7%. A system that is safe only because it frequently does nothing is not ready for VRM interaction.

## Model-size conclusion

For this pragmatic classification role, the available 0.8B and 2B models are too small: their structured-output and semantic failures dominate any latency advantage. The 4B model is the current minimum viable starting point, but it still needs a better task interface rather than more free-form responsibility.

## Next hypothesis

Keep the 4B classifier, but remove `evidence_index` from model output and select an exact grounded span deterministically. Then compare:

1. commitment-only output with the V42 target context;
2. commitment-only output plus all grounded targets and general relational guidance for coordinated requests, local negation scope, replacement, and cancellation.

This isolates whether the remaining failures come from unnecessary output burden or missing relational context. Unsupported-action discovery remains a separate open-set task.
