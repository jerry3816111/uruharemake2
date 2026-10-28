# P4-B same-shape non-B prompt/usage parity — prospective protocol

Status: **independently reviewed GO as prospective design baseline only;
NO-GO for immediate real run**. Before a live request, separately freeze the
adapter's allowed files/API/tests and pass fake transport, identity and
watchdog negative controls. No real run is authorized by this file.
This is one dependency of the existing P4-B gate, not a new M, a B token
certificate, or evidence of a better reply. The fixed B question/gold,
budgets, product gate, and previous failures do not change. No A/B prompt,
formal holdout, user memory, Web turn, or Safari Send is used here.

## Before / one variable / falsifiable claim

`compact_request()` now yields the exact transformed M21 shape; the new
`p4_b_transformed_request_diagnostic.py` verifies that shape under injected
fake HTTP only. Its three synthetic fake tokens and the older 35-token
fixed-fixture private probe are **not** provider prompt usage or a B bound.
The missing causal link is whether Ollama 0.34.4's rendered prompt passed to
its *same live private runner* `/tokenize` accounts for the prompt tokens
reported by one normal completion with otherwise identical request fields.

Test hypothesis, declared **before** any real generation: if the frozen
model/template has no added or stripped BOS and the live normal completion
does not truncate the prompt, then
`usage.prompt_tokens - len(/tokenize tokens) == 0` for **this one synthetic
request**. A nonzero difference or missing evidence rejects this parity
hypothesis; it is not repaired by changing the expected margin after seeing
the answer. One match would support only a same-run conformance observation,
not a universal ±0 margin, an upper bound for B, or 20-second Web delivery.

