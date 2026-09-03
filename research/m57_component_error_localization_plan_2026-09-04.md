# M57 Outcome-Blind Component Error Localization Plan

Date: 2026-09-04

Status: prospective readiness contract frozen before implementation, any M56 result, and any real target-outcome access

Single changed variable: an explicit component-substitution diagnostic that can distinguish recoverable error at
perception, retrieval, computational state, decision and realization boundaries instead of reporting only aggregate
B5-versus-Ours scores.

## Problem proved before the change

The M56 scorer correctly reports seven condition metrics and 30 paired B5/Ours records, but it has no fields for a
diagnostic stage, substitution target, oracle/proxy source, changed component, stage-level delta, attribution status
or leading recoverable stage. A temporary forged report contains zero of ten required localization keys. This proves
that M56 can say whether the system won or lost but not where recoverable error entered the pipeline. It does not
prove that any real component is wrong.

## Operational stage boundary

M57 separates five stages and never calls inferred private mental state a human oracle:

1. `perception`: independently adjudicated, pre-outcome observable input features;
2. `retrieval`: independently adjudicated relevant history IDs restricted to the prediction cutoff;
3. `state`: an observable-only computational proxy; unavailable when no sourced proxy exists;
4. `decision`: a post-outcome one-hot upper bound, reported as a ceiling and excluded from causal ranking;
5. `realization`: behavior-preserving surface evidence from independent human ratings; unavailable for the current
   behavior-only M56 result.

Every substitution plan must be committed before outcome access. Only the named component is replaced at its stage;
all upstream inputs and execution rules remain hash-bound, while downstream values may change and must be recorded.
The same sample set, base model, hardware, decoding, token accounting and no-retry policy apply. Outcome-dependent
scoring happens only after all prediction commitments exist.

## Metrics and attribution rule

For each eligible stage, compare original Ours with the single-stage substitution on the same samples. Positive
`original minus substituted` Brier and NLL deltas mean the substitution recovered loss. Use 20,000 paired bootstrap
draws with seed 570904. A stage is `recoverable_effect` only when both lower 95% bounds are above zero and top-1 is
not worse. `leading_recoverable_stage` is descriptive and requires the same unique leader on both mean deltas with
at least 0.05 separation from the runner-up. Ties, mixed metrics, unavailable evidence or interaction ambiguity must
abstain. M57 never authorizes a unique biological or psychological cause claim.

## Frozen engineering success conditions

- current formal entry accepts only `run_id` and refuses before private outcome access while M56 is unauthorized;
- pure analyzer validates exact labels, probabilities, 30 aligned samples, one changed stage and frozen provenance;
- state without an observable proxy and realization without human ratings remain unavailable, never synthesized;
- decision upper bound is excluded from leading-stage ranking;
- a clear author-constructed retrieval fixture is localized to retrieval;
- a tied fixture returns no leading stage;
- mutation, missing sample, future-leaking provenance, retry/fallback, outcome-before-commit and stage drift fail closed;
- result reports paired deltas, bootstrap intervals, availability, cost and claim boundary;
- graphical page distinguishes aggregate comparison from component localization and displays current human-data denial.

## Formal completion and failure response

This readiness milestone may pass without a formal M57 scientific result. Formal localization remains blocked until
M55 real rows and an authorized M56 result exist. After that result, all formal substitution plans must be committed
without viewing outcome labels. If no eligible stage has a recoverable effect, retain the negative result rather than
inventing a cause. If multiple stages tie or interact, report `ambiguous_interacting_or_unresolved` and design M58
around one prospectively chosen variable on new sealed data.

## Claim boundary

M57 readiness can establish that a frozen analyzer distinguishes eligible observable oracle/proxy substitutions,
abstains on ambiguous fixtures and refuses formal execution while M56 is unavailable. Synthetic localization does
not identify a real Uruha error, validate latent human state, prove Equation V1, show superiority over an LLM, or
replace the two-human data gate and later independent human realization ratings.
