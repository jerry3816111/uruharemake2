# RightBrain v9 Rejection Training Compare

這份報告比較 v8 與加入 rejection curriculum 後訓練出的 v9，在同一套 11 題 model-surface holdout 上的差異。

## 一句話結論

v9 rejection 補強訓練成功完成且 eval loss 下降，但在同一套 11 題 model-surface holdout 上，accepted/model-selected/final quality 指標與 v8 相同。這代表 6 筆補強資料不足以讓模型行為在 holdout 上出現可測差異，下一步應擴大 curriculum 或提高針對 semantic slot 的訓練權重。

## 訓練摘要

- baseline adapter: uruha_rightbrain_plan_sft_lora_v8_contract_v1_from_v5
- trained adapter: uruha_rightbrain_plan_sft_lora_v9_rejection_v1
- training rows: 1031 = 1025 primary + 6 supplemental
- optimizer updates: 15
- nonfinite skips: 0
- initial eval loss probe: 3.3050
- sampled eval loss: 3.2186

## Holdout 指標

| metric | v8 | v9 | delta |
|---|---:|---:|---:|
| generated_candidate_count | 10 | 10 | 0 |
| accepted_candidate_count | 4 | 4 | 0 |
| raw_candidate_acceptance_rate | 40.0% | 40.0% | 0.0% |
| model_selected_case_count | 1 | 1 | 0 |
| model_selected_case_rate | 9.1% | 9.1% | 0.0% |
| final_quality_pass_rate | 100.0% | 100.0% | 0.0% |
| final_forbidden_surface_leak_rate | 0.0% | 0.0% | 0.0% |
| final_generic_template_hit_rate | 0.0% | 0.0% | 0.0% |

## 個案差異

- 每題 final reply、model rejection reasons、accepted count 都沒有差異。

## 工程判斷

- v9 訓練本身是穩定的：沒有 non-finite loss，eval loss 有下降。
- holdout 沒變，表示 6 筆補強樣本不足以改變模型在這 11 題的輸出分布。
- 下一輪應擴大 rejection curriculum，或對 semantic slot / no ASCII / no Chinese 的樣本增加權重，而不是放鬆 gate。
