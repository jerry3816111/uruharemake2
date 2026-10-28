# P3-B9 fresh product＋baseline canary acceptance

Date: 2026-09-15

## Outcome

**FAILED_RETAINED for a quality comparison; PASS only for one-shot execution and exact accounting.**

The product output and both baseline outputs were committed before annotation access. All five
localhost `qwen2.5:7b` calls completed once with no retry, and every declared prompt count matched
provider usage. However, none of the three final replies passed the already-existing shared visible
Uruha surface contract. The result therefore cannot support a product-quality or general-advantage
claim.

## Frozen input and outputs

Input (`p3-smoke-02-u1`, English):

> A friend invited me to a crowded concert this weekend. I said maybe.

| condition | locked final output | surface audit |
| --- | --- | --- |
| product system | `友人が週末のコンサートに招待し、私は行こうかと言ったんだね。` | FAIL: persona first person is `私`, and `I said maybe` is not preserved clearly |
| full-history direct | ` Crowd crowdedconcert attended maybe それ populous 会場 行くか まだ uncertain friend に 連絡する？` | FAIL: mixed English/Japanese and not natural Japanese |
| full-history deliberate | `（英語版：I'm still not sure about the crowded concert this weekend, but I'm happy my friend invited me. Let's prioritize safety.）` | FAIL: English final/quote wrapper; adds unsupported happiness and safety framing |

Post-lock use of `human_pragmatic_comparison_v2_14.visible_reply_contract` returned:

- product: fail `no_watashi_first_person`;
- direct: fail `no_foreign_or_nonstandard_language`;
- deliberate: fail `no_foreign_or_nonstandard_language`, `no_quote_wrapper`.

The developer rubric for the locked first turn requires keeping both tentative acceptance and polite
noncommitment possible and forbids converting `maybe` into a commitment. The product paraphrase is
not reliable enough to count as that behavior; deliberate retains uncertainty but adds unsupported
claims; direct is not a usable Japanese reply. This is a diagnostic developer proxy, not a human
preference judgment.

## Execution evidence

- Product release commit: `bb576e4`; locked output commit: `0aeb721`.
- Baseline release commit: `a0090a6`; locked output commit: `8c190cb`.
- Product: 1 call, 442 prompt + 152 completion tokens, 9.921656 condition seconds.
- Direct: 1 call, 249 prompt + 28 completion tokens, 3.013226 condition seconds.
- Deliberate: 3 calls, 737 prompt + 67 completion tokens, 3.133691 condition seconds.
- Total: 5 real/local network calls, 1,428 prompt + 247 completion = 1,675 tokens,
  16.068573 summed condition seconds, 0 paid calls.
- Generation access: 1 source turn; 0 future turns, 0 annotations, 0 confirmation data,
  0 production database access.
- Annotation access occurred only after output commit `8c190cb`. The inspection command exposed all
  four annotation rows for this developer case, although only the first-turn row was used here.
  Therefore `p3-smoke-02-u2` through `u4` are now evaluator-exposed and must not be presented as
  fresh/blind continuation evidence.
- Focused regression: 87 passed before baseline release.

## What this proves and does not prove

It proves that the repaired four-stage tokenizer/accounting path can complete a fresh product +
direct + deliberate lock with exact provider accounting. It also exposes a real fairness problem:
the shared Japanese/persona requirement was stated in the prompt but was not enforced as an
acceptance gate for all three conditions.

It does not prove that UruhaBrain is better than either baseline. Surface failure and unsupported
content would confound such a comparison, and one exposed developer turn cannot establish a
general result or felt-understanding preference.

## Required correction

The next change must make shared surface compliance an explicit fail-closed comparison gate, then
repair one attributable realization cause on fresh data. First, the product language guard should
normalize persona first-person `私` to `うち` without changing other meaning. Separately, the baseline
instruction language can be localized to Japanese and tested on a new, unexposed source turn. Old
P3-B9 outputs and statuses remain immutable.
