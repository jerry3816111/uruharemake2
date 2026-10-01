# M13 PUB Published Pragmatics Benchmark

**Decision: `fail_narrow_pragmatic_gain_with_implementation_fidelity_gap`**

## Controlled result

| Condition | Accuracy | Answer parse | Full schema | Prompt tokens | Completion tokens | Latency |
|---|---:|---:|---:|---:|---:|---:|
| B0_DIRECT | 45.3% | 100.0% | 100.0% | 14,058 | 514 | 114.2s |
| B1_GENERIC_DELIBERATION | 75.0% | 100.0% | 100.0% | 16,810 | 6,723 | 462.0s |
| OURS_PRAGMATIC_LOOP | 70.3% | 100.0% | 23.4% | 19,562 | 5,544 | 411.8s |

Primary is Ours versus generic deliberation on the same 64 items and model: accuracy delta `-0.047`, paired bootstrap 95% CI `[-0.125, +0.016]`, exact McNemar `p=0.3750`, wins/ties/losses `1/59/4`.

Secondary Ours versus direct: delta `+0.250`, CI `[+0.109, +0.391]`, McNemar `p=0.0025`.

## Task-level result

| Task | Direct | Generic | Ours | Ours - Generic |
|---|---:|---:|---:|---:|
| T12 dialogue assumption validity | 18.8% | 31.2% | 31.2% | +0.000 |
| T13 deictic reference resolution | 43.8% | 87.5% | 81.2% | -0.062 |
| T2 indirect-answer interpretation | 75.0% | 100.0% | 93.8% | -0.062 |
| T6 sarcasm versus agreement | 43.8% | 81.2% | 75.0% | -0.062 |

## Locked gate

- `H1_all_parse`: PASS
- `H2_primary_accuracy_and_significance`: FAIL
- `H3_no_large_task_regression`: PASS

## Honest interpretation

Authorized claim: reasoning conditions outperform direct answering on this frozen subset; no evidence that the current pragmatic implementation outperforms generic deliberation.

The posthoc implementation-fidelity audit found complete Ours schemas in `15/64` rows. Most violations omitted `pragmatic_target`. Therefore this run is evidence about the actual prompt behavior, not a clean causal test of a fully instantiated cognitive loop.

This score does not evaluate whether the final Japanese reply makes a person feel understood. It also does not validate a persistent user model or Uruha persona. Public benchmark exposure during base-model pretraining cannot be excluded, and the project prompt differs from the paper's exact MCP implementation.

## Reproducibility

- Protocol SHA-256: `de9109eaa508535dc608b09bcb0680348d26b5c480dd4f41164d0599fabac5d0`
- M13.1 amendment SHA-256: `d03a751b306efff89cc09749c10fdd5699a5610d60940d2359ffeae0689e8693`
- Case manifest SHA-256: `8a86ce624fa452d289468c5a0b62f35a254a0148fd8eb5228665fac638e4f6ee`
- Raw result SHA-256: `9a49f8add4bb33a1a94b580ae72c48b21858f98f03f986c3ef7cc9144b634a74`
- Production memory writes: `0`
