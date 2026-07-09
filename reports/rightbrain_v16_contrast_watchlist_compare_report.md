# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

不建議升版：多 seed 證據未同時通過候選可靠度、接管數與最終品質門檻。

## 控制變因

- baseline adapter: `configured_default`
- candidate adapter: `uruha_rightbrain_plan_sft_lora_v16_contrast_watchlist_v1`
- comparison mode: `adapter_promotion_gate`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds non-inferior: `False`
- metric gate pass: `False`
- final quality guard: `True`
- diagnostic only: `False`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 32/60 (53.3%) | 31/60 (51.7%) |
| 模型實際接管 | 4/22 | 5/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用不同 adapter，因此 rejection reason 增減主要反映候選模型輸出品質差異。

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 53.3% | 60.0% | +6.7% | 2 | 3 |
| 20260709 | 53.3% | 43.3% | -10.0% | 2 | 2 |

## 資料邊界

| 指標 | 值 |
|---|---:|
| training rows | 32 |
| holdout case overlap | 0 |
| holdout target overlap | 0 |

No holdout case or target overlap was detected in the supplied curriculum report.

## Rejection Reason Family Delta

| family | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| semantic_slots_missing | 10 | 16 | +6 | regressed |
| cjk_language_leak | 5 | 6 | +1 | regressed |
| duplicate_candidate | 1 | 2 | +1 | regressed |
| missing_japanese_surface | 1 | 0 | -1 | improved |
| nonstandard_cjk_surface | 6 | 5 | -1 | improved |
| nonstandard_punctuation | 1 | 0 | -1 | improved |
| over_max_chars | 3 | 4 | +1 | regressed |
| polite_tone_drift | 7 | 8 | +1 | regressed |
| unexpected_ascii_leak | 12 | 13 | +1 | regressed |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| semantic_slots_missing:0/1 | 2 | 5 | +3 | regressed |
| semantic_slots_missing:3/4 | 3 | 6 | +3 | regressed |
| cjk_language_leak | 5 | 6 | +1 | regressed |
| duplicate_candidate | 1 | 2 | +1 | regressed |
| missing_japanese_surface | 1 | 0 | -1 | improved |
| nonstandard_cjk_surface | 6 | 5 | -1 | improved |
| nonstandard_punctuation | 1 | 0 | -1 | improved |
| over_max_chars | 3 | 4 | +1 | regressed |
| polite_tone_drift | 7 | 8 | +1 | regressed |
| semantic_slots_missing:0/4 | 1 | 0 | -1 | improved |
| semantic_slots_missing:2/3 | 0 | 1 | +1 | regressed |
| unexpected_ascii_leak | 12 | 13 | +1 | regressed |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| daily_state_answer | daily | -3 | +0 | duplicate_candidate, semantic_slots_missing:0/1 | - |
| support_read_receipt_self_blame | support | -1 | -1 | cjk_language_leak, nonstandard_cjk_surface, over_max_chars, polite_tone_drift, semantic_slots_missing:2/3 | - |
| explicit_stomach_coffee | audited_memory | -1 | +0 | foreign_script_leak, semantic_slots_missing:3/4 | cjk_language_leak, missing_japanese_surface, semantic_slots_missing:0/4 |
| reference_fragment_probe | repair | -1 | +0 | cjk_language_leak, unexpected_ascii_leak | polite_tone_drift |
| explicit_spicy_food_update | audited_memory | +0 | +0 | - | cjk_language_leak, nonstandard_cjk_surface |
| private_do_not_mention | audited_memory | +0 | +0 | - | - |
| absurdity_mirror_quantum_police | tease | +1 | +0 | unexpected_ascii_leak | foreign_script_leak, semantic_slots_missing:0/1 |
| support_tired_no_closing_template | support | +1 | +0 | - | - |
| no_memory_plain_question | audited_memory | +1 | +1 | cjk_language_leak | polite_tone_drift |
| background_family_pressure | audited_memory | +2 | +1 | - | nonstandard_cjk_surface, nonstandard_punctuation |

研究邊界：此 gate 在相同 seed 與相同候選數下比較 adapter。它測的是模型候選可靠度與受保護整合，不是完整的人類自然度。若提供 curriculum report，會檢查 holdout overlap；有重疊時會阻止升版。
