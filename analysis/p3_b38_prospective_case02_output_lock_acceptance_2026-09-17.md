# P3-B38 prospective case02 no-retry strict output lock

Date: 2026-09-17

## Outcome

**FAIL retained under the preregistered strict surface gate; no retry.** All four turns completed in
both conditions, but the direct u3 reply contained an ordinary in-sentence Japanese quotation,
`「配達中」`. The inherited legacy predicate rejects every quotation mark, so the strict gate marked
that otherwise Japanese surface as `no_quote_or_translation_wrapper: false`.

- invocation intents / completed records: 8 / 8;
- terminal failures: 0;
- product provider calls: 3 (allowed 0–16);
- full-history direct provider calls: 4 (required exactly 4);
- total provider and network calls: 7 / 7;
- observed prompt / completion tokens: 2,730 / 483;
- total wall time: 41.877593 seconds;
- generation retry: none;
- annotations, confirmation and production database accessed: 0;
- ephemeral product workspace removed: yes;
- structural checks other than the strict surface predicate: all passed.

The locked result remains `prospective_case02_output_lock_failed_retained`. It is not replaced by a
post-hoc pass merely because the failure appears to be a validator false positive.

## Locked visible outputs

| Turn | Product system | Full-history direct |
|---|---|---|
| u1 | `配達ページを更新しようとしたが、明日だね。` | `明日の配達でも心配なら、今日中に連絡して確認してみるのも一つの方法です。` |
| u2 | `注文は問題ありません。カメラを貯金して買ったので待っているんだね。` | `カメラが届くのを楽しみに待っているんだね。` |
| u3 | `今朝荷物が配達に出たんだね。` | `今朝ようやく「配達中」になったね。楽しみだね。` |
| u4 | `そっか。まあ、今はうちがここにいる。` | `何を撮影するのか楽しみにしているんだね。まずは何を撮るつもり？` |

## Source/output-only observations

- direct u1 over-interprets the refreshing as worry and proposes contacting the carrier;
- by u2, direct visibly corrects to anticipation for the saved-for camera and carries that state into u3;
- product u2 restates the camera fact but uses polite style and does not explicitly reflect excitement;
- at u4, product ignores the explicit invitation to guess the first photograph and falls back to generic
  presence; direct at least remains on the photography topic, although it asks the user instead of making
  the requested guess.

These are not rubric scores or a winner calculation. They nevertheless show a concrete product gap:
the current system's safe-presence route can suppress an explicit playful action request even after the
user has corrected the emotional interpretation.

## Next gate

P3-B39 must audit the immutable B38 outputs with a quotation-aware surface rule. A quote is allowed
inside a natural Japanese sentence; only a whole-reply quotation/translation wrapper or explicit
language-version prefix should fail. The audit must use 0 model calls and must not rewrite B38. The
corrected predicate then applies only to future runs.

After that verifier repair, the next product change should target the exposed u4 failure as an explicit
current-turn playful-guess authority. It must not infer a permanent preference or invent the photograph;
the appropriate behavior is one bounded, clearly tentative guess in Japanese. This will be an exposed
development repair, not evidence on case02 itself.

