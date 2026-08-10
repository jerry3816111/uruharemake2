# V2.14 Lexical-Oracle Failure Attribution

**Decision: `lexical_answer_available_but_selection_or_expression_failure_dominates`**

| Measure | Result |
|---|---:|
| Cases | 57 |
| Mean lexical-oracle F1 | 0.636 |
| Lexical quality available | 48/57 |
| 27B mean F1 | 0.228 |
| 27B lexical-available misses | 40 |

## 27B attribution

- `lexical_answer_available_model_miss`: 40
- `model_quality_pass`: 10
- `no_lexical_answer_evidence_in_target_session`: 7

V2.14 is a gold-aware deterministic diagnostic on 57 fully exposed development cases and already-generated 9B/27B predictions. Its oracle may localize lexical source availability versus answer-selection or nonverbatim-inference failures, but the oracle itself is prohibited from runtime use and cannot prove a fix, fresh-generation gain, generalization, full-pipeline value, persona similarity, or production readiness.
