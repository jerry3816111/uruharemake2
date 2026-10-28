# P4-AH multilingual observable-trigger coverage acceptance

Date: 2026-09-24  
Freeze commit: `0d2ea6f`  
Formal status: **PASS**

## Capability change

P4-AH adds a typed, additive perception trace for multilingual expressions of
cognitive overactivity.  A trigger requires both a cognitive head and an
unresolved or continuing regulation predicate inside one bounded span.  A
metalinguistic guard rejects uses where the same tokens are merely quoted or
written as words.

The released M37 detector, P4-AF authority rule, P4-AG feedback/binding logic,
candidate scores, visible reply, prompt, model calls, and memory writes were not
changed.  The extension records observable language evidence only and keeps
`private_state_truth_claimed=false`.

## Frozen result

- exposed P4-AG upstream failures repaired: `2/2`
- fresh positive Chinese/English/Japanese cases: `9/9`
- fresh near-control abstentions: `12/12`
- full frozen sentence strings embedded in implementation: `0`
- released base trace mutations: `0`
- candidate ranking changes: `0`
- visible/model/fact/profile/episode side effects: `0/0/0/0/0`
- raw dialogue persisted in the extension trace: `0`
- P4-M through P4-AH plus M24 regression: `317 passed`

The twelve controls include ordinary fan movement, metalinguistic token use,
resolved thought states, and physical head movement.  Passing these controls is
what distinguishes the change from adding a broad keyword such as `turn` or
`head`.

## Evidence scope

This is deterministic contract evidence on developer-authored frozen cases.
It shows that the two P4-AG misses came from bounded multilingual trigger
coverage and can be repaired without changing downstream reasoning.  It does
not retroactively make P4-AG pass, because those P4-AG cases are exposed.

The next valid test is a newly frozen end-to-end multi-turn set created after
P4-AH is fixed.  That set must traverse trigger coverage, eligibility, competing
hypotheses, exact identity binding, and supported/contradicted/unknown outcome
updates without changing visible behavior.

## Claim boundary

This does not prove open-domain semantics, the truth of a private mental state,
felt understanding, natural-distribution performance, a human equation, or
advantage over a strong LLM.
