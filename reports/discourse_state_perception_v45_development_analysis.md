# V45 discourse-state perception development result

| condition | parse | commitment | requested P/R | frame exact | call exact | evidence | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v44_final_control | 100.0% | 94.7% | 100.0% / 100.0% | 94.4% | 100.0% | 97.4% | 5.47s |
| taxonomy_definition_only | 100.0% | 97.4% | 100.0% / 100.0% | 97.2% | 100.0% | 97.4% | 4.61s |
| taxonomy_plus_discourse_signals_candidate | 100.0% | 97.4% | 100.0% / 100.0% | 97.2% | 100.0% | 97.4% | 5.57s |

- Definition -> signals: fixed 0, regressed 0
- V44 -> V45: fixed 1, regressed 0
- Metric gate passed: `True`
- No semantic regression: `True`
- Decision: `authorize_fresh_v45_holdout_freeze`