Source reasons that make this hypothesis testable rather than assumed:
tagged Ollama 0.34.4 `server/routes.go` handles `_debug_render_only` before
completion; `llm/llama_server.go`'s `completionPrompt` can remove a leading
BOS, and `completionPromptForRequest` can truncate by runtime `NumCtx`;
the latter file's prompt timing adds cache and eval counts, which
`openai/openai.go` maps to `prompt_tokens`. These mechanisms are not
interchangeable with the tokenizer's standalone count. Primary source:
[routes](https://github.com/ollama/ollama/blob/v0.34.4/server/routes.go),
[runner path](https://github.com/ollama/ollama/blob/v0.34.4/llm/llama_server.go),
[OpenAI usage adapter](https://github.com/ollama/ollama/blob/v0.34.4/openai/openai.go).

The frozen private GGUF metadata read-only inspection found
`qwen2.context_length=32768`, `tokenizer.ggml.model=gpt2`,
`tokenizer.ggml.pre=qwen2`, `tokenizer.ggml.add_bos_token=false`;
the frozen small config has no renderer field. This suggests the BOS-removal
branch is inactive for that frozen model. **32768 is trained context, not
the live `opts.NumCtx`**. The next live runner's `-c` and `-np` argv,
daemon context environment, model options and the actual request must be
recorded and reconciled *before* using Δ=0 as a pass criterion. Old runner
PIDs/options cannot substitute. If truncation or leading-BOS semantics
remain unproved, mark `REVIEW_REQUIRED`, not parity PASS.
One source-level gap is that the existing diagnostic sends `/tokenize` with
`parse_special=true`, whereas tagged Ollama's runner-facing tokenize path
uses `add_special=false` with `parse_special` omitted/default. The test must
measure both treatments of the **same** rendered string; their equality is
an observed precondition, not a source-proven axiom.

## Prospective isolated experiment, subject to review

- Work only in the safe worktree and a new 0700 private run directory,
  reusing the previously isolated private model clone only after rechecking
  its permissions/digests; do not duplicate the 4.4 GiB logical model
  without a recorded need. Use frozen `qwen2.5:7b` manifest/blobs and Ollama 0.34.4
  daemon/runner binaries. Do not attach to or reconfigure shared 11434,
  production DB, original dirty checkout or an existing user session.
  No external deployment or paid API.
- Build **one** synthetic non-B, non-holdout two-message request by calling
  real `compact_request()`; it must satisfy the diagnostic's exact M21
  model `qwen2.5:7b`, temperature 0.1, JSON schema, max output 256,
  timeout 20.0 and `User Input: ` prefix. Set
  `URUHA_P4_COMPACT_JSON_SCHEMA=1` and disable the optional
  `URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT` arm in an explicit child env.
  Freeze the pre-compact system string as
  `"You are the Left Brain Planner for a dual-brain character system.\nSynthetic parity only.\n[Output JSON schema]\nNever part of the experiment."`
  and the user string as
  `"User Input: 非Bの検証用。改行\nJSON記号 {\"x\":1} だけ。"`.
  Neither is the actual B question. A source-only dry run of this literal
  fixture with the exact two env arm settings returned six request keys,
  JSON-schema format, 870 system characters, 40 user characters,
  1,833 canonical UTF-8 bytes and SHA-256
  `7ea87c8e8985dfe7fb2b5dc9198cd9f26caaaa3fbf4c93559405a06230b4eb56`.
  The live run must reproduce this digest before contacting Ollama. Record
  its canonical SHA-256 and UTF-8 length privately; do not print raw prompt
  or rendered text in a durable report.
- Start at most one new private daemon (one runner spawned by it). Before
  any request check 0700 root, model blob/manifest and binary identities,
  daemon loopback binding and no proxy/redirect. Metadata may use exactly
  `/api/version`, `/api/tags`, `/api/show` (three calls); make exactly one
  `_debug_render_only=true` call with only client `timeout` removed from
  the copied request, then two `/tokenize` diagnostics on its **exact**
  returned string: one with `add_special=false, parse_special=true` and
  one with `add_special=false` and `parse_special` omitted. The token
  lists/counts must agree or this branch is `REVIEW_REQUIRED`; neither
  diagnostic is a completion. Make exactly one normal
  `/v1/chat/completions` call with a fresh copy of the same transformed
  request minus client-only `timeout` and debug flag. No retries, parallel
  sends, additional completion or model warm-up. Total ≤7 HTTP calls
  including all metadata and identity HTTP, **one external normal
  completion attempt** maximum (do not infer the count of internal runner
  generations solely from HTTP count), each request ≤256 KiB canonical
  UTF-8, each response ≤2 MiB, output cap 256, observation window ≤90s.
  Use a supervising watchdog that attempts a 90s stop, and terminate only
  the newly started private daemon/runner after rechecking their exact PID
  generations and loopback listeners; if cleanup identity is uncertain,
  report it and do not kill an unrelated process.
  A limit breach is FAIL; it does not authorize another attempt.
- Render-only may lazy-load the runner. Bind daemon identity before render;
  after render capture the live runner PID/raw generation, absolute binary
  and GGUF path/hash, template/system/manifest digest, parent relationship,
  listener and argv `-c`/`-np`. Recheck run-bound daemon and runner identity
  immediately before tokenize, before normal completion and afterward.
  A changed/missing runner or ambiguous `NumCtx` is `REVIEW_REQUIRED`.
  The pre/post checks are cooperative local evidence, not an atomic
  defense against a malicious same-user process. Count full SHA bytes and
  wall time; do not hide identity or cold-load overhead.
- The seven-call cap is fully allocated: three metadata, one render, two
  tokenize and one normal completion. All repeated identity checks must be
  OS/filesystem-only; if one needs extra HTTP, stop for a prospective
  budget amendment instead of silently exceeding seven.
- The transport must explicitly bind the private loopback URLs, suppress
  proxy use, reject redirect/effective-URL change, and close on timeout.
  Check response model and exact integer `prompt_tokens`,
  `completion_tokens`, `total_tokens` with total=sum; retain no raw
  response outside the private run. A malformed response, absent usage,
  different rendered string/request, changed source, identity uncertainty,
  timeout or nonzero Δ is a retained negative result. Generation failure
  still consumes the one-attempt budget; never chase a green result.
- Receipt: private 0600 raw-free JSON only with request/render/identity
  digests, lengths, both runner counts, provider usage, signed Δ, source/BOS/
  NumCtx/truncation decision, HTTP and generation counts, wall time and
  estimated disk/model-hash bytes. The public result note may cite these
  numbers but not the raw request, rendered prompt, token IDs or response.
  Report `b_upper_bound_proven=false`, `b_send_authorized=false` regardless
  of parity. Stop the newly started private daemon/runner after the run;
  do not stop shared services or recursively delete the clone.
  Distinguish `external_completion_attempts=1` from
  `internal_runner_generations=unknown` unless separate same-run telemetry
  proves the latter. Private daemon logs, raw callback exceptions and
  temporary prompts are possible raw-data surfaces: keep the run directory
  0700 and any logs 0600, never place original exceptions or raw bodies in
  the report, and add canary-leak negative tests. A 90s supervisor can
  terminate only PIDs whose raw generation still matches; if identity is
  uncertain, it must not kill an unrelated process and must report
  `physical_stop_unproven`. Thus the time limit is **conditional fail-closed**,
  not an unconditional hard promise on an adversarial host.

## Release gate and next dependency

Independent review found this design suitable **only** as the next
implementation baseline. Before any real HTTP, write a separate freeze
listing allowed files, exact adapter and supervisor API, fake observations,
precise tests and resource accounting. Red/green the adapter with injected
fake transport, OS-only identity, timeout, cleanup and raw-leak controls;
obtain independent patch review. Confirm live `NumCtx`, BOS branch and no
truncation before interpreting the single allowed live run.
If the reviewer cannot determine a safe exact test or physical stop,
retain `REVIEW_REQUIRED` and do only read-only source work. Any live result
must report both matching and mismatching evidence honestly; no fixed
synthetic replay establishes B's token bound.

Only afterward may a **separate** frozen/reviewed diagnostic use the actual
post-compact B request to seek a B-specific bound, followed by one-shot
product gate activation and all remaining A, identity, 20s Safari and
late-surface gates. No result here authorizes the fourth B Ollama attempt
or B Safari Send.
