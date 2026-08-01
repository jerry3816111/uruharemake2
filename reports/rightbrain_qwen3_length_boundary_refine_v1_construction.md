# Qwen3 640-704 token 邊界精煉實驗

- 長度：`[640, 656, 672, 688, 704]`。
- 每個長度十個獨立程序，各執行一次 backward。
- 唯一變因是 allocated sequence length。
- 所有條件共享相同 64-token 有效前綴與 16 個 labels。
- 追加內容全部為 label=-100，不參與 loss。
- 不授權訓練、儲存、生成、人格或 production 主張。
