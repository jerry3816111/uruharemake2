# Qwen3 反向傳播邊界定位實驗

- 唯一變因：完整鏈、LM head 到 hidden、hidden 到 Transformer。
- 三組共享模型、LoRA、512 tokens、seed 與裝置。
- 每組 18 個隔離程序；六種執行順序各重複三次。
- Transformer 邊界使用固定、來源獨立且 hash 鎖定的上游梯度。
- 不執行 optimizer、儲存、生成、人格訓練或 production 修改。
