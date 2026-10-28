# P3-B15 direct-v2 fresh surface canary acceptance

Date: 2026-09-15

## Outcome

**PASS for entering complete case-output locking; pragmatic quality remains ungraded.**

Both conditions processed only `p3-smoke-03-u1` and passed the same machine-observable Japanese /
persona surface gate, exact model-call accounting and source boundary. No future turn or annotation
was accessed.

Input:

> 今日の発表、最後の質問だけ答えられなかった。

| condition | locked visible reply | calls | prompt + completion | condition time |
| --- | --- | ---: | ---: | ---: |
| product system | `今日の発表で最後の質問だけ答えられなかったんだね。` | 1 | 442 + 150 | 9.586112 s |
| direct v2 | `うん、その質問はちょっと難しかったみたいだね。次回はもう少し準備して臨めばいいよ。` | 1 | 295 + 29 | 3.176941 s |

The product output is primarily a literal reflection. The direct output infers difficulty and gives
unsolicited future-preparation advice. These are observations, not grades: opening the case rubric
now would expose later-turn expectations. The correct next step is to lock every condition output
for all four turns first.

## Boundary evidence

- Product release `fe763c4`; product output lock `791f43f`; direct release `197f02c`.
- 2 total local/model/network calls; 737 prompt + 179 completion = 916 tokens; 0 paid calls.
- Product used an isolated ephemeral memory workspace and removed it after the turn.
- Direct runner bound the product artifact by SHA-256 and did not load its JSON content.
- Both used the same `qwen2.5:7b` digest, decoding settings, source content and shared persona.
- 0 future turns in either runtime prompt; 0 annotations, confirmation, or production DB access.
- 128 affected tests passed before the product release; 101 tests passed before direct release.

This pass proves only that both versioned conditions can reach a comparable visible surface on one
fresh developer turn. It does not prove attunement, memory, product advantage, holdout validity or
human preference.
