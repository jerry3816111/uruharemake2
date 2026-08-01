# 人格策略 prompt token 公平配置最終審查

**final_review_passed**

| 檢查 | 結果 |
|---|---:|
| target／neutral 配對情境 | 6 |
| 每次配置 prompt tokens | 640／640 |
| 原有效 token 序列保留 | 12／12 |
| 左側 padding 完全遮罩 | 12／12 |
| legacy 行為變更 | 0 |
| focused tests | 93／93 |
| expanded behavior tests | 250／250 |
| 真模型權重載入／生成 | 0／0 |

本輪消除了 target 與 neutral 因 prompt 張量長度不同而造成的算力混淆：兩邊都配置 640 tokens，較短的一邊只補 `attention_mask=0` 的左側 padding。原有效 tokens 不截斷、不重排，實際有效長度差異仍保留在 ledger，不偽裝成相同內容。

1 項 V90 歷史來源 SHA 鎖因 `uruha_brain_mac.py` 本輪變更而失效；其 5 項實際行為與證據邊界測試均通過，所以不判為行為回歸，也不修改歷史鎖。

本輪只授權合併與下一個小型實際本機模型 target／neutral pilot。它尚未產生人格相似度、自然度或正式上線證據。
