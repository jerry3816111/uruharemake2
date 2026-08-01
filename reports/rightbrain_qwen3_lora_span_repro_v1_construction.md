# Qwen3 LoRA 覆蓋層數定位實驗

- 唯一變因：36 層圖中有 1 層或全部 36 層啟用 LoRA。
- 第 1 層 LoRA 初始化在兩組完全相同。
- 1 層 LoRA 參數：`1835008`。
- 36 層 LoRA 參數：`66060288`。
- 固定 Metal、輸入、MSE、零 checkpoint 與零 optimizer update。
