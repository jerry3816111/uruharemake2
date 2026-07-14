# Memory Highlight + Span Contract V2: Frozen Analysis

## Verdict

**Reject V2 runtime integration.** Full-context highlighting preserved source context and the span contract worked whenever upstream evidence existed, but highlighting did not improve paired semantic accuracy and failed one frozen transfer case.

| condition | semantic pass | evidence recall | position-invariant |
| --- | ---: | ---: | ---: |
| A: full context | 97.22% | 88.89% | 91.67% |
| B: full context + highlight | 97.22% | 97.22% | 91.67% |
| C: B + span contract | 97.22% | 97.22% | 91.67% |

## Paired result

- `highlighted_full_session_freeform - full_session_freeform`: +0.00 pp, wins/losses 1/1, McNemar p=1.000000, bootstrap 95% CI [-8.33, +8.33] pp.
- `highlighted_full_session_span_contract - highlighted_full_session_freeform`: +0.00 pp, wins/losses 0/0, McNemar p=1.000000, bootstrap 95% CI [+0.00, +0.00] pp.

## What worked

- Attention found all target utterances: 100.00% recall, 98.15% precision.
- Every highlighted context restored exactly: 100.00%.
- Span contract conditional validity: 35/35 (100.00%).

## Why the gate failed

| case | condition | failure |
| --- | --- | --- |
| dev_therapy_current_time__end | full_session_freeform | assistant_acknowledgement_misread_as_user_fact |
| transfer_grocery_previous_frequency__middle | highlighted_full_session_freeform | controller_markup_copied_into_quote |
| transfer_grocery_previous_frequency__middle | highlighted_full_session_span_contract | controller_markup_copied_into_quote |

## Complementarity

- Both A and B passed: 34/36.
- A only passed: 1/36.
- B only passed: 1/36.
- Neither passed: 0/36.
- At least one path carried answer evidence: 36/36.

## Causal interpretation

- Keeping the full session prevented the nine extraction losses seen in V1, but inline highlight markup was copied into one otherwise correct quote and was properly rejected by source grounding.
- Highlighting fixed one control failure where an assistant acknowledgement was misread as the user's appointment time, but introduced one different transfer failure, so its paired net semantic gain was zero.
- Control and highlight failures were complementary: at least one path had the answer-bearing evidence in all 36 cases. This supports evidence arbitration or a confidence-triggered second read, not unconditional trust in either path.
- The controller-owned span contract was valid and semantically correct in all 35 cases with an upstream ledger, including same-quote comparisons and explicit negation, but it cannot recover evidence that extraction discarded.

## Next experiment constraints

- Use new scenarios; V2 cases are consumed development evidence.
- Strip only controller-owned highlight tags from generated quotes before exact grounding, and accept the repair only when the stripped quote aligns to source.
- Add a provenance sufficiency check that distrusts assistant acknowledgements as user-memory values and triggers an attention-guided second read.
- Keep the span contract after evidence arbitration, because its conditional 35/35 result does not justify removing it.
- Measure the extra latency and token cost of any second read.
- Do not change runtime until a new untouched comparison passes every gate.

These 36 cases are consumed development evidence. No runtime file was changed.
