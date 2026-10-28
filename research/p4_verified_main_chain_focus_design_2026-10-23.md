# P4-D-F：已驗證當輪主鏈的可讀圖像（實作前凍結）

日期：2026-10-23。D-G 的新隔離 Safari 已證明圖上 D／selected-plan 訊號當輪及 reload 各 2/2 正確，但完整產品圖仍 strict FAIL：兩輪重建分別為 78/81 節點、113/121 邊，17 個固定欄使畫布達 2890×2312px；132px 卡片及單行 ellipsis 截斷訊號。這是**呈現層**問題，不改 D0–D10 舊 FAIL、D2 自然度、D5 衝突值或新 dg0/dg1 的判定。真 Safari before 僅工具內目視，沒有可落盤原生 PNG/AX，這個缺證也不以本項假裝補齊。

## 唯一變因與邊界

在 `uruha_memory_observatory.py` 同一 renderer 增加一個**已驗證 D 主鏈的折疊視圖**，置於現有長圖之前；現有 `collect_cognitive_graph`、所有原圖節點／邊／detail／trace／budget 與 Web、D gate、回覆、記憶、DB 均不變。僅對 `_verified_current_decision_graph_signals_p4` 成立且原圖中各有唯一 input、D、selected_plan、utterance、final output、以及真實有向主鏈路徑的輪次啟用。按原圖 `is-main` 的 blackboard **記錄順序**折疊 input→D→selected_plan→utterance→output，每段標明略去的原始節點數；只有唯一的 trace-reported `episodic_memory` write node 與 output→write 的 `is-active` 邊存在時才接寫回，無則明示未在焦點圖顯示寫回。缺任一必要 node／edge、重複、stale/foreign cert、跨輪來源不符，回退舊完整圖。

折疊主鏈不等於獨立證明「D 導致回覆」或外部事實為真；圖面應直寫「原圖主鏈／記錄順序」與「略去 N 個節點」。寫回只可稱 trace 報告的 `episodic_memory` node，不能單憑圖斷言 DB 已持久化；不得由 D cert 推測 profile 已保存或訂正已撤銷舊值。焦點卡片沿用**同一 graph node ID、signal、detail、trace_id** 並換行；原 `signal` 在 collector 已截為 42 字，所以 input/output 卡的可見全文應取同 node 的未截短 `detail`，D／selected 訊號則逐字顯示同 node 的 signal。不得用換行假稱截短 signal 變完整。原始 17 欄 graph 放在原生可展開區，預設收起只在驗證 D 焦點時發生，節點與箭頭可逐一打開核對。非 D／不一致來源保持原圖預設呈現。不可新增綜合文字推理卡、模型呼叫或虛構邊。

允許：`uruha_memory_observatory.py` 的局部 renderer/CSS/helper、新 `test_p4_verified_main_chain_focus.py`、本文件／前瞻題本／SHA／結果、`CURRENT_TASK.md`。不改 `uruha_web_ui.py`、D gate、原有 D/D-G 題本、正式資料、私有 log 或任何其他產品部件。視覺擷取設施是**另個變因**，本項不以 shell/UI 替代路徑偷補原生 PNG/AX。

## 未曝光案例與事前判準

`datasets/p4_verified_main_chain_focus_probe_2026-10-23.json` 的 f0/f1/f2 是新 developer-authored、非 holdout 的 2089 年來源；建檔前對日期／物件／地點的 tracked repo 逐字碰撞 0。f0 直接 User 決定，f1 同件明示訂正，f2 只是朋友的決定，不能得到 User-D 焦點。Safari 題各送一次、0 retry，不重播 D0–D10 或 dg0/dg1。測試 fixture 還要覆蓋 cert 缺失／stale／跨路由、重複／缺失 anchor、斷開每一段主鏈、偽 write edge、錯型 write node、HTML escape 與非 D 原圖；負控不得產生焦點或假箭頭。

零模型成功條件：兩個 D 正例焦點 anchor 皆由原圖真 node 提供，每段可在原圖同類有向邊重建，折疊數精確；f2 與所有結構負控 fail closed；原 `collect_cognitive_graph` 結果逐欄相同，原圖 DOM 的完整節點／邊／inspector 不減，正文不漏 private trace。新增模型呼叫 **0**；報新增 HTML bytes／暖機後 renderer 耗時，HTML 增量目標 ≤15KB。受影響 graph/Web/D 契約與 compile 通過。

真 Safari 成功條件：新 0700 隔離 root、官方 SHA ONNX 私有複本／封下載預熱、zero-turn 同 PID ready/planned stop 與 T0 空 DB 後，以新 session f0/f1/f2 各 1 次；每輪泡泡＝raw＝guard＝graph utterance、profile 不被 D 心理推測污染、獨立 SQLite 核 trace-reported episode 寫回、當輪與 reload 一致、每輪等待 ≤20 秒。100% 原生 Safari 視口無須水平捲動或點焦點卡即能讀出 f0/f1 完整 D 與 selected 訊號、同 node detail 的輸入／輸出全文與 trace-reported episodic write 有序，f2 不顯 D 焦點；展開後原圖及每個 inspector 仍在。若不能保存同輪原生 Safari PNG/AX，**saved-visual gate 仍 FAIL**；若圖仍需大量操作才可讀，旁觀者展示 gate FAIL；全管線 token ledger 仍缺，不能稱 whole product PASS。可見的狹義前後差與總判分開報。

凍結前產品 SHA 見同名 preimplementation manifest。先提交 plan／題／SHA／任務卡並推 PR #435、核 exact head，之後才改 renderer；失敗保留，不回改題／閾值。最多兩個有原因的修正批次，仍敗則 REVIEW_REQUIRED。
