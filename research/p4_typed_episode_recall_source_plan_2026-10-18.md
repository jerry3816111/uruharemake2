# P4 跨重啟顯性回憶：typed episode 來源修正（首輪前凍結）

狀態：2026-10-18，設計與新題在實作／新模型生成之前凍結。這是開發者自編產品驗收，不是正式 holdout、人評或同模型優勢實驗。既有六輪 Safari 的 strict FAIL 與 raw SHA `2b343e003101ba0cbf5940c6093686fc96ff0c333e60738a6dcaba72b4d3db78` 不改判、不重播。

## Before、問題與唯一變因

上批 T6 的同一隔離 DB 有 T1 直接 User episode（候選 rank 7）及 rank 3 的合法 `EpisodicSummary:`。`_valid_pool_rows` 對所有 `source=episode` 候選一律要求原始 turn serializer；trace 投影丟失 Chroma metadata `source`，合法整合摘要被當成畸形 turn，整池 `episode_provenance_incomplete`，故沒有進一步檢查 T1。T1 的 stored `source=turn_episode`、摘要的 `source=episodic_consolidation` 可區分；`consolidation_state=consolidated` 不等於摘要。上批 T6 答錯與 T1 表面措辭、copula coverage 為不同問題，本項不混修。

唯一能力變因：在**新 opt-in 入口**把已儲存的 episode record type 投影到可追溯候選；狹義顯性回憶的焦點視圖只讓 `turn_episode` 的原始 `User:` 可作答案，把驗證為 `episodic_consolidation` 且具預期摘要格式者列為 audit-only。候選池、排序、top-5、分數、原資料、一般聊天與其他模組保持原樣。未知 type、類型與文檔矛盾、重複 ID、畸形直接 turn 必須 fail-closed。焦點視圖是副本，query 與最後 surface guard 兩次須核同一原話／core；graph 顯示摘要不能作答案的收據。不得只靠 `EpisodicSummary:` 字串跳過來源驗證。

可改：新 opt-in type adapter 與聚焦測試、新薄 Web entry/controller、本計畫、前瞻 dataset/SHA、必要結果報告及 `CURRENT_TASK.md`。不得改已凍結 focus module、全域 scorer／Chroma 寫入、上批資料/gold/報告判決、正式 DB、原始 dirty checkout及無關 `output/graduate_application_report/`。若 adapter 無法保有來源與 guard 一致，先停設計審查。

## 新題與 strict gate

`datasets/p4_typed_episode_recall_source_fresh_probe_2026-10-18.json` 九輪，建立前 tracked tree 逐字碰撞 0/9。T1 原話位置、T2/T3 同焦點衝突、T4 第三者引述、T5 無關直述；T5 後先留至少 55 秒無輸入並只讀確認隔離 DB 真有 `source=episodic_consolidation` 的摘要收據，才 planned stop／同隔離 DB 重啟；若沒有生成，先決條件／coverage FAIL，不人工插入或補送。T6 問 T1 位置、T7 問 T2/T3 時刻、T8 問不存在的顏色、T9 撤回時刻。T6 必須同時看見可信摘要及 T1 直接來源於 retrieved pool，否則本次機制覆蓋不足即 strict FAIL，不可憑猜對算成功；T7 必須兩個衝突來源均進 pool，否則不算衝突控制成功。T6 只准 T1 白い階段，不准 T4 赤い門或摘要推論；T7 不任選八／九時；T8 不編色；T4/T9 不造假的 profile fact。若 T1 rank>5 則再核專用 handoff；若未出現，不額外宣稱 rank>5 再現。

首輪前：新 0700 隔離 root、0-turn readiness/stop、官方 SHA ONNX 私有離線預熱、空 profile；先聚焦零模型和相鄰回歸、code／依賴／dataset SHA、diff review、commit/push 與 PR head。Safari 兩 session 同 DB、九題各一次／0 retry，T5 後 planned restart。9/9 raw＝graph UTTERANCE＝當輪 Safari 泡泡、自然日文／人格身份安全不退化、各不同 episode、T0–T9 全量 profile 0 rows／同 digest、user wait 每輪 ≤20.0 秒、新 adapter 0 模型呼叫，記錄可得 token／延遲／summary type/rank、PID exit／port vacant。每一 gate 都要通過才算整批 PASS；任一失敗存原件、strict FAIL，不重播或放寬 gold。至多兩個有根據修正批；仍失敗 `REVIEW_REQUIRED`。

零模型另核 metadata/doc mismatch、unknown/missing type、畸形 turn、duplicate ID、retrieved/pool 不一致、衝突、撤回、敏感原文及兩次 builder／guard 同源；測試題不同於 Safari 字面。先跑 `test_p4_typed_episode_recall_source.py`，再跑 `test_p4_explicit_episode_recall_focus.py`、`test_memory_provenance_trace_v1.py` 與相關 P4 回歸；不重跑無關長套件。結果只可主張有界日文 User 原話回憶的來源類型修正，不可外推為任意長對話、跨語言回憶、真人被理解感或普遍勝 LLM。
