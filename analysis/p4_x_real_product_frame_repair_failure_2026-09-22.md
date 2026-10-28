# P4-X 隔離真實產品／Safari 語境修復驗收：負結果

日期：2026-09-22  
狀態：**FAIL，原案例禁止重跑**

## 這一步實際驗收什麼

P4-X 在凍結四個全新中／英／日輸入、產品入口、資源上限、成功條件與失敗政策後，於新的 private runtime root
啟動 `uruha_web_ui_product_p4_w.py`，並在 Safari 實際送出四輪。它要確認的不是離線函式，而是模型候選、
P4-T frame extraction、P4-V coverage、P4-W repair、使用者可見回覆、durable episode 與 node graph 能否在同一個真實產品輪次一致。

## 成功觀察到的部分

- 4/4 輪均完成，4/4 使用者可見回覆為日文。
- 4/4 輪各有 durable episode，沒有寫入 typed preference。
- 每輪的 generic runtime graph 均可見，節點數為 69。
- JSONL `logic` 內每輪均有 P4-T、P4-V、P4-W trace。
- 三輪自然觸發 P4-W repair；分支旗標與 repaired digest 4/4 一致，凍結的 frame-level after violation 為 0。
- 四輪總等待 53.1081 秒，單輪最慢 17.0623 秒，未超過事前上限；沒有 retry、fallback、付費 API、外部部署或關閉既有 Safari tab。

## 凍結 gate 為何失敗

Safari 顯示的 `cognition_trace.runtime_trace.blackboard` 雖有 generic graph，但 4/4 輪都沒有 P4-T、P4-V、P4-W node。
因此 graph 上的 P4 trace count 為 `0/4, 0/4, 0/4`，而不是事前要求的 `4/4, 4/4, 4/4`。gate 固定得到七項失敗：

1. 四個 `turn_N_surface_trace_missing`；
2. 三個 `metric_mismatch:p4_{t,v,w}_trace_count`。

這表示修復邏輯確實執行，但研究展示面沒有呈現同一份決策鏈。它不能被宣稱為「完整圖像化的真實修復流程」。

## gate 外、但更重要的語意反例

凍結 gate 只檢查 frame family，真實回覆另暴露三個命題保存問題：

- Turn 1：修復器補回引用形式，但包住的是模型產生的無關澄清句，而不是「冬季入口八點關門」這個來源命題。
- Turn 3：補回 `らしい` 傳聞立場，卻遺失「後輩弄丟杯子」的 `なくした` 事件。
- Turn 4：保留假設形式，卻把使用者假設中的 `I` 改成角色的 `うちは`；P4-V 沒有偵測到這個假設內 ownership shift。

所以「after frame violations = 0」只能證明有限框架被修復，不能證明原始命題已保存。這個負結果收窄了 P4-W 的 claim，
而不是推翻其離線 frame contract。

## 下一步與界線

1. **P4-Y（單一變因）**：不改可見回覆、detector、repair、模型、prompt 或 memory，只把已存在於 `logic` 的
   P4-T／P4-V／P4-W trace 正確送進 real runtime graph；以合成 integration fixture 先凍結，不重跑 P4-X。
2. **P4-Z（另一個單一變因）**：另用全新 prompt 凍結 source-bound proposition preservation 與 hypothetical ownership，
   不把已曝光 P4-X 案例再稱 holdout。

P4-X 證明 bounded repair 能在真實產品自然觸發，也證明目前的圖像化鏈與命題保存仍不完整。它不證明 felt understanding、
人類偏好、強 LLM 優勢或人類方程式。

可重現證據：

- `analysis/p4_x_real_product_frame_repair_evidence_2026-09-22.json`
- `analysis/p4_x_real_product_frame_repair_result_2026-09-22.json`
- `test_p4_x_real_product_frame_repair_result.py`
