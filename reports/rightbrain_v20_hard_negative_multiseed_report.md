# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

不建議升版：多 seed 證據未同時通過候選可靠度、接管數與最終品質門檻。

## 控制變因

- baseline adapter: `configured_default`
- candidate adapter: `uruha_rightbrain_plan_sft_lora_v20_hard_negative_simpo_v1`
- comparison mode: `adapter_promotion_gate`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds raw-acceptance non-inferior: `False`
- metric gate pass: `False`
- runtime shadow safety pass: `False`
- final quality guard: `False`
- diagnostic only: `False`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 26/60 (43.3%) | 23/60 (38.3%) |
| 模型實際接管 | 3/22 | 2/22 |
| 最終品質通過率 | 100.0% | 95.5% |
| 同版 checker 重評的表面通過率 | 100.0% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用不同 adapter，因此 rejection reason 增減主要反映候選模型輸出品質差異。

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 40.0% | 33.3% | -6.7% | 1 | 0 |
| 20260709 | 46.7% | 43.3% | -3.3% | 2 | 2 |

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
| semantic_slots_missing | 10 | 17 | +7 | regressed |
| unexpected_ascii_leak | 12 | 19 | +7 | regressed |
| cjk_language_leak | 5 | 9 | +4 | regressed |
| awkward_or_caregiver_surface | 5 | 3 | -2 | improved |
| nonstandard_cjk_surface | 6 | 8 | +2 | regressed |
| polite_tone_drift | 7 | 5 | -2 | improved |
| ascii_symbol_artifact | 2 | 3 | +1 | regressed |
| unicode_replacement_character | 0 | 1 | +1 | regressed |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| unexpected_ascii_leak | 12 | 19 | +7 | regressed |
| cjk_language_leak | 5 | 9 | +4 | regressed |
| semantic_slots_missing:2/3 | 0 | 3 | +3 | regressed |
| awkward_or_caregiver_surface | 5 | 3 | -2 | improved |
| nonstandard_cjk_surface | 6 | 8 | +2 | regressed |
| polite_tone_drift | 7 | 5 | -2 | improved |
| semantic_slots_missing:0/1 | 2 | 4 | +2 | regressed |
| semantic_slots_missing:1/2 | 1 | 3 | +2 | regressed |
| semantic_slots_missing:2/4 | 2 | 4 | +2 | regressed |
| semantic_slots_missing:3/4 | 3 | 1 | -2 | improved |
| ascii_symbol_artifact | 2 | 3 | +1 | regressed |
| semantic_slots_missing:0/4 | 1 | 0 | -1 | improved |
| semantic_slots_missing:1/4 | 1 | 2 | +1 | regressed |
| unicode_replacement_character | 0 | 1 | +1 | regressed |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| support_read_receipt_self_blame | support | -2 | -1 | semantic_slots_missing:2/3 | duplicate_candidate |
| no_memory_plain_question | audited_memory | -1 | +0 | cjk_language_leak, foreign_script_leak, missing_japanese_surface, unicode_replacement_character | - |
| private_do_not_mention | audited_memory | -1 | +0 | ascii_symbol_artifact | over_max_chars |
| reference_fragment_probe | repair | -1 | +0 | cjk_language_leak, unexpected_ascii_leak | - |
| support_tired_no_closing_template | support | -1 | +0 | duplicate_candidate, nonstandard_cjk_surface | awkward_or_caregiver_surface |
| daily_state_answer | daily | +0 | +0 | nonstandard_cjk_surface, over_max_chars, unexpected_ascii_leak | awkward_or_caregiver_surface |
| explicit_spicy_food_update | audited_memory | +0 | +0 | nonstandard_punctuation, semantic_slots_missing:1/4 | - |
| absurdity_mirror_quantum_police | tease | +1 | +0 | unexpected_ascii_leak | foreign_script_leak, semantic_slots_missing:0/1 |
| background_family_pressure | audited_memory | +1 | +0 | semantic_slots_missing:0/1 | nonstandard_cjk_surface, nonstandard_punctuation, polite_tone_drift |
| explicit_stomach_coffee | audited_memory | +1 | +0 | nonstandard_cjk_surface | missing_japanese_surface, polite_tone_drift, semantic_slots_missing:0/4 |

研究邊界：此 gate 在相同 seed、相同候選數下進行配對比較；同 adapter 的 runtime checker 比較還要求每題 raw candidates 完全相同。它只證明已定義表面缺陷的攔截與受保護整合，不等同完整的人類自然度。若提供 curriculum report，會檢查 holdout overlap；有重疊時會阻止升版。
