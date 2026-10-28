# P4-R Multi-turn Interference Comparison

Status: **PASS**

## Question

After a preference is written and later corrected, can the released typed-state
mechanism keep the correct current value when the next 12 turns contain recent
but misleading mentions from another speaker, a quotation, a hypothetical and
another preference scope?

This is a mechanism question. The comparison baseline is deliberately named a
**recent-five-turn lexical diagnostic**, not a strong LLM. It sees the identical
transcript and picks the latest visible token ending in `茶`, but it has no
speaker, quotation, negation or typed-state representation.

## Exact result

| Recall | Correct state | Lexical diagnostic | P4 typed state |
|---|---|---|---|
| Turn 6 | `月桃茶` | `紫蘇茶` from quoted turn 4 — wrong | `月桃茶` — correct |
| Turn 12 | `よもぎ茶` | `紫蘇茶` from friend turn 11 — wrong | `よもぎ茶` — correct |

The visible system surfaces were exactly:

> 今の飲み物の好みは月桃茶。前のじゃなくて、今の方ね。

and, after the explicit correction:

> 今の飲み物の好みはよもぎ茶。前のじゃなくて、今の方ね。

The frozen gate passed with **0 failed gates**. System exact recall was **2/2**;
the diagnostic baseline was **0/2**, a difference of **+100 percentage points**
on this single frozen case.

## What actually changed inside state

- Turn 1 wrote one active `drink=月桃茶` record.
- Six non-write distractor turns produced **0** typed writes.
- Turn 5 wrote a separate `game=cooperative games` record; it remained active
  without entering either drink answer.
- Turn 8 created `drink=よもぎ茶`, linked it to the prior drink record, retained
  `月桃茶` as historical evidence, and created an explicit-negative record for
  the old value.
- At turn 12 the final profile had exactly four records: active drink 1, active
  game 1, historical drink 1 and explicit-negative drink 1.
- Recall read historical values **0** times, negative values **0** times and
  wrote the profile **0** times.
- Unverified mental-fact writes: **0**. Full user utterances were not copied into
  the typed profile.

## What this adds beyond the old 50-turn result

It does not replace the V2.22 comparison. V2.22's full-context strong-LLM
reference and UruhaBrain both scored 4/5, while UruhaBrain cost more tokens and
latency. That negative/mixed result remains valid.

P4-R answers a narrower causal question that V2.22 could not isolate: the new
typed current-state and correction lineage, by itself, resists several concrete
forms of textual interference. The next evidence layer must exercise the same
kind of interference through the complete product runtime and Safari; only
after that would another same-model/full-context comparison be justified.

## Accounting and boundary

The holdout was executed exactly once in a fresh temporary Chroma store: 0
retry, 0 fallback, 0 model call, 0 paid API, 0 production-memory access and 0
Safari turn.

This pass does not establish advantage over a strong LLM, full-product
reliability, open-domain or 50-turn memory, felt understanding, human
preference, future prediction or a human equation.
