# Qwen3 Metal free-cache 梯度重現實驗

- 唯一變因：Metal free-buffer cache 保持預設或設為 0。
- 兩組皆固定 BF16、640 tokens、36 層、全 LoRA、相同 loss。
- 每種 cache mode 十個獨立程序，各執行一次 backward。
- 不執行 optimizer、儲存、生成或人格訓練。
