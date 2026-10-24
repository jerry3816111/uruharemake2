# P4 B 來源限定：首輪前 preflight 修訂紀錄

原設計／八題在 `ca0fb5b` 凍結、已推 PR；此修訂發生在任何新題模型生成與 Safari 之前，不修改原 dataset/gold 或舊 B 失敗。只讀對照首批 raw 顯示：緊接前輪的被動 working memory `memory_anchor.source=short_term`、`trace_id=derived:short_term:<20 hex>`、`memory_id=null`、`provenance_channel=selected_working_memory`、`expected=false`、`memory_use_expected=false`、`memory_speakability=background_only/relevant_but_not_requested`；重啟後才可能是 `source=episode`、`stored:episode:<memory_id>`。因此原計畫僅容 `episode` 將新 T3 錯擋，與 T3 作為已知對象後正例的事前設計衝突。

修訂的同一「本輪引文來源限定」權限：可接受 `episode` 或 `short_term` 的**被動、可追溯** context；`episode` 需 `stored:episode:` 與 memory ID 一致，`short_term` 需 `derived:short_term:`＋20 位十六進位、無 memory ID；兩者皆須 `expected=false`、`selected_working_memory`、`memory_use_expected=false`、`background_only/relevant_but_not_requested` 或 `latent_ok/weak_contextual_memory`。這些僅是被檢索的背景，不是答案來源，也不證明確認對象未知。其他來源、缺欄位、明示回憶／profile／protected 或 suppressed 仍 fail closed。句子仍只承接當輪轉述，不用背景內容填確認對象，也不說「還不知道」。

此為首輪前的設計缺口修正，不是觀察新題答案後追分；新資料 SHA 仍 `ad39f8d8cd729d9c250a99aec08999ab64fe50047fca77db1aaa58e05edb63ea`。實作須補零模型 `short_term` 有效／trace 錯誤／source 不符測試及相鄰回歸，最終 code/測試/本修訂另列 SHA 並推 PR 後才可做一次新 Safari。若新批 T3/T5 仍 coverage 失敗，保留 strict FAIL／`REVIEW_REQUIRED`。
