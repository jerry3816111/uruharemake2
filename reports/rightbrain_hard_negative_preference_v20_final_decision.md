# RightBrain V20 最終決策

## 結論

V20 通過 synthetic 前置檢查，但真實模型雙 seed 退步，因此不升級；正式右腦維持 V10。

## Synthetic 前置證據

| 指標 | 訓練前 | 訓練後 |
|---|---:|---:|
| 未見 pair 偏好正確率 | 100.0% | 100.0% |
| 未見平均 margin | +1.259030 | +1.273806 |

## 真實模型雙 Seed

| 指標 | V10 | V20 | 差異 |
|---|---:|---:|---:|
| raw 候選接受率 | 43.3% | 38.3% | -5.0 pp |
| 模型接管 | 3/22 | 2/22 | -1 |
| 最終品質 | 100.0% | 95.5% | -4.5 pp |

## 為什麼拒絕升級

V20 的未見 synthetic pair 在訓練前已達 100% 偏好正確率，訓練後只有極小 margin 增益；這個訊號沒有轉移到真實生成，反而使語意缺漏與語言污染增加。

| 退步錯誤族群 | V10 | V20 | 增加 |
|---|---:|---:|---:|
| semantic_slots_missing | 10 | 17 | +7 |
| unexpected_ascii_leak | 12 | 19 | +7 |
| cjk_language_leak | 5 | 9 | +4 |
| nonstandard_cjk_surface | 6 | 8 | +2 |
| ascii_symbol_artifact | 2 | 3 | +1 |
| unicode_replacement_character | 0 | 1 | +1 |

## 下一個有意義的實驗

下一輪應改用與正式 holdout 分離的開發情境，收集 V10 真實生成的自然錯誤候選作為 on-policy preference data；訓練前還要先確認未見 pair 不是 100% 飽和。

研究邊界：這份決策證明 V20 這組資料與訓練方法未改善指定的 11-case actual-model holdout；它不代表所有 preference learning 都無效，也不代表完整人類自然度已被測量。
