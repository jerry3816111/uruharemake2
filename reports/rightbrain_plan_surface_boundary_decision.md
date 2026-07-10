# F 右腦日文回覆計畫邊界：採用決策

## 決策

採用 F 右腦日文回覆計畫邊界；V10 adapter 不變，learned selector 繼續 observe-only。

這次修正的不是左腦推理能力，而是 F 右腦的輸出責任：內部可以保留回覆策略，最終只能對使用者直接說話。

## 唯一操作變因

F 右腦候選 gate 與評分器中的日文回覆計畫外洩邊界

模型、V10 adapter、候選文字、記憶、左腦計畫、seed 與人類評分都保持不變。

## 證據一：固定真人盲評候選

| 指標 | 修改前 | 修改後 | 差異 |
|---|---:|---:|---:|
| 最高人類分數命中 | 41.7% | 58.3% | +16.7 pp |
| 平均自然度 | 2.917/5 | 3.167/5 | +0.250 |
| 平均語意 | 2.583/5 | 2.917/5 | +0.333 |
| 可直接聊天 | 33.3% | 50.0% | +16.7 pp |

控制條件為相同 12 題、48 個候選與相同人類評分。

代表性改變：

- 修改前：`返事がない不安を認め、自分で決めつけないように返す。`
- 修改後：`既読で止まると不安になるよな。でも煩いって決めつけるな。`

## 證據二：真實 V10 雙種子 shadow

| 控制與結果 | 數值 |
|---|---:|
| matched seeds | 2 |
| holdout cases | 22 |
| raw candidates | 60 |
| 前後逐字相同 raw candidates | 全部相同 |
| 新增最終表面問題 | 0 |
| 最終品質通過率 | 100.0% |

這批真實 V10 候選沒有出現待修正策略句，因此不能單獨證明修復效果；它證明的是加入邊界後安全非劣。

## Gate

| 條件 | 結果 |
|---|---|
| paired_human_preference_effect_pass | PASS |
| actual_model_shadow_safety_pass | PASS |
| actual_model_raw_candidates_fully_matched | PASS |
| actual_model_introduced_surface_issue_count_is_zero | PASS |
| learned_selector_remains_observe_only | PASS |

## 證據邊界

真人配對證據只有一位評分者與 12 題嚴格樣本；60 個真實模型候選沒有命中策略外洩，因此只能支持安全非劣，不能支持真實模型已有修復效果，也不能主張開放世界的人類自然度。

learned selector 仍輸給真人偏好基準，因此繼續 observe-only，不能接管正式回答。

V10 兩個 seed 的原始候選接受率合計仍只有 43.3%，下一個主要瓶頸仍是模型本體生成可靠度。
