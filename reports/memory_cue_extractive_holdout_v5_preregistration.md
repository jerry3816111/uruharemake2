# Memory cue-driven fallback V5 preregistration

## Why this holdout exists

V4 recovered one of 48 cases over the shared provenance path, with no paired loss, but the effect was statistically weak. Reusing V4 to tune and retest would make the result adaptive. V5 therefore uses 24 new scenarios and 72 new cases while freezing the complete V4 treatment.

## Frozen design

| Property | Value |
|---|---:|
| New scenarios | 24 |
| Cases (beginning / middle / end) | 72 |
| Answerable / unanswerable | 54 / 18 |
| Holdout A / B | 36 / 36 |
| Exact scenario or question reuse from V1-V4 | 0 |
| Official benchmark items | 0 |
| Model calls before preregistration | 0 |

The model, seed, temperature, context length, V4 runner, cue module, selector, sufficiency gate, candidate limit, scoring, and fixed abstention are frozen by SHA-256.

## Known risks frozen before model execution

- The selector found 96/99 required source quotes and also selected 54 non-gold user utterances.
- The candidate gate rejected 6 answerable natural-frequency cases.
- The candidate gate marked 6 unanswerable identity/ownership cases as potentially sufficient.
- These cases and components will not be repaired after seeing V5 results.

## Confirmatory questions

1. Does E remain at least as accurate as R while using less latency and fewer prompt tokens?
2. Does E recover at least two distinct scenarios over P, with no paired losses and recovery in both holdout splits?
3. Does E still abstain on all 18 genuinely unanswerable cases despite the known gate risk?
4. Are candidate sources always exact user utterances, with zero assistant admission?

## Decision boundary

Passing every gate permits only a separate review for an off-by-default shadow integration. It does not authorize an active runtime change. If quality and safety hold but recovery breadth does not, V5 supports only an efficiency conclusion. Any safety or quality regression rejects integration.
