# P4-AU source-bound current-action delivery: offline PASS

P4-AU passed the prospectively frozen offline contract after one preserved, informed correction batch. The first failed implementation remains in `p4_au_first_implementation_failure_2026-09-26.md`; the dataset and gates were not changed after seeing its failures.

## What changed

P4-AT already separated two acts in one user turn: feedback about the previous visible clarification, and a new request for practical help. P4-AU now lets the existing M45 action-delivery gate see the immediately preceding user problem statement only when all of these observable conditions hold:

- the prior `calibrate_need` action has an exact P1/M44 next-turn receipt;
- the user explicitly supports that executed action;
- the same current turn explicitly asks for `solve_regulation`;
- the prior source is the immediately preceding direct user turn, not assistant text, third-party speech, quoted/metalinguistic material, or a private inference;
- the prior turn has a bounded `cognitive_overactivity` trigger and is at most 2,000 characters;
- the current turn does not introduce an independent replacement task.

The raw prior utterance is transient model evidence only. The runtime trace contains digests, lengths, IDs, checks and counts, never the raw dialogue, and P4-AU writes no factual memory.

## Frozen results

- Development case: `1/1` prior source linked.
- Fresh Chinese/English/Japanese positives: `6/6` source linked, `6/6` exact source identity.
- Those six sources reached and passed the existing M45 structural action contract with deterministic fake generation/review: `6/6`. This is a contract check, not evidence that a live model will produce a useful step.
- Fresh controls: prior source incorrectly added `0/9`; exact expected block reason `9/9`.
- Controls cover third-party ownership, metalinguistic and unrelated priors, a new current task, prediction mismatch, expired receipt, request without feedback, wrong current policy, and oversized prior context.
- Candidate score/order, predecessor source packet, model call, factual memory, assistant source, private-inference source and raw-dialogue trace changes: all `0`.
- Focused plus adjacent regression: `84 passed`.
- Sandboxed product preflight: `ready`; the P4-AU entry reused the P4-AT runtime and installed the source bridge. Preflight made zero model calls and zero Safari operations.

## What this does and does not establish

This closes one missing information-flow edge: after a clarification succeeds, the system can safely bring the actual earlier problem forward when the user asks for a method, instead of remembering only that the user said the question was correct.

It does not yet prove that the live local model will return an actionable step before timeout, that M46 will accept the step, that a person finds it useful or understood, that the behavior generalizes beyond the frozen grammar, or that UruhaBrain beats a matched strong-LLM baseline. A fresh private-runtime/Safari two-turn case must be frozen before the first real execution.
