# Qwen3 provider-pair CPO objective probe

- 唯一變因：pairwise objective weight `0` 或 `1`。
- 16 個平衡 train rows，各做 16 次更新。
- 8 個 holdout prompts 來自四個先前完全未使用來源。
- 不生成文字、不保存 adapter、不使用本人原句或 benchmark。
