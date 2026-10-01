# M2 Strong Temporal Baselines — acceptance report

Date: 2026-08-15  
Master specification: `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`  
Master specification SHA-256: `6f0a12f1ed5992baebae22ae10b3f614c54317bc575a86ce37761b49f85dc389`  
Safe worktree: `/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`  
Claim level: **nonfresh synthetic-fixture strong-baseline engineering evidence only**

## Outcome first

M2 is complete. The temporal benchmark now contains all preregistered comparison floors B0–B5 before implementation of the proposed hybrid model. B4 uses one model-generated derivative of all authorized pre-cutoff history; B5 gives the same base model a structured representation of the complete authorized history. Both produce the same six-label probability contract as B0–B3, retain row-level evidence and runtime accounting, and are rendered in the Safari observatory.

This is not evidence that the system predicts Uruha. The fixture is invented and was already exposed in M1. The result establishes that the engineering comparison instrument works and that the later `Ours` model faces strong, measured baselines.

## Frozen information conditions

| Condition | Information available before prediction | Model calls |
|---|---|---:|
| B0 | pre-cutoff label prior | 0 |
| B1 | current event only | 12 |
| B2 | current event + frozen persona summary | 12 |
| B3 | current event + persona + pre-cutoff lexical retrieval | 12 |
| B4 | current event + one model-condensed full-history summary | 12 prediction + 1 summary |
| B5 | current event + persona + all pre-cutoff history grouped by behavior | 12 |

B4 summary construction receives no current test event and no future outcome. B5 receives every authorized history row but no explicit state-transition algorithm. The exact probability-label set is fail-closed; partial or unknown maps are rejected. There is no retry or fallback distribution.

## First-generation result

- Status: `complete_fixture_run`.
- B4/B5 prediction rows: 24/24.
- Shared B4 summaries: 1.
- Model calls: 25.
- Failures: 0.
- Temporal references checked by the inherited dataset validator: 144.
- Leakage violations: 0.
- Model: local Ollama `qwen3.5:9b`, temperature 0, seed 240815.

| Condition | Top-1 ↑ | Top-3 ↑ | Macro F1 ↑ | Brier ↓ | NLL ↓ | ECE ↓ |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 0.167 | 0.500 | 0.0476 | 0.8333 | 1.7918 | 0.0000 |
| B1 | 0.500 | 0.750 | 0.4389 | 0.5457 | 1.1084 | 0.1183 |
| B2 | 0.833 | 0.917 | 0.8278 | 0.3534 | 0.7704 | 0.2701 |
| B3 | 0.833 | 1.000 | 0.8222 | 0.3122 | 0.6673 | 0.3288 |
| B4 | 0.583 | 1.000 | 0.4841 | 0.4234 | 0.8257 | 0.1733 |
| B5 | 0.750 | 1.000 | 0.6944 | **0.2912** | **0.6368** | 0.2870 |

Bounded observations:

- B2 and B3 share the highest Top-1 accuracy, 83.3%.
- B5 is lower on Top-1 at 75.0%, but has the best Brier and NLL. The later hybrid model therefore cannot be judged by accuracy alone.
- B4 is weaker than B2/B3/B5 on Top-1. Compressing twelve observations into one general summary lost event-specific predictive detail on this fixture.
- B0's zero ECE is not superiority: the fixture is exactly balanced and B0 is uniformly uncertain.
- Twelve synthetic samples are too few for a general effect-size or statistical-superiority claim.

## Resource evidence

| M2 component | Calls | Prompt tokens | Completion tokens | Total tokens | Model latency |
|---|---:|---:|---:|---:|---:|
| B4 predictions | 12 | 5,321 | 1,098 | 6,419 | 85.7 s |
| B5 predictions | 12 | 17,705 | 1,375 | 19,080 | 155.2 s |
| B4 summary construction | 1 | 1,472 | 112 | 1,584 | 16.8 s |
| M2 total | 25 | 24,498 | 2,585 | 27,083 | 257.7 s |

M1 and M2 together used 61 model calls, 48,049 tokens, and approximately 497.8 seconds of reported model latency. B5 is the most expensive baseline; this cost remains part of every later comparison.

## Verification evidence

### Unit and contract

```text
python3 -m unittest -v \
  test_m2_strong_baselines.py \
  test_temporal_prediction_lab_m1.py \
  test_m1_temporal_benchmark.py \
  test_m1_temporal_benchmark_v1_1.py

Ran 25 tests — OK
```

The tests cover one shared history signature, future-free summary construction, B4 summary-only prediction input, B5 complete-history input, wrapped/direct exact probability contracts, partial-map rejection, one-summary/24-row/25-call fake execution, temporal validation, M1 inheritance, and six-lane Web rendering.

### Frozen live generation

- Result: `analysis/m2_strong_temporal_baselines_synthetic_first_generation_raw.json`.
- Result SHA-256: `1e7339b4d53da7f24f2a2f63b5208f564ae362a8218d9d8b54a0a096515b7e6d`.
- Config, runner, modules, dataset, inherited M1 result, and test were hash-bound before execution.
- Lock validation passed before the run.

### Web and Safari

Safari at `http://127.0.0.1:7860` was reloaded without closing any existing tabs. The selected S11 graph visibly contains:

- all twelve pre-cutoff history nodes;
- cutoff wall, current event, and post-prediction outcome;
- six parallel B0–B5 probability lanes;
- the B3 retrieved memories and B4 frozen summary;
- B0–B5 Top-1/Brier/NLL/ECE table;
- M1/M2 token and latency cost;
- retained V1 failure and V1.1 repair;
- archived M1 boundary, completed M2, pending M3–M6, and blocked Uruha data gate.

Screenshots:

- `analysis/m2_safari_b0_b5_s11_2026-08-15.png`
- `analysis/m2_safari_b0_b5_metrics_2026-08-15.png`

## Gate decision and next dependency

M2 engineering gate: **PASS**.  
Formal Uruha predictive gate: **BLOCKED** (`0` independently coded target behavior events).  
General same-model advantage claim: **NOT TESTED**.

The next dependency-ordered engineering stage is M3 structured temporal memory: provenance-bearing records, validity/cutoff filtering, configurable activation components, inspectable retrieval, and memory-only ablation. M3 must not silently tune weights on these exposed outcomes or be called a predictive win before a new preregistered evaluation.
