# M56.8 Durable-Release-Gated Formal Scoring Plan

Date: 2026-09-03
Status: prospective engineering contract; frozen before any real M56 target-outcome access
Single changed variable: formal-scoring authorization depends on the exact M56.7 durable-generation release

## Problem

M56.7 proves that generation artifacts created through its new entry point cross the bound Mac file-and-directory
full-sync barrier before a durable-generation release is issued.  The already frozen M56.4 scorer predates that
release.  Its own isolated success fixture contains only M56.2/M56.3 artifacts and can still open the withheld
outcome and commit an M56.4 result without any M56.7 mode or release.

That behavior is valid historical M56.4 evidence, but it cannot be the currently authorized formal path.  Otherwise
the experiment could claim crash-safe generation while the scorer never proves that the predictions came from that
generation boundary.

## Single attributable change

Add one new formal-scoring authorization state before the unchanged M56.4 scorer:

`M56.4 pre-score integrity -> exact M56.7 mode/release -> durable M56.8 gate -> unchanged M56.4 outcome join/score`

This milestone does not change the prediction packet, model calls, prompts, condition views, resources, scores,
metrics, thresholds, outcome key, human data or M56.4 result semantics.  It performs zero scorer model calls.

## Required boundary

1. The only new formal entry point is `execute_durable_release_gated_formal_scoring(run_id)`.  It accepts no
   caller-supplied mode, release, predictions, outcome, result, threshold, readiness or bypass flag.
2. Before any private outcome access, revalidate the frozen M56.4 pre-score inputs and require byte-equivalent
   canonical M56.7 mode and durable release at the standard private run paths.
3. The M56.7 release must bind the same lease, submission, prediction commitment, M56.3 scoring release, call count,
   M56.7 contract and filesystem device as the run being scored.
4. When the M56.4 resource gate is ready, durably commit one immutable M56.8 scoring gate with file and parent
   directory `fsync` plus macOS `F_FULLFSYNC` before delegating to M56.4.
5. A run that already has an M56.4 outcome-access receipt, private score report or result commitment but lacks the
   M56.8 gate is rejected.  Historical access cannot be retroactively certified as M56.8-authorized.
6. An identical restart may validate the same M56.8 gate and let M56.4 finish or validate its deterministic result.
   A changed gate, release, result or dependency fails closed.
7. Existing M56.4 and M56.7 files remain frozen.  The old M56.4 API remains historical/cooperative code; results
   created by calling it directly do not carry M56.8 authorization.

## Success conditions

- missing or mutated M56.7 mode/release is rejected before `load_outcome_inputs`;
- an outcome-access/result artifact predating the M56.8 gate is rejected as non-certifiable;
- a forged 30-row run completed through the actual M56.7 entry can pass the new gate and then produce exactly the
  unchanged M56.4 score/result, with 180 mock generation calls and zero scorer model calls;
- repeated completion reuses the identical gate and identical M56.4 result;
- old M54-M56.7 frozen hashes remain unchanged;
- live state remains V7 `0/18 + 0/18`, V9/real rows `0/30`, formal calls/outcome access/result absent;
- a read-only graphical page explains the before/after authorization chain and evidence boundary to a non-expert.

## Evidence boundary

M56.8 makes the sanctioned application workflow refuse to authorize scoring unless the generation release is
present, exact and durably bound before outcome access.  It is not an operating-system sandbox: a cooperative or
malicious same-host caller can still run the historical M56.4 function or read files if it already has filesystem
permission.  Such access is detectable as lacking M56.8 authorization but is not cryptographically prevented.

Forged fixtures prove state-machine composition only.  They are not two-human evidence, real temporal rows, actual
formal model performance, Equation V1 validity, a solved human-response equation, full-pipeline evidence or
production readiness.
