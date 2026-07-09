# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

建議採用 runtime gate 改動：2 個 matched seeds 合計 raw 接受率由 43.3% 提升至 51.7%，模型接管數由 3 增至 4，且最終品質防線維持 100%。

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
| raw 候選接受 | 26/60 (43.3%) | 31/60 (51.7%) |
| 模型實際接管 | 3/22 | 4/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用同一個 adapter，因此 rejection reason 的增加可能代表 runtime checker 更嚴格抓出原本漏標的污染，而不是模型本身退步；升版仍必須看候選接受率、接管數與最終品質。

## 各 Seed

| seed | baseline raw | candidate raw | delta | baseline selected | candidate selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 36.7% | 46.7% | +10.0% | 1 | 2 |
| 20260709 | 50.0% | 56.7% | +6.7% | 2 | 2 |

## Rejection Reason Family Delta

| family | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| duplicate_candidate | 6 | 1 | -5 | improved |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| duplicate_candidate | 6 | 1 | -5 | improved |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| reference_fragment_probe | repair | +0 | +1 | - | - |
| support_tired_no_closing_template | support | +1 | +0 | - | duplicate_candidate |
| absurdity_mirror_quantum_police | tease | +2 | +0 | - | duplicate_candidate |
| daily_state_answer | daily | +2 | +0 | - | duplicate_candidate |

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness. When a curriculum is supplied, holdout overlap is reported and blocks promotion.
