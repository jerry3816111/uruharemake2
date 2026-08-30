# M10.2 behavior-preserving casual-register remediation plan

Status: design frozen before any M10.2 model output  
Date: 2026-08-15

## Motivation

M10.1 shows that explicit behavior authority is usually obeyed (87.5%) but the visible surface contract fails mainly through polite-register drift. The M10.1 cases are exposed and cannot be reused to claim a repair.

M10.2 evaluates a single downstream change on a new source-disjoint synthetic language fixture: every case first receives the frozen one-pass behavior-authoritative realization; the same raw utterance is then passed through a register-only repair that may change wording but may not change the authoritative behavior, facts, stance, or safety boundary.

## Conditions

- `S0_ONE_PASS`: frozen M10 behavior-authoritative utterance.
- `S1_REGISTER_REPAIR`: a second same-model call rewrites only casual register. Every case is repaired, including S0 passes, so selection is not conditional on observed quality.

The fixture has 18 cases: six behavior labels × three cases, with Chinese, English, and Japanese event contexts balanced 6/6/6. Its events and wordings do not overlap M9/M10.1.

## Falsifiable gates

1. S1 complete visible-contract pass rate is at least 85%.
2. S1 authority alignment is at least 90% and not lower than S0.
3. No S0-aligned case becomes authority-misaligned after repair.
4. At least one output changes, proving the treatment ran.
5. Private-person and mind-reading claims remain zero.
6. All 18 initial, 18 repair, and 36 classifier calls complete with no scored retry or production-memory write.

Classifier alignment is a fixed same-model proxy, not human evidence. A blinded paired packet will be created, but preference remains pending until independent raters complete it.

## Claim boundary

This is a synthetic language-layer remediation after the failure type was known. A pass establishes only source-disjoint engineering evidence that casual register can be improved without obvious behavior drift under this fixture. It does not repair M9 prediction accuracy, validate Uruha fidelity, prove human preference, or authorize runtime persona activation. Voice and VRM remain downstream.
