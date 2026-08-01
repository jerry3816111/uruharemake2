# RightBrain max_norm 公平訓練試驗 v2 無效結果

- 判定：`invalidate_v2_before_holdout_due_backward_nondeterminism`
- `foreach=False`：兩組全部更新皆成立
- 前 8 個 loss：完全一致
- control 第一個 raw norm：`3.3520023823`
- treatment 第一個 raw norm：`534403.8125000000`
- 相對誤差：`99.999373%`
- holdout／全新生成：`未執行`
- 正式 runtime 修改：`0`

v2 排除了 foreach reduction，但 backward 本身仍無法跨程序重現。下一步只能做零更新因素診斷，不能直接重訓。
