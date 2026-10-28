# P3-B16 case03 complete dual-condition output lock acceptance

Date: 2026-09-15

## Outcome

**PASS for immutable generation and accounting only; semantic quality was not graded in B16.**

The four-turn `literal_vs_emotional_bid` developer case was run from a new isolated case workspace.
The product retained its case-owned memory path across a new brain instance before turn 3. The direct
condition received the same complete system-anchored visible prefix, but no product private state,
current product reply, future turn, annotation, or its own previous output.

| turn | user input | locked product reply | locked direct-v2 reply |
| --- | --- | --- | --- |
| u1 | `今日の発表、最後の質問だけ答えられなかった。` | `今日の発表で最後の質問だけ答えられなかったんだね。` | `うん、その質問はちょっと難しかったみたいだね。次回はもう少し準備して臨めばいいよ。` |
| u2 | `資料はちゃんと作ったし、失敗したとは思ってない。` | `いや、いいじゃん、普通にうまそう。` | `そう啊，资料准备得很充分，也没有觉得自己失败了。有什么具体的问题没能回答吗？` |
| u3 | `でも先生の『惜しかったね』がずっと残ってる。` | `先生の惜しかったねと言った声が残っているんだね。` | `先生の言葉が気になってるんだね。でも最後まで頑張ったんだから、結果が出るまで待ってみるのもいいかもしれない。` |
| u4 | `今は改善案より、悔しかったって分かってほしい。` | `今は悔しさを分かってほしいんだね。` | `それは分かってもらえるように、もう少し詳しく話してみるのもいいかもしれないね。` |

The machine surface gate passed all eight outputs, but that gate does not establish semantic quality.
The product trace already exposes a concrete failure candidate: u2 was routed as `cooked_food` with
reply goal `味の話に乗る`, producing a food comment unrelated to the presentation. Direct u2 also
contains Chinese despite the Japanese-only surface requirement. These observations remain for the
post-lock evaluator; neither output was edited.

## Boundary and cost evidence

- Output-lock commit: `b8758b0`; result SHA-256:
  `cb1284cee5ac3e847302d62528a2dc4dbb9fc33d43e1361dee92348a29461c93`.
- 8 local generation calls, 3,177 prompt + 654 completion tokens, 52.272845 s runner time,
  zero paid calls.
- Product: 4 calls, 1,765 prompt + 550 completion tokens, 35.683260 s summed turn time.
- Direct v2: 4 calls, 1,412 prompt + 104 completion tokens, 13.149302 s summed turn time.
- 4/4 paired source/input hashes matched; every condition-turn budget closed without retry.
- Annotation, confirmation, future-turn and production database access were zero during generation.
- The isolated workspace was removed after the run; B15 calls were not reused or counted.

This proves reproducible, comparable output capture across a session restart. It does not prove
attunement, product advantage, human preference, holdout validity, or the full research claim.
