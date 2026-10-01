# P3-B8 stage-complete tokenizer binding acceptance

Date: 2026-09-15

Status: **FAILED_RETAINED / SECOND CORRECTION REQUIRED**

## Frozen local result

The four-call localhost probe ran only after release commit `1f5b40e`. It used
new synthetic text, the frozen `qwen2.5:7b` digest, temperature 0, seed
20260909, `think=false`, one completion token per call, no retry, and no access
to the failed P3-B7 request, developer smoke source, annotations, future turns,
confirmation data, or production memory.

| Stage | Offline candidate | Provider prompt | Offset | Outcome |
|---|---:|---:|---:|---|
| direct | 245 | 245 | 0 | exact |
| draft | 219 | 219 | 0 | exact |
| critique (one assistant scratch) | 238 | 238 | 0 | exact |
| revise (two adjacent assistant scratches) | 244 | 239 | -5 | failed verification |

Evidence: 4 immutable intents, 4 immutable completions, 4 provider/network
calls, 4 completion tokens, 0 paid calls, 4.431273 seconds. Raw generated text
was discarded; only output hashes remain. Result SHA-256:
`0a2a35b86e82e31c98a692fb71e424ab277759519ff8729d4b137ca9739d9b49`.

## What this disproved

P3-B8's first correction assumed the provider removed only the terminal
`<|im_end|>\n` from the final assistant message. That explains the one-scratch
critique shape but not the two-adjacent-scratch revise shape. The provider count
for revise is another five tokens lower, so the frozen verification gate
correctly failed and the binding remains unverified.

Offline counterfactual rendering shows that merging the two adjacent assistant
scratch messages before applying the terminal-assistant rule produces 239
tokens, exactly the retained provider observation. This is a prospective
hypothesis, not yet provider-validated.

## Decision and boundary

P3-B7 remains failed and is not retried. A second and final scoped correction
may normalize only adjacent private assistant scratch messages before token
counting, then verify the same four stage families with fresh synthetic text and
zero tolerance. If that confirmation fails, P3-B8 becomes `REVIEW_REQUIRED`;
the exact gate may not be removed or weakened.

This is tokenizer/accounting evidence only. It gives no reply-quality winner,
human preference, holdout result, Safari acceptance, or UruhaBrain advantage.
