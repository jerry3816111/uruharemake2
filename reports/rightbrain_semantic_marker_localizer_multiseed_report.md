# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

建議採用 runtime gate 改動：2 個 matched seeds 合計 raw 接受率由 51.7% 提升至 61.7%，模型接管數維持 4，且最終品質防線維持 100%。

## 控制變因

- baseline adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- candidate adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- comparison mode: `same_adapter_runtime_gate_check`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds non-inferior: `True`
- metric gate pass: `True`
- final quality guard: `True`
- diagnostic only: `False`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 31/60 (51.7%) | 37/60 (61.7%) |
| 模型實際接管 | 4/22 | 4/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用同一個 adapter，因此 rejection reason 的增加可能代表 runtime checker 更嚴格抓出原本漏標的污染，而不是模型本身退步；升版仍必須看候選接受率、接管數與最終品質。

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 46.7% | 53.3% | +6.7% | 2 | 2 |
| 20260709 | 56.7% | 70.0% | +13.3% | 2 | 2 |

## Rejection Reason Family Delta

| family | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| nonstandard_cjk_surface | 14 | 4 | -10 | improved |
| semantic_slots_missing | 16 | 10 | -6 | improved |
| cjk_language_leak | 6 | 5 | -1 | improved |
| unexpected_ascii_leak | 13 | 12 | -1 | improved |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| nonstandard_cjk_surface | 14 | 4 | -10 | improved |
| semantic_slots_missing:1/4 | 5 | 1 | -4 | improved |
| semantic_slots_missing:2/4 | 4 | 2 | -2 | improved |
| cjk_language_leak | 6 | 5 | -1 | improved |
| semantic_slots_missing:0/1 | 3 | 2 | -1 | improved |
| semantic_slots_missing:3/4 | 2 | 3 | +1 | regressed |
| unexpected_ascii_leak | 13 | 12 | -1 | improved |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| no_memory_plain_question | audited_memory | +0 | +0 | - | - |
| support_tired_no_closing_template | support | +0 | +0 | - | nonstandard_cjk_surface |
| background_family_pressure | audited_memory | +1 | +0 | - | nonstandard_cjk_surface, semantic_slots_missing:0/1 |
| explicit_spicy_food_update | audited_memory | +2 | +0 | - | semantic_slots_missing:1/4 |
| explicit_stomach_coffee | audited_memory | +3 | +0 | - | nonstandard_cjk_surface, semantic_slots_missing:3/4 |

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness. When a curriculum is supplied, holdout overlap is reported and blocks promotion.
