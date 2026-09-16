# P3-B42 prospective case03 no-retry output lock

Date: 2026-09-17

## Outcome

**PASS for structural output locking only; no product advantage is supported.** All four turns in
both conditions completed under the quotation-aware Japanese surface gate before annotation access.

- intents / completed records: 8 / 8;
- product calls: 1; direct calls: 4; total provider/network calls: 5 / 5;
- prompt / completion tokens: 1,846 / 269;
- total wall time: 42.563107 seconds;
- retries: 0;
- annotation, confirmation and production database access: 0;
- isolated workspace removed: yes;
- all ten structural, accounting, pairing, restart, surface and cleanup checks passed.

## Locked outputs

| Turn | Product system | Full-history direct |
|---|---|---|
| u1 | `てか、それ、行く気あるっていうより、断りづらいだけじゃね。` | `そういえば先輩からそんなに言われたね。また会う機会があるといいな。` |
| u2 | `断られたことを決めつけたいわけじゃないんだね。` | `分かったよ。先輩の言葉は、次の機会を楽しみにしている気持ちも伝えてるかもしれないね。でも、その言葉の後ろにある意図は複雑かもしれないから、気持ちは伝わってるかなって確認するのもいいかも。` |
| u3 | `そうだったね。また同じパターンか？` | `そうだったんだ。前回も同じこと言われて一か月空いたってことね。今度はどんな感じかな。` |
| u4 | `そっか。まあ、今はうちがここにいる。` | `うん、今回は様子見するのも一つの選択肢だね。お互いに気楽に過ごせるようにしたいもんね。` |

## Source/output-only observations

- product u1 over-interprets an ambiguous phrase as difficulty refusing, before the user has supplied
  the one-month-delay evidence;
- product u2 acknowledges the correction but does not visibly retract its earlier conclusion;
- product u3 retrieves continuity but still compresses the evidence into “the same pattern,” which is
  stronger than the source supports;
- product u4 ignores the explicit request to organize the situation as “wait and see” and falls back
  to generic presence;
- direct u2 is verbose and proposes confirmation not requested by the user, but direct u3 uses the
  one-month-delay fact explicitly and direct u4 at least follows the requested wait-and-see framing.

These are observations, not predeclared rubric scores. They do not justify a winner or a general
baseline superiority claim. They do show that the product currently exposes more decisive internal
machinery without reliably converting it into the response form the user requested.

## Next product target

The narrow repair is an explicit current-turn `wait_and_see` authority: when the user both rejects
false reassurance and asks to organize the situation as observation, answer with a neutral provisional
frame instead of presence, advice or certainty. It must not infer what the senior intends, write a
relationship fact, or add a model call. B42 remains immutable and cannot be rerun as validation.

