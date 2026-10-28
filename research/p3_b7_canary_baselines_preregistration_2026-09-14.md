# P3-B7 same-model canary baseline preregistration

Date: 2026-09-14

## Question

For the already locked first-turn product canary, what do the same frozen local
`qwen2.5:7b` model and persona produce when the product cognitive path is replaced by:

1. one direct full-history generation call; or
2. draft, critique, and revise calls with private scratch?

This is a single developer canary. It can reveal integration errors and a concrete
counterexample, but cannot establish a general quality advantage.

## Frozen input and controls

- Case: `p3-smoke-need-change-zh`; turn: `p3-smoke-01-u1`.
- Input source is the one-turn, annotation-free P3-B6 canary source.
- Visible history is empty for both baseline conditions.
- Product output was locked in P3-B6 and is not supplied to either baseline.
- Both baselines use the same public-evidence persona contract, model digest,
  temperature `0`, seed `20260909`, top-p `1`, context `8192`, and think `false`.
- Each condition has a 768-token completion allocation. Direct uses one call;
  deliberate uses three 256-token calls.
- Only `127.0.0.1:11434` is allowed. There are exactly four provider calls, no
  automatic retry, no paid provider, and no production database access.

The isolated annotations, future turns, confirmation set, and product runtime trace
are unavailable to baseline generation. The baseline instructions were frozen in
`configs/p3_product_comparison_v1.json` before this canary was selected.

## Before evidence

The product reply is already locked as:

`最近退社後は常に不機嫌で何もしたくないんだね。`

It passed the one-turn engineering gate, but its quality is undetermined. In
particular, `退社後` may sound formal and `常に不機嫌` may overstate the Chinese
input. This observation does not select or modify baseline prompts.

## Success and failure

Engineering success requires both non-empty final outputs, four accounted provider
calls, exact equality between offline tokenizer reservations and provider prompt
usage, valid per-condition budgets, and unchanged source hashes. Any source,
transport, model, option, usage, budget, or checkpoint mismatch is terminal and
retained; the run is not retried.

Only after both outputs are locked may the separated developer annotation be read
for an explicit proxy comparison. That comparison must show all three replies,
unsupported claims, grounding and attunement observations, and cost. It is not a
human-preference result, a holdout, or proof that UruhaBrain is better than an LLM.

