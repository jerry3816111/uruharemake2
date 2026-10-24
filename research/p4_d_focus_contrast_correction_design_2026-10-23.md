# P4-D-F-C：焦點圖對比修正（實作前凍結）

日期：2026-10-23。前一批 fresh Safari f0/f1/f2 已在 `analysis/p4_verified_main_chain_focus_fresh_product_result_2026-10-23.md` 留下不可覆寫的結果：D 主鏈窄義 PASS，整體旁觀者展示 strict FAIL。f0/f1 標題與箭頭在原生畫面呈深色低對比；沒有落盤的 PNG/AX 或 computed style，不能把 CSS 覆蓋來源說成已證實。原卡片文字可讀。前一批只在工具內目視，也未獨立記錄 100% zoom。

## 單一變因與 before 證據

`uruha_memory_observatory.py` 的 `.brain-d-focus-head` 把亮色設在父層，但 HTML 標題是子 `<span>`；`.brain-d-focus-link` 把亮色設在父層，SVG `<path stroke="currentColor">` 仍仰賴繼承。卡片 label/value/small 有直接顏色。這個差異與 Safari 目視相符，僅為待驗原因，不是確證。只允許同一焦點圖 CSS 呈現層把 `> span` 指定 `#fef3c7`，把 `> svg > path` 的 stroke 指定 `#facc15`；若父層背景不變，兩色對深底的設計對比應足以辨識。不得改 HTML、graph collection、D gate、回覆、記憶、DB、題意或其他網站區塊。允許本文件、新 probe/manifest、新局部契約測試、結果報告與 `CURRENT_TASK.md`。

修正前 renderer SHA、Web CSS 導入檔與局部測試 SHA 另見 `research/p4_d_focus_contrast_preimplementation_2026-10-23.sha256`。前一批的程式 `c83306f`、真實觀察 `f6684ed` 已先推 PR #435。新題在寫入前對日期、物件、兩地名的 tracked repo 逐字碰撞為 0。新題是開發者撰寫的 prospective product probes，非 temporal holdout／人評／公平模型比較；不得用來追分或重寫 f0/f1/f2 結果。

## 判準與資源上限

先做零模型契約：局部 CSS 的標題子 span 與 SVG path 均有明確高對比色；D 焦點的原 node、edge、detail、signal、trace、HTML DOM 結構與無焦點回退逐欄不變，`uruha_web_ui.py` 未變；聚焦測試及受影響 graph/Web/D 契約、compile、diff check 通過。新增模型呼叫 0；renderer HTML bytes 及暖機成本相對修正前不得增加（CSS 只在頁首，圖 HTML 不變）。若契約失敗最多兩個有原因修正批次，否則 `REVIEW_REQUIRED`。

零模型通過、產品 code＋測試 commit/push 並核 PR exact head 後，才用新 0700 私有隔離 root、官方 SHA ONNX 私有複本／預熱、zero-turn ready/stop/T0 空 DB，原生 Safari 在一個新 session 各送 `datasets/p4_d_focus_contrast_probe_2026-10-23.json` 的 c0/c1 一次、0 retry，不重播 f0/f1/f2、dg0/dg1 或 D0–D10。c0 應顯 User 決定 D，c1 同件訂正 D；當輪與 reload 的 focus/原圖/回覆來源一致。Safari 明確使用實際尺寸（100%）後，標題與箭頭在深底可直接辨讀、卡片全文仍可讀、焦點無水平捲動；每輪 ≤20 秒，私有 SQLite 獨立核 profile/episode，raw 與可見回覆核對。若能從合規 UI 路徑保存同輪 native Safari PNG/AX，才通過 saved-visual gate；無法保存就保留 FAIL。重點只判 CSS 對比的可見前後差，不因這項修正宣稱整個產品、D0–D10 或研究 PASS。
