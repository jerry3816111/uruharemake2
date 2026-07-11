# RightBrain V27 單一變因比較

## 結論

在資料、V10 起點、MPO、NLL、seed 與 epoch 全部固定時，learning rate 由 1e-7 提高到 3e-7 沒有提高未見回答的絕對排序，因此拒絕 V27，正式右腦維持 V10。

| 指標 | V26 (1e-7) | V27 (3e-7) |
|---|---:|---:|
| 訓練更新 / 非有限跳過 | 8 / 0 | 8 / 0 |
| 未見相對偏好 | 79.41% | 61.76% |
| 未見絕對偏好 | 26.47% | 23.53% |
| 絕對偏好變化 | +0.00% | -2.94% |
| 正回答集合機率增加 | +0.58% | +0.43% |
| 通過 gate | 12/16 | 9/16 |

控制變因一致：PASS

## 下一個有意義的證據步驟

停止只增加學習率或 epoch。下一步先把現有人類盲評轉成可追溯的多維偏好診斷，檢查現行自動 contract 標籤是否真的對應自然、完整、有人格的人類回答；資料 gate 通過前不再訓練。

研究邊界：This paired run rejects this V27 candidate under one fixed seed and frozen dataset. It does not prove that every larger learning rate is universally harmful. The current labels measure strict contract realization rather than broad human preference.
