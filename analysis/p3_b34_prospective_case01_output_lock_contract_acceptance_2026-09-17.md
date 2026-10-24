# P3-B34 prospective case01 output-lock contract acceptance

Date: 2026-09-17

## Outcome

**PASS for preregistration and zero-call preflight; generation is not yet authorized.**

B33 froze three source-only cases. B34 selected the first case by immutable source order—not by
expected quality—and projected its exact four turns into a generation-only source. The projection,
config, verifier and preflight were committed as `95cb7f6` before any output existed.

## Frozen comparison contract

- case: `p3-prospective-v2-overwhelm-company-zh`
- conditions: actual `product_system` and `full_history_direct`
- shared source: same current input and same system-anchored visible prefix for both conditions
- future-turn rule: only current and prior user turns are visible; later turns remain locked
- session boundary: restart the product brain before turn 3 while retaining the same isolated case
  memory path
- model and decoding: qwen2.5:7b, exact digest, temperature 0, seed 20260909, top_p 1,
  num_ctx 8192 and think false
- provider budget: product 0–16 calls, direct exactly 4, total at most 20
- records: 8 intents and 8 complete-or-terminal-failure records, concurrency 1, no retry
- annotations, confirmation, production database, external deployment and paid calls: forbidden

## Verification

- 18 B34, B33 and case06 adjacent tests passed in 2.85 seconds;
- all four offline paired views shared source/history hashes and excluded the current product reply;
- all four views matched B33 visible/locked-future manifests;
- qwen2.5 model digest matched and the first direct prompt had an offline count of 291 tokens;
- all 14 preflight checks passed;
- preflight used 0 generation calls, 0 network calls and 0 paid calls, and accessed 0 annotations;
- `git diff --check` passed.

## Evidence boundary

B34 is only a frozen execution contract. It does not contain outputs, scores or a claim that either
condition is better. A separate reviewed release and an intent-before-call runner are required before
one no-retry execution. If any transport, surface, budget, checkpoint or cleanup gate fails, the
partial evidence must be retained and the case cannot be graded as a complete pair.
