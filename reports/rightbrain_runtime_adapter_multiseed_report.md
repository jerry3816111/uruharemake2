# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

建議升版：2 個 matched seeds 合計 raw 接受率由 23.3% 提升至 30.0%，模型接管數由 1 增至 3，且最終品質防線維持 100%。

## 控制變因

- baseline adapter: `uruha_v10_all_linear_lora`
- promoted adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds non-inferior: `True`
- final quality guard: `True`

## 合計結果

| 指標 | 舊 adapter | promoted adapter |
|---|---:|---:|
| raw 候選接受 | 14/60 (23.3%) | 18/60 (30.0%) |
| 模型實際接管 | 1/22 | 3/22 |
| 最終品質通過率 | 100.0% | 100.0% |

## 各 Seed

| seed | baseline raw | promoted raw | delta | baseline selected | promoted selected |
|---:|---:|---:|---:|---:|---:|
| 20260708 | 16.7% | 26.7% | +10.0% | 0 | 1 |
| 20260709 | 30.0% | 33.3% | +3.3% | 1 | 2 |

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness.
