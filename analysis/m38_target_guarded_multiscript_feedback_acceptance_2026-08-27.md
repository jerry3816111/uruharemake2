# M38 Target-Guarded Multiscript Feedback Linkage — Acceptance Report

## Outcome

M38 is complete as a bounded engineering milestone, but its first and only frozen formal reserve is **FAIL**. The mechanism improved linkage accuracy from 44.44% to 94.44% on the 18-case source-disjoint reserve, while preserving zero false linkages on ordinary negation and targetless rejection. One Chinese correction remained unrecognized, so four accuracy/recall/revision gates did not pass.

The implementation and formal result are frozen. The failed sentence must not be patched into M38 or rerun; any coverage remediation belongs to a separately frozen later milestone.

## What M38 changed

Before M38, a visible `不／not／ない` could be confused with feedback about the previous reply. M38 requires all three observable conditions before it changes the previous branch:

1. an immediately pending response prediction exists;
2. the current turn observably refers back to and rejects that response;
3. the current turn contains exactly one non-negated replacement response policy.

If any condition is missing, M38 records an uncertain outcome and leaves the previous branch unchanged. It does not replace a missing target with a guess.

## Frozen formal reserve

- Reserve: 18 cases across Chinese, English and Japanese.
- Baseline linkage/outcome accuracy: **44.44%**.
- M38 linkage/outcome accuracy: **94.44%** (**+50.00 percentage points**).
- Unique-target correction recall: **88.89%** (8/9).
- Replacement-policy accuracy: **88.89%**.
- Ordinary-negation false linkage: **0/6**.
- Targetless-rejection false linkage: **0/3**.
- M34 revision accuracy: **94.44%**.
- Raw dialogue persistence: **0**.
- Unverified mental-fact writes: **0**.
- Median / p95 linkage latency: **0.000667 / 0.001715 seconds**.
- Model generation calls in the linkage evaluator: **0**.

Failed gates: overall accuracy, unique-correction recall, replacement-policy accuracy and M34 revision accuracy. The sole miss was `m38r_zh_corr_share_03`: the correction reference was detected, but the word-order variant did not yield a unique `share_arousal` target, so M38 safely failed closed. That is safer than inventing a replacement, but it is still a formal miss.

Formal result SHA-256: `b08df2707e37d0253c9a1ff591f8f7fdb135d6802517fdec03e3cb38f92e89c1`.

## Real Safari multi-turn evidence

The Web UI was run in Safari against an isolated temporary memory DB, session store, adaptive-person model and log. Existing tabs were left untouched; one M38-owned tab was added.

### 1. Unique replacement correction

Initial request selected `solve_regulation`. The next English turn explicitly rejected that reading and asked the system to stay while waiting. M38 linked the feedback to the pending prediction, M34 marked the old branch contradicted, retained it for audit, and revised `solve_regulation → share_arousal`. The visible Japanese reply performed the companionship policy.

### 2. Ordinary negation

`I didn't sleep last night, but I'm not asking you to fix anything.` contained negation but no observable reference to the prior response. M38 recorded `ordinary_negation_not_feedback`, did not link it and did not revise the prior branch.

This turn also exposed a separate product failure: the visible Japanese inverted the speaker role (`私は昨夜寝なかった...`) as if Uruha, not the user, had not slept. This is not hidden by the successful M38 linkage decision; it is the primary retained counterexample for M39.

The turn finished in 16.182 seconds. It remained under the historical 20-second product target, but the large jump from roughly 2–4 seconds on guarded turns shows that response latency is not uniformly controlled.

### 3. Targetless rejection

After a new `solve_regulation` prediction, the Japanese feedback `違う、そういうことじゃない。` rejected the prior reading but provided no unique replacement. M38 recorded `fail_closed_no_replacement_target`, did not revise the old branch and moved the current turn to `calibrate_need`. The final reply asked a short, low-pressure question instead of pretending to know the missing target.

One malformed punctuation-only turn caused by simulated Japanese keystrokes was excluded and repeated with clipboard-safe entry; it is retained in the isolated log and explicitly identified in the evidence JSON rather than silently deleted.

## Regression and integrity evidence

- M38 focused/evaluator tests: **8 passed** before implementation freeze.
- M16–M38 plus personhood compatibility: **206 passed**.
- Python compile and diff checks: passed.
- M37 frozen-file integrity: **10/10 unchanged**.
- M38 implementation freeze: 11 files; all matched before the single formal run.
- Adaptive model: `raw_dialogue_persisted=false`; none of the accepted Safari utterances appeared in the adaptive JSON.

## Claim boundary and next milestone

M38 supports the narrow claim that observable next-turn corrections can be linked more safely across three scripts while ordinary and targetless negation fail closed. It does **not** prove open-domain pragmatic understanding, private-intent truth, natural Uruha persona quality, human felt-understanding preference, or overall superiority to a strong LLM.

M39 is `Semantic + Persona Surface-Act Verifier`. Its single core variable is whether the final visible Japanese both preserves source roles/facts and actually performs the already-selected response policy. M39 must use a new pre-frozen reserve and may not modify M37/M38 frozen artifacts.
