# P4 stateful f2：真產品前零模型路由 gate

狀態：**零模型路由 PASS；真模型、Safari 與可見品質尚未驗收**。本題是作者撰寫的開發診斷，不是 holdout 或同模型 LLM 比較。f0 的 pre-Send strict FAIL、f1 修正前的路由 FAIL 均維持原判，不重送舊題。

事前凍結為 `b8f955274d9262ac489a2326af9b21082352a440`，題目、gold、單一真 Safari 送出上限與停止條件見 `research/p4_turn_admission_stateful_f2_plan_2026-10-24.md`。本階段再核 `sha256sum -c research/p4_turn_admission_stateful_f2_preimplementation_2026-10-24.sha256`：**8/8 OK**。未改凍結題本或 gold。

`test_p4_turn_admission_stateful_f2.py` 在隔離記憶中以真 RightBrain、假 LeftBrain、現行 M29 優先產品入口及 opt-in repair-cue 完整執行 `run_turn_debug`。檢查 M29=`brief_encouragement`、M33=`not_applicable`、M18 未取得 authority、M21=`full_planner` 且 compact 完成、scene=`support`、dialogue act=`direct_chat_answer`、最後回覆等於 episode，並只有 **1 次假模型呼叫**。正式指令：

```text
.venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_turn_admission_stateful_f2.py
1 passed in 7.13s
```

第一次測試因 harness 把 M18「未接管」錯誤地寫成 trace 必須有明確 `applied=false`，觀察值實為缺欄位 `null`，得到 **1 failed**；此非產品路由失敗。只把測試改成「不能為 `true`」，與舊 f1 的判法一致；**題目／gold／產品 code 均未更動**，然後上述測試通過。保留這次測試解讀修正，不把首次紅燈藏掉。

這個 gate 只准進入全新私有 root 的 zero-turn rehearsal；它不證明模型會說自然日文、能承接家具決定、Safari graph 綁同一輪、逐輪 DB/journal 歸因、成本或使用者感到被理解。後續必須逐項按凍結計畫核對，任何前送 gate 失敗即不按 Send，任何送後 gate 失敗即保留 FAIL 而不重試 f2。
