# P3-B35 prospective case01 no-retry output lock

Date: 2026-09-17

## Outcome

**PASS for immutable output locking only; comparison-quality readiness is held.** The released run
completed all four source turns in both conditions before annotation access. No output was regenerated
after inspection.

- invocation intents / completed records: 8 / 8;
- terminal failures: 0;
- product provider calls: 2 (allowed 0–16);
- full-history direct provider calls: 4 (required exactly 4);
- total provider and network calls: 6 / 6;
- observed prompt / completion tokens: 2,323 / 379;
- total wall time: 43.114338 seconds;
- generation retry: none;
- annotations, confirmation and production database accessed: 0;
- ephemeral product workspace removed: yes.

The runner's frozen structural checks all reported true. A post-lock source/output-only inspection,
however, found that its shared surface predicate was too weak: it counted any Han character as
Japanese. The direct u1 output is Chinese but was therefore marked `has_japanese: true`. This does
not alter or erase the locked result. It means the result cannot yet pass the declared common Japanese
surface gate, and annotation or comparative grading remains blocked until a separate immutable audit
records the corrected outcome.

## Locked visible outputs

| Turn | Source input | Product system | Full-history direct |
|---|---|---|---|
| u1 | `房間整理到一半我就坐下來了。` | `うちは半分だけ部屋を片付けてから座ったんだね。` | `可能是整理房间累了，坐下来休息一下了。继续整理的话，要注意休息哦。` |
| u2 | `我知道要怎麼整理，只是東西太多很煩。` | `あ、そっちか。さっきは読みすぎた。今の言い方で直す。 今ほしいの、止め方と、ただ聞いてほしいのと、どっちに近い？` | `そういえば、何でも片付けるのが難しい時って、物が多すぎるから難しいんだよね。` |
| u3 | `後來我只把床清出來，其他還沒動。` | `床だけ片付けたのね。` | `うちは床だけを片付けて、他のものは動かしてないんだね。` |
| u4 | `先別給我清單，陪我嫌一下這些東西怎麼可以這麼多。` | `うん。今は質問しないで、ちょっとここにいる。そのくらいでいいだろ。` | `うちは今、何をどう整理したらいいか考えているんだね。まずは何から始めてみようか？` |

## What can already be observed without a rubric

- direct u1 violates the common natural-Japanese output requirement;
- direct u4 ignores the explicit no-checklist request and asks how to start organizing;
- product u2 notices that its earlier reading may be wrong, but introduces an unsupported
  `止め方` alternative instead of simply reflecting the stated annoyance;
- product u4 stops asking questions, but does not visibly join the requested complaint. It therefore
  should not be presented as successful felt understanding merely because it avoided advice.

These are source/output observations, not rubric scores, human preference results or a winner decision.

## Claim boundary and next gate

This is the first source-order case from the prospective developer-authored B33 batch. It was not
selected by output quality, but it is not a formal temporal holdout or human evaluation. B35 proves
that the paired generation path, accounting, restart boundary and isolation can execute once without
retry. It does not prove product advantage.

P3-B36 must bind a stricter machine-observable Japanese surface audit to the immutable B35 result,
retain the direct-u1 failure, and harden future prospective runs before any annotation is opened. The
locked B35 outputs and checkpoints must not be changed or rerun to make the gate pass.
