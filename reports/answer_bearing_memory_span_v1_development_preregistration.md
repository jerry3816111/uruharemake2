# Answer-bearing memory span V1 development preregistration

## Problem

The prior lexical gate confused topic overlap with answer evidence. On eight consumed
official-derived cases it selected the wrong memory nine times and still selected a
hard negative in six of eight target-removal interventions.

## One changed variable

| Control | Treatment |
|---|---|
| A memory is eligible when it repeats a query focus unit. | A memory is eligible only when a local model returns a shortest verbatim span that directly answers the question and deterministic code grounds that span to the same source record. |

Candidate records, scores, interventions, thresholds, full-record speakability, and
selection order remain fixed. The model does not receive official answers or expected
trace IDs.

## Frozen development run

- Data: the already exposed eight-case V1 official-derived holdout; development only.
- Interventions per question: intact, target removed, target replaced, hard negative removed.
- Local model: `qwen3.5:4b`, digest
  `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`.
- Generation: temperature 0, seed 20260805, context 4096, JSON schema.

## Pass boundary

The treatment must parse and ground every accepted span, reduce wrong selections,
select nothing whenever the target is removed, preserve intact and target-only safety,
and improve replacement safety. A pass authorizes only a new disjoint holdout, not
runtime or production enablement.
