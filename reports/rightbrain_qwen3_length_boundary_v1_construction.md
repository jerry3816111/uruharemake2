# Qwen3 完整 LM 序列長度邊界實驗

- 長度：`[64, 256, 512, 640, 704, 768, 800]`。
- 每個長度以五個獨立程序重複一次 backward。
- 唯一變因是 allocated sequence length。
- 所有條件共享同一段 64-token 有效前綴與 16 個 labels。
- 追加部分全部是 label=-100 的 padding，不參與 loss。
- 不執行 optimizer、儲存、生成、人格訓練或 production 修改。
