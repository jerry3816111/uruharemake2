# RightBrain MLX 單步梯度定位結果

- 判定：`single_step_backward_is_already_unstable`
- 定位：`isolate_checkpointed_backward_kernel_or_dtype`
- 三次執行完成：`True`
- 量測：`{"gradient_norms": [949045.7864385556, 6.288678883442298, 6.288678883442298], "mean_gradient_norm": 316352.7879321075, "gradient_norm_coefficient_of_variation": 1.4141854496606245, "gradient_norm_max_to_min_ratio": 150913.38006418713, "pairwise_group_profile_cosines": [0.9901494515758406, 0.9901494515758406, 1.0], "minimum_pairwise_group_profile_cosine": 0.9901494515758406, "gradient_hashes": ["79473f32a7a65fb7423dd702f11b27fde7fac376e4214bc2bd35419485424c8c", "4de67b3003eae998d8fa9b3191b9a7157ba86ad8eecdb567d2aa7c0ef04086bf", "4de67b3003eae998d8fa9b3191b9a7157ba86ad8eecdb567d2aa7c0ef04086bf"], "gradient_hashes_identical": false, "losses": [3.84375], "peak_memory_bytes": [17350466602, 17350466602, 17350466602], "duration_seconds": [14.132, 14.448, 14.229]}`
- optimizer step：`0`
- production 修改：`0`
