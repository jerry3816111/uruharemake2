# P3-B18 judge JSON conformance retained failure

Date: 2026-09-15

## Outcome

**REVIEW_REQUIRED. Both OpenAI-compatible serialization conditions failed, with exact accounting.**

One synthetic prompt, containing no developer case, annotation file, confirmation data, or production
state, was sent to the same local `qwen3.5:9b` under two conditions. The only planned change was the
OpenAI-compatible `response_format` value.

| condition | valid strict JSON | finish | prompt + completion | wall | raw response hash |
| --- | --- | --- | ---: | ---: | --- |
| `json_object` | no | `length` | 555 + 384 | 22.497350 s | `12ae32cb...2e126` |
| `json_schema` | no | `length` | 555 + 384 | 16.838208 s | `12ae32cb...2e126` |

Both conditions reached the 384-token ceiling and produced the same raw response hash. Therefore the
schema-wrapper change did not constrain this local route; this is stronger evidence than the B17
failure alone and rules out a one-off parser error as the primary explanation for this fixture.

The B18 accounting repair worked: 2 intents, 2 post-transport failures, 2 provider/network calls,
1,110 prompt + 768 completion tokens, 0 retries and 0 paid calls are all retained. It does not repair
the immutable B17 artifact retroactively.

## Review decision

Ollama's official structured-output documentation specifies that native `POST /api/chat` accepts
either `json` or a JSON Schema directly in the `format` field, and returns `done_reason`,
`prompt_eval_count`, and `eval_count`. The final bounded correction candidate is therefore one
synthetic native `/api/chat` call with the same schema, prompt, model, seed, and 384-token ceiling.
It is not an additional OpenAI-compatible retry and does not touch case03.

- Official structured-output reference: <https://docs.ollama.com/capabilities/structured-outputs>
- Official native chat request/usage fields: <https://docs.ollama.com/api/chat>
- Local client/server version observed: `0.33.3`.

If the native schema call fails, proxy model judging remains blocked and no third serialization
experiment is allowed without a new design decision. If it passes, it authorizes only a future fresh
developer-case judge transport; case03 stays ungraded and cannot be rerun.
