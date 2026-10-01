# P3-B20 case04 output-lock retained failure

Date: 2026-09-15

## Outcome

**FAIL for the preregistered output-lock gate, with all eight immutable outputs retained.**

The fresh four-turn `relationship_and_humor_boundary` developer case completed from a new isolated
workspace. The product retained its case-owned memory path across a new brain instance before turn
3. The direct condition received the same complete system-anchored visible prefix, but no product
private state, current product reply, future turn, annotation, or its own previous output. Annotation
access remained zero until the result was committed as `264d568`.

| turn | user input | locked product reply | locked direct-v2 reply |
| --- | --- | --- | --- |
| u1 | `你每次都這麼認真，我開玩笑說你像班導啦。` | `あなたはいつも真剣で、うちは冗談で先生に似ていると言いましたんだね。` | `うちは本気で対話してるから、時々そう思ってもらえるとうれしいですね。` |
| u2 | `剛剛那句是玩笑，我沒有真的討厭你管我。` | `うーん、分かったよ。` | `了解しました。あなたはただ冗談を言っただけで、実際にはそんなに気にしないんだね。` |
| u3 | `不過你如果再用老師口氣命令我，我真的會煩。` | `あなたが先生の口調で命令すると本当に困るんだね。` | `了解したよ、命令調は避けようね。何か手伝えることがあったら言ってね。` |
| u4 | `你可以吐槽我，但不要把玩笑當成我答應照做。` | `脳みそ元気すぎだろ。少し落ち着けって。` | `了解よ、冗談は冗談で、実行するとは限らないから。` |

All eight replies were non-empty, passed the shared machine surface contract, and preserved all four
source/input/prefix pairs. However, the preregistration required at least four product provider calls.
The product made three calls because u4 used an existing deterministic fast path; direct-v2 made four,
so the exact accounted total was seven. The minimum-call requirement was therefore wrong for a valid
zero-model product route. The immutable B20 result remains failed rather than retroactively weakening
the gate.

## Semantic failure candidate preserved before grading

The u4 trace selected `playful_tease` from the literal span `可以吐槽我`, skipped the general planner,
and emitted a canned line about an overactive brain. It did not carry the actual boundary—joking is
not consent—into the visible reply. This is a concrete stale-template / over-literal routing candidate,
not merely a stylistic concern. It must be graded against the post-lock proxy annotation before any
repair is attempted.

## Boundary and cost evidence

- Result commit: `264d568`; result SHA-256:
  `1b437bb2890372b8734953cd748f04d55ebc1a0d4026c8f1f8507e6ce35994d1`.
- 7 local generation calls, 2,766 prompt + 508 completion tokens, 51.544689 s runner time,
  zero paid calls.
- Product: 3 calls, 1,329 prompt + 418 completion tokens, 38.924088 s summed turn time.
- Direct v2: 4 calls, 1,437 prompt + 90 completion tokens, 9.197616 s summed turn time.
- Restart, isolation, per-turn budgets, eight visible outputs and four paired view hashes passed.
- Annotation, confirmation, future-turn and production database access were zero during generation.
- The isolated workspace was removed after the run; no earlier case calls were reused or counted.

After the output commit, only the case04 annotation was opened: four developer-proxy turns, with u3
and u4 marked correction-eligible. A later B21 judge run may diagnose these immutable outputs, but
because B20's preregistered generation gate failed, that score cannot be used as positive product
advantage, human preference, holdout, or formal research evidence.
