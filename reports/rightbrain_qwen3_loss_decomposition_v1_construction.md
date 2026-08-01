# Qwen3 loss 分解梯度定位實驗

- 唯一變因：完整 cross-entropy、target score、logsumexp。
- 三組共享完整 36 層模型、LoRA、512 tokens、labels 與 seed。
- 每組 18 個隔離程序；六種條件順序各重複三次。
- 不執行 optimizer、儲存、生成、人格訓練或 production 修改。
