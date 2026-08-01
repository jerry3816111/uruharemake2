# RightBrain AdamW 首步裁切效果 v2：分析

## 結論

使用跨 process、MPS 與 CPU 都確認過的 gradient norm `2.878972` 後，
`max_norm=0.3` 對第一個 AdamW 更新具有事前定義的 **實質效果**。

裁切係數為 `0.104204`。裁切後更新 L2 是未裁切的 `80.6948%`，兩個
假想更新的相對 L2 差為 `33.1815%`，方向 cosine 為 `0.954872`。這些
結果跨過事前 material-effect 門檻，而不是事後挑選標準。

因此，下一步可以建立一個 matched clipped-versus-unclipped 小型訓練
pilot；但目前仍不能直接調整正式 max_norm 或宣稱右腦品質改善。

## 完整性

| 項目 | 結果 |
|---|---:|
| raw gradient norm | 2.8789722919 |
| 控制 norm | 2.8789722919 |
| 相對誤差 | 0 |
| clip coefficient | 0.1042038149 |
| 8 筆 loss | 8/8 與控制逐值相同 |
| 有 gradient 的張量 | 392/392 |
| 權重 SHA-256 前後 | 完全相同 |
| optimizer step | 0 |
| 模型儲存／正式 runtime 修改 | 0／0 |

## 效果量

| 指標 | 未裁切 | 裁切 |
|---|---:|---:|
| 第一更新 L2 | 0.0023260082 | 0.0018769683 |
| 相對 adapter 權重 L2 | 0.005087% | 0.004105% |

| 比較指標 | 結果 |
|---|---:|
| clipped / unclipped L2 | 0.806948 |
| 相對 L2 差 | 0.331815 |
| 更新方向 cosine | 0.954872 |
| 超過 1% 相對差的元素 | 79,045,844 / 80,740,352 |
| 超過 1% 相對差比例 | 97.9013% |

AdamW 在第一步會以 gradient 絕對值正規化，但 `epsilon=1e-6` 使這種
縮放不會完全抵消。當 gradient 乘上約 `0.1042` 後，大量小梯度元素相對
epsilon 的比例改變，因此更新幅度與整體方向都出現可量測差異。

## 語意修正紀錄

原始 v2 執行正確輸出 `material_effect=true` 與
`first_step_clipping_has_material_effect`，但沿用 v1 分類器，使
`hypothesis_confirmed` 布林欄位仍採用「near-equivalent 才成立」的舊語意。

修正流程保留原始 JSON、所有門檻與所有數值，只把正式 v2 的
`hypothesis_confirmed` 定義為事前假設所預測的 `material_effect`。修正層
沒有 backward、optimizer、模型載入或數值重算。

## 證據邊界

可以主張：

- max_norm=0.3 會實質改變這個第一步 AdamW 理論更新。
- 第一個 matched 小型訓練 pilot 已有機制依據。

不能主張：

- 不裁切或提高 max_norm 一定會改善 loss、人格或聊天品質。
- 其餘九次更新具有相同效果量。
- 已授權修改正式模型或 runtime。

下一步應讓兩個條件使用完全相同的模型、資料、seed、learning rate、更新
數與評測，只改 `max_norm=0.3` 與一個事前固定的較高門檻，先驗證訓練動態
與新生成品質，再決定是否值得擴大。
