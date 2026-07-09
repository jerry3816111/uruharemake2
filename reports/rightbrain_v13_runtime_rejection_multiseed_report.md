# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

不建議升版：多 seed 證據未同時通過候選可靠度、接管數與最終品質門檻。

## 控制變因

- baseline adapter: `uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- candidate adapter: `uruha_rightbrain_plan_sft_lora_v13_runtime_rejection_v1`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- all seeds non-inferior: `False`
- final quality guard: `True`

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

研究邊界：This gate compares adapters under matched seeds and runtime candidate count. It measures model candidate reliability and guarded integration, not human naturalness.
