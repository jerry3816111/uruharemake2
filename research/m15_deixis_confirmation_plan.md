# M15 Prospective Deixis Confirmation

M14 is treated only as development evidence: it fixed schema fidelity and
revealed a large, task-specific T13 signal.  M15 turns that observation into a
falsifiable confirmatory question on 300 new T13 cases.  It does not recycle a
formal M13/M14 case and does not claim broad pragmatic superiority.

The comparison keeps the same `qwen3.5:9b` model, input, option order, decoding,
strict JSON enforcement, and answer scoring.  The only condition difference is
the internal reasoning scaffold: generic deliberation versus literal content,
pragmatic target, evidence, and alternative interpretation.  Per-item order is
deterministically counterbalanced.

The smallest useful effect is frozen at +15 accuracy points.  Using M14 T13's
planning discordance rate of 10/16, the exact unconditional power of a
candidate-direction result assessed with a two-sided exact McNemar test is
0.9007 at n=300.  The run stops at 300 whether it passes or fails.  A pass also
requires 100% answer parsing, 100% full-schema fidelity, a paired bootstrap CI
whose lower endpoint is above zero, and exact McNemar p <= .05.

Passing would establish one bounded research advantage: this explicit
decomposition improves exact deictic reference resolution over a strong
same-model generic-reasoning control in this protocol.  It would not establish
general human understanding, a memory advantage, felt understanding, Uruha
fidelity, or equivalence to human cognition.  Failing is retained as a formal
negative result; no extra cases are appended after looking at the outcome.
