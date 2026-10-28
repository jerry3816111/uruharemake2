# M56.4 Separate Formal Scorer and Result Commitment · 2026-09-02

## Problem

M56.3 can finish an outcome-blind B0–B5/Ours generation matrix, bind all 210
predictions and actual resource observations, and issue a capability for a
separate scorer.  The repository still lacks a frozen formal entry point that
consumes that capability, checks resource comparability before opening the
withheld outcome key, computes the preregistered metrics without caller-supplied
thresholds, and commits an immutable scoped result.  Using an ad-hoc notebook at
that point would make the most important evidence boundary non-reproducible.

## Single attributable change

Add one deterministic post-commit scoring state machine:

`validate frozen predictions → pre-outcome resource gate → open withheld outcome → join → frozen metrics → immutable score report → result commitment`

This milestone does not change the Equation, predictions, labels, outcome key,
primary contrast, metrics, thresholds, model outputs, human data, or frozen
M54–M56.3 evidence.  It performs zero model calls.  While the human chain is
incomplete it must deny scoring before any outcome access or result write.

## Required boundary

1. The only public formal entry point is `execute_formal_scoring(run_id)`.  It
   accepts no prediction, outcome, metric, threshold, sensitivity-pass, result,
   provider, or readiness injection.
2. Before opening `scoring/`, revalidate the M56.2 request/receipt/lease, M56.3
   schedule/submission/commitment/release, Equation artifacts, runtime binding,
   and formal call ledger.  Mutation, omission, reorder, retry, fallback, wrong
   model, incomplete resources, or release-before-commit fails closed.
3. Compute the B5/Ours actual prompt-token difference before outcome access.  If
   it exceeds the frozen 5% threshold and no separately frozen prospective
   sensitivity artifact exists, stop before opening the outcome key.  A caller
   boolean may never bypass this requirement.
4. After the pre-outcome gate passes, load only the standard withheld outcome key
   and split report from `scoring/`; bind both to the activation request and
   validate sample order, labels, timestamps, confidence, packet hash, zero
   future leakage, and generation-access denial.
5. Report all seven conditions.  The frozen primary contrast remains
   `B5_STRUCTURED_HISTORY` versus `OURS_HYBRID`; co-primary Brier and NLL use the
   frozen paired bootstrap and sign-flip rules, with top-1 noninferiority and
   exact McNemar unchanged.  No post-result control or metric selection exists.
6. The private report must not contain source text, private mental-state claims,
   raw model responses, reasoning traces, or caller-authored conclusions.  It may
   contain aggregate metrics, preregistered paired deltas, opaque sample ids,
   resource totals, hashes, and the bounded pass/fail decision.
7. Atomically write the private score report, then a SHA-256 result commitment.
   An identical rerun may only validate/finalize the same immutable report; it
   cannot replace predictions, outcomes, thresholds, or decision.  No production
   memory write, deployment, model retry, or broad human-equation claim follows.

## Acceptance while human data is unavailable

- live `run_id` scoring is denied with zero outcome access and no directory or
  result creation;
- a test-only forged 30-row real-shaped packet can exercise the 210-row scorer
  mechanics in memory or an isolated temporary directory, but remains zero-human
  engineering evidence;
- missing or mutated release, submission, commitment, call ledger, outcome key,
  split report, row, label, resource, or hash fails closed;
- token imbalance blocks before outcome access and cannot be overridden through
  the public API;
- synthetic/no-call rehearsal uses a distinct schema and cannot produce a formal
  result or claim;
- focused and compatibility tests pass, and a read-only graphical page explains
  the pre-outcome resource gate, private outcome join, frozen metrics, and result
  commitment.

## Claim boundary

Passing M56.4 proves only that a future already-authorized and already-committed
M56 prediction matrix has a deterministic, fail-closed, resource-gated scoring
and scoped-result commitment path.  With V7/V9/M55 incomplete, current scoring
must remain denied and no formal result may exist.  This is not real-person
predictive validity, Equation V1 validity, Ours superiority, private mental
truth, a solved human-brain equation, full-pipeline readiness, or production
readiness.
