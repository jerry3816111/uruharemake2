# 公開人格 Scorer Contract V4 校準結果

- 決策：`authorize_preregistration_of_a_new_matched_carrier_experiment_only`
- 校準正確：30/30
- 模型呼叫、runtime 修改、holdout 檢視、訓練授權：全部 0。

| 情境 | 正確率 |
|---|---:|
| fatigue_update_with_near_term_plan | 100.0% |
| functional_stream_start_notification | 100.0% |
| informal_public_self_introduction | 100.0% |
| minor_delay_then_positive_promotion | 100.0% |
| minor_health_uncertainty_affecting_schedule | 100.0% |

| 變形類型 | 正確率 |
|---|---:|
| canonical_positive | 100.0% |
| forbidden_injection | 100.0% |
| length_violation | 100.0% |
| missing_required | 100.0% |
| optional_omission | 100.0% |
| optional_present | 100.0% |
| order_reversal | 100.0% |
| synonym_substitution | 100.0% |

## 證據邊界

A pass proves only internal semantic consistency of the deterministic scorer on synthetic calibration probes. It does not prove that the behavioral contract is a complete description of the target public persona, that model outputs improved, or that unseen human judgments will agree.
