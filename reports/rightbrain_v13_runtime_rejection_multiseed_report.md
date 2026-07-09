# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

不建議升版：這次比較含有訓練資料與 holdout case/target 重疊，只能作為 diagnostic/dev 證據；即使分數上升也不能當成可上線 promotion evidence。此外，多 seed 數字本身也未同時通過候選可靠度、接管數與最終品質門檻。

## 控制變因

- baseline adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- candidate adapter: `uruha_rightbrain_plan_sft_lora_v13_runtime_rejection_v1`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds non-inferior: `False`
- metric gate pass: `False`
- final quality guard: `True`
- diagnostic only: `True`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 18/60 (30.0%) | 15/60 (25.0%) |
| 模型實際接管 | 3/22 | 2/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 26.7% | 36.7% | +10.0% | 1 | 2 |
| 20260709 | 33.3% | 13.3% | -20.0% | 2 | 0 |

## 資料邊界

| 指標 | 值 |
|---|---:|
| training rows | 40 |
| holdout case overlap | 10 |
| holdout target overlap | 10 |

Candidate training data overlaps the evaluated holdout case IDs or target replies. This comparison is useful for debugging but must not be used as promotion evidence.

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| background_family_pressure | audited_memory | -1 | +0 | - | - |
| daily_state_answer | daily | -1 | +0 | - | - |
| private_do_not_mention | audited_memory | -1 | +0 | - | - |
| support_read_receipt_self_blame | support | +0 | -1 | semantic_slots_missing:0/3 | over_max_chars |
| explicit_spicy_food_update | audited_memory | +0 | +0 | - | - |
| explicit_stomach_coffee | audited_memory | +0 | +0 | - | missing_japanese_surface, semantic_slots_missing:0/4 |
| no_memory_plain_question | audited_memory | +0 | +0 | missing_japanese_surface | nonstandard_cjk_surface |
| reference_fragment_probe | repair | +0 | +0 | duplicate_candidate | over_max_chars |
| support_tired_no_closing_template | support | +0 | +0 | - | - |

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness. When a curriculum is supplied, holdout overlap is reported and blocks promotion.
