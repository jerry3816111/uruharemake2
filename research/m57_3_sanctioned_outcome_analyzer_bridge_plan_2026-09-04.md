# M57.3 Sanctioned Outcome-to-Analyzer Bridge — Plan

Date: 2026-09-04

Status: prospective contract frozen before implementation and before any real M57 diagnostic target-outcome access

Single changed variable: add the only sanctioned post-result bridge that joins the already committed M57.2 component
predictions to the withheld observed behavior and the unchanged M57 analyzer. M56 samples, predictions, model,
hardware, decoding, scores and thresholds, and all M57 stage/statistical rules remain frozen.

## Problem proved before the change

M57.2 has 30 rows and 90 outcome-blind perception/retrieval/state predictions, but deliberately has zero observed
labels and zero decision ceilings. Its schema cannot enter the M57 analyzer. The existing M57 formal entry also
deliberately rejects every caller-created real bundle because there is no artifact authority bridge.

The M56 score report cannot safely substitute for the missing labels. In the retained full-chain forged probe, all 30
labels were ambiguous when attempting to infer them from B5/Ours paired score deltas. M57.3 must therefore neither
guess a label nor accept one from the caller.

## Frozen authority and access boundary

The public execute and validate functions accept only `run_id`. Before an M57.3 outcome access they must revalidate:

1. the exact M57.1 pre-outcome mode;
2. the complete M57.2 evidence, schedule, 90-call ledger, capsule and commitment under the formal evidence policy;
3. the complete M56.8/M56.10 gate, intent, checkpoint, score report and result commitment;
4. exact dataset, packet, prediction, resource and private-outcome hash bindings.

M57.3 has one explicit diagnostic authorization distinct from M56 scoring. Under the same per-run scoring lock it
commits a mode and no-retry intent before opening the private outcome compartment. It may load that compartment at
most once, validates it with the unchanged M56.4 validator, creates a full-sync private joined checkpoint, and never
loads it again after a valid checkpoint exists. A crash after intent but before checkpoint is terminal because whether
the outcome was opened is unknowable. Thus a successful complete research run has two named sanctioned loads total:
one for M56 scoring and one for M57 diagnosis, never an unrecorded replay load.

## Frozen transformation and analysis

For every exact M57.2 row the bridge adds only:

- `observed_label` from the validated private outcome row;
- a decision diagnostic ceiling that is one-hot on that observed behavior, explicitly post-outcome and excluded from
  causal ranking;
- the existing perception/retrieval/state committed probabilities;
- an unavailable realization stage unless independent blind human surface ratings exist.

No component probability may be regenerated or changed. The bridge creates the exact legacy M57 row shape, verifies
all source hashes and commitments, then produces a mechanics-only projection whose rows are numerically identical.
That projection is passed to the unchanged `analyze_component_substitution_bundle`; M57.3 wraps its deterministic
aggregate output with the authenticated source/result chain. The projection cannot itself create formal authority.

The formal aggregate result and commitment may be written only when the upstream evidence is real and public
validation passes. The private joined checkpoint retains the observed-label rows inside the scoring compartment.
Author-constructed fixtures may use only the explicitly internal rehearsal path, remain `engineering_only`, cannot
create a formal result and never authorize M58.

## Acceptance criteria

- public execute/validate signatures contain only `run_id`;
- a complete forged full chain proves 30 labels joined, 30 decision ceilings, 90 unchanged pre-outcome predictions,
  120 available stage substitutions and unavailable realization;
- M56 loads once, M57.3 loads once, successful replay adds zero loads, and checkpoint restart adds zero loads;
- intent-only restart is terminal with zero additional load;
- public formal execution and validation reject the same forged run;
- missing/partial/mutated M57.1, M57.2, M56.10, outcome, checkpoint, projection, result or commitment fails closed;
- label order/sample/hash drift, caller label injection, duplicate/missing outcomes and decision mutation fail closed;
- unchanged M57 clear/tie fixtures and prior selected milestone tests remain green;
- current live state remains denied and no real outcome/model call/formal result is created;
- the graphical page clearly distinguishes pre-outcome predictions, M56 score read, M57 diagnostic read, post-outcome
  decision ceiling, unchanged analyzer and the real-human-data gate.

## Failure policy and next step

No retry is permitted after an M57.3 intent. If the checkpoint is missing, corrupt or cannot be validated, the run is
terminal; a new formal run ID and newly committed pre-outcome predictions are required. Passing engineering rehearsal
does not enable M58. Only a valid real M57.3 result may authorize planning the next result-dependent diagnostic step.

## Claim boundary

Passing M57.3 establishes only that committed component predictions can be joined to a withheld observable outcome
through an attributable, crash-safe, fail-closed result path and analyzed without changing the frozen diagnostic
statistics. It does not validate coder truth, recover private mental states, prove a real leading Uruha component,
validate Equation V1, show broad LLM superiority, solve a human-response equation, or establish production readiness.
