# Qwen3 單層 CPU / Metal 後向定位實驗

- 唯一變因：MLX 執行裝置（CPU 或 Metal GPU）。
- 官方 Qwen3 第 1 層參數：`100930816`。
- LoRA 可訓練參數：`1835008`。
- 固定輸入：`[1, 64, 2560]`。
- 每個裝置獨立執行三次，零 optimizer update。
- 本實驗只定位後端，不授權人格訓練或 production 修改。
