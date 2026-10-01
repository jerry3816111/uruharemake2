# M57.2 Pre-Outcome Component Prediction Capsule — Plan

Date: 2026-09-04

Status: prospective contract frozen before implementation and before any real M56 target-outcome access

Single changed variable: replace M57.1's generic five-stage plan with a concrete, sample-level, pre-outcome evidence and
prediction capsule for the perception, retrieval and state substitutions. This milestone does not alter the M56
samples, original predictions, model, hardware, decoding options, outcome, scoring, retry policy or M57 statistics.

## Problem proved before the change

M57.1 durably binds five generic stage plans to the exact M56 run, but it binds no per-sample independent evidence
manifest, no stage-specific replacement payload, no 30-row substitution schedule and no substitution prediction.
Consequently it can prove that the diagnostic idea preceded the answer, but cannot prove which concrete component
replacement preceded the answer or later populate the frozen M57 analyzer without retrospective construction.

The retained pre-change probe records five generic plans but zero concrete evidence-manifest, schedule and capsule
bindings. Current live execution remains denied at V7 0/18 + 0/18 and zero real temporal rows.

## Frozen evidence boundary

Each of the 30 M56 samples must have one source-bound record for all five M57 stages:

- `perception`: exactly two independent pre-outcome coders plus one distinct adjudicator produce an observable-input
  representation; no private mental state is labelled.
- `retrieval`: exactly two independent pre-outcome coders plus one distinct adjudicator select only history IDs that
  existed at or before the frozen cutoff.
- `state`: a source-bound observable proxy may be provided, but private transient, relationship or goal state may not
  be invented. Otherwise the stage is unavailable.
- `decision`: always unavailable in this capsule because its one-hot upper bound requires the withheld outcome.
- `realization`: unavailable unless later independent blind human surface ratings exist; it is not a pre-outcome
  behavior-distribution substitution here.

Every contribution, adjudication and stage record is content-addressed. The formal manifest must identify real
independent evidence. Author-constructed evidence is accepted only by the isolated engineering rehearsal and never
by the public formal entry point.

## Frozen generation state machine

`execute_m57_preoutcome_component_predictions(run_id)` accepts only a safe run ID. Under the same per-run lock as the
M56 scoring path, it must:

1. validate the immutable M57.1 mode and the complete pre-outcome M56 generation chain;
2. reject first execution if any M56 outcome-state artifact already exists;
3. validate the 30-row evidence manifest against the exact M56 sample order, source hashes, cutoffs and history IDs;
4. durably commit an ordered schedule before the first model call;
5. for each available perception, retrieval or state substitution, change only that named component and ask the same
   frozen Ours model under the same provider options and token budgets for a new 13-label distribution;
6. record actual prompt/completion tokens, latency, CPU, memory and Ollama duration fields with one transport attempt,
   zero retry and zero fallback;
7. durably commit the complete prediction capsule, call ledger and a hash commitment while still holding the lock.

The capsule carries the original M56 Ours distributions and every pre-outcome substitution distribution but contains
no observed label. A later result bridge may join the independently withheld outcome, create the decision upper
bound, preserve unavailable stages and invoke the unchanged M57 analyzer.

## Engineering acceptance

- public execute and validate functions accept only `run_id`; no evidence, provider, outcome, readiness, authorization,
  retry or resource injection;
- a temporary forged 30-row run can execute 90 mocked single-attempt calls (three available stages per sample), commit
  the ordered schedule before calls and produce a complete immutable capsule without outcome access;
- the public formal entry rejects the identical author-constructed evidence before a call;
- missing, duplicate, post-cutoff, non-independent, non-adjudicated, private-state, outcome-key, hash-mutated and
  partial evidence fails closed;
- an outcome marker before first execution prevents schedule creation and model calls;
- prompt/source, stage, model identity, token budget, call-count, ledger and capsule mutations fail closed;
- current live state remains denied, and M57.1 plus prior selected milestone tests remain green;
- a graphical page distinguishes generic plan, concrete pre-outcome capsule and later outcome join, while labelling all
  author-constructed data as engineering-only.

## Failure and result-dependent next step

If the evidence manifest is absent or invalid, the correct result is `unavailable`, not generated proxy evidence. If a
model call, resource check or durable write fails, the run is terminal and cannot be retried under the same run ID.
M57.2 passing does not authorize M57 formal analysis or M58. M57.3 is allowed only after a valid M56.10 result exists
for a run that already contains the M57.1 mode and this complete M57.2 capsule.

## Claim boundary

Passing M57.2 establishes only a fail-closed mechanism for committing concrete, source-bound, single-component
substitution predictions before withheld outcomes. Forged fixtures prove mechanics only. It does not prove that an
annotator is correct, identify a real Uruha error, validate private mental states, validate Equation V1, show superiority
over a strong LLM, solve a human-response equation, or establish production readiness.
