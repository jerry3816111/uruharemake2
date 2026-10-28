# P3-B46 real-adapter implementation acceptance

Date: 2026-09-17

## Outcome

**PASS for implementation freeze; real generation remains unexecuted.**

The B45 no-retry journal is now connected to both local transports used by the product: the
OpenAI-compatible chat path and the native Ollama chat path. A completed call can be reconstructed
into the response shape expected by the existing product without invoking the transport again.

## Verified behavior

- an intent is durably written before either transport is called;
- complete records retain only normalized content, hashes, exact usage and transport evidence, not
  another raw prompt copy or a reasoning trace;
- OpenAI SDK-style and native JSON response shapes are reconstructed on complete reuse;
- reused calls report zero new network/model calls;
- intent-only, terminal transport failure, request drift and mutated completion fail closed;
- the batch runner fixes three isolated case workspaces, 12 paired turns, 24 visible outputs, three
  third-turn product restarts and direct-baseline order;
- case workers are fresh subprocesses and annotation paths are not runner inputs;
- workspace deletion is exact-path and sentinel gated.

## Verification

- 5 adapter tests passed;
- 6 runner-contract tests passed;
- 20 B45/B46 focused and adjacent tests passed in 35.97 seconds;
- preflight 8/8 checks passed against the installed `qwen2.5:7b` digest;
- 0 real generation calls, 0 network calls, 0 annotation reads and 0 production database access.

## Remaining gate

This only freezes the implementation. A separate release must bind these exact bytes, the B45
contract and the single checkpoint/result paths. Only after release validation may the batch run
once. Output locking still precedes rubric access, so even a successful run will not yet be a quality
or product-advantage result.
