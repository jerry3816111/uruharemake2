# M8 / M8.1 Rolling Cutoff and History Scaling — Frozen Acceptance

Date: 2026-08-15 (JST)

## Outcome

M8 completes the rolling-cutoff, history-volume, multi-seed, and new-semantic-text engineering instrument. The scientific result is predominantly negative: only one of eight preregistered diagnostic hypotheses passes. This is a completed hypothesis test, not a successful superiority claim.

The fictional sequence contains 24 unique multilingual events. Eight are initial history; four later cutoffs each seal four new events. Available history grows 8 → 12 → 16 → 20 only after the prior outcomes are available. All 16 test texts were absent from M5/M6 development, and all cutoff validators report zero future leakage.

## Preserved first failure and M8.1 amendment

The first M8 run stopped at history event H08 after seven completed calls because Qwen emitted `support=-0.5`, outside the strict [0,1] contract. The raw failure is immutable.

M8.1 changed one parser rule only: finite numeric values are clipped to [0,1] and both raw and bounded values are retained. Prompt, data, model, seed, cutoffs, hypotheses, and no-retry policy did not change. Two of 24 feature calls were clipped: H08 support -0.5 → 0 and E3-02 support -0.3 → 0. The 16 rolling test prompts had not been called before this amendment.

## New semantic holdout: B0–B5 vs Ours

| Condition | Top-1 ↑ | Top-3 ↑ | Macro F1 ↑ | Brier ↓ | NLL ↓ | ECE ↓ |
|---|---:|---:|---:|---:|---:|---:|
| B0 prior | 6.25% | 50.0% | 0.030 | 0.848 | 1.837 | 0.140 |
| B1 base LLM | 62.5% | 87.5% | 0.551 | 0.556 | 1.147 | 0.130 |
| B2 persona | 37.5% | 81.25% | 0.284 | 0.791 | 3.086 | 0.276 |
| B3 RAG | 31.25% | 62.5% | 0.216 | 0.709 | 2.995 | 0.168 |
| B4 full summary | 50.0% | 75.0% | 0.385 | 0.621 | 1.325 | 0.163 |
| B5 structured history | **81.25%** | **87.5%** | **0.790** | **0.428** | **0.879** | 0.291 |
| Ours hybrid | 62.5% | 81.25% | 0.533 | 0.741 | 2.916 | 0.389 |

Ours does not beat the strongest baseline. It ties B1 in Top-1 but has substantially worse Brier, NLL, and ECE, indicating severe overconfidence. The two preregistered fresh-semantic superiority checks both fail.

## Rolling stability

| Cutoff | Available history | Top-1 | Brier | NLL | ECE |
|---|---:|---:|---:|---:|---:|
| E1 | 8 | 75% | 0.529 | 0.931 | 0.337 |
| E2 | 12 | 50% | 0.937 | 3.547 | 0.511 |
| E3 | 16 | 100% | 0.003 | 0.035 | 0.034 |
| E4 | 20 | 25% | 1.494 | 7.148 | 0.743 |

The Top-1 range is 75 percentage points, exceeding the preregistered 50-point stability limit. E3 looks nearly perfect while E4 collapses, so a single aggregate score would conceal material temporal brittleness.

At E4, Ours correctly accepts concrete trusted rollback support, but assigns essentially zero correct probability to the repeated production failure and private-schedule boundary cases, and only 0.0033 to the ambiguity case. B5 classifies three of four E4 rows correctly.

## History-volume scaling

More history does not monotonically improve this model:

| History condition | Top-1 | NLL |
|---|---:|---:|
| D0 profile only | 56.25% | 2.683 |
| D1 last 2 | 50.0% | 2.121 |
| D2 last 4 | 62.5% | **2.055** |
| D3 last 6 | 43.75% | 2.707 |
| D4 last 8 | 56.25% | 2.209 |
| D5 last 12 | **68.75%** | 2.427 |
| D6 last 16 | **68.75%** | 2.636 |
| D7 all available | 62.5% | 2.916 |

D7 is worse than D0 in NLL, so the main data-scaling hypothesis fails. The final incremental gain is no larger than the first, so the narrow diminishing-return inequality passes, but it does not rescue the nonmonotonic curve. The result indicates retrieval/training interference, not “more life history always helps.”

## Seed stability and M7 sign reversals

Across five preregistered bootstrap seeds, Top-1 ranges 50.0–68.75%, Brier 0.546–0.830, and NLL 2.142–2.944. The model is not invariant to the sampled historical observations.

All three M7 negative directions reverse on M8:

| Removed component | M7.1 Δ NLL | M8.1 Δ NLL | Interpretation |
|---|---:|---:|---|
| temporal dynamics | -0.220 | +0.852 | removal helped old fixture, harms new fixture |
| relationship | -0.116 | +0.259 | sign reversal |
| preference | -0.014 | +0.327 | sign reversal |

Therefore the M7 finding cannot be promoted to a global claim that these components are harmful. Their effect is context- and dataset-dependent.

## Resources and boundary

- 24 fresh feature-extractor calls + 84 B1–B5 calls = 108 total calls.
- 63,101 prompt tokens + 11,719 completion tokens = 74,820 tokens.
- 864.80 seconds accumulated local-model latency.
- 81.66 seconds numeric bootstrap fitting, scaling, prediction, and ablation.
- Zero utterance generation and zero production-memory writes.

Completed: reproducible rolling cutoffs, strict leakage checks, new semantic texts, B0–B5 comparison, eight history volumes, five seeds, M7 sign-replication tests, failure preservation, and full resource accounting.

Not established: real-person validity, Uruha prediction, monotonic data scaling, stable temporal performance, superiority over structured-history LLM, or human felt-understanding. The next dependency is M9 second-person transfer with the same core logic and person-specific data/parameters only.

Result SHA-256: `afcc425ef550444204d219c300a256d4f59d4a5eeccbe580ab15c3766d899726`
