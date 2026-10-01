# P4-AO reachable temporal graph — preserved failure

## Outcome

P4-AO is a formal **FAIL**. Its first fresh Safari turn passed every frozen
per-turn gate:

- natural Japanese reply;
- durable isolated episode;
- released M37 `cognitive_overactivity` path;
- six present candidates with `calibrate_need` selected;
- a locked next-turn outcome commitment;
- exact logic/runtime/graph payload before `utterance`;
- zero raw/private graph leakage.

Safari showed:

`過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`

The second formal turn then failed before it could return a reply or append a
log row:

`ValueError: P1 prediction sequence skipped the next event`

The same case was stopped and was not rerun.

## Root cause

The product-wide P1 identity adapter correctly minted sequence 1 on turn one
and sequence 2 on turn two. P4-AG, however, reconstructed its classifier-only
shadow feedback model from `adaptive.empty_model()` for every new binding.
That empty shadow model had identity floor 0, so committing the genuine
sequence-2 event looked like an illegal skipped event and was rejected.

This is not a language-generation error and not a temporal-graph rendering
error. It is a real multi-turn identity-continuity defect between the P1 event
ledger and P4-AG's isolated feedback shadow. The earlier synthetic P4-AG and
P4-AL fixtures did not reproduce the product-wide identity sequence advancing
between turns, so their passes did not cover this boundary.

## Evidence boundary and next split

The first turn is useful evidence that P4-AN can deliver a truthful current
candidate/future-commitment node in Safari through an already reachable
released path. It cannot be promoted into a three-turn pass.

The next change may fix only the shadow identity floor/continuity needed to
accept the exact product prediction event. It must not change detection,
candidate ranking, reply text, feedback classification, factual memory or the
temporal state machine. A new three-turn case is required; P4-AO is now exposed
and closed.

The separate P4-AH-to-P4-AD live ordering defect found by P4-AN remains open
and must not be hidden inside this identity repair.
