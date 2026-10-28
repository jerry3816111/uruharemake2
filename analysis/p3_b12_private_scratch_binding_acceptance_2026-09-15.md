# P3-B12 private-scratch tokenizer binding acceptance

Date: 2026-09-15

## Outcome

PASS for two new user-role labeled private-scratch message shapes only.

- critique: offline 302 = provider 302 prompt tokens;
- revise: offline 313 = provider 313 prompt tokens;
- 2 intents, 2 completes, 2 real/local network calls, 2 completion tokens;
- 3.026870 total wall seconds, 0 paid calls;
- raw output text was discarded; only output hashes were retained;
- 0 developer cases, annotations, confirmation, or production DB access.

The counter now has an explicit Ollama mode that merges any adjacent same-role messages with two
newlines before applying the Qwen chat template. The previous assistant-only mode remains available
for the immutable B8/B8.1 evidence.

This establishes exact accounting for the proposed critique/revise carrier. It does not show that
the carrier produces a useful critique or a better final answer. P3-B13 must test that separately
against the already locked P3-B11 assistant-carrier control.
