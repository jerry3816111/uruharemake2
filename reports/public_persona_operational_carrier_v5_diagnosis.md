# Operational Carrier V5 負面結果診斷

## 結果

| 條件 | 語意 | V4 人格 | 表面 gate | 中位延遲 |
|---|---:|---:|---:|---:|
| 靜態人格 | 18/20 | 12/15 | 14/20 | 3.618s |
| 抽象 carrier | 18/20 | 12/15 | 16/20 | 4.174s |
| 自然日文 carrier | 18/20 | 12/15 | 17/20 | 4.281s |

自然日文規則改善了表面品質，但人格通過數沒有增加；相對兩個控制組都是新增 1 題、退步 1 題、表面退步 1 題，所以正式失敗。

## 架構診斷

- `notice_01` 的 V4 契約要求入口指示，但左腦 speech plan 只有「開始」與「內容」，沒有入口內容。右腦同時被要求不得新增或改寫左腦內容，因此右腦 carrier 無法可靠補上。
- `health_01` 自然日文 carrier 保留語意但變得過長，證明更多表達指令仍可能增加負荷與冗詞。
- `fatigue_02` 三組都使用「へろへろ」，目前 deterministic scorer 只接受「疲／へとへと」，顯示同義詞覆蓋仍不是完整的人類語意評估。

## 下一個可推翻假設

把 V3 `planning_policy` 的 dialogue act、content order 與 epistemic boundary 編譯進左腦 speech plan，再讓右腦只做語句實現，應比要求右腦補認知內容更符合目前的左右腦責任邊界。下一輪必須只改 planner policy integration，不同時調整 carrier、模型或 scorer。
