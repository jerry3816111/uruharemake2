# M3 Structured Temporal Memory — acceptance report

Date: 2026-08-15  
Master specification: `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`  
Claim level: **synthetic memory-mechanism evidence only**

## Outcome first

M3 is complete at the mechanism layer. The research core now represents each memory as a provenance-bearing temporal record, excludes memories that are unavailable, future, expired, not yet valid, or assigned to another subject, and ranks the remaining records using seven separately inspectable components. Every component can be removed and the retrieval recomputed under a frozen single-component ablation.

This does not establish that the weights model Uruha or any real person, and it does not yet establish behavior-prediction improvement. The synthetic fixture verifies that the memory instrument is controllable and fail-closed before M4 `HumanState` consumes it.

## Implemented mechanism

`longitudinal_human_model/memory.py` provides:

- mandatory memory identity, subject, observable event, event interval, availability time, source ID, source timestamp, extraction model, and dataset version;
- confidence, importance, emotional salience, relationship tags, frequency, validity interval, and supersession metadata;
- timezone-aware temporal validation;
- subject/cutoff/source/availability/validity eligibility gate;
- configurable recency half-life and frequency saturation;
- a seven-component activation trace: semantic relevance, recency, frequency, importance, emotional salience, relationship relevance, and confidence;
- deterministic ranking and tie-breaking;
- provenance and validity attached to every selected score;
- named single-component ablation with fail-closed unknown-component checks.

Semantic relevance in this first mechanism run is explicitly a deterministic lexical proxy. The module accepts a replaceable scorer; the proxy is not represented as semantic understanding.

## Frozen synthetic mechanism run

- 14 invented memory records.
- 6 invented retrieval queries.
- Top-k = 2.
- 8 conditions: full memory function plus seven single-component ablations.
- Equal weights, 120-day recency half-life, frequency saturation count 3.
- Parameters were not fitted or tuned to estimate a person.
- Result status: `complete_mechanism_run`.
- Gate: PASS.
- Result: `analysis/m3_structured_memory_synthetic_first_result.json`.
- Result SHA-256: `596af4e2332bbebc84bcc5fb7f7a72aeb7193d5663bac03af571691b4e772db7`.

## Observed retrieval and ablation

| Condition | Recall@2 | Rank-order changed | Selected-set changed | Mean absolute score change |
|---|---:|---:|---:|---:|
| Full | 100.0% | 0/6 | 0/6 | 0.0000 |
| Remove semantic relevance | 83.3% | 5/6 | 2/6 | 0.0696 |
| Remove recency | 100.0% | 6/6 | 0/6 | 0.0323 |
| Remove frequency | 100.0% | 6/6 | 0/6 | 0.0170 |
| Remove importance | 100.0% | 6/6 | 0/6 | 0.0101 |
| Remove emotional salience | 66.7% | 5/6 | 3/6 | 0.0471 |
| Remove relationship relevance | 100.0% | 4/6 | 0/6 | 0.0270 |
| Remove confidence | 100.0% | 5/6 | 0/6 | 0.0373 |

All seven components had a nonzero observed contribution. Every ablation changed a score or ranking; semantic and emotional-salience removal also changed selected sets and reduced the author-defined retrieval proxy.

These are designed synthetic mechanism effects, not estimated causal importance in human memory. In particular, the apparent importance of emotional salience is a property of this fixture and equal-weight configuration.

## Temporal and validity controls

Two deliberately tempting records were included:

- `m13_future`: high values in every component but event, availability, and source all occur after the query cutoff;
- `m14_expired`: high values and matching privacy topics but validity ended before prediction time.

Across the full condition:

- future memory selected count: 0;
- expired memory selected count: 0.

They are rejected before activation ranking, so a high score cannot override temporal or validity safety.

## Verification evidence

```text
python3 -m unittest -v \
  test_m3_structured_memory.py \
  test_structured_memory_lab_m3.py \
  test_m2_strong_baselines.py \
  test_temporal_prediction_lab_m1.py \
  test_m1_temporal_benchmark.py \
  test_m1_temporal_benchmark_v1_1.py

Ran 40 tests — OK
```

The frozen M3 lock validated with zero mismatches. The Web application built successfully in the actual project environment.

## Safari graphical acceptance

The first Web tab is now `Memory Core · M3`. Safari verification covered:

- six selectable query scenarios;
- 14 memory nodes;
- selected, eligible, future-blocked, and expired-blocked visual states;
- two selected memory cards with seven component bars and provenance;
- all eight full/ablation conditions;
- explicit engineering-pass and real-person-blocked badges;
- M4 `HumanState` as the next scientific dependency.

Switching Q6 technical failure to Q4 privacy changed selected memory nodes from M11/M12 to M07/M08 while preserving the future and expired exclusions. No existing Safari tabs were closed.

Screenshots:

- `analysis/m3_safari_structured_memory_q06_top_2026-08-15.png`
- `analysis/m3_safari_structured_memory_ablation_2026-08-15.png`

## Gate decision

M3 structured-memory mechanism: **PASS**.  
M3 real-person parameter validity: **NOT TESTED**.  
Behavior-prediction lift over B0–B5: **NOT TESTED**.  
Formal Uruha data: **BLOCKED**.

The next dependency is M4: a person-independent, timestamped, uncertainty-bearing `HumanState` snapshot that consumes these retrieval traces and can be serialized, replayed, and compared before implementation of T0–T3 state transitions.
