# Qwen3 active-head 短程收斂軌跡探針

- 唯一變因：相同 optimizer 路徑從 1 次更新增加為 32 次。
- 3 個隔離程序；每次從相同 base 與 fresh LoRA 開始。
- 必須同時有限、受限、逐程序完全一致，而且 loss 明確下降。
- 只做單一 micro-batch 的可學習性檢查；不儲存、不生成、不修改 production。
