# Qwen3 active-head 多批次 train／holdout 探針

- 固定 32 次更新；從單一重複 batch 改成 16 筆來源分組資料的兩輪訓練。
- Holdout 16 筆使用完全不同 source_id，更新前後只讀評估。
- Train、holdout、target policy、neutral policy 必須同時符合門檻。
- 不儲存 adapter、不生成、不使用本人原句或 benchmark。
