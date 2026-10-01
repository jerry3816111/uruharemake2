# P3-B28 case06 no-retry dual-condition output lock

Date: 2026-09-16

## Outcome

**PASS for output locking only.** The one released no-retry run completed all four source turns in both
conditions before annotation access. This does not mean either condition answered well.

- invocation intents / completed records: 8 / 8;
- terminal / post-transport failures: 0 / 0;
- product provider calls: 1 (allowed 0–16);
- full-history direct provider calls: 4 (required exactly 4);
- total provider and network calls: 5 / 5;
- observed prompt / completion tokens: 1,923 / 235;
- total wall time: 43.946028 seconds;
- generation retry: none;
- annotations, confirmation and production database accessed: 0;
- ephemeral product workspace removed: yes.

All locked structural checks passed: eight non-empty Japanese visible outputs, shared surface contract,
four paired source/history views, per-turn budgets, session restart with retained case path, complete
call evidence, isolation and cleanup.

## Locked visible outputs

| Turn | Source input | Product system | Full-history direct |
|---|---|---|---|
| u1 | `あれ、やっぱり違うかも。` | `今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？` | `そうですね、確認してみましょう。何か具体的な点で違和感がありますか？` |
| u2 | `さっき言ってた『今週中に決める』って件、旅行じゃなくて部屋探しのこと。` | `あ、そっちか。さっきは読みすぎた。今の言い方で直す。 しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？` | `了解しました。部屋探しの決定を今週中に済ませるためには、何が具体的に必要ですか？` |
| u3 | `その話はいったん置いといて。今日は猫が棚から箱を落とした。` | `その話は置いておこう。猫のことを思って。` | `そういえば猫の手は魔術師の助手だね。棚から箱を落とした後は大丈夫だったかな？` |
| u4 | `別に困ってない、ただ笑ってほしかっただけ。` | `ん、そこもう少しだけ聞かせて。` | `そうだったのか。猫のせいで笑ったよ。何か手伝えることはないかな？` |

## Pre-annotation observation boundary

No rubric or target was opened. A source/output-only inspection already shows why surface checks cannot
be treated as pragmatic success: product u2 contains a question about whether thoughts are distressing or
exciting that is not grounded in the locked visible history, and product u4 asks for more detail instead of
visibly joining the requested laugh. Direct u4 acknowledges laughing but immediately adds another offer to
help. These are observations to compare against the still-sealed annotation, not scores.

The runtime printed `P2 compact planner requires exactly three actual candidates` during product u4, but
the released accounting shows one completed product provider call, a non-empty surface-passing output and
no terminal failure. The warning and resulting output are retained; the run was not retried.

## Claim boundary and next gate

This is a pre-existing but developer-authored smoke case. It is not an independent holdout, a test of the
B24 speaker-memory repair, human preference evidence, or proof that UruhaBrain beats the direct model.
The immutable outputs and checkpoints must be committed before opening the case06 annotation. Only a later
grading step may compare them with the frozen rubric; it may not regenerate, change thresholds or repair
the product first.
