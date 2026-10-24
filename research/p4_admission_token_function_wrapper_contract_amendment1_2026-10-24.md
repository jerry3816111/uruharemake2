# P4 admission token × Function Calling：歷史凍結驗證修訂 1

狀態：**產品修正後、舊驗證器修改前的 source-only 修訂**。原契約計畫及 f2 Safari strict FAIL 不重判。此修訂只允許修正舊 P4-C 凍結測試的驗證來源，不更改 `research/p4_c_product_function_calling_integration_freeze_2026-09-20.json` 的任何位元組、gold、模型或產品程式。

## Before 證據與原因

- 事前 source-only 設計／六 SHA 已在 `48390dd43c75a59358c2e52087aa95ee0771e9c3` 推 PR #435；此提交的 `uruha_product_function_calling_p4.py` SHA-256 是舊凍結值 `7173e8c5dcf3f201a4e4597361e66e08c4230d6c2e220763bf4bbf233c58af6c`。
- 新增 contract 測試改前 4 failed／1 passed，四個錯誤都是 f2 的 `admission_token` TypeError；最小 wrapper 修正後聚焦 **5 passed**。當前 adapter SHA-256 `308679b947c7eb1abfc44b78afbb15d4601d39b47ed64fdf2a7db8c7c6119c29`，新契約測試 SHA-256 `abd119cbb54e4042f550cfe749143f36bfc8f408ea810577a423c7f212d3e851`。
- 11 檔受影響回歸 **166 passed／1 failed**；唯一失敗 `test_p4_c_product_function_calling_integration_freeze.py::test_integration_freeze_binds_core_real_gate_adapter_entry_and_tests` 仍把舊凍結 adapter SHA 與今天有意修正的檔案直接比較。這是歷史檔案與現用產品兩個不同時間點的混淆，不是 adapter contract 失敗。既有 `product_entry` 已有同類型的歷史例外。
- 修改前舊驗證器 SHA-256 `2ba758bc22267b0675b159b8d8f794d532a75a2dbbf70949c7bd1c7b7034ae6d`；凍結 JSON SHA-256 `d52a8ae375e493244a7744752125d7eb9ee2c9a81c2d43f91729ba9f087df5b8`。

## 唯一增補、成功／失敗判準

允許額外修改 `test_p4_c_product_function_calling_integration_freeze.py`：對 `product_adapter` 的**歷史** SHA，以固定已提交 Git blob `48390dd43c75a59358c2e52087aa95ee0771e9c3:uruha_product_function_calling_p4.py` 計算並與原 JSON 比較；其餘既有 binding 判準不放寬。現用 adapter 的新契約仍由 `test_p4_admission_token_function_wrapper_contract.py` 的 Web 真路徑、雙層 wrapper、正負控及新 product SHA 綁定。不能跳過歷史 hash、把凍結 JSON 改為現值、吞 `git show` 錯誤或用產品當前內容冒充歷史。若 Git blob 不存在／位元組不符，測試必須 fail。Git 來源驗證器不是發行版無 Git 環境的 runtime 契約；只在 repo 開發測試執行。

先將本修訂 source-only commit/push、核 PR exact head，再改測試、跑前述 11 檔回歸與 compile、diff/SHA review。新增真 provider calls=0、Safari Send=0、正式 DB writes=0；f2 絕不重送。若通過，僅判 wrapper／Web 零模型接線 PASS；未來真產品需另凍新 f3，tool-selected＋admission token 仍明確 fail-closed。
