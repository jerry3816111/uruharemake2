# V75 專用左腦規劃器資料就緒稽核

## 結論

**目前禁止訓練專用左腦規劃器。**

專案共掃描 2,714 筆來源紀錄，辨識出 1,626 份完整或部分計畫。
其中 44 份通過完整結構檢查，受正式評測保護的有 44 份；嚴格人工接受的完整計畫為 0，最終可訓練資料為 0。

這不是模型失敗，而是資料用途不相容：現有 1,025 筆 canonical 資料教的是「已知計畫後怎麼用日文說」，不是「聽到原始發話後怎麼形成計畫」。

## 逐來源結果

| 來源 | 紀錄 | 計畫實例 | 完整計畫 | 嚴格人工計畫接受 | 可訓練 | 受評測保護 |
|---|---:|---:|---:|---:|---:|:---:|
| future_strict_planner_annotations | 0 | 0 | 0 | 0 | 0 | 否 |
| human_blind_surface_annotations | 19 | 19 | 0 | 0 | 0 | 否 |
| human_feedback_regression_cases | 10 | 0 | 0 | 0 | 0 | 否 |
| canonical_rightbrain_surface_training | 1025 | 1025 | 0 | 0 | 0 | 否 |
| legacy_rightbrain_training_corpora | 1036 | 0 | 0 | 0 | 0 | 否 |
| v2_human_answer_evaluation | 345 | 345 | 0 | 0 | 0 | 是 |
| cognitive_architecture_evaluation | 58 | 58 | 0 | 0 | 0 | 是 |
| v61_formal_plan_captures | 30 | 30 | 30 | 0 | 0 | 是 |
| v63_formal_plan_captures | 14 | 14 | 14 | 0 | 0 | 是 |
| reflection_experiment_outputs | 48 | 96 | 0 | 0 | 0 | 是 |
| formal_holdout_datasets | 90 | 0 | 0 | 0 | 0 | 是 |
| automatic_annotation_drafts | 39 | 39 | 0 | 0 | 0 | 否 |

## 為什麼 44 份完整計畫仍不能訓練

V61 與 V63 保存的 44 份計畫包含 BDI、三候選、記憶與路由欄位，但它們是模型在正式 holdout 上產生的答案。把它們回灌訓練會同時造成兩個問題：沒有人工證明計畫正確，以及訓練資料接觸評測輸入。

## 自訂門檻

- 60 筆：10 種能力 × 3 種輸入語言 × 每格至少 2 筆，只允許小型 pilot。
- 600 筆：每格至少 20 筆，才可預註冊正式訓練實驗。
- 以上是本專案的覆蓋設計，不是論文或官方規定的神奇樣本數。

## 下一個必要工程單位

讓正式聊天或隔離情境保存「原始發話、有限上下文、記憶選擇、心理狀態、完整候選計畫」，再由人類只審查計畫是否合理。未接受的計畫不能進訓練集；正式 benchmark 與 holdout 永遠不能進訓練集。

## 證據邊界

本輪只證明資料是否足以啟動規劃器訓練，沒有修改 runtime，也不能宣稱對話、認知、像人程度、分數或速度已改善。
