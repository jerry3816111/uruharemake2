# M1 Temporal Prediction Observatory — acceptance report

Date: 2026-08-15  
Master specification: `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`  
Master specification SHA-256: `6f0a12f1ed5992baebae22ae10b3f614c54317bc575a86ce37761b49f85dc389`  
Safe worktree: `/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`  
Claim level: **synthetic-fixture engineering evidence only**

## Outcome first

The one-week M1 engineering milestone is complete: the repository can now run a frozen, leakage-checked temporal behavior benchmark and render its entire evidence path in Safari. It predicts a probability distribution over future observable behaviors before revealing the outcome, compares B0–B3, computes proper scoring and calibration metrics, records resource cost, retains invalid runs, and refuses to treat synthetic results as Uruha evidence.

The scientific Uruha result is not complete. The formal target dataset still has zero independently coded behavior events and remains explicitly `DATA_GATE_BLOCKED`.

## What was implemented

### Research definition and migration

- Long-term objective migrated to `Interpretable Longitudinal Human Digital Twin`.
- Uruha is the first public-evidence-grounded reference person, not architecture code and not a claim of private identity reproduction.
- Research definitions, hypotheses, variables, annotation, leakage, ethics, and artifact-registry contracts were added under `research/`.
- Full repository/data/evaluation audit was recorded in `reports/RESEARCH_MIGRATION_AUDIT.md`.

### Temporal benchmark core

- `longitudinal_human_model/temporal.py`
  - timezone-aware prediction, cutoff, availability, observation, and source timestamps;
  - fail-closed future-leakage detection;
  - outcome-stripped model input;
  - explicit synthetic/formal authorization boundary.
- `longitudinal_human_model/metrics.py`
  - Top-1/Top-k, Macro/weighted F1;
  - Brier, NLL, ECE with reliability bins;
  - MRR and NDCG.
- `longitudinal_human_model/baselines.py`
  - B0 smoothed historical prior;
  - B1 same base LLM, current event only;
  - B2 same model plus frozen persona summary;
  - B3 same model plus pre-cutoff lexical retrieval;
  - common six-label probability contract and token/latency accounting.
- `longitudinal_human_model/registry.py`
  - SHA-256 bindings, Git/runtime snapshots, atomic results, lock validation.
- Reproducible runners and immutable V1/V1.1 locks.

### Data and governance

- A 12-history / 12-future invented `Synthetic Mika` fixture was created only to validate the instrument.
- All 144 history references are no later than the relevant cutoff.
- No future outcome, observed time, annotation confidence, or acceptable label field is passed into model input.
- Uruha gate binds the existing V7/V9 locks, source manifest, and event schema. Formal model execution remains false.

### Graphical Web observatory

The first Web tab now shows, without requiring raw JSON:

1. the research equation and the separation between behavior probability and language;
2. 12 historical event nodes;
3. the hard cutoff wall and hidden future;
4. current event and post-prediction observed outcome;
5. four parallel baseline probability lanes;
6. B3 memories actually retrieved for the selected event;
7. Top-1, Brier, NLL, and ECE comparison;
8. token and latency cost;
9. V1 failure → V1.1 single-change remediation;
10. completed, blocked, and future roadmap stages;
11. explicit allowed and forbidden claims.

## Frozen first generation and remediation

### V1 — retained invalid result

- Expected: 48 rows.
- Valid: 29 rows.
- Failures: 19.
- Status: `invalid_incomplete_run`.
- Cause: the local model emitted an exact six-label probability map at the JSON top level rather than inside the preregistered `probabilities` key.
- The runner did not invent a fallback distribution or retry individual rows.

### V1.1 — single transport-only change

V1.1 accepts either:

```text
{"probabilities": {label: number}}
```

or the semantically identical exact top-level label map. Partial maps, unknown keys, zero-mass, negative, or non-finite values remain failures. Dataset, prompts, model, seed, retrieval, smoothing, metrics, and no-retry policy were unchanged.

V1.1 is a nonfresh protocol rerun because V1 already processed the samples. It is valid engineering evidence, not an untouched scientific holdout.

## V1.1 observed result

Model: local Ollama `qwen3.5:9b`, temperature 0, seed 240815.  
Rows: 48/48. Failures: 0. Leakage violations: 0.

| Condition | Information | Top-1 | Top-3 | Macro F1 | Brier ↓ | NLL ↓ | ECE ↓ |
|---|---|---:|---:|---:|---:|---:|---:|
| B0 | pre-cutoff label prior | 16.7% | 50.0% | 0.0476 | 0.8333 | 1.7918 | 0.0000 |
| B1 | current event only | 50.0% | 75.0% | 0.4389 | 0.5457 | 1.1084 | 0.1183 |
| B2 | current event + persona summary | 83.3% | 91.7% | 0.8278 | 0.3534 | 0.7704 | 0.2701 |
| B3 | current event + persona + pre-cutoff RAG | 83.3% | 100.0% | 0.8222 | 0.3122 | 0.6673 | 0.3288 |

Observed, bounded interpretation:

- Adding the invented persona summary improved Top-1 from 50.0% to 83.3% on this designed synthetic fixture.
- B3 did not improve Top-1 over B2, but had better Brier, NLL, Top-3, MRR, and NDCG.
- B3 had worse ECE and the highest compute cost; more history made ranking sharper but not better calibrated.
- B0's zero ECE is not predictive superiority. A uniform predictor is perfectly calibrated on this exactly balanced 12-row fixture while remaining uninformative and low-accuracy.
- S03 and S09 are retained counterexamples: persona/history did not force a correct top-1 prediction.

