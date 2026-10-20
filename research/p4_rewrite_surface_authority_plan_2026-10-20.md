# P4 已接受改寫的表達權限交接：前瞻修正批

日期：2026-10-20。這是上一批明示引述改寫 strict FAIL 後的一個有根據修正批；舊八句、gold、raw SHA `1c45c0bfeead0799849eb77017149e37488f8103f54e1ed7f72d8872d87642ad` 與失敗判斷不可變更或重送追分。新題是 developer-authored 產品探針，不是獨立 holdout 或人評。

## 修改前證據與唯一變因

舊 T3 已有 opt-in typed rewrite candidate，卻在原 `semantic_commit_repair_m32.surface_authority=true` 下被舊 `response_jp` 覆蓋；P4-W 再使用相對舊 plan 的 frame violation 作 `quote_embedding_restore`。`candidate_equals_speak=false`、`candidate_equals_final=false`、guard≠final。這是**已接受 typed action 與舊表達權威未仲裁**，不是只需改末端字串。舊候選 `「私は今行けません」がいいかな。` 自身含敬體 `ません` 卻通過當前形狀檢查；T1/T2 候選被 `formal_register` 拒絕；T8 身份 core→final 失真。後三者是獨立缺陷，本批不改候選 prompt／檢查、身份或舊結果。

唯一核心變因：當 **既有 opt-in 明示引述改寫** 接受一個完整日文候選、且 protected／安全／事實來源權限沒有競爭時，把該候選明確交給 `RightBrain.speak`，將當輪舊 M32 表達權限降為有痕 shadow，並對新候選重新核當輪 P4-V frame。之後原 self-monitor、M39、日文 guard、P4-W、writeback 與 graph 仍執行；不在 emit 結束後強改 final。若後段仍改候選，記 mismatch/FAIL。沒有有效候選、旗標關閉、有競爭 protected 權限或形狀不明時完全保持原路徑。不可在回覆或 trace 捏造語義等價、私人心理或正式證據。

允許檔案：`uruha_explicit_rewrite_action_p4.py`、`test_p4_explicit_rewrite_action.py`、薄產品入口若安裝鏈必要、此計畫／新題／SHA、結果報告、`CURRENT_TASK.md`。不改 frozen 舊題/score、`uruha_brain_mac.py`、M32/M39/P4-V/P4-W 核心、正式 DB、原始 dirty checkout或無關 `output/graduate_application_report/`。

## 新題、判準、成本與停止規則

`datasets/p4_rewrite_surface_authority_fresh_probe_2026-10-20.json` 在程式改動與新模型呼叫前凍結。P1–P3 是中／英／日新引述改寫，與前批 exact source/utterance 不同；N1 詞義、N2 轉述、N3 敏感內容、N4 普通對話、N5 身份為負控。P1–P3 各一次本機模型、零重試；只有接受了自然常體、保留來源人稱／否定／時間且無捏造的候選，才能計 `candidate→speak→guard→graph/泡泡` 完整交付。模型若再生成敬體、畸形或錯義，即使權限修正正確也按正例 FAIL，保留 candidate-quality 責任，不為通過更改題目。N1–N5 新路徑 0 誤接管；N3 保護路由不退步，N5 自我身份不退步。

硬門檻：P1–P3 語義及自然日文 3/3 且至少一個被接受候選完成全部 digest 交接；N1–N5 0/5 誤接管；全部泡泡＝raw＝graph `UTTERANCE`＝最後 guard、每輪 ≤20 秒 runtime wait proxy、T0–T8 episode／profile 快照與正式 DB 隔離。逐輪列新增及可得全管線 model calls、prompt/completion tokens、elapsed；缺值標 unavailable。當任一 gate 失敗，整批 strict FAIL；不重送這八句或事後改 gold。若本次修正仍不能讓有效候選可見，進 `REVIEW_REQUIRED` 設計審查，不反覆加入表面特例。

先做零模型：M32 只在 typed candidate 成功時 shadow、P4-V 重算不沿用舊 violation、`RightBrain.speak` 記錄候選一次且不創造額外模型呼叫、無效候選/旗標 off/protected 不變、後段篡改顯示 FAIL、graph 不存原句；再跑受影響相鄰、compile、diff、SHA。只提交本批後，另起 0700 隔離 root、0-turn same-PID ready/stop、官方 SHA ONNX 私有預熱、空 profile/T0，真 Safari 新 session 八句各一次，逐輪即時核 raw/graph/profile/成本，停服務並只處理自己的分頁。正式同模型、temporal holdout、人評、VRM/Function Calling 統一驗收仍 pending。
