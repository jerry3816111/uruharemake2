# M53 Source-Neutral Scaffold Authorization · 2026-08-30

## 單一問題

M52 Safari 的白紙報告只有「做三個見出し」證據，候選卻具名為「環境／經濟／社會」。M46
same-model reviewer 把 `no_invented_facts=true` 並交付，表示同模型自審不能單獨承擔來源邊界。

## 修改

在 M46 structural boundary 增加 deterministic named-label authorization：

- 只檢查生成 plan 中明示加引號的具名 label；label 若逐字出現在 exact allowed source，可通過。
- 少量語義中性的 scaffold role（例如見出し1、項目2、導入、本論、結論、空欄、未定）可通過；
  它們表示結構位置，不冒充報告主題或使用者事實。
- 其他無 exact source 的具體 label 產生 typed violation，整個 plan fail closed；不把它改成另一個答案。
- 原 M48/M52 surface、M51 candidate、M46 content/surface review全部保留；不新增模型呼叫。
- trace 只存 label digest、支持類型、數量與違規，不存 raw candidate label、不寫長期記憶。

## 成功／失敗

成功：M52 真實 `環境／経済／社会` 反例在 fixture 與新 Safari 都不可交付；中性導入／本論／結論
與 source exact quote 不被誤擋；無 label 的 color grouping 不退化；安全負例零介入；node/card可見。

失敗：把 report 題目硬寫進程式、把所有日文名詞都當捏造、改寫 plan 成固定答案、略過 M46、
或把 bounded quoted-label gate 宣稱為通用 hallucination detector。

## 邊界

這個 gate 只能處理明示具名 label；未加引號的暗示性補充、跨語翻譯後的等價 label 與一般世界知識
仍未證明。跨語 source label 若無可追溯對齊會保守拒絕。它不是人評、語義真值或完整來源忠實度。
