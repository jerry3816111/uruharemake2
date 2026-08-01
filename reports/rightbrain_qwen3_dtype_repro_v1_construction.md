# Qwen3 bfloat16 / float16 梯度重現實驗

- 唯一變因：base model compute dtype。
- 兩組皆固定 640 tokens、36 層、全 LoRA、相同 labels 與 loss。
- 每種 dtype 十個獨立程序，各執行一次 backward。
- LoRA trainable parameters 維持 float32。
- 不執行 optimizer、儲存、生成或人格訓練。
