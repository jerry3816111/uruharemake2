# P4 admission f0 凍結計畫：receipt 鍵名更正

此 amendment 在 f0 任何真模型/Safari Send 前記錄；不覆寫 `93f4963` 的原始計畫，也不改成功門檻、題目、程式或資料。原計畫第 2 gate 寫 `finish_human_turn_count=0`，這是欄位名稱筆誤。產品 `uruha_web_ui.py` 的 active-DB receipt、`test_p4_product_active_db_receipt.py` 實際使用 `human_submission_finish_count`。故 Tpre 必須解析精確鍵 `human_submission_finish_count == 0`，Tpost 預期 `== 1`；缺鍵／型別不符仍 unknown→FAIL，不能用別的欄位推定。其餘 tick0／same PID-session-DB-reset、journal、DB、可見品質與成本 gate 全不變；舊 d0/d1/e0 FAIL 不變。
