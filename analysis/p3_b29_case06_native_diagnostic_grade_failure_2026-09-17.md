# P3-B29 case06 native diagnostic grade

Date: 2026-09-17

## Outcome

**INCONCLUSIVE RETAINED.** The released blind AB/BA diagnostic stopped after the first invalid received
judgment, as preregistered. It was not retried.

- completed valid judgments: 5 / 8;
- grading coverage: 62.5% (required at least 95%);
- invocation intents / completed records / post-transport failures: 6 / 5 / 1;
- accounted judge provider and localhost network calls: 6 / 6;
- judge prompt / completion tokens: 4,418 / 1,512;
- judge wall time: 82.513994 seconds;
- failed item: `p3-smoke-06-u3:BA`;
- failure: received JSON used a `reply_quote` that was not an exact substring of the corresponding locked reply;
- generation rerun, judge retry, output mutation, confirmation or production access: none.

B28 remains a valid immutable output lock: its SHA-256 is still
`f4efe1a3efaf522691d9fa9615b5f561ca31e1396b0c08a220d4a6a610af2b8b` and all generation checks remain
passed. B29 failed only as a complete grading result.

## Why the partial numbers cannot decide a winner

The five accepted rows produced three mapped ties, one product preference and one direct preference. Only
u2 had both AB and BA judgments agree; u1 changed between tie and direct when order changed, and u3 has only
one valid order. The provisional means happen to be equal on all four dimensions, but they cover neither a
complete order-balanced case nor u4. Reporting those means as a result would hide the failed coverage and
order gate.

The source/output-only observation made before annotation access also remains relevant but ungraded:
product u2 appended an unrelated distress-versus-excitement question, while product u4 asked for more detail
instead of joining the requested laugh. The blind judge tied both u2 replies and never reached u4. This is a
warning about evaluator sensitivity as well as product behavior, not permission to alter the frozen rubric
or rerun B29.

## Next bounded change

The failure was not a malformed generation reply and not a transport failure. It exposed a judge-output
contract weakness: the JSON schema can require a non-empty string but cannot currently guarantee that the
model copies an exact span. The next task may harden the **future-case** native judge schema by binding
`reply_quote` to an exact supplied reply value (or another deterministic exact-span mechanism), test that
the validator still rejects invented evidence, and freeze the change prospectively. B29 must remain
inconclusive and must not be completed by retrying its failed item.

This developer-proxy failure is not human preference, formal holdout evidence or proof for or against an
overall UruhaBrain advantage.
