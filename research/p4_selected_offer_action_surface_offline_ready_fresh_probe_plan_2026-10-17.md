# P4 selected offer action：離線 embedding 就緒後的第二批前瞻 Safari 產品驗收

狀態：2026-10-17，**第二批逐字題／gold 首輪前固定，尚未送 Safari／模型**。第一批 T1 `胡椒ポテト、一口いる？` 已曝光且在 ONNX 首載逾時，整批 strict FAIL，T2–T6 未送但整組均不重播或換 gold；見 `analysis/p4_selected_offer_action_surface_fresh_product_probe_abort_2026-10-17.md`。本批是第二個有理由的驗收批次，仍是同團隊 developer-authored，不是獨立 holdout。唯一環境修正是新隔離 HOME 的官方 SHA-matching embedding 資產離線就緒；產品 source/gold/模型候選准入／全域路由均未改。

## 已完成、與真輪次分開計成本的 0-turn 預檢

- 全新 launcher-owned 0700 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-wy07nein`；run `4983a4098a928bdd`、PID `24249`。`start` 約 54.5 秒，只回 `ready=false`；有界同 run `verify-ready` 最後核同 PID、單一 loopback `127.0.0.1:7894`、HTTP 200。隨後 controller `stop` 回 `planned_stop=true`、PID exited、port vacant。此為第 1 次 0-turn 啟停，**不算** T3 後 planned same-DB restart，也不是 Safari PASS。
- 此時 `memory_db`、`session_db`、`web_logs` 均無檔案。主機已存在的 Chroma ONNX archive 83,178,821 bytes，其 SHA256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 與所安裝 Chroma class 官方 `_MODEL_SHA256` 相同。只在此 root 的 `.cache/chroma/onnx_models/all-MiniLM-L6-v2/` 做獨立檔案副本，mode 0600、不同 inode、link count 1、再核 SHA；未碰正式 HOME cache、正式 DB 或 repo code。
- 同 venv 的 fresh interpreter 以 `HOME`／`TMPDIR` 指此 root、同 frozen sandbox profile，將 `httpx.stream` patch 為「任何下載立即報錯」後，`ONNXMiniLM_L6_V2()(["cache-readiness-v1"])` 離線得到 1×384 finite vector；Chroma 六個模型檔皆在 root 解壓。embedding 呼叫 0.405 秒，預檢整個子程序約 0.811 秒；之後三個 DB/log 目錄仍空。這僅證設施就緒，不證將來模型對話、圖或語義通過。

## 要推翻的有界主張與一次性程序

題與逐輪事前 gold 見 `datasets/p4_selected_offer_action_surface_offline_ready_fresh_probe_2026-10-17.json`。T1/T3/T4/T6 是新物品／修飾語直接邀請，預測已選中的正面 food-offer action 能保留到最終泡泡；T2 引文第三者及 T5 中文為不准入負控制。六句在建立時逐字搜尋 repo 無先前命中。任何正例 planner 沒選對、core 本身不接受、final 不回答、graph 不符，均按原 gold 記 FAIL，不能事後改成「未覆蓋」。

1. 首輪前將 dataset、本計畫、SHA manifest、當前任務卡 commit/push 到既有 PR #435；首次 abort 報告已由 `59fef28` 推送。核對新舊 manifest 與 PR head。之後原檔不改，不重播曝光題。
2. 在上述**同一已預熱、停機、0-turn** root 上 `p4_offer_action_detached_control.py start --reuse-runtime-root <root> --mode product --python <同venv>`，記新 run ID/PID。`verify-ready` 必須是同 PID、單一 localhost listener、HTTP 200；啟動失敗獨立計入程序 FAIL，不送題。此啟動預熱已預定，不是答案錯後重試。
3. Safari 開新分頁，同一 root／DB T1–T3 各逐字送一次，最多等 20 秒，不重按、不改提示。每輪保存可見泡泡、selected/core、offer verify、utterance、input 及所需 graph node、profile row IDs、episode IDs、latency、可見模型 token/呼叫數。一般語義 FAIL 可繼續未曝露題以收集反例；UI/runtime 錯誤則停止本批，不重試該輪。
4. T3 後 controller planned stop，核原 PID 已退出／port vacant；以 `--reuse-runtime-root` 同 root、同 DB 啟第二個真對話 session，再 verify-ready，T4–T6 各一次。結束 planned stop、root/raw 留存、舊 Safari 分頁不任意關。
5. strict PASS 須 6/6 真輪次且 ≤20 秒、0 retry、事前安排的一次 T3 後 same-DB stop/restart、profile row-ID delta `[0,0,0,0,0,0]`、六個不同 episode、六輪泡泡＝graph utterance；四正例 selected/core/item/action/verify 皆合 gold，兩負例不得出現新 offer verify、六輪自然日文無無據來源。任一缺失明列 FAIL／未覆蓋，預檢、零模型或前批失敗不能灌成這批 PASS。

本批不比較一般 LLM；即使通過，也只支持有界 P4 產品忠實度，不證一般人類語用理解、人評、正式 temporal holdout、VRM/Function Calling 整合或人腦方程式。首批持續列 FAIL，隔離預檢與真輪次延遲／模型成本分開報。若第二批仍失敗，按目前卡片的兩批上限保留反例並轉 `REVIEW_REQUIRED`，不得第三批追分。
