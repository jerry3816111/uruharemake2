# RightBrain dropout=0 梯度重現結果

- 判定：`dropout_zero_does_not_restore_gradient_reproducibility`
- 三次 gradient norm：`[2573.6162109375, 2127.049560546875, 1049475.625]`
- CV：`1.40475`
- max/min：`493.395`
- 最低 profile cosine：`0.9693948515`
- optimizer step：`0`
- 正式 runtime 修改：`0`
