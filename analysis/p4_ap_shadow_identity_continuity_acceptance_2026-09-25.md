# P4-AP shadow identity continuity — acceptance

## Outcome

P4-AP passed its prospectively frozen contract in one fresh isolated Safari
session. The prior P4-AO crash did not recur: genuine product prediction IDs
advanced `p1-1 → p1-2 → p1-3`, while the classifier-only shadow was seeded
with the immediately preceding floor `0 → 1 → 2`. Every event still passed
the original P1 no-skip guard; the guard was not disabled or weakened.

The visible temporal graph advanced as frozen:

1. `過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`
2. `過去 0｜現在 6候選/選択 calibrate_need｜前輪 supported→本輪驗證｜本輪未來 已封存`
3. `過去 1｜現在 6候選/選択 calibrate_need｜既有驗證→過去｜前輪 supported→本輪驗證｜本輪未來 已封存`

Both the identity node and temporal node were visible in Safari before
`utterance` on all three turns. Logic, top-level runtime payload and blackboard
payload matched exactly. The isolated database contains three embeddings, the
formal log contains three rows, and the maximum end-to-end turn latency was
`3.7837s` (`10.4651s` total).

## What changed

Only P4-AG's throw-away feedback-classifier shadow gained identity continuity.
For a real `p1-N-*` prediction, the adapter puts `N-1` into the empty shadow's
sequence floor and then invokes the unchanged P1 setter. It copies zero product
ledger rows, adds zero model calls, writes zero factual memories and stores no
raw dialogue in the graph trace.

## What this does and does not prove

This proves a bounded engineering mechanism: one real three-turn product path
can commit a response-action prediction, verify it on the next turn, keep that
verification out of same-turn past, and promote it to past evidence only on a
later turn, while preserving exact event identity.

It does **not** prove that the selected response is psychologically correct,
that the prediction generalizes, that users feel more understood, that the
system beats a strong LLM, or that a human equation has been discovered.

There are two explicit remaining observations:

- turns 2 and 3 produced the same clarification surface. The frozen contract
  tested identity and temporal causality, not human preference or repeated-
  clarification quality;
- P4-AN's separate P4-AH-to-P4-AD live ordering failure remains open. P4-AP
  deliberately used a released M37 trigger and cannot be used to claim the
  later multilingual extension is live in the product.
