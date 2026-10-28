# M4 Timestamped HumanState — acceptance report

Date: 2026-08-15  
Master specification: `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`  
Claim level: **synthetic state-schema and replay evidence only**

## Outcome first

M4 is complete at the snapshot-contract layer. The system can now bind the current observable event and M3 memory activations into a person-independent, timestamped `HumanState` containing Memory, Emotion estimate, Personality tendency, Relationship, Preference/value, Goal, Habit, Context, and Uncertainty. Every estimate is explicitly `observed`, `inferred`, or `unknown`, has confidence and evidence IDs, and can be serialized and replayed under a deterministic snapshot identity.

M4 deliberately contains no state transition and no behavior predictor. The synthetic confidence values are author-designed model variables, not real private mental states.

## Implemented state contract

`longitudinal_human_model/state.py` adds:

- timestamp and historical cutoff;
- current-event identity and evidence;
- M3 memory activation snapshots with component contributions;
- M/E/P/R/V/G/H/K/U dimensions;
- per-value status, confidence, evidence IDs, update time, and evidence-boundary note;
- exact relationship fields: role, familiarity, trust, affinity, conflict, and interaction frequency;
- evidence catalog with observation time, availability time, source, extractor, and dataset;
- derived average confidence, explicit unknown paths, and low-confidence paths;
- canonical SHA-256 snapshot identity;
- exact serialize/reload replay validation;
- fail-closed future evidence and unresolved evidence references.

Unknown estimates must have null value, zero confidence, and no evidence. Inferred or observed estimates must cite evidence. Psychological-looking dimensions are named and documented as model estimates.

## Frozen synthetic snapshot run

- 2 author-designed snapshots: repeated technical failure and privacy-boundary request.
- 4 inherited M3 memory activations.
- 2 unique deterministic snapshot IDs.
- 6 explicit unknown fields.
- 6 low-confidence fields under the frozen 0.6 threshold.
- Future evidence: 0.
- Unresolved evidence references: 0.
- Exact roundtrip replay: 2/2.
- State transition enabled: false.
- Behavior predictor enabled: false.
- Status: `complete_snapshot_run`.
- Result SHA-256: `5eae08891217cb33b1ca3067f280960c3d8116e561c8349f044d38216b07b731`.

Example unknown spaces are `context.private_fatigue`, `relationships.team.affinity`, `relationships.team.trust`, and `context.private_offline_consequence`. They remain blank instead of being filled by plausible-sounding invention.

## Verification evidence

```text
python3 -m unittest -v \
  test_m4_human_state.py \
  test_human_state_lab_m4.py \
  test_m3_structured_memory.py \
  test_structured_memory_lab_m3.py \
  test_m2_strong_baselines.py \
  test_temporal_prediction_lab_m1.py \
  test_m1_temporal_benchmark.py \
  test_m1_temporal_benchmark_v1_1.py

Ran 52 tests — OK
```

The frozen M4 lock validated with zero mismatches. The Web application built successfully in the actual project environment.

## Safari graphical acceptance

The first Web tab is now `HumanState · M4`. It displays:

- current event → M3 memory → nine-part state → immutable snapshot flow;
- the snapshot timestamp, cutoff, and SHA;
- nine separate M/E/P/R/V/G/H/K/U nodes;
- observed/inferred/unknown labels, confidence, and evidence IDs;
- the evidence catalog and its availability times;
- deterministic/replay/evidence gates;
- explicit `NO TRANSITION / NO PREDICTOR` boundary;
- M5 T0–T3 as the next dependency.

Safari switched from Q6 technical state to Q4 privacy state and showed the changed goal and evidence (`protect_private_information`, M07/M08). Eight existing Safari tabs remained open.

Screenshots:

- `analysis/m4_safari_human_state_q06_top_2026-08-15.png`
- `analysis/m4_safari_human_state_evidence_2026-08-15.png`

## Gate decision

M4 state schema/snapshot/replay: **PASS**.  
Empirically estimated state values: **NOT TESTED**.  
State transition dynamics: **NOT IMPLEMENTED IN M4**.  
Behavior-prediction lift: **NOT TESTED**.  
Formal Uruha data: **BLOCKED**.

The next dependency is M5: implement and compare T0 static, T1 configurable weighted, T2 learned transition, and T3 hybrid feature-extractor plus learned transition without changing the frozen M4 snapshot contract.
