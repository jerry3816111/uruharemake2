# M15 Prospective Deixis Confirmation

**Decision: `pass_focused_deixis_advantage`**

## Confirmatory result

| Condition | Accuracy | Parse | Full schema | Prompt tokens | Completion tokens | Latency |
|---|---:|---:|---:|---:|---:|---:|
| Generic deliberation | 52.7% | 100.0% | 100.0% | 122,603 | 31,285 | 2286.3s |
| Pragmatic decomposition | 68.7% | 100.0% | 100.0% | 135,503 | 32,215 | 2395.4s |

Paired Ours-Generic: `+0.160`; paired bootstrap 95% CI `[+0.070, +0.250]`; exact two-sided McNemar `p=0.00079446`; wins/ties/losses `123/102/75`.

## Frozen gates

- `H1_answer_parse`: PASS
- `H2_full_schema`: PASS
- `H3_SESOI`: PASS
- `H4_CI_excludes_zero`: PASS
- `H5_exact_McNemar`: PASS

## Authorized interpretation

For qwen3.5:9b under this frozen strict-schema protocol, the explicit pragmatic decomposition improves exact deictic-reference resolution over equally strict generic deliberation by at least the preregistered 15-point SESOI on 300 new PUB T13 cases.

Precision note: The observed +16-point sample effect exceeds the +15-point SESOI and its confidence interval excludes zero. The 95% CI lower endpoint is +7 points, so M15 does not establish that the population effect is at least +15 points.

## Development-to-confirmation stability

M14 generated the focused signal at `+37.5pp` on 16 cases. M15 confirmed the direction at `+16.0pp` on 300 disjoint cases; the magnitude attenuated by `-21.5pp`. The splits are not pooled.

## Cost

Ours used `13,830` more total tokens (`+9.0%`) and `109.2s` more aggregate latency (`+4.8%`).

## Exploratory mechanism slices (not confirmatory gates)

| Question family | n | Generic | Ours | Delta |
|---|---:|---:|---:|---:|
| action_attribution | 40 | 47.5% | 77.5% | +30.0pp |
| entity_state_or_location | 112 | 54.5% | 75.0% | +20.5pp |
| epistemic_certainty | 93 | 53.8% | 62.4% | +8.6pp |
| person_location | 55 | 50.9% | 60.0% | +9.1pp |

## Boundary

M15 is a focused post-development confirmation on disjoint public PUB T13 items. It compares one model and one deterministic option permutation, may be exposed through base-model pretraining, and tests exact multiple-choice deictic reference resolution rather than longitudinal human understanding, felt understanding, human preference, Uruha persona fidelity, or a human-brain equation.

## Reproducibility

- Formal cases/calls: `300` / `600`
- Recomputed prospective power: `0.900724`
- Config SHA: `2c28ee7fa35b116cd45c4af3932aa5e263d60e4967e8211793b0aafa33c723ab`
- Manifest SHA: `e8f6512be9b73507710936f3ee5720e98a99e35d73da266ebf849a813da138fc`
- Probe SHA: `3da39cb49eec2fce1c9a6f1ac04a04940cc38c1be4adbfa9f55ddad3453996f9`
- Raw result SHA: `0f740971332eef70e602a898aa9cfda3810eff0bef3537d2e2dac0f6905a2d99`
- Production memory writes: `0`
