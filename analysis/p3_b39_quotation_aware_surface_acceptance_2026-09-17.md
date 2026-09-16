# P3-B39 quotation-aware immutable surface audit

Date: 2026-09-17

## Outcome

**PASS for validator repair; B38 remains failed and comparison-quality readiness remains false.**
The B38 result hash and all eight visible-output hashes were verified. Its single preregistered
surface failure was the direct u3 sentence:

`今朝ようやく「配達中」になったね。楽しみだね。`

Under the quotation-aware rule, all 8/8 outputs pass the machine-observable Japanese surface checks.
The original B38 status `prospective_case02_output_lock_failed_retained` is not changed.

## What changed

The first strict predicate is retained byte-for-byte for B37/B38 reproducibility. A versioned v2
predicate now distinguishes:

- allowed: an ordinary quotation inside a Japanese sentence, such as `「配達中」になった`;
- rejected: a whole response wrapped as `「今日は休め。」`;
- rejected: language-version wrappers such as `日本語版：...` or `中国語版: ...`.

The generic dual-condition engine now imports v2 for future releases. Historical release hashes still
identify the exact prior code at their commits.

## Verification

- immutable B38 result SHA-256: `10236fc37c2f87acc081a74ee326a500923429f2f9a468eef04fd06355d6a0a4`;
- output hashes verified: 8/8;
- original surface failures retained: 1;
- quotation-aware audit: 8 pass / 0 fail;
- 21 focused B39/B36/B38/engine tests passed in 2.82 seconds;
- 108 B39/B36/B37/shared P3 tests passed in 30.04 seconds;
- 0 model calls, 0 network calls, 0 paid calls and 0 annotation access;
- generation was not repeated.

## Claim boundary

B39 only closes a validator false positive. It does not upgrade B38 into a preregistered success,
open annotations, grade pragmatic quality or choose a winner. The source/output-only negative product
observation remains: when explicitly invited to guess the first photograph, the product returned
generic presence instead. That exposed failure is the next bounded product target.

