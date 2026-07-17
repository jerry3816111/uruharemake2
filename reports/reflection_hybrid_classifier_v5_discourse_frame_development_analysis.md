# Reflection Discourse-Frame Development Pilot V5

| Condition | Correct | Accuracy |
|---|---:|---:|
| Historical frozen V3 direct carrier | 29/32 | 90.62% |
| Live matched direct carrier | 29/32 | 90.62% |
| V5 structured discourse frame | 30/32 | 93.75% |

| Candidate class | Correct | Accuracy |
|---|---:|---:|
| semantic | 8/8 | 100.00% |
| procedural | 8/8 | 100.00% |
| interpretive | 8/8 | 100.00% |
| none | 6/8 | 75.00% |

- Delta vs live matched direct carrier: +3.13%
- Live control prediction drift vs frozen V3: 0
- Newly correct: 3
- Regressions: 2
- Critical false positives: 2
- Structured tool parse success: 100.00%
- Median fallback latency: 4.991s
- Warm p95 fallback latency: 5.213s
- All preregistered gates: **FAIL**
- Decision: `freeze_negative_result_and_abandon_exact_discourse_frame_contract`

This is development evidence on a retired, Codex-labeled dataset. It cannot authorize runtime memory writes or broad human-likeness claims.
