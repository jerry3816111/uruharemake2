# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

不建議升版：多 seed 證據未同時通過候選可靠度、接管數與最終品質門檻。

## 控制變因

- baseline adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- candidate adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- comparison mode: `same_adapter_runtime_gate_check`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds non-inferior: `True`
- metric gate pass: `False`
- final quality guard: `True`
- diagnostic only: `False`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 18/60 (30.0%) | 18/60 (30.0%) |
| 模型實際接管 | 3/22 | 3/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用同一個 adapter，因此 rejection reason 的增加可能代表 runtime checker 更嚴格抓出原本漏標的污染，而不是模型本身退步；升版仍必須看候選接受率、接管數與最終品質。

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 26.7% | 26.7% | +0.0% | 1 | 1 |
| 20260709 | 33.3% | 33.3% | +0.0% | 2 | 2 |

## Rejection Reason Family Delta

| family | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| nonstandard_cjk_surface | 10 | 14 | +4 | stricter_detection |
| semantic_slots_missing | 24 | 23 | -1 | improved |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| nonstandard_cjk_surface | 10 | 14 | +4 | stricter_detection |
| semantic_slots_missing:0/1 | 7 | 6 | -1 | improved |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| background_family_pressure | audited_memory | +0 | +0 | - | - |
| no_memory_plain_question | audited_memory | +0 | +0 | - | - |

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness. When a curriculum is supplied, holdout overlap is reported and blocks promotion.
