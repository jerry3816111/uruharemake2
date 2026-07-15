# V39 grounded frame-isolation development replay

| condition | exact | no-action | recall | false action | execution parse | trace wellformed | failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| full_v38_control | 97.2% | 100.0% | 95.5% | 0.0% | 91.7% | 88.9% | 1 |
| colloquial_anchor_only | 100.0% | 100.0% | 100.0% | 0.0% | 91.7% | 88.9% | 0 |
| frame_isolation_only | 97.2% | 100.0% | 95.5% | 0.0% | 100.0% | 88.9% | 1 |
| full_v39_candidate | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 88.9% | 0 |

- Candidate passed: `False`
- Failed checks: `['trace_wellformed_rate']`
- Decision: `do_not_advance_v39_grounded_frame_isolation`
