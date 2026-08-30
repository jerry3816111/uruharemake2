# M13 Published Pragmatics Benchmark Plan

Date: 2026-08-17  
Status: preregistered before reviewing selected case content or generating outputs

## Why this is the next necessary step

M12 showed that the current synthetic behavior equation does **not** replicate an
advantage over the strongest structured-history LLM baseline.  The public Uruha
temporal track cannot yet produce formal truth labels without violating its
manual, two-coder protocol.  M13 therefore tests one narrower organ of the
research system—pragmatic interpretation—on an existing published benchmark
with public answer keys.

PUB defines pragmatics through implicature, presupposition, reference, and
deixis.  M13 uses four tasks closest to the project's operational claim:

- indirect-answer interpretation;
- sarcasm versus agreement;
- dialogue presupposition validity;
- deictic reference resolution.

## Controlled comparison

All conditions receive the same item, deterministically permuted options, local
`qwen3.5:9b`, decoding parameters, and maximum generation budget.

1. `B0_DIRECT`: answer immediately.
2. `B1_GENERIC_DELIBERATION`: generic careful reasoning with a counterargument.
3. `OURS_PRAGMATIC_LOOP`: explicitly separate literal content, pragmatic target,
   context evidence, and an alternative interpretation before answering.

The primary comparison is Ours versus the stronger generic-deliberation control,
not Ours versus the easiest baseline.  Sixty-four items are selected by frozen
hash ranking.  IDs 0 and 1 are excluded because their content was seen during
source-schema inspection.

## Locked success and failure rule

Success requires all of the following:

- 100% parse validity in every condition;
- Ours minus B1 accuracy at least +5 percentage points;
- exact paired McNemar p at most .05;
- no task-specific Ours regression larger than 12.5 points.

The report must retain a failed or null result.  It will also show 20,000-repeat
paired bootstrap intervals, task-level errors, prompt/completion tokens, and
latency.

## Evidence boundary

This is not the exact score reported in the PUB paper: M13 uses project-specific
prompts and one frozen option permutation.  A public benchmark may also have
appeared in base-model pretraining.  A pass would support only the narrow claim
that explicit pragmatic decomposition improved these held-out PUB decisions for
this model.  It would not prove a human-brain equation, long-term person
understanding, felt understanding, or Uruha fidelity.
