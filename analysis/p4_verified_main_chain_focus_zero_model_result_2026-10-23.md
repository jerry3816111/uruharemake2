# P4-D-F：當輪主鏈折疊圖零模型結果（Safari 前）

日期：2026-10-23。設計／f0–f2 題本／preimplementation SHA 已先於程式以 `c4d413c` 推 PR #435 並核 exact head；三題未送模型或 Safari。D-G 舊真 Safari 的 78/81 節點、113/121 邊、2890×2312 只作 before 原因與離線顯示成本診斷，不拿來當本項 fresh product 結果。

## 真正改動

`uruha_memory_observatory.py` 只增加驗證 D 的 renderer focus：沿原圖 `is-main` **記錄順序**折疊 input→D 來源憑證→selected_plan→utterance→final output；只有唯一、真 trace-reported `turn_episode` 寫回與 output→write `is-active` 邊俱在時才接 episodic write。每段 `+N` 標折疊的原始節點，完整 17 欄 graph 以原生 `<details>` 保留。D／selected signal 逐字呈現；input/output 使用同 node 未截短 detail，所有動態 HTML escape。缺失、錯 route／cycle／來源、重複 anchor、斷邊或偽寫回不造焦點／假箭頭。非 D 原圖預設不變。沒有改 graph collector、生成、回覆、Web 接線、D gate、記憶或 DB；這些線只證明原圖記錄順序，不證明語義因果或持久化。

## 零模型驗收與成本

- 新 `test_p4_verified_main_chain_focus.py`：f0/f1 正例、f2 非本人負例、凍結 13/13 結構負控及額外不同 kind 重複寫回等負控通過；焦點 anchor 是原 node identity，主鏈每段由原 `is-main` 邊重建，fixture 折疊數 **1/2/1/1**，寫回只由 `is-active` 真邊；result 和 graph 原件不變，完整原圖 node／edge／inspector DOM 不減，HTML escape 與完整 input/output 內容核對。聚焦 **8/8**。
- 聚焦＋D gate、D-G、M24 graph、P4 producer／atomic、browser hydration、Web final graph、teacher graph、tool failure truth 的受影響集：**205/205 passed、9 個依賴 warning**。`py_compile`、`git diff --check`、Web `build_demo()`＝Blocks。無新模型呼叫。歷史 P4-AB 寫死舊 graph SHA 的 3 pass/1 pre-existing stale fail 仍不改舊凍結；本次不宣稱全套件全綠。
- 對 D-G 私有兩輪**舊** raw 離線同資料 before/after render，各 25 次暖比較：兩輪都是 6 個焦點 anchor、主鏈省略 **25/0/34/9** 個原節點、寫回真邊 1 條；原圖仍 78/113 與 81/121。HTML 162,357→172,487 bytes（+10,130）與 173,981→184,127（+10,146），均低於凍結 +15KB；render 中位 5.252→5.330ms（+0.078）與 5.840→6.101ms（+0.261）。這是展示程式的離線成本，不是新產品輪次或完整 token ledger。
- 獨立只讀 code review 發現「不同 kind 的第二筆 episodic_memory 可能被忽略」並已修正／補負控；複核無剩餘 code blocker。這不是人評。

## 判定界線與下一 gate

**零模型／局部呈現契約通過；fresh model、原生 Safari 可讀性、reload 與持久視覺尚未驗收，不能判產品 PASS。** 先核 product SHA／精確 diff/status，只提交 renderer、新 test、SHA、報告、本卡並 push PR #435 exact head。之後按凍結 f0/f1/f2 在全新 0700 私有 root 作官方 SHA ONNX 複本、封下載預熱、zero-turn ready/planned stop／T0 空 DB，再以原生 Safari 每題一次、0 retry 核焦點與展開原圖、bubble/raw/guard/SQLite、≤20 秒。Safari PNG/AX 如仍不能落盤，saved-visual gate 必須 FAIL；D2 自然度、D5 衝突值、完整 token、正式同模型／人評／temporal holdout、VRM/Function Calling 統一驗收與 Goal 均 pending。
