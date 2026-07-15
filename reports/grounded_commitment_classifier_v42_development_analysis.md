# V42 grounded commitment-classifier development result

The ontology fixed each supported domain-value target and exact evidence candidates. Each local model classified only the final commitment and evidence index.

| model | parse | commitment | requested P/R | frame exact | call exact | false action | p95 | passed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V39 full-frame control | 88.9% | 65.8% | 100.0% / 100.0% | 63.9% | 100.0% | 0.0% | 5.05s | control |
| commitment_qwen3_5_0_8b | 2.6% | 0.0% | 0.0% / 0.0% | 27.8% | 55.6% | 0.0% | 2.42s | False |
| commitment_qwen3_5_2b | 68.4% | 21.1% | 100.0% / 22.7% | 38.9% | 63.9% | 0.0% | 2.16s | False |
| commitment_qwen3_5_4b | 94.7% | 79.0% | 100.0% / 72.7% | 80.6% | 86.1% | 0.0% | 3.52s | False |

- Eligible: `[]`
- Selected: `None`
- Decision: `do_not_advance_v42_grounded_commitment_classifier`
- Unsupported-action discovery remains a separate open-set task.
