# f3 事前零模型 go/no-go

**結果：route gate PASS，真模型／Safari 仍 0 次。** 題本、gold、成本與硬 gate 先於本測試以 `4a68154` 推 PR #435；preimplementation 10/10 SHA 驗過。新 `test_p4_turn_admission_stateful_f3.py` 使用隔離真 RightBrain＋假 LeftBrain、與產品相同的 opt-in M29/control/repair-cue chain，測得 M29 `brief_encouragement`、M33 `not_applicable`、M18 不接管、M21 `full_planner`＋compact completed、scene `support`、dialogue act `direct_chat_answer`、final＝隔離 episode，**1 次假模型呼叫**。這不評真模型生成的自然日文、Safari wrapper 或視覺圖。

第一次以全域 Python 3.12 執行，隔離子進程缺 `colorama`，1 failed；這是錯誤測試環境，未改產品／題本／gold。改用既有 `.venv/product_checks/bin/python`，新 f3 聚焦 **1/1 passed**；與 f2 route、wrapper Web-level 正負控合跑 **7/7 passed**、9 個既有警告，0 real provider calls。上述錯誤不計產品失敗，也不隱藏。f0/f1/f2 舊 FAIL 不變。

下一層才准依凍結計畫建立新的 0700 root、持久 T0/Tpre DB 原件與原生 Safari **一次**；如果 snapshot／admission／可見品質或視覺保存缺證，嚴格 FAIL 且不補送。Web delivery 額外 Chroma 成本依舊 unknown，不得稱完整產品成本或同模型優勢。
