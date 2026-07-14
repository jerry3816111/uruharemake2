# RightBrain V30 matched base-model ablation preregistration

## Question

The active RightBrain uses Qwen2.5-7B plus the V10 LoRA adapter. This experiment asks whether the adapter itself improves the current surface-realization contract, or whether the unmodified base model is more reliable.

## One changed variable

| Condition | Qwen2.5-7B | Current payload | Sampling | Gate | V10 LoRA |
|---|---:|---:|---:|---:|---:|
| V10 | fixed | fixed | fixed | fixed | on |
| Base-only | fixed | fixed | fixed | fixed | off |

The adapter is additive to the frozen base model. Turning it off is therefore a matched ablation of the learned low-rank update, not a comparison against a different LLM.

## Frozen evidence

- Cases: 12 V29 development cases with 12 distinct source families and 8 categories.
- Seeds: 20260712, 20260713, 20260714.
- Candidates: 3 per case and seed, 108 raw generations per condition.
- Primary unit: 36 matched seed-case pairs.
- V10 outputs were generated before this preregistration and are bound by file hashes.
- No base-only V29 generation has been run before this preregistration.

## Metrics

The primary metric is strict case coverage: whether at least one of the three raw candidates for a seed-case pair passes the unchanged semantic, language, persona, and length gate. The paired comparison uses exact McNemar testing over the 36 seed-case pairs. Candidate-level rates are descriptive because three candidates from the same case are correlated.

Secondary diagnostics separate hard surface failures, semantic omissions, polite-register drift, and duplicate candidates. This prevents a clean-looking but semantically incomplete answer from being counted as an improvement.

## Decision boundary

The automatic experiment cannot promote a runtime model. A base-only improvement of at least 10 percentage points in strict case coverage, with no seed-level coverage loss, no higher hard-surface failure rate, and no meaningful semantic-omission increase, authorizes only a new same-policy human blind comparison. Otherwise V10 remains active.

This is a diagnostic development ablation, not an official benchmark and not proof of human likeness.
