# P3-B8.1 adjacent-assistant tokenizer confirmation acceptance

Date: 2026-09-15

Status: **PASS / STAGE-COMPLETE BINDING ONLY**

## Result

After release commit `41285f8`, four fresh synthetic stage-shaped requests ran
against local Ollama 0.33.3 and frozen `qwen2.5:7b`. The only correction was to
collate adjacent private assistant scratch messages with `\n\n` before applying
the already frozen terminal-assistant template rule.

| Stage | Offline count | Provider count | Offset |
|---|---:|---:|---:|
| direct | 244 | 244 | 0 |
| draft | 223 | 223 | 0 |
| critique | 241 | 241 | 0 |
| revise | 250 | 250 | 0 |

- 4 invocation intents, 4 immutable completions, 0 failures
- 958 declared prompt tokens = 958 provider-observed prompt tokens
- 4 completion tokens, 4 real/network calls, 0 paid calls
- provider wall total: 3.186574 seconds
- raw generated output not retained; only hashes remain
- result SHA-256:
  `e360e626931d40ff52f5a217131541701a1eb69831fa3b249214dbb4fed5774f`

The installed-version behavior is also supported by Ollama 0.33.3's own
`template/template.go`: `collate` merges consecutive messages of the same role
with two newlines before template execution. Source:
https://github.com/ollama/ollama/blob/v0.33.3/template/template.go#L411-L439

## Regression and consumer wiring

- focused P3 comparison suite: 85 passed
- previous P3-B8 failed result remains immutable
- post-transport failures now retain declared reservation and provider-observed
  usage, and CLI summaries derive attempts/completions from checkpoints
- the local baseline runner now uses the provider-bound stage counter; no new
  baseline generation was performed as part of this wiring

## Decision and evidence boundary

The tokenizer gate is now released only for direct, draft, critique, and revise
message families under this exact model digest, HF snapshot, Ollama template,
and adjacent-assistant behavior. P3-B7 remains a failed no-retry run and is not
reclassified.

This pass permits a new unexecuted developer-source turn to receive a separately
released product canary plus baseline pair. It does not prove better answers,
human preference, holdout performance, Safari behavior, memory value, or a
general UruhaBrain advantage. Model, template, role-shape, or provider-version
changes require rebinding.
