# RightBrain MLX dropout=0 梯度結果

- 判定：`mlx_dropout_zero_does_not_restore_gradient_reproducibility`
- 三次執行完成：`True`
- 量測：`{"gradient_norms": [755772.6168452774, 841401.2065827517, 1011895.8761133733], "mean_gradient_norm": 869689.8998471341, "gradient_norm_coefficient_of_variation": 0.12240918425707872, "gradient_norm_max_to_min_ratio": 1.3388893081853082, "pairwise_group_profile_cosines": [0.9998216141016687, 0.9831170923214293, 0.9801873989241868], "minimum_pairwise_group_profile_cosine": 0.9801873989241868, "gradient_hashes": ["4e5afb4a5dd0a5d82e886559d328c831d1f44ac9963301cb6582d567d2109c7c", "6e4c6ca1737dc941c2b0d2c46b40a4820a736a7ef002c146eba531ebcf88d27c", "72090d26beecdba95cb46788c766e06b1df54e888efefda285d48cf0dd0ea190"], "gradient_hashes_identical": false, "losses": [3.84375, 0.8125, 2.1500000953674316, 5.443749904632568, 2.91015625, 2.7532894611358643, 2.56640625, 3.1136362552642822], "peak_memory_bytes": [17673428010, 17673428010, 17673428010], "duration_seconds": [85.621, 85.439, 85.666]}`
- optimizer step：`0`
- production 修改：`0`
