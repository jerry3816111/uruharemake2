# Memory Highlight + Span Contract V2: Preregistration

## Research question

Can query-aware attention improve memory reasoning without deleting episodic context, and can a
controller-owned span contract preserve the selected meaning without giving the model answer keys?

V1 selected all 72 target utterances but harmed answer quality because it replaced the complete
session with selected turns. V1 also assigned one semantic role to a whole quote, so a single quote
containing both an old and a current value could not expose both answer roles.

## Evidence behind the design

- HiLight keeps the original context and inserts minimal evidence tags instead of compressing or
  rewriting it: https://arxiv.org/abs/2604.22565
- Attribute First, then Generate separates source selection from later realization and keeps
  fine-grained source attribution: https://aclanthology.org/2024.acl-long.182/
- QA-SRL binds semantic relationships to argument spans rather than forcing one role onto an entire
  sentence: https://aclanthology.org/P18-1191/

These papers motivate the architecture, not the result. The frozen paired experiment below must
still show that the implementation helps this system.

## Frozen matched conditions

| condition | full source retained | highlight tags | note + ledger | final answer stage |
| --- | --- | --- | --- | --- |
| A: `full_session_freeform` | yes | no | existing pipeline | existing freeform reader |
| B: `highlighted_full_session_freeform` | yes | yes | same pipeline | same freeform reader |
| C: `highlighted_full_session_span_contract` | yes | yes | reuse B artifacts | controller-owned slots; model binds exact spans |

`B - A` isolates evidence highlighting. `C - B` isolates the final semantic binding contract. No
gold answer, gold source index, or expected relation is present in an inference prompt.

## Frozen data and controls

- 12 new scenarios, each placed at the beginning, middle, and end: 36 paired cases.
- Development and transfer each contain 18 cases with disjoint entities.
- Zero official benchmark items and zero V1 case reuse.
- The V1 selector is frozen. Its preimplementation V2 audit found all 72 target utterances and two
  extra adjacent utterances; those false positives remain in the experiment.
- Model, seed, temperature, context budget, input order, question frames, and scoring are fixed.
- Dataset file SHA-256: `48e56f2e403d3cb5859dad075869085e4d633e17c16565a7090d03b2e1a0b75a`.
- Canonical cases SHA-256: `c1a464badc4dbb284e338d0fd257a908d4947149f1938eb3abd2f59827f7e35c`.

## Success boundary

Both architectural changes must avoid semantic regressions in development, transfer, every
capability family, and position invariance. Every highlighted context must restore byte-for-byte to
the original session. Every accepted source quote and answer span must be grounded, and every span
contract must contain exactly the controller-required slots.

Passing these gates permits only a new untouched evaluation. It does not authorize a runtime
change, an external benchmark claim, or reuse of these cases as a future promotion holdout.
