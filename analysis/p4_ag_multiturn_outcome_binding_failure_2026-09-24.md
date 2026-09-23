# P4-AG multi-turn ambiguity outcome binding — preserved failure

Date: 2026-09-24  
Freeze commit: `2b62bb6`  
Formal status: **FAIL**

## What was tested

P4-AG was limited to one additive shadow variable: bind second-turn evidence to
the exact first-turn desired-response prediction and candidate ledger.  It did
not change P4-AF, the released feedback classifier, candidate ranking, visible
Japanese output, prompts, model calls, or factual memory.

The frozen set contained nine developer-authored two-turn sequences: three
support, three contradiction-with-explicit-replacement, and three unrelated
topic changes.  Six were prospectively frozen English/Japanese sequences.

## Result

- first-turn authorized ledger: `7/9`
- exact prediction/ledger identity binding: `7/9`
- exact final outcome: `8/9`
- supported selected candidate: `3/3`
- contradicted selected candidate plus explicit supported replacement: `2/3`
- unknown counted as success: `0`
- visible/model/fact/profile/episode side effects: `0/0/0/0/0`
- raw dialogue persisted in the P4-AG trace: `0`

Two fresh first turns never reached P4-AG:

1. `ag_fresh_contradict_with_tease_ja`
2. `ag_fresh_unrelated_topic_en`

Both produced `no_bounded_observable_trigger` upstream.  Therefore there was
no P4-AF ledger to bind, and P4-AG correctly refused to fabricate one.  The
other seven sequences show that identity binding itself works conditionally
when the first-turn observable trigger and eligibility gates are satisfied.
That conditional evidence does not override the frozen overall **FAIL**.

## Static root cause

The failing paraphrases express cognitive overactivity compositionally but do
not match the released M37 head/predicate cue inventory.  Their desired-response
state remains inactive even though semantically close frozen paraphrases are
recognized.  This is an upstream perception-coverage gap, not a second-turn
support/contradiction/unknown binding error.

The failure is not repaired inside P4-AG because doing so would mix two causal
variables: observable-trigger coverage and outcome binding.  The next task must
freeze an additive multilingual trigger-coverage extension separately; the
P4-AG fresh cases are exposed and can only become development regression cases.
An independent later multi-turn set is still required.

## Claim boundary

This result is controlled developer-authored evidence.  It does not establish
the user's private desired response, natural-distribution performance, felt
understanding, a human equation, or advantage over a strong LLM.
