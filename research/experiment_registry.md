# Experiment registry contract

Every result used in a report or paper must bind at least:

```yaml
experiment_id:
git_commit:
date:
dataset_version:
cutoff_date:
train_period:
validation_period:
test_period:
model_name:
model_version:
llm_provider:
prompt_version:
embedding_model:
retriever_version:
state_config:
parameter_config:
random_seed:
hardware:
metrics:
notes:
```

Required result artifacts are a config snapshot, metrics, row-level predictions, calibration data, logs, environment metadata, and hashes. Undocumented results are exploratory only and must not support a thesis claim.

## Registered experiments

### `m1_temporal_prediction_observatory_synthetic_fixture_v1`

- Frozen first-generation result: `analysis/m1_temporal_prediction_observatory_synthetic_first_generation_raw.json`
- Status: `invalid_incomplete_run` (29/48 rows, 19 transport-contract failures).
- Claim authorization: engineering failure evidence only.
- Preservation rule: do not overwrite, rescore, or relabel as a valid benchmark.

### `m1_temporal_prediction_observatory_synthetic_fixture_v1_1`

- Frozen nonfresh protocol-remediation result: `analysis/m1_temporal_prediction_observatory_synthetic_v1_1_raw.json`
- Status: `complete_fixture_run` (48/48 rows, zero failures).
- Single change from V1: accept an exact top-level behavior-probability map as transport-equivalent to the wrapped map.
- Claim authorization: synthetic-fixture engineering evidence only; no target-person, human-twin, or general LLM-advantage claim.
- Acceptance report: `analysis/m1_temporal_prediction_observatory_acceptance_2026-08-15.md`.

### `m2_strong_temporal_baselines_synthetic_fixture_v1`

- Frozen first-generation result: `analysis/m2_strong_temporal_baselines_synthetic_first_generation_raw.json`.
- Status: `complete_fixture_run` (24/24 B4/B5 prediction rows, one shared B4 summary, zero failures).
- Inherited comparison: frozen M1 V1.1 B0–B3 result with SHA-256 `a134bc6ff22369f922079b7417c0aa4809f3cb29335c69b8c6336c1233a5c118`.
- Information conditions: B4 current event plus a pre-cutoff full-history summary; B5 current event, frozen persona summary, and structured complete pre-cutoff history.
- Claim authorization: nonfresh synthetic-fixture strong-baseline engineering evidence only; no target-person or general predictive claim.
- Result SHA-256: `1e7339b4d53da7f24f2a2f63b5208f564ae362a8218d9d8b54a0a096515b7e6d`.
- Acceptance report: `analysis/m2_strong_temporal_baselines_acceptance_2026-08-15.md`.

### `m3_structured_memory_synthetic_mechanism_v1`

- Frozen first result: `analysis/m3_structured_memory_synthetic_first_result.json`.
- Status: `complete_mechanism_run` (14 memory records, 6 queries, full plus 7 single-component ablations).
- Full retrieval proxy: Recall@2 1.0; future selected 0; expired selected 0.
- Parameters: equal-weight engineering probe, not fitted person parameters; semantic relevance is a lexical proxy.
- Claim authorization: synthetic memory-mechanism evidence only; no behavior-prediction lift or real-person claim.
- Result SHA-256: `596af4e2332bbebc84bcc5fb7f7a72aeb7193d5663bac03af571691b4e772db7`.
- Acceptance report: `analysis/m3_structured_memory_acceptance_2026-08-15.md`.

### `m4_human_state_synthetic_snapshot_v1`

- Frozen first result: `analysis/m4_human_state_synthetic_first_result.json`.
- Status: `complete_snapshot_run` (2 deterministic snapshots, exact replay, 0 future evidence, 0 unresolved references).
- State scope: M/E/P/R/V/G/H/K/U with observed/inferred/unknown status, confidence, and evidence IDs.
- Transition and behavior prediction: explicitly disabled.
- Claim authorization: synthetic state-schema and replay evidence only; no private-state or real-person claim.
- Result SHA-256: `5eae08891217cb33b1ca3067f280960c3d8116e561c8349f044d38216b07b731`.
- Acceptance report: `analysis/m4_human_state_acceptance_2026-08-15.md`.
