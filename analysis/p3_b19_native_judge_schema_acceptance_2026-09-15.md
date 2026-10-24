# P3-B19 native judge structured-output acceptance

Date: 2026-09-15

## Outcome

**PASS for one synthetic native structured-output call.**

The exact B18 synthetic prompt, `qwen3.5:9b` digest, temperature, seed, 384-token ceiling,
and strict validator were retained. The single attributable change was moving from the
OpenAI-compatible response-format carrier to native `POST /api/chat` with the JSON Schema supplied
directly as `format`, following Ollama's documented contract.

| route | prompt + completion | finish | strict schema | wall |
| --- | ---: | --- | --- | ---: |
| prior OpenAI-compatible `json_schema` | 555 + 384 | `length` | fail | 16.838208 s |
| native direct `format=<schema>` | 557 + 244 | `stop` | pass | 16.248327 s |

The valid result scored the grounded synthetic reply `まだ決めてないんだね。` as 2/2 for
attunement, grounding and continuity, and scored the unsupported assertion `絶対行きたいんだね。`
as 0/2 with `unsupported_assertion=true`. This checks both serialization and the smallest expected
rubric behavior; it does not validate judging reliability on real cases.

## Boundary evidence

- Release commit `1ecbdb3`; immutable result commit `b515b0a`.
- 1 intent, 1 complete call, 0 failures, 0 retries; 557 prompt + 244 completion tokens.
- 0 developer-case, annotation, confirmation, production DB, remote or paid access.
- Local Ollama client/server version `0.33.3`; model digest exact.
- 114 affected tests passed before release.

This pass authorizes designing the native transport for a future, not-yet-run developer case.
It does not authorize rerunning case03, grading previously spent judge items, claiming product
advantage, or treating the model judge as human preference.
