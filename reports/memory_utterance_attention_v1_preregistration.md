# Memory Utterance Attention V1: Preregistration

## Research question

When the correct session has already been retrieved, can UruhaBrain preserve the
user's relevant utterance and the answer-bearing value more reliably by separating:

1. query-aware utterance selection,
2. grounded fact extraction,
3. typed answer proposition,
4. surface realization?

This tests an architectural mechanism, not memorization of benchmark answers. The
36 cases contain no official LongMemEval question or answer.

## Frozen data boundary

- 12 source scenarios: 6 development and 6 internal transfer scenarios.
- Each scenario is rendered with evidence at beginning, middle, and end.
- Total: 36 cases.
- Development and transfer use disjoint people, objects, values, and wording.
- The transfer split is still an internal diagnostic, not an external heldout claim.
- Frozen dataset SHA-256:
  `513c4eb42de97abdb451989df6635b1c55d0fa91c40197360b189a54132a4a19`.
- Frozen semantic-cases SHA-256:
  `5347f700c48477b05655804cf88b73e8ad7d3daa56fefc9abd16d1e711f81d15`.

## Matched conditions

| Condition | Session reading | Final answer | Single changed component |
| --- | --- | --- | --- |
| Full session + freeform | Full retrieved session | Existing freeform answer | Control |
| Utterance attention + freeform | Top query-aware user utterances | Same freeform answer | Utterance attention only |
| Utterance attention + proposition | Same selected utterances | Source-anchored typed proposition | Answer contract only |

All conditions use the same model tag, resolved model digest, seed, temperature,
context limit, question frame, evidence schema, ledger logic, and scoring code.

## Why this mechanism is plausible

- LongMemEval exposes both session-level and turn-level evidence, and its official
  repository supports turn or session retrieval granularity.
- Long-context models can lose relevant facts in the middle of context, so simply
  supplying more text does not prove that the fact will be used.
- Content selection, content planning, and surface realization are separable NLG
  stages. A typed proposition makes the semantic handoff observable before style is
  applied.

Sources:

- https://github.com/xiaowu0162/LongMemEval
- https://arxiv.org/abs/2307.03172
- https://xinyuhua.github.io/Resources/emnlp19/

## Metrics fixed before implementation

Primary metrics:

- exact recall of the gold evidence utterances,
- presence of every required answer span,
- correct yes/no or change relation,
- whole-case semantic pass,
- position-invariant pass across beginning/middle/end.

Integrity metrics:

- structured parse rate,
- evidence quote grounding rate,
- proposition span grounding rate,
- empty response rate,
- latency and token use.

Paired differences use exact McNemar tests and paired bootstrap confidence
intervals. Results are also reported separately for development, transfer,
capability family, and evidence position.

## Decision gates

The mechanism is not eligible for a future runtime heldout unless all of these are
true in this development experiment:

1. Frozen hashes match.
2. Every admitted evidence quote is grounded in its source session.
3. Every valid proposition span is verbatim-grounded in its source quote.
4. Neither development nor transfer semantic pass is lower than its matched control.
5. No capability family regresses.
6. Position invariance does not regress.

Passing these gates still does not authorize a runtime change. It only permits a
separate, untouched transfer or heldout evaluation. The previously consumed
LongMemEval heldout is explicitly excluded from tuning and reruns.
