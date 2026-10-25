# P4 B `REVIEW_REQUIRED`：私有身份架構設計審查

本審查承接 `analysis/p4_b_private_zero_turn_third_real_review_required_2026-10-25.md`；三次真 zero-turn 與兩個修正批次的負結果不改，**不授權第四次模型冷啟或 B Send**。兩條架構候選由不同代理只讀檢查；仍是同一協作系統的非獨立審查，沒有真人／跨機器證據。本輪沒有產品碼、模型、Web 或 Safari 操作。

## 保留的安全／成本需求

現行 child 每次 provider create 前兩次重核，不能只驗初始 0600 receipt：daemon/runner 的 PID 啟動代次、可執行檔與 argv、runner 的 daemon parent、私有模型路徑及 `OLLAMA_MODELS`／`OLLAMA_NO_CLOUD`、兩個 loopback listener owner、模型檔與二進位 SHA、變更期間再驗、同一 gate／run／receipt，缺任一即拒。`/bin/ps` 在真 sandbox 被 EPERM，是 OS 觀察缺口，不是略過檢查的理由。每次 `_inspect_live_identity` 對 4.683 GB model store 做兩次 SHA；每次 create 重核兩次，至少約 **18.73 GB 邏輯讀取**，未含二進位及其他檢查。這是現有實作的靜態讀取量，**不是**實測 click→DOM 秒數；20 秒仍未驗。

## 候選判讀

1. **child-local 無 `/bin/ps`：尚未放行。** 非正式、未保存原始命令與結果檔的探索觀察顯示：同沙盒、受控同 uid 程序的 `KERN_PROCARGS2` 可讀外部 PID 的 buffer/argc；`libproc` BSD info 可回 PID／parent／非零 start。這**不是驗收證據**；兩個已知環境欄位在受控 `/bin/sleep` buffer 及外部 `ps -wwE` 均未出現，不能判定是 OS 禁止、surrogate 不合格或解析問題。外部 listener owner、原 receipt 的 `ps lstart` 與 kernel raw start 也未完成等價核對。不能把 self-argv 通過或只驗可執行檔路徑當成 daemon/runner 全身份通過。
2. **外部 attestation broker：現階段 NO-GO。** controller `start()` 後退出，必須新增受監督常駐程序與私有 IPC，將 child/run/PID generation、nonce/sequence、短效／單次見證綁定，每次 create 同步查詢，broker 消失／逾時即送前拒。它會增加 IPC 與可界定但非零的 TOCTOU；沿用現有四次模型 SHA 不會解除 18.73 GB 每輪讀取及 20 秒風險。不是改 receipt 一欄就能安全完成，需獨立重大架構凍結。
3. **維持 B 常閉：目前產品狀態。** 不因 B 子路線卡住而宣稱整個人類反應方程式或其他產品能力失敗；也不能拿零服務機制通過替代公平比較／人評／Safari。

設計決定：**只放行下一個有界、零模型、零 Web 的 child-local 身份可見性探針設計審查**，規格見 `research/p4_b_ps_free_identity_feasibility_plan_2026-10-25.md`。它是一個 stop/go 調查，不是第三個逐項補洞批次。若完整身份欄位在同沙盒仍不可可靠取得，停止 child-local 路線並評估 broker 的額外安全／成本是否值得；兩者未過不啟第四次私有模型，不送 B。此審查沒有提升認知能力或對照分數，只避免用無效身份證據污染後續產品驗收。
