# P4 原生 producer lineage 圖像投影：前瞻凍結

狀態：**實作前凍結**。前批 L1–L4 原始結果、SHA 與 strict FAIL 固定於 `analysis/p4_mixed_act_lineage_fresh_product_probe_result_2026-10-20.md`，不重送、不改分。其 raw `runtime_trace.mixed_act_lineage_p4.producer_edges` 四輪各有兩條，但 Safari node graph 沒畫：`collect_cognitive_graph` 僅接最後黑板節點並按序投影，早期 event/M31/M32 因核心黑板保留上限消失；對 L1 原件生成的圖有 receipt 節點卻 `is-producer=0`。本項要修的是**視覺證據交付**，不是語義模型、改寫／回憶、速度或權限。

## 單一變因與範圍

只在 `uruha_memory_observatory.py` 的純 renderer，對完整 `runtime_trace` 已有的 `mixed_act_lineage_p4` **linked** receipt 進行防禦性核對，從該收據投影 event、M31、M32 三個明標「verified receipt projection」的可展開節點與兩條 `is-producer` 專用箭頭。節點在大型圖裡清楚可定位，說明 `action_coverage_status=unverified`、`authority_transfer_permitted=false`；不把原始引述全文或私密原話複製到節點。投影不可稱新模型運作、行動完成或權限准入。

renderer 核對至少：receipt schema/status/reason、單次 event ID／兩 proposal IDs 唯一、current raw SHA 與 current cycle、一組**恰好兩條**原生 typed edges 的 exact endpoints/order、M31/M32 兩 producer stamp 的 schema／producer／event/cycle/digest／直接父 ID、狀態連接及無移交旗標。任一缺失、錯父、錯 event、錯 digest、重複或未產生就**不畫 verified 邊**，可只呈現保守的既有一般節點；不得用文字相似、相鄰順序或舊 label-based M31→M32 猜線。protected 即使 linked 亦可畫來源鏈，但要明示 blocker 和禁止權限轉移；blocked/rejected/not_produced 不可畫 verified 線。

允許修改：`uruha_memory_observatory.py`、新增 `test_p4_verified_producer_graph_projection.py`、本 plan、新 developer-authored 三輪 probe dataset、驗收報告與 `CURRENT_TASK.md`。若發現需動 `uruha_brain_mac.py`／舊 producer／記憶／回覆，先停下另審；不藉此改核心黑板上限、source-role gold、M31/M32/M33 權限或任何 baseline。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不碰。

## 事前判準與資源

- 零模型：合成 linked 正例必得三個 projection 節點、**exact 2** 條 `is-producer` edges，SVG HTML 有兩條對應 `<path>`，收據摘要可在頁面看出來源、兩 producer、coverage 未驗、authority 未移交；**新增 projection 節點的 detail** 不含原始 user_text（既有 USER SIGNAL 節點仍顯示原話）；錯 parent/event/digest/cycle/重複邊、缺 M31/M32、`not_produced`／`rejected` 全部零 verified edge。HTML 內容 escaping，M24 detail budget 仍通過。現有 observatory、M24 progressive graph、lineage tests 全過。
- 前瞻產品三輪在 `datasets/p4_verified_producer_graph_probe_2026-10-20.json`；使用前同一分類器 0-call 預檢 role=`ordinary_chat/mixed_request/protected`、新日期地點無舊 dataset exact collision。全新 0700 隔離 root、0-turn same-PID readiness/planned stop、官方 SHA ONNX 私有離線預熱、T0 空 profile；真 Safari G1–G3 各一次／0 retry，逐輪看**實際圖上的三節點與兩條線**及可展開 provenance，raw receipt 必須和圖對應，3/3 才算圖交付。protected 不升權，profile 0 rows/digest、Safari 泡泡＝raw＝guard＝graph utterance＝episode，逐輪日文與 ≤20 秒、可得模型呼叫／token／等待都獨立列。原始回覆任務品質如仍失敗，整體 mixed product 繼續 strict FAIL，不能用 graph PASS 抵銷。
- 新程式模型呼叫 0；圖渲染細節須在既有 M24 byte budget 內。若 renderer gate 失敗，保存失敗並至多兩個有根據修正批；不重跑曝光 G 題追分，下一批另凍結新資料。若圖 gate 過，下一項才是 typed action coverage／原子 composer 的獨立設計與權限審查，不能自動移交。

本項證據只到純 renderer 與新隔離 Safari，不代表正式同模型強 LLM 優勢、人評、temporal holdout、真人理解或完整產品完成。
