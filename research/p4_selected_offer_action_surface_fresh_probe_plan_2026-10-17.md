# P4 selected 食物邀請行動的前瞻本機 Safari 產品驗收

狀態：2026-10-17，**六句逐字 source 與 gold 已在第一次模型／Safari 輪次前固定，尚未送題**。這是同團隊 developer-authored 新題，不是獨立 holdout。根因、單一變因與禁止邊界見 `p4_selected_offer_action_surface_fidelity_design_2026-10-17.md`。前一六輪的 T2 原文／結果已曝光且 strict FAIL，絕不重播、改 gold 或事後重算為本批成功。

## 要證明／推翻什麼

本批只檢查「planner 已選直接食物邀請的接受行動 → 最終泡泡仍實際回答那個邀請」。新 overlay 不選吃不吃，不改模型候選 eligibility、不新增模型呼叫、不寫偏好記憶；若 core 自身不肯定接受、來源不明或候選不能驗證，就不把它報成已保留。真正 final reply 後的獨立 verify node 須誠實報 `visible_action_preserved` 或 mismatch。零模型 7/7 與相鄰回歸只能證指定合約，不能代替此輪。

六句與逐輪語義 gold 在 `datasets/p4_selected_offer_action_surface_fresh_probe_2026-10-17.json`。與開發 `塩ポテト` 及歷史 `海苔昆布おにぎり` 不同；建立前逐字查詢 repository，六句皆無既有 match。T1/T3/T4/T6 是四種新 item／修飾語組合；T2 是引文第三者負控制，T5 是中文輸入／日文輸出負控制。T3 後停服務、同一 0700 root／同一隔離 DB 計畫重啟，T4–T6 續作；這個 restart 是事前安排而非錯題 retry。

## 嚴格一次性程序

1. 將 implementation、入口、控制器、測試、dataset、本 plan 和 SHA manifest 一同 commit/push 到既有 branch／PR #435，核對首輪前 manifest 全部 hash。後續原檔不改。若改程式，保留本批為已曝光或未曝光狀態，須另有全新題與審查；不得靜默替換。
2. 使用 `p4_offer_action_detached_control.py start --mode product --python "$PWD/.venv/product_checks/bin/python"`，記錄回傳的絕對 root、run ID、final PID。`verify-ready` 須是同 PID 的單一 `127.0.0.1:7894` LISTEN 與 HTTP 200；短暫啟動 race 可對**同一次 run**有界重驗。0-turn 啟動失敗獨立計入產品程序 FAIL，保留 root/log，不算任何 Safari 句子結果。不得用公開分享網址。
3. Safari 開新分頁 `http://127.0.0.1:7894/`；逐字 T1–T3 各送一次，每輪最多等 20 秒；不因輸出不好重按、不改提示。逐輪擷取真泡泡、runtime graph selected/offer verify/utterance、profile row IDs、turn episode IDs、原始 trace、模型呼叫／token／延遲能取得的實值。T2 不得出現本新 verify node；T1/T3 須出現且為 preserved。逐輪核 `utterance.reply` 與泡泡同字。
4. T3 後以同 wrapper planned stop，核原 PID 已退出、port vacant；用 `--reuse-runtime-root` 同 root、同 DB 新 PID 啟動並 verify-ready，逐字 T4–T6 各一次。T5 不得出現新 verify node，其 visible 回覆仍須自然日文；T4/T6 須有正確 canonical item＋接受動作。完成後 planned stop，root/raw 留存，舊 Safari tabs 不任意關。
5. 全批 strict PASS 要求 6/6 完整真輪次且 ≤20 秒、0 retry、兩個 session／一次真 same-DB restart、profile row-ID delta `[0,0,0,0,0,0]`、六個不同 episode、六輪泡泡＝graph utterance、四個正例 selected/core/verify/item/action 全符、兩個負控制不誤准入、六輪自然日文且不捏造來源。任一語義、graph、DB、啟停、等待或成本資料缺失按原 rubric 報 FAIL／未覆蓋，不用小測或同模型非獨立評分補成 PASS。

成本：記實際模型呼叫、input/output token（若 endpoint 暴露）、等待秒數、隔離 DB delta；不可把 0-turn 或零模型的 0 呼叫外推為 Safari 0 成本。本批不比較一般 LLM；即使 PASS，也只支持這個有界產品選案→表面忠實度，不證人類理解、人評偏好、正式 temporal holdout、VRM/tool 整合或人腦方程式。首批若 FAIL，最多兩個依原設計有理由的新題修正批次；不能反覆在同六題加語法追分。
