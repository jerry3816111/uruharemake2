# RightBrain max_norm 公平訓練試驗 v1 無效結果

- 判定：`invalidate_v1_due_nonreproducible_preclip_norm`
- 前 8 個 loss：兩組完全相同
- control 第一個 preclip norm：`3893.809326`
- treatment 第一個 preclip norm：`366715.875000`
- norm 比率：`94.179x`
- 相對誤差：`98.938195%`
- holdout／全新生成：`未執行`
- 正式 runtime 修改：`0`

兩組在第一次裁切前的計算完全相同，raw norm 卻不一致，因此單一變因不成立。v1 不能回答 0.3 或 3.0 哪個較好。

下一個允許步驟是使用已由 MPS、CPU float64 與逐參數合成共同驗證的 `foreach=False` 路徑重跑。
