# RightBrain V27 Group MPO 決策

## 結論

V27 未通過群組訓練 gate，不執行 runtime holdout，正式右腦維持 V10。

相對 reference 的未見排序為 61.8%，模型絕對排序由 26.5% 變為 23.5% (-2.9%)，正集合機率變化 +0.43%。絕對錯排反而增加，這個候選必須拒絕；不能把相對 reference 的位移誤報為實際能力提升。

| 指標 | 訓練前 | 訓練後 |
|---|---:|---:|
| train 相對 reference 排序 | 0.0% | 58.5% |
| unseen 相對 reference 排序 | 0.0% | 61.8% |
| train 模型絕對排序 | 39.6% | 39.6% |
| unseen 模型絕對排序 | 26.5% | 23.5% |
| unseen 正集合機率質量 | 58.3% | 58.8% |
| unseen 全正回答高於全負回答 | - | 25.0% |
| unseen 組內最高為正回答 | - | 50.0% |

凍結 V10 的絕對機率 probe 勝率為 26.5%。相對分數衡量每個回答相對 V10 移動的方向；模型絕對排序才表示最後模型是否真的翻轉原本錯排。

## Gate

| 條件 | 結果 |
|---|---|
| train_eval_source_overlap_is_zero | PASS |
| all_group_updates_completed | PASS |
| nonfinite_training_events_are_zero | PASS |
| frozen_reference_identity_delta_at_most_5e_4 | PASS |
| train_pairwise_positive_preference_at_least_75pct | FAIL |
| unseen_pairwise_positive_preference_at_least_75pct | FAIL |
| unseen_strict_group_separation_at_least_50pct | FAIL |
| unseen_positive_top1_at_least_75pct | FAIL |
| unseen_positive_mass_gain_at_least_5pp | FAIL |
| unseen_mean_group_margin_improved | PASS |
| train_absolute_pairwise_preference_improved | FAIL |
| unseen_absolute_pairwise_preference_improved | FAIL |
| unseen_absolute_mean_margin_improved | PASS |
| positive_likelihood_evidence_is_complete | PASS |
| unseen_mean_positive_log_prob_non_decreasing | PASS |
| unseen_positive_likelihood_decrease_rate_at_most_50pct | PASS |

下一個單一變因：候選仍未達 promotion gate；下一個實驗必須依失敗 gate 選擇單一變因，不能直接上線。

研究邊界：Passing these likelihood gates would authorize only actual-generation comparison against V10. Relative policy/reference ranking is reported separately from absolute policy ranking. No matched all-pairs training control has been run yet, so this experiment cannot isolate the MPO objective as the cause of any gain. It does not by itself prove more human-like dialogue or authorize promotion.
