# V69 正式程式旁路整合

## 改動能力

新寫入的使用者姓名、喜好與不喜好，除了原有文件外，現在也帶有可分辨「同一件事」「何時開始有效」的 typed metadata。正式程式會讀回這些紀錄並產生現況／歷史診斷 snapshot。

## 不變部分

- snapshot 不進入 working memory。
- snapshot 不進入 LeftBrain、RightBrain 或 prompt。
- 不遷移、刪除或改寫既有 legacy rows。
- 最終回答保持不變。

## 可觀察證據

`get_runtime_snapshot()["profile_state_shadow"]` 會提供 typed、legacy、active、historical 與 inapplicable 數量及 ID。這讓後續能先量測正式資料中的 legacy 比例，再另行決定是否設計資料庫遷移。

此整合仍不是 profile 記憶正式上線；只有在新的回答層 holdout 與真實對話回歸都通過後，才可討論把 active profile 放入 working memory。
