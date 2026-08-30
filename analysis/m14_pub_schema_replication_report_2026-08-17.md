# M14 Schema-enforced PUB Replication

**Decision: `fail_schema_enforced_pragmatic_gain`**

| Condition | Accuracy | Answer parse | Full schema | Prompt tokens | Completion tokens | Latency |
|---|---:|---:|---:|---:|---:|---:|
| B0_DIRECT | 62.5% | 100.0% | 100.0% | 14,836 | 514 | 117.2s |
| B1_GENERIC_DELIBERATION | 54.7% | 100.0% | 100.0% | 17,588 | 6,656 | 462.6s |
| OURS_PRAGMATIC_LOOP | 64.1% | 100.0% | 100.0% | 20,340 | 6,242 | 456.2s |

Primary Ours−Generic: `+0.094`, 95% CI `[-0.062, +0.250]`, McNemar `p=0.3269`, wins/ties/losses `16/38/10`.

Secondary Ours−Direct: `+0.016`, 95% CI `[-0.125, +0.156]`, McNemar `p=1.0000`.

## Task-level accuracy

| Task | Direct | Generic | Ours | Ours - Generic |
|---|---:|---:|---:|---:|
| T12 | 62.5% | 56.2% | 56.2% | +0.000 |
| T13 | 37.5% | 37.5% | 75.0% | +0.375 |
| T2 | 75.0% | 56.2% | 68.8% | +0.125 |
| T6 | 75.0% | 68.8% | 56.2% | -0.125 |

## Cross-split stability

M13 Ours−Generic was `-0.047` with only `23.4%` complete schemas; M14 is `+0.094` with `100.0%` complete schemas. Direction replicated: `False`.

M13 did not instantiate the full Ours schema reliably, so pooling it with schema-enforced M14 would conflate implementation fidelity with sample effects.

## Locked gates

- `H1_answer_parse`: PASS
- `H2_full_schema`: PASS
- `H3_primary_gain`: FAIL
- `H4_no_large_task_regression`: PASS

## Interpretation

schema enforcement establishes implementation fidelity only; no pragmatic superiority claim.

M14 is a disjoint replication of a project-specific prompt intervention on public PUB. It repairs implementation fidelity but remains potentially exposed in base-model pretraining, uses one option permutation, and cannot establish longitudinal person understanding, felt understanding, Uruha fidelity, or a human-brain equation.

## Reproducibility

- Config SHA: `8e2f8954876e1d38b32c259734130bb02d1bca63172426f11537d01dc82c6e34`
- Manifest SHA: `9cd4546966794d1d057588c4fcfec87e762c7e3254c26c1ff77f2d58f5183cd9`
- Probe SHA: `74ee61b664e038b76dc715c74ec0e3cf8442993c95fb28180a9268325c2ef224`
- Raw SHA: `4f3504e8a39d4e063e294c8e83070c241938e10515074a6fb945ca18b827f5b3`
- Production memory writes: `0`
