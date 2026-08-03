# Qwen3 active-head 64-step 延長探針

- 唯一變因：相同 16 筆排程從 32 更新延長到 64 更新。
- 32-step 的逐輪平均 loss 再下降：`0.0271303653717041`。
- 模型、資料、learning rate、gradient clipping、holdout 與門檻不變。
- 不儲存 adapter、不生成、不使用本人原句或 benchmark。
