# Qwen3 fresh-generation pre／post 探針

- 8 個 prompt 從未用於 train、32/64-step loss holdout。
- 同一全新 LoRA 在 64-step 前後各 greedy 生成一次。
- 參考回答在兩階段生成後才載入，只用於評分。
- 不存 adapter、不使用本人原句或 benchmark。
