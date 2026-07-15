# V41 selective validator-repair development result

The V39 4B primary outputs were frozen. Only four validator-flagged traces were sent to each local repair specialist.

| repair specialist | exact calls | trace wellformed | frame exact | repair accepted | calls/case | median | p95 | passed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| repair_qwen3_5_0_8b | 100.0% | 88.9% | 52.8% | 0.0% | 0.111 | 3.57s | 6.11s | False |
| repair_qwen3_5_2b | 100.0% | 88.9% | 52.8% | 0.0% | 0.111 | 3.57s | 7.45s | False |
| repair_qwen3_5_4b | 100.0% | 94.4% | 55.6% | 50.0% | 0.111 | 3.57s | 7.23s | False |

- Eligible: `[]`
- Selected: `None`
- Decision: `do_not_advance_v41_selective_validator_repair`
