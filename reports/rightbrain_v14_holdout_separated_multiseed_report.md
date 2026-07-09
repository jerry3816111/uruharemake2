# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

不建議升版：多 seed 證據未同時通過候選可靠度、接管數與最終品質門檻。

## 控制變因

- baseline adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- candidate adapter: `uruha_rightbrain_plan_sft_lora_v14_holdout_separated_v1`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds non-inferior: `False`
- metric gate pass: `False`
- final quality guard: `True`
- diagnostic only: `False`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 18/60 (30.0%) | 12/60 (20.0%) |
| 模型實際接管 | 3/22 | 1/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 26.7% | 20.0% | -6.7% | 1 | 0 |
| 20260709 | 33.3% | 20.0% | -13.3% | 2 | 1 |

## 資料邊界

| 指標 | 值 |
|---|---:|
| training rows | 40 |
| holdout case overlap | 0 |
| holdout target overlap | 0 |

No holdout case or target overlap was detected in the supplied curriculum.

## Rejection Reason Family Delta

| family | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| semantic_slots_missing | 24 | 29 | +5 | regressed |
| polite_tone_drift | 4 | 8 | +4 | regressed |
| unexpected_ascii_leak | 30 | 26 | -4 | improved |
| cjk_language_leak | 3 | 6 | +3 | regressed |
| missing_japanese_surface | 1 | 0 | -1 | improved |
| over_max_chars | 5 | 4 | -1 | improved |
| unicode_replacement_character | 0 | 1 | +1 | regressed |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| polite_tone_drift | 4 | 8 | +4 | regressed |
| unexpected_ascii_leak | 30 | 26 | -4 | improved |
| cjk_language_leak | 3 | 6 | +3 | regressed |
| semantic_slots_missing:0/1 | 7 | 10 | +3 | regressed |
| semantic_slots_missing:2/4 | 4 | 7 | +3 | regressed |
| semantic_slots_missing:1/3 | 1 | 3 | +2 | regressed |
| missing_japanese_surface | 1 | 0 | -1 | improved |
| over_max_chars | 5 | 4 | -1 | improved |
| semantic_slots_missing:0/2 | 1 | 0 | -1 | improved |
| semantic_slots_missing:0/4 | 1 | 0 | -1 | improved |
| semantic_slots_missing:1/2 | 1 | 2 | +1 | regressed |
| semantic_slots_missing:1/4 | 5 | 4 | -1 | improved |
| semantic_slots_missing:3/4 | 2 | 1 | -1 | improved |
| unicode_replacement_character | 0 | 1 | +1 | regressed |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| support_read_receipt_self_blame | support | -2 | -2 | cjk_language_leak, nonstandard_cjk_surface, polite_tone_drift | - |
| reference_fragment_probe | repair | -2 | -1 | cjk_language_leak, semantic_slots_missing:0/1 | - |
| background_family_pressure | audited_memory | -2 | +0 | polite_tone_drift | - |
| support_tired_no_closing_template | support | -2 | +0 | - | - |
| daily_state_answer | daily | +0 | +0 | - | duplicate_candidate |
| explicit_spicy_food_update | audited_memory | +0 | +0 | - | semantic_slots_missing:3/4 |
| explicit_stomach_coffee | audited_memory | +0 | +0 | - | missing_japanese_surface, semantic_slots_missing:0/4 |
| private_do_not_mention | audited_memory | +0 | +0 | - | over_max_chars, semantic_slots_missing:0/2 |
| absurdity_mirror_quantum_police | tease | +1 | +0 | - | semantic_slots_missing:0/1, unexpected_ascii_leak |
| no_memory_plain_question | audited_memory | +1 | +1 | cjk_language_leak, unicode_replacement_character | polite_tone_drift |

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness. When a curriculum is supplied, holdout overlap is reported and blocks promotion.