These observations are useful instrument checks. They do not estimate real-world effect size.

## Resource evidence

| Condition | Model calls | Prompt tokens | Completion tokens | Total tokens | Model latency |
|---|---:|---:|---:|---:|---:|
| B0 | 0 | 0 | 0 | 0 | 0.0 s |
| B1 | 12 | 3,138 | 1,423 | 4,561 | 79.0 s |
| B2 | 12 | 4,338 | 1,178 | 5,516 | 66.3 s |
| B3 | 12 | 9,676 | 1,213 | 10,889 | 94.8 s |
| Total | 36 | 17,152 | 3,814 | 20,966 | 240.1 s |

B3 used 2.39 times B1's tokens. This cost must accompany any future performance claim.

## Verification evidence

### Unit and contract

```text
python3 -m unittest -v \
  test_temporal_prediction_lab_m1.py \
  test_m1_temporal_benchmark.py \
  test_m1_temporal_benchmark_v1_1.py

Ran 17 tests — OK
```

Covered clean validation, deliberate future leakage, outcome-before-prediction, safe model input, shared baseline contract, metrics, formal-claim refusal, Uruha gate bindings, 48-row fake run, exact direct-map compatibility, partial-map rejection, and Web rendering.

### Adjacent Web/research regression

Across the new M1 modules and the existing 50-turn comparison, repair, long-memory, equation, teacher-demo, and memory-observatory modules, 56 logical tests were executed in the appropriate environments:

- 55 passed;
- 1 existing frozen-integrity assertion failed because `configs/v2_14_human_pragmatic_holdout_lock.json` no longer matches the already-modified `uruha_personhood_loop.py` mechanism source;
- the frozen V2.14 raw result itself still matches SHA-256 `9005d3495d90e4500409bb1304cc5b68ab62edc134e6b200ecb0fb91a7ed3c22`;
- M1 did not modify `uruha_personhood_loop.py` or rewrite the historical V2.14 lock;
- `git diff --check` passed.

Five of these existing tests initially failed to import under the system Python because it lacks Gradio/ChromaDB. They were rerun with the project's actual Web venv; this environment mismatch is not counted as a behavioral failure.

### Frozen live generation

- V1 and V1.1 configs and code were hash-bound before their respective generation.
- V1 invalid result was retained.
- V1.1 validation: 144 checked references, zero leakage, zero hash mismatches.
- V1.1 live local-model run: 48/48 rows, zero failures.

### Web and Safari

- Gradio Web build smoke test passed using the existing project environment.
- TTS server was unavailable; it is irrelevant to the read-only temporal lab and remains a separate limitation for voice chat.
- Safari opened `http://127.0.0.1:7860` successfully.
- Safari accessibility tree contained the title, 12 selectors, cutoff, current event, future outcome, B0–B3, metrics, cost, blocked Uruha gate, and claim boundaries.
- S07 → S09 selection changed the rendered current event and downstream graph.
- Screenshots:
  - `analysis/m1_safari_temporal_twin_s07_2026-08-15.png`
  - `analysis/m1_safari_temporal_twin_metrics_2026-08-15.png`

## Strict completion accounting

### One-week M1 deliverable

- Engineering/demo rubric: **100% complete**.
- Real-person scientific evidence: **not part of the passed M1 gate and still blocked**.

This means the one-week result is a complete experimental instrument and public demonstration, not a completed Human Digital Twin.

### Full project

Percentages are kept on separate axes because averaging engineering and scientific validity would be misleading:

- Engineering architecture: approximately **40–45%** of the master roadmap.
- Scientific evidence for the central claim: approximately **10–15%**.
- Coarse combined roadmap accounting, if one number is unavoidable: approximately **25–30%**, with low scientific weight.

### Completed parts of the full project

- research question, falsifiable hypotheses, variables, ethics, leakage policy;
- repository/data/evaluation migration audit;
- temporal benchmark schema and fail-closed cutoff;
- B0–B3 common probability interfaces;
- proper scoring, calibration, ranking, and cost accounting;
- reproducible frozen artifacts and failure retention;
- full graphical local observatory and Safari validation;
- explicit target-person authorization gate.

### Not yet completed

- independently coded Uruha temporal behavior dataset and reliability;
- untouched real-person temporal holdout;
- B4 long summary and B5 structured-state prompt baselines;
- person-independent `HumanState` and timestamped snapshots;
- T0–T3 transition models;
- trained/estimated hybrid `Ours` predictor;
- full ablation and probability-changing intervention proof;
- rolling cutoffs, historical scaling, and second-person transfer;
- blind human evaluation of explanatory usefulness and Uruha behavior validity;
- optional language, voice, and VRM integration on top of validated behavior prediction.

## Required resources for the next credible step

The limiting resource is human ground truth, not another prompt rule:

1. two independent consenting coders for the frozen 18-slot V7 reliability pilot;
2. adjudication time and a frozen reliability report;
3. only after passing, independent target calibration coding under V9;
4. then a new untouched temporal benchmark and same-model B0–B5/Ours execution;
5. local compute grows from tens to hundreds or thousands of model calls as rolling cutoffs, ablations, and transfer are added.

No estimate should promise a finished human-equation system within one week. A defensible real-person pilot requires human scheduling and coding; a thesis-grade longitudinal/transfer result is a multi-month research program.

## Final claim boundary

M1 proves that the project now has a reproducible instrument capable of asking the right longitudinal prediction question and exposing its evidence, probability, error, calibration, and cost. It does not prove that UruhaBrain predicts Uruha, reconstructs a brain equation, reads minds, has consciousness, or generally outperforms an LLM.
