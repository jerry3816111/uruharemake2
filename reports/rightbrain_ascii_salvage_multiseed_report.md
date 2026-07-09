# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

建議採用 runtime gate 改動：2 個 matched seeds 合計 raw 接受率由 30.0% 提升至 43.3%，模型接管數維持 3，且最終品質防線維持 100%。

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
| raw 候選接受 | 18/60 (30.0%) | 26/60 (43.3%) |
| 模型實際接管 | 3/22 | 3/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用同一個 adapter，因此 rejection reason 的增加可能代表 runtime checker 更嚴格抓出原本漏標的污染，而不是模型本身退步；升版仍必須看候選接受率、接管數與最終品質。

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 26.7% | 36.7% | +10.0% | 1 | 1 |
| 20260709 | 33.3% | 50.0% | +16.7% | 2 | 2 |

## Rejection Reason Family Delta

| family | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| unexpected_ascii_leak | 30 | 13 | -17 | improved |
| semantic_slots_missing | 23 | 16 | -7 | improved |
| duplicate_candidate | 2 | 6 | +4 | regressed |
| cjk_language_leak | 3 | 6 | +3 | regressed |
| over_max_chars | 5 | 3 | -2 | improved |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| unexpected_ascii_leak | 30 | 13 | -17 | improved |
| duplicate_candidate | 2 | 6 | +4 | regressed |
| cjk_language_leak | 3 | 6 | +3 | regressed |
| semantic_slots_missing:0/1 | 6 | 3 | -3 | improved |
| over_max_chars | 5 | 3 | -2 | improved |
| semantic_slots_missing:2/3 | 2 | 0 | -2 | improved |
| semantic_slots_missing:0/2 | 1 | 0 | -1 | improved |
| semantic_slots_missing:1/3 | 1 | 0 | -1 | improved |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| absurdity_mirror_quantum_police | tease | +0 | +0 | - | unexpected_ascii_leak |
| daily_state_answer | daily | +0 | +0 | - | semantic_slots_missing:0/1, unexpected_ascii_leak |
| explicit_spicy_food_update | audited_memory | +0 | +0 | cjk_language_leak | - |
| explicit_stomach_coffee | audited_memory | +0 | +0 | - | - |
| no_memory_plain_question | audited_memory | +1 | +0 | - | - |
| private_do_not_mention | audited_memory | +1 | +0 | - | semantic_slots_missing:0/2 |
| support_tired_no_closing_template | support | +1 | +0 | duplicate_candidate | semantic_slots_missing:0/1 |
| support_read_receipt_self_blame | support | +2 | +0 | duplicate_candidate | over_max_chars, semantic_slots_missing:1/3, semantic_slots_missing:2/3 |
| reference_fragment_probe | repair | +3 | +0 | - | over_max_chars, unexpected_ascii_leak |

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness. When a curriculum is supplied, holdout overlap is reported and blocks promotion.
