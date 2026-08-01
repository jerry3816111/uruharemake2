# RightBrain AdamW 首步裁切效果診斷 v2

- 判定：`first_step_clipping_has_material_effect`
- 有效 raw gradient norm：`2.8789722919`
- 裁切係數：`0.1042038149`
- 未裁切更新 L2：`0.0023260082`
- 裁切更新 L2：`0.0018769683`
- 更新 L2 比率：`0.8069482485`
- 相對更新差：`0.3318146777`
- 更新方向 cosine：`0.9548719501`
- 權重前後一致：`True`
- optimizer step：`0`

本結果只判斷第一步理論效果，不代表小型訓練 pilot 一定會改善模型。
