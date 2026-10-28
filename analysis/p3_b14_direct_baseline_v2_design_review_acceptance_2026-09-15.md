# P3-B14 direct-baseline v2 design review acceptance

Date: 2026-09-15

## Outcome

**PASS for implementation readiness; no generation was authorized or executed.**

The frozen three-stage deliberate condition is retired from the versioned developer comparison.
This does not rewrite v1 or discard its negative results. It follows two attributable, locked repair
attempts:

1. P3-B11 changed stage-instruction language. Japanese improved the narrow language surface, but
   the deliberate final was an unrelated service sentence and critique was empty.
2. P3-B13 changed only the scratch carrier. Critique became nonempty, but merely copied the draft;
   revision reproduced the draft and failed the preregistered register gate.

Keeping that condition would create an artificially weak comparator. The v2 candidate is the
one-call full-history direct baseline, which was the only candidate with a locked Japanese surface
pass in B11. That evidence is not enough to call it competent, so fresh validation remains required.

## Fair comparison retained

The candidate direct control and product system receive the same raw visible history, shared
persona contract, `qwen2.5:7b` digest, temperature, seed, `top_p`, context size, local hardware and
transport. Each condition retains the same aggregate 768 completion-token ceiling. Direct uses at
most one call and product at most four; actual prompt tokens, completion tokens and latency must be
reported separately rather than described as equal.

The product's private cognitive state is the intervention. It is not copied into the control;
otherwise the component being tested would disappear. Baseline output is not written back, and the
current product reply remains hidden from the baseline. The shared Japanese/persona surface check
is a fail-closed gate, not a pragmatic-quality score.

## Next evidence gate

The next untouched developer source is `p3-smoke-03-u1`:

> 今日の発表、最後の質問だけ答えられなかった。

First lock product and direct outputs without future turns or annotations. Only if both meet the
shared surface and exact accounting gates may the remaining case turns be generated. Annotation
content stays closed until every condition output for the whole case is immutable, preventing the
later turns from becoming answer-exposed as happened for case 02.

## Resources and boundary

- 105 focused tests passed.
- 0 model calls, network calls, paid calls, annotations, confirmation, or production DB access.
- This review establishes a fair candidate design, not product advantage, baseline competence,
  holdout validity, human preference, or general understanding.
