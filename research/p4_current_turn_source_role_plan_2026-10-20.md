# P4 當輪行動／引述來源角色憑證：實作前凍結

日期：2026-10-20。這是 `p4_current_turn_action_role_design_review_2026-10-20.md` 之後的新、較廣的產品工作項；不是第三次重跑舊明示改寫題。前兩批八輪原件、0/3 gold 與 `REVIEW_REQUIRED` 不改判。案例是開發者撰寫的 source-disjoint 契約資料，不是正式 holdout、人評或產品成功證明；審查由同一開發流程完成，非獨立審查。

## Before 與唯一變因

- 前批真 Safari P3：M31 用整個當輪輸入取得 `surface_authority=true`，可見句只是重述「把引號內的話柔化」；P4 候選生成後因競爭權限被拒。M31 是原文 SHA-256 前 16 位，P4 舊 scope 是 NFKC 後完整 SHA-256；不能直接比較。M32 無可獨立核對的當輪 M31 來源 ID。
- 本批未曝光開發輸入 M1「改寫＋回憶」被舊純函式判為單一改寫；R4「朋友會讀到」的改寫被舊純函式誤判為轉述。這是零模型 before，不是 Safari 結果。13 句對現存 40 份 P4 probe、252 條 user/input 的 exact、NFKC 與引號內來源逐字碰撞均為 0；不主張對整個 repository 未曝光。
- 唯一變因：**把整句關鍵字准入改為有界的當輪引述／外層指令來源角色憑證**。記原始事件與 NFKC digest、原文 span 坐標、引述與外層角色、單一／混合行動、可觀察 cue、未知理由；不存原話於圖或長期 profile。這不是一般人類語用理解器，也不能靠回答字串裁定權限。

## 邊界、階段與判準

1. 先以 `datasets/p4_current_turn_source_role_contract_2026-10-20.json` 的 13 句做零模型憑證；五個明示改寫可准入，M1 混合、D1 詞義、RPT1/RPT2 第三者、Q1 引語評價、O1 普通話、P1 敏感與 P2 身份假設不可當成改寫。錯任一個為 FAIL。raw span 必須能回指同一原文，R4 不可因讀者 `友達が` 誤判 reported，U1 全形數字 raw/NFKC 需分開核帳。
2. 准入前即檢查受保護 route；負控不能增加改寫模型呼叫。已准入的生成與候選品質仍走原 fail-closed；`_validate_phrase` 只檢機械形狀，**不是語義等價證明**。不改 JSON transport、敬體漏網、N1 詞義、身份或 P4-W。這些維持獨立失敗。
3. M31/M29 原文 digest 可重算，但單靠 16 位 digest 無法排除另一輪相同原文；M32 更缺明確 parent digest/event ID。因此本項不得因憑證而 shadow 任何 authoritative M31/M32，也不得把 `source_first_fast_path` 當充分證明。先在收據與 graph 標 `lineage_insufficient_for_authority_transfer`，舊保護／事實／記憶／M33/M28 權限照舊。若後續要轉移，另需上游事件／cycle lineage、M32 parent 及候選語義驗證後前瞻設計與新題；缺一即 fail-closed。
4. 允許檔案：本計畫與資料、`uruha_current_turn_source_role_p4.py`、`uruha_explicit_rewrite_action_p4.py`、`test_p4_current_turn_source_role.py`、必要的既有改寫測試、本卡、精簡結果與 freeze SHA。不得改核心 M31/M32、其他產品 route、正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 或既有凍結題／gold。
5. 精確零模型驗證：先新聚焦 `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_current_turn_source_role.py test_p4_explicit_rewrite_action.py`；再回歸 `test_p4_current_statement_source_authority.py test_p4_reported_ack_m31_priority.py test_p4_quoted_line_act_scope.py test_semantic_authorization_m31.py test_semantic_commit_repair_m32.py test_p4_v_utterance_frame_coverage_extension.py test_p4_w_frame_preserving_visible_repair.py`。改前相鄰八檔 97 passed／9 既有 warnings／61.79 秒。加上 raw/NFKC、重複相同原文不同 cycle、錯 digest、畸形契約、protected、flag-off、graph 只存 digest 的契約。
6. 新 Safari 產品層只有在零模型與 diff／source SHA 通過後才另定 fresh 單次無重試探針。若本階段只有證書，Safari 與語義品質明列 pending，不用舊題當新驗收。資源上限：本階段 0 模型／網路／正式 DB 呼叫；零模型測試最多兩個有根據修正批次。後續真實輪次另凍結 call、token、延遲、隔離與 graph gate。

成功只代表當輪資料／指令分界與誤准入修正、可追溯 lineage 限制；不能代表改寫成品、M31 仲裁、人類反應方程式或相對強 LLM 的優勢。任一不確定分類須 abstain，保留原 route 與舊負結果。
