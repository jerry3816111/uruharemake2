# P3-B17 case03 proxy-grade retained failure

Date: 2026-09-15

## Outcome

**FAIL before any valid grade; no quality comparison is available.**

The B16 outputs were committed before case03 annotations were opened. B17 then preregistered eight
blinded local `qwen3.5:9b` judge calls: AB and BA for each of four turns, with exact reply-quote and
visible-evidence validation. The first item, `p3-smoke-03-u1:AB`, returned HTTP 200 but the response
was not complete strict JSON. The run stopped immediately and did not retry.

The local Ollama server log records 620 prompt tokens, exactly 384 generated tokens (the frozen cap),
and 23.629662 s HTTP time. Hitting the completion ceiling is evidence consistent with truncated JSON;
because the invalid raw response was not retained, it is not proof of the exact textual cause.

## Newly discovered accounting defect

The failure checkpoint recorded only `p3_b17_judge_json_invalid`. It did not retain the already
received provider usage, response hash, or `response_received=true`. Consequently the B17 result
incorrectly reports zero provider/network calls even though the local server log proves one completed
HTTP request. The immutable result remains unchanged as evidence of the instrumentation defect.

This defect must be repaired before another judge experiment. The repair may add post-transport
failure accounting and a synthetic schema-conformance probe; it may not rerun this case03 item,
change the locked answers, weaken the rubric, or claim a comparison result.

## Evidence boundary

- Preregistration commit: `7290a49`; release commit: `fc836f9`; retained failure commit: `d2444cd`.
- 1 invocation intent, 1 terminal validation failure, 0 valid judgments, 0 retries.
- Actual local judge calls: at least 1 from server-log evidence; exact observed usage 620 + 384 tokens.
- Human preference remains unavailable; the 24-case formal gate remains unevaluable.
