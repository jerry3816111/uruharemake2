# Qwen3 active-head 單次 optimizer update canary

- 固定 active-token 完整反向路徑，只新增一次 clipped AdamW update。
- 9 個隔離程序；每次從相同 base 與 fresh LoRA 開始。
- 更新只存在記憶體；不儲存、不生成、不修改 production。
- 只有非零、有限、受限且跨程序一致的更新才可通過。
