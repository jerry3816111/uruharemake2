# P3-B32 exact-evidence native conformance acceptance

Date: 2026-09-17

## Outcome

**PASS for native compatibility with the prospective B30 exact-evidence contract.**

B29 permanently failed closed when the sixth native judgment returned a non-exact `reply_quote`.
B30 replaced that prospective schema with keyed `scores.A` / `scores.B` objects and one-value enums
that bind each slot to its entire locked reply. B32 tested whether the same local qwen3.5:9b native
structured-output transport could actually satisfy that contract before any new developer case is
graded.

The source, implementation, tests and zero-call preflight were committed as `4e5fb89`; the separate
two-call release was committed as `cb69365`. Only then was the canary executed once.

## Actual result

- status: `exact_evidence_native_conformance_pass`
- orders: AB and BA, both strictly valid
- invocation intents / completes / failures: 2 / 2 / 0
- native judge calls / localhost network calls: 2 / 2
- retries: 0
- prompt / completion tokens: 948 / 496
- judge wall time: 28.044645 seconds
- paid calls: 0
- developer cases / annotation files / production database accessed: 0 / 0 / false
- B29 regraded: false
- B29 result SHA-256 remained
  `f17edab479026d58d0ecc0c2f57c1cb77e34462c42ade2a1caf171d849dfe5b7`

For both orders, qwen3.5 returned keyed A/B score objects, a non-length finish, the correct null
correction field, and each slot's complete reply exactly. Swapping AB to BA swapped the enum-bound
reply evidence without changing the synthetic replies. The returned `tie` preference is irrelevant
to this transport test and is not a product-quality result.

## Verification

- 18 B32, B30 and native-schema adjacent tests passed in 0.38 seconds.
- offline preflight verified the exact model digest, Ollama 0.33.3, immutable B29/B30 inputs, both
  prompt/schema/body hashes and zero generation calls.
- four signed checkpoints retained two intents and two completes; no failure checkpoint exists.
- all eight result checks passed, including exact evidence, provider accounting, no retry,
  localhost-only and no case/annotation access.
- `git diff --check` passed.

## Evidence boundary

This synthetic two-call result authorizes only reuse of the B30 native exact-evidence transport for a
future prospective case. It does not evaluate UruhaBrain, repair or regrade B29, validate a rubric,
establish human preference, create holdout evidence, or prove an advantage over the direct baseline.
The next evidence cycle must freeze new source-only cases before generation and before annotations.
