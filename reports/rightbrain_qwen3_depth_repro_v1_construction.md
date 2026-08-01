# Qwen3 1 層 / 36 層深度定位實驗

- 唯一變因：啟用 1 層或完整 36 層 Transformer。
- 固定 Metal、官方權重、LoRA、輸入、loss 與零更新。
- 1 層參數：`100930816`。
- 36 層參數：`3633509376`。
- 不含 LM head 或 cross entropy，不授權人格訓練。
