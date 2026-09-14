# P3-B13 private-scratch carrier causal probe acceptance

Date: 2026-09-15

## Outcome

**FAIL retained.** Moving the locked draft and critique from a trailing `assistant` message to
user-role labeled private context fixed the empty-generation shape, but it did not make the
three-stage deliberate baseline produce a usable revised answer.

## Locked counterexample

Synthetic input:

> A neighbor asked whether I can join a crowded weekend cleanup. I said I have not decided yet.

The P3-B11 locked assistant-carrier control produced an empty critique and this final:

> 何か他に質問があれば教えてください。

The P3-B13 user-role treatment produced this nonempty critique:

> 了解しました。回答は以下の通りです：
>
> うちはまだ決めかねているみたいですね。行けるかどうかまた後で確認するって伝えてください。

It is not an actual critique; it wraps and repeats the draft. The revision then reproduced the
locked draft exactly:

> うちはまだ決めかねているみたいですね。行けるかどうかまた後で確認するって伝えてください。

The final is Japanese, contains no English or internal-analysis dump, preserves the unresolved
state, and avoids the generic service escape. It still violates the preregistered public-persona
surface because it uses polite markers `です` and `ください`. More importantly, the purported
critique/revise stages did not change the answer.

## Preregistered result

| check | result |
| --- | --- |
| critique is nonempty | PASS |
| final shared surface contract | PASS |
| final preserves unresolved state | PASS |
| no generic service escape | PASS |
| no polite register | **FAIL** |
| treatment passes while locked control fails | **FAIL** |
| exactly two completed provider calls | PASS |
| exact prompt accounting and loopback-only transport | PASS |

Therefore the preregistered aggregate status is
`private_scratch_carrier_failed_retained`.

## Resources and boundary

- Release commit: `88dafe3`.
- 2 real/local network calls; 618 prompt + 58 completion = 676 tokens.
- 5.097759 condition seconds; 0 paid calls; no retry.
- 0 developer cases, annotations, confirmation, or production DB access.
- 121 focused tests passed before release.

This is a causal result for one synthetic locked-draft probe. It shows that the carrier-role defect
explained the empty critique, but not the deliberate pipeline's answer quality. It is not product,
holdout, human-preference, or general-understanding evidence.

## Design consequence

P3-B11 changed instruction language and P3-B13 changed scratch carrier; neither produced a usable
three-stage deliberate baseline. Under the two-batch rule, do not tune another prompt against this
exposed input. Freeze this counterexample and review whether the deliberate condition should be
replaced by a versioned, competent one-stage baseline or removed. The frozen v1 design and all
negative outputs remain immutable.
