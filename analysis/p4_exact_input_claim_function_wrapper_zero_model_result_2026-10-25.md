# P4-C × exact-input claim：零模型相容性修正結果

日期：2026-10-25。此批是 P4 統一入口的必要接線修正，不是新的 M，也不是 A/B 真實產品驗收。

## 前後差異

在修改前來源 SHA 凍結後，原測試 `test_p4_admission_token_function_wrapper_contract.py` 得到 **3 passed / 2 failed**：Web 普通文字送出固定帶 `exact_input_claim=None`，P4-C wrapper 不接受該 keyword，故普通文字與工具負控皆在認知前 `TypeError`。先加 identity、None/缺席與 claim-only 工具測試而未改產品時，得到 **3 passed / 5 failed**，失敗仍集中在此接線。

產品只修改 `uruha_product_function_calling_p4.py` 的介面：普通路由僅在 claim 非 `None` 時以原物件傳給原 Web；缺席或 `None` 保持舊 keyword 形狀。選中工具且 token 非空或 claim 非 `None` 時，在 activity、provider factory／invoke、status reader、原 turn 前以 `tool_route_admission_unavailable` 拒絕，不合成 cognition journal。外層 truth wrapper 未修改。

修改後聚焦 **9/9 passed**，包含實際 Web browser-bound 普通文字、音訊、工具負控，以及一次使用隔離 prepared root／假 Brain 的完整 exact-input claim 路徑；後者核對 `arrival→admission_snapshot→cognition_start→cognition_end→terminal delivered`。測試中的 fake cognition 故意把內容替換成固定 fixture，故此項**只證明 claim 穿過兩個 wrapper 後抵達原 Web capability／journal**，不證明真模型能回答該輸入。

相鄰 9 個測試檔的零模型回歸：**154 passed / 1 skipped / 2 xfailed**，無新 failure；`py_compile` 與 `git diff --check` 通過。兩個 xfail 與一個 skipped 保留原有判讀，不計為新 PASS。獨立只讀審查未見 wrapper 身分傳遞或工具 fail-closed 繞過。產品／測試最終 SHA-256：

```text
d8adc8cc992c578ea43424022ce52372cc0504f60b59c8104e27e54bb58eb3aa  uruha_product_function_calling_p4.py
7440f0f974939e1b806c522ccc2ef75aecc3b6f63120fb1d3b74d82d5688747a  test_p4_admission_token_function_wrapper_contract.py
```

## 證據邊界與下一步

本批 0 真 provider、0 Safari Send、0 付費、0 正式 DB 寫入；測試 session 與 capability root 均隔離。不能據此宣稱真 A、B、自然日文、VRM／Function Calling 統一產品全過或 P4 完成。

A 仍需要使用者作者對固定日文候選的自然度／人格／不過度直抄或捏造三項真評分與外部 receipt，真 A/B 都仍 0 次。B 原凍結的事前硬成本／時間上限尚無可證實作，需另行設計審查與前瞻修訂；本次相容修正不授權 Safari Send。下一個產品放行動作仍受 A on-only 真結果與 B hard-cap gate 約束。
