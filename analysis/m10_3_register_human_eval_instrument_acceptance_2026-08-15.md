# M10.3 Register Human-evaluation Instrument Acceptance

Date: 2026-08-15  
Result: **instrument complete; human evidence pending**

## What was completed

- Frozen, preregistered four-dimension A/B rubric for all 18 M10.2 pairs.
- Minimum of three complete independent human raters; partial or malformed data fail closed.
- One-way SHA-256 rater pseudonyms; the raw identifier is not written to rating records.
- Required independence and unseen-key attestations.
- Isolated writes under `analysis/m10_3_register_ratings/`; no production memory, chat log, persona fact, or formal Uruha data write.
- Atomic latest-state JSONL plus a separate revision audit stream.
- Offline analysis of S1−S0 dimension deltas, item-cluster bootstrap intervals, changed-pair preference, pairwise quadratic-weighted kappa, and the exposed `R-JA-06` disagreement.
- Graphical local Safari page with packet context, blind A/B candidates, rubric, progress, and explicit 0/3 claim boundary.

## Frozen gates

The gates were fixed before any human rating: three complete raters, reliability ≥0.40, natural-casual-Japanese mean delta ≥+0.50 with CI lower bound >0, semantic/behavior/non-overclaiming mean deltas each ≥−0.15, and changed decisive-pair S1 preference >0.60. `R-JA-06` must always be reported separately.

## Verification

- M10.3 unit/contract tests: 8/8 passed.
- Python compile and scoped diff check passed.
- Preregistration/packet/key lock validation passed.
- Zero-rating analyzer result: valid instrument, 0 complete raters, every human gate false except the required-case reporting invariant, `claim_authorized=false`.
- Safari: `Blind Rating · M10.3` loaded; A/B source identity remained hidden; 0/3 pending boundary was visible; blank save was rejected; no rating file was created; all 8 existing Safari tabs remained open.
- Screenshot: `analysis/m10_3_safari_blind_rating_entry_2026-08-15.jpeg` (SHA-256 `44b3f49059562048b2e4a6e14479ccf0147656ee44c34c09ae7dd4a18d96f289`).

## What this does not prove

There are currently **zero human ratings**. Therefore this milestone does not establish human preference, naturalness improvement, behavior preservation, felt understanding, Uruha fidelity, general language superiority, consciousness, mind-reading, real-person identity, or production readiness. It completes the instrument needed to collect such bounded evidence; it does not substitute engineered test scores for people.

## Next gate

Three distinct, consenting people who have not seen the hidden key must each complete all 18 pairs. Only after the locked offline analyzer processes those files may M10.3 report a formal pass or failure. A failure remains a research result and does not authorize post-hoc threshold or packet changes.
