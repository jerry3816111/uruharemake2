# P4-AT dual-act development failure (preserved)

Status: **FAIL / exposed development evidence only**. This exact two-turn pair must not be reused as fresh or formal evidence.

## What happened

The P4-AS product on the isolated port `7881` correctly executed a visible `calibrate_need` action on turn 1:

- input: `My mind keeps churning and cannot switch off at all.`
- visible Japanese: `今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？`
- P1/M44 identity: `p1-1-59401c9870bf6d5f`, registered for exactly the next user turn
- temporal graph: `過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`

Turn 2 then said:

`Yes—that question was right. I want a practical method now.`

This contains two independently testable conversational acts:

1. “that question was right” supports the **previously performed clarification action**;
2. “I want a practical method now” selects the **current response policy** `solve_regulation`.

The released system collapsed both into `uncertain/unknown`: M44 reported `linked=false`, P4-AG kept all six candidates unknown, no current binding was created, and the visible reply became the generic clarification `ん、そこもう少しだけ聞かせて。`. The temporal graph therefore showed `前輪 unknown` instead of supported closure.

## Root cause and next bounded change

The existing single-label path does not separate feedback about the performed action from the user's current request. Its English cue inventory also misses these two specific paraphrases. P4-AT will add one bounded capability: clause-level **executed-action feedback / current-request decomposition**, requiring exact M44/P1 identity. It will not change P4-AG's base classifier, candidate scores, P1 guard, memory truth, persona prompt, or language guard.

The frozen comparison will score action acts, not one exact Japanese sentence. Exact wording remains recorded separately so action-level causal closure cannot be confused with lexical reproducibility.

## Reproducibility

- isolated root: `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-y19q2ock`
- log SHA-256: `12b29fdc6c27d70bff212793068dbbfcaa42b1030d96fb9e525d275241f957d3`
- observed turn-2 latency: `36.4479s`; local model timed out before the existing fallback surface

This failure does not prove how often the pattern occurs in natural conversation, whether people prefer the repaired output, or that a human reaction equation has been found.
