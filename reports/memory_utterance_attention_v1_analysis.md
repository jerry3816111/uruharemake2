# Memory Utterance Attention V1: Frozen Analysis

## Verdict

**Reject V1 runtime integration.** Selection worked, but replacing the full session with selected turns harmed extraction, and the first proposition contract was too coarse.

| stage | result | interpretation |
| --- | ---: | --- |
| selected target utterances | 72/72 | selector found every frozen target |
| full-session evidence recall | 97.22% | control retained discourse context |
| attention-only evidence recall | 75.00% | 9 cases lost evidence after truncation |
| full-session semantic pass | 83.33% | matched control |
| attention-only semantic pass | 63.89% | -19.44 pp |
| typed-proposition semantic pass | 38.89% | -25.00 pp |

## Paired evidence

- `utterance_attention_freeform - full_session_freeform`: -19.44 pp, wins/losses 2/9, McNemar p=0.065430, bootstrap 95% CI [-36.11, -2.78] pp.
- `utterance_attention_proposition - utterance_attention_freeform`: -25.00 pp, wins/losses 3/12, McNemar p=0.035156, bootstrap 95% CI [-44.44, -5.56] pp.

## Failure localization

- 6/36: model generated an invalid system-owned field or index
- 14/36: passed
- 6/36: one quote could not expose before + current roles
- 9/36: attention extraction / ledger missing
- 1/36: valid grounded answer failed the preregistered strict phrase metric

All 27 admitted proposition spans were source-grounded (100.00%).

Gate audit: `all_valid_proposition_spans_grounded` was implemented as requiring every proposition contract to be valid, which is stricter than the gate name. This does not change the rejection because four other gates also failed.

## Capability effects

| capability | attention - control | proposition - attention |
| --- | ---: | ---: |
| change_direction | +16.67 pp | -100.00 pp |
| current_count | -50.00 pp | +0.00 pp |
| current_location | +0.00 pp | +0.00 pp |
| current_time | +16.67 pp | -50.00 pp |
| historical_yes_no | -50.00 pp | +50.00 pp |
| previous_frequency | -50.00 pp | -50.00 pp |

## What this changes

- Query-aware selection found every frozen target utterance, so selection was not the observed bottleneck in this experiment.
- Replacing the full session with selected utterances removed discourse context and caused nine repeated extraction failures; attention must augment rather than replace source context.
- A ledger event assigns one evidence role to an entire quote, but six comparison cases encoded before and current values in the same quote; answer roles must bind to source spans, not only whole events.
- The model should not choose system-known contract fields such as answer type, required roles, or whether a nonrelational question has a relation.

## Next experiment constraints

- Use new scenarios; V1 cases cannot serve as a promotion holdout again.
- Keep the full source session and add selected utterances as explicit highlights.
- Represent old/current values as separately grounded source spans.
- Let the controller define slot names and relation constraints; let the model only bind spans.
- Keep runtime unchanged until a new untouched comparison passes every gate.

The V1 dataset is now analysis data and cannot be reused as an untouched promotion set. No runtime file was changed.
