# P2 第一批：未知不是可以質問的假設

2026-09-07，實作前固定。這是 P2（跨情境修正與經驗使用）第一個必要修正批次，不等於完整 P2。

## 已有問題與原因

P1 真實 runtime 六輪中，使用者已要求先傾聽，後續確認／致謝卻被問「想獨處，還是想被傾聽」。
圖中的 `active_validation_strategy_v2_13` 顯示原因：`literal_intent_unresolved` 的未知需求行，
連續被記入 influence_count，便被當作 high-value clarification candidate。`_clarification_copy` 按類別
提供固定二選一，沒有證據支持這兩個選項。M27 仍為 uncertain，不能為了好看將它改成 supported。

## 單一核心變因

只改**主動澄清的來源資格**：未知／缺少有效 typed pragmatic hypothesis 的新提問不得取代原先計畫。
以既有 schema、label、連結與 inference 欄位檢查；不根據使用者句子匹配、不增加關鍵字、prompt 或測試答案。
保留上游模型、歷史、來源、confidence、校準與既有保護。具體且有來源的假設仍可按舊規則提出澄清。
舊的未完成澄清不因當輪資料缺少而擅自清除；只撤回本輪無根據的新提問。

## 最小實作與範圍

- `uruha_grounded_validation_p2.py`：opt-in adapter，安裝在現有 M54/M53＋P1 之後。
- `uruha_web_ui_product.py`：安裝 P2；凍結研究入口不變。
- `test_grounded_validation_p2.py`：純機制、stack／graph 回歸。
- `run_product_restart_probe.py`：若需新增 trace 欄位則另版 schema，舊輸出保留。
- 新的 `analysis/p2_*` 保存前後結果和失敗；開發資料不改名 holdout。

## 預先成功與失敗條件

1. 未解決 label／缺少 schema／不匹配的欄位值，不得產生新的假二選一提問；trace 給出原因與 source ID。
2. 有效非空的暫定假設仍可澄清；安全、事實、記憶、直接要求、既有 pending 行為不退化。
3. 撤回只改該次新 action／validation，不把未知當支持；層次記憶、置信度與 calibration 不被修飾。
4. 原始六輪，後測沿用相同 setup。核對日本語句、當輪 graph、writeback、ID；不將 contract fixture
   視為模型生成或 Safari。若無根據追問消失但回覆仍不自然，判定機制通過／體驗仍未達標。
5. 至少加入未參與這次實作的新開發控制：真正不確定、帶新請求、否定、引述及無上下文。
   本次作者已看到的所有案例皆不能作正式 holdout 或人類偏好證據。
6. 0 新模型呼叫；量測有限機制成本。既有模型逾時不以加長 timeout 或反覆 rerun 隱藏。

## 確切命令與下一步

```sh
.venv/product_checks/bin/python -m pytest -q test_grounded_validation_p2.py test_prediction_identity_p1.py test_supported_feedback_closure_m43.py test_personhood_loop_v2_13.py
.venv/product_checks/bin/python run_product_restart_probe.py --backend contract --output analysis/p2_product_stack_contract_run1_2026-09-07.json
.venv/product_checks/bin/python run_product_restart_probe.py --backend local --output analysis/p2_product_stack_local_run1_2026-09-07.json
git diff --check
```

Safari 仍受工具限制，保持 pending。若機制未通過先修本批；若機制通過但整體對話未通過，第二批依實際
失敗定位一般 planner／記憶作用，而不是追加這兩句的專用回覆。P2 全階段最多兩個前瞻修正批次後重評。
