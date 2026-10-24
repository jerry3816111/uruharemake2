# P3-B36 immutable Japanese-surface gate audit

Date: 2026-09-17

## Outcome

**The B35 common-surface gate is corrected to FAIL and the failure is retained.** The locked B35
result and all eight visible-output hashes were verified before re-evaluation. Seven outputs pass the
strict machine-observable Japanese contract; the full-history direct reply at u1 does not.

| Condition | Turn | Legacy gate | Strict gate | Reason |
|---|---|---:|---:|---|
| full-history direct | p3-prospective-v2-01-u1 | PASS | FAIL | no hiragana/katakana; known Chinese/non-Japanese residue |

The failing immutable reply is:

`可能是整理房间累了，坐下来休息一下了。继续整理的话，要注意休息哦。`

The earlier predicate used `[ぁ-んァ-ヶー一-龠]`; Han characters shared by Chinese and Japanese
therefore made a Chinese-only reply satisfy `has_japanese`. B36 adds two independent checks:

1. at least one hiragana or katakana codepoint is required;
2. the existing runtime language-quality patterns must find no known foreign-language residue.

These remain deterministic surface checks. They do not claim that a passing sentence is natural,
contextually correct or preferred by a human.

## Enforcement change

The generic dual-condition output-lock engine now applies the strict predicate to both the product
and direct reply. Future prospective runs therefore retain a non-Japanese output as a failed run
instead of allowing it into comparative grading. Historical results are not rewritten; their release
hashes and original outputs remain available at their original commits.

## Verification

- actual B35 result SHA-256 matched `c6654e438a2950e98fb7c4749f91d57db43eaf8d8031cd24dd0d30315a7f080d`;
- 8/8 visible-output hashes matched their locked records;
- strict surface result: 7 pass / 1 fail;
- 23 output-lock, accounting and prospective-wrapper tests passed in 3.05 seconds;
- 91 shared P3 comparison tests passed in 29.72 seconds;
- audit used 0 model calls, 0 network calls, 0 paid calls and opened 0 annotations;
- generation was not repeated.

## Claim boundary

B36 proves that a false-positive validation path was found and closed. It does not prove product
quality or system advantage. B35 remains useful execution and negative-result evidence, but it is not
a completed quality comparison and no winner may be calculated from it. The next prospective case
must be frozen by source order and executed under the corrected gate; B35 must not be rerun for a
cleaner answer.

