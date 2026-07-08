# RightBrain Learned Repair Selector v1 - Training

## 一句話結論

F 右腦候選排序器現在不只檢查語言表面，也會比較候選是否承接使用者輸入與左腦語意；權重只從訓練合約學習，並在完全不同合約指紋的 validation 上選候選。

## 資料隔離

| split | rows | unique contracts |
|---|---:|---:|
| train | 252 | 199 |
| validation | 54 | 45 |
| test | 54 | 43 |

合約指紋跨 split 重疊：`{'train_validation': 0, 'train_test': 0, 'validation_test': 0}`。三項都必須是 0。

## Validation 選擇結果

| 方法 | 選中乾淨候選 | 錯選壞候選 |
|---|---:|---:|
| first_candidate | 16.7% | 83.3% |
| seeded_random | 11.1% | 88.9% |
| length_only | 0.0% | 100.0% |
| learned_selector | 98.1% | 1.9% |

## 研究邊界

- 模型沒有讀候選來源、gold 標籤、錯誤標籤、題號或 benchmark 答案。
- 特徵是合約導向的表面、語意槽位與文字對齊訊號，因此這是 learned calibration/reranker，不是通用語意模型。
- test split 保留到獨立評測腳本，不能用來挑 epoch。
