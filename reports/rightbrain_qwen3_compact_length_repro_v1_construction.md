# Qwen3 512 / 640 token 梯度重現實驗

- 唯一變因：allocated sequence length 為 512 或 640。
- 兩組共享同一 64-token 有效前綴與 16 個 labels。
- 每組 20 個獨立程序，各執行一次 backward。
- 舊 compact serializer 曾降低 tokens 但品質退步，本輪不採用它。
- 不執行 optimizer、儲存、生成、人格訓練或 production 修改。
