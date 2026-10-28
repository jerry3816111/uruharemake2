# M9 / M9.1 Second-Person Transfer — Frozen Acceptance

Date: 2026-08-15 (JST)

## Outcome

M9 demonstrates engineering transfer but fails the predictive-transfer hypothesis. The exact M8 schema, rolling machinery, memory/state/transition code, component features, predictor, and parser run on a second fictional person and a new research-collaboration domain without target-specific core branches. However, adapting on the second person's full history makes prediction worse, not better.

Only one of seven preregistered transfer hypotheses passes.

## Second-person boundary

Synthetic Mira contains 24 new multilingual events, four strict cutoffs, and 16 future events. Schema, taxonomy, state dimensions, event features, memory signals, and core functions are identical to Synthetic Ren. Mira has different text, domain, history, person parameters, and fitted artifacts.

All eight frozen core files contain zero `synthetic_mira` or `synthetic_ren` branches. This proves source-level person independence for the tested implementation path, not universal human generalization.

## Preserved first failure and M9.1 amendment

The first M9 run stopped after 46 completed calls at the E2 B4 summary. Qwen returned a valid string under `behavior_prediction_summary` rather than the requested `summary` key. M9.1 accepts that one equivalent alias and retains the original JSON plus hashes. Prompt, data, transfer arms, model, seed, hypotheses, and no-retry policy remain unchanged.

Three B4 summaries used the alias during M9.1. The rerun is nonfresh parser-remediation evidence because all 24 Mira texts had already reached the feature extractor and E1 baseline calls were complete.

## Transfer comparison

| Condition | Top-1 ↑ | Top-3 ↑ | Macro F1 ↑ | Brier ↓ | NLL ↓ | ECE ↓ |
|---|---:|---:|---:|---:|---:|---:|
| Ren zero-shot | 50.0% | 93.75% | 0.429 | 0.875 | 2.844 | 0.463 |
| Mira parameters only | **56.25%** | 93.75% | **0.501** | **0.862** | 3.035 | **0.435** |
| Mira full history adaptation | 43.75% | **100%** | 0.380 | 1.050 | 2.945 | 0.509 |

Parameter substitution improves Top-1 by 6.25 percentage points and slightly improves Brier/ECE versus zero-shot, so the sole passing hypothesis is `parameter_swap_top1_at_least_zero_shot`. Its NLL is worse, so this is not uniform probability improvement.

Full history adaptation is worse than both zero-shot and parameter-only in Top-1 and Brier. Top-3 reaches 100%, meaning the correct label is ranked somewhere in the top three, but the probability distribution is badly miscalibrated and often puts high confidence on the wrong label.

## Strong baseline floor

| Baseline | Top-1 | Brier | NLL |
|---|---:|---:|---:|
| B1 base LLM | 43.75% | 0.584 | 1.224 |
| B2 persona | 43.75% | 0.658 | 1.300 |
| B3 RAG | 50.0% | 0.708 | 1.495 |
| B4 full-history summary | **75.0%** | **0.378** | **0.728** |
| B5 structured history | **75.0%** | 0.475 | 0.956 |

Full adaptation does not reach the B4/B5 Top-1 floor and does not beat the best Brier. Thus the architecture has not demonstrated predictive advantage on the second person.

## Rolling instability

Full-adaptation Top-1 across E1–E4 is 0%, 25%, 100%, and 50%; NLL is 5.515, 2.729, 0.058, and 3.479. The 100-percentage-point range fails the preregistered 50-point stability bound. As in M8, aggregate metrics hide severe time-window variation.

## Resource accounting and interpretation

- 24 feature calls + 84 B1–B5 calls = 108 calls.
- 64,574 prompt + 12,183 completion = 76,757 tokens.
- 888.76 seconds local-model latency.
- 23.55 seconds numeric transfer fitting/prediction.
- Zero feature-boundary clips, three B4 alias normalizations, zero utterance generation, zero production memory writes.

Completed: second-person schema execution, three transfer arms, strict cutoffs, B0–B5, identical-core SHA evidence, person-specific-branch audit, failure preservation, and cost accounting.

Not established: performance transfer, benefit from target history, stable rolling prediction, real-person validity, Uruha prediction, or general human modeling. The next stage is M10 downstream language/persona/human evaluation and runtime integration, while formal Uruha temporal evidence remains blocked on human coding.

Result SHA-256: `e3c35e1236d7c99d3707fbac75fc6469dc46585f432ff0918a942ead028f8aba`
