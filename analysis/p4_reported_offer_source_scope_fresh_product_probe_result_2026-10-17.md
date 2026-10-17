# P4 第三者引述邀請來源作用域：六輪 Safari 產品驗收

狀態：2026-10-17；**有限來源／行動機制符合 6/6 事前分流條件，但整批產品 strict FAIL**。T1 的最終句首 `先に、` 是沒有當輪來源或語境授權的固定表面前綴，日文不自然，且可被理解為額外的先後關係；事前要求的逐輪「profile 全內容 hash 不變」也未取得。不能用新節點 `visible_report_preserved` 把這個反例報成完整產品 PASS。這批是開發者所寫、首次 Safari 前已凍結的前瞻六題；不是獨立 holdout、人評、同模型 LLM 比較或開放域引述理解證據。上批 selected-offer 引述誤接的 strict FAIL 也不被本批追溯改分。

## 事前凍結、執行與隔離

- 程式、六題與逐題 gold／程序在首輪前 commit `00e3016` 推送至既有 PR #435；`research/p4_reported_offer_source_scope_fresh_probe_freeze_2026-10-17.sha256` 8/8 現在仍相符。新六句各送一次、0 retry、每輪門檻 20 秒；T3 後按原計畫在**同一 DB** stop/restart。
- 使用 launcher-owned 0700 私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-57nek51o`，非正式 DB。真產品 run `6652ab14b11f25a8`（PID 53637）與重啟 run `47db8e22a71fdfc8`（PID 54305）均核唯一 loopback listener／HTTP 200；兩次 planned stop 都核原 PID exited、port vacant。Safari 使用兩個新分頁、兩 session `20261017_171653_d0227b8c`／`20261017_172040_90435cd7`；保留原有分頁，未外部部署。
- T0→T1–T3 的 persisted episode 數為 0→1→2→3，停機／重啟前後同 3 個 ID，T4–T6 為 4→5→6；最終六個 ID 各異。每輪 `subject=user` profile 快照 `user_profile_rows=[]`，canonical 空陣列 SHA256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` 不變。但快照工具只擷取此 filter 的 ID／metadata，沒有擷取全 profile collection 的 documents／其他 subject；故事前「profile 全內容 hash」條件**未驗成**，不能事後拿空陣列 hash 充當。T5 的偏好候選因 `question_scope` 被拒絕（候選 1／准入 0）；六輪 trace 寫回皆只有 `episodic_memory/turn_episode`，未觀察到第三者偏好寫入本人 profile。

## 事前 gold 對照與實際可見結果

Safari 泡泡由外部瀏覽器逐輪觀察；它不是由 raw log 的 `browser_bubble_observed` 欄位推斷。六輪泡泡與同輪 graph `utterance`、log `assistant_reply` 逐字一致，輸出皆為日文。以下的「節點符合」只說明有限稽核結果，不能代替自然度評分。

| 輪 | 輸入／Safari 最終泡泡 | selected／可見稽核 | 判定 |
|---|---|---|---|
| T1 | `同僚に「味噌焼きおにぎり、一口いる？」って言われた。` → `先に、同僚におにぎりを一口勧められたのか。で、なんて返した？` | `chat/plain_reply`；引述來源 `同僚→reported_user`；新 audit `visible_report_preserved`；沒有直接接受 | **strict FAIL**：沒有來源的 `先に、` 不自然／可能多加時間關係；有限 audit 漏檢 |
| T2 | `山椒ポテト、一口いる？` → `いや、ポテトなら一口ほしい。今それくらいがちょうどいい。` | `food_offer_generic/named_offer_accept`；舊 offer audit `visible_action_preserved`；新 scope node 缺席 | 直接邀請及肯定接受符合有限控制；`いや` 接肯定句是自然度警訊 |
| T3 | `先輩に「海苔チーズピザ、一口いる？」と聞かれた。` → `ん、先輩にピザを一口勧められたのか。で、なんて返した？` | `chat/plain_reply`；`先輩→reported_user`；新 audit `visible_report_preserved`，未直接接受 | 來源／行動符合有界 gold |
| T4 | `友達に「胡椒おにぎり、一口いる？」と言われた。` → `ん、友達におにぎりを一口勧められたのか。で、なんて返した？` | 重啟後 `chat/plain_reply`；`友達→reported_user`；新 audit `visible_report_preserved` | 來源／行動符合有界 gold；未借用前輪邀請 |
| T5 | `後輩は梨ゼリーが好き？` → `いや、後輩が梨ゼリーを好きかどうかは、今の話だけじゃ分からないな。そのくらいでいいだろ。` | `chat/plain_reply`；舊 unknown audit `visible_unknown_preserved`；新 scope node 缺席 | 未捏造後輩偏好，控制保留；結尾語氣生硬，仍待人格／自然度驗收 |
| T6 | `昆布ポテト、一口いる？` → `ポテトなら一口ほしい。今それくらいがちょうどいい。` | `food_offer_generic/named_offer_accept`；舊 offer audit `visible_action_preserved`；新 scope node 缺席 | 當輪直接邀請與肯定接受符合有界 gold |

三個引述例 3/3 轉為 reported speech，兩個直接邀請 2/2 保留 action，第三者偏好未知控制 1/1 未被新 gate 接管；新/舊 graph 節點各在預期輪次出現，T1/T3/T4 final 皆未直接替 Uruha 接受。M19 `user_wait_seconds` 依序 `[2.7057, 2.7410, 3.0062, 2.7409, 2.9818, 2.7930]`，最大 3.0062 秒、總 16.9686 秒，皆低於 20 秒；這是 runtime 指標，非 Safari 手動牆鐘。六輪 M21 均為 `deterministic_rule_plan`、一般模型 planner calls 0；可核的 model surface 欄位顯示 blend 停用，未見候選生成，沒有可比較的本輪生成 token 成本，不能據此主張勝過強 LLM。0-turn ONNX 離線預熱是獨立設施成本，不併入每輪延遲。

## 失敗定位與下一個必要交付

T1 `selected_plan.core_message_jp` 為 `同僚におにぎりを一口勧められたのか。で、なんて返した？`，沒有 `先に、`。`uruha_brain_mac.py::_finalize_surface_reply` 依 intent／surface act／輸入字元和在八個固定開頭間選一個，沒有對開頭語義與上下文作准入；這次選了 `先に、`。新 `uruha_reported_offer_source_scope_p4.py::_PREFIXES` 又將其列為可接受，M39 對此輪 `unsupported_additions_before=[]`，故新 audit 報 `final_report_faithful=true`。所以根因是**決策之後的固定前綴授權／稽核盲點**，不是這次第三者／直接邀請的路由又選錯。這是只讀的局部因果定位，不代表已證明所有表面品質問題同因。

本批原題、gold、程式／freeze、raw 不改、不重播，不把 `先に、` 從 gold 事後放寬。下一步先獨立審查**表面開頭是否有來源與語境授權**這一單變因：事前列報告引述、直接接受、未知、轉折、真正時間先後等正反例；下一個 fresh batch 曝光前另補足全 profile 內容 hash 的快照工具／證據 gate，再決定有界修正與全新未曝光 Safari batch。T2 的 `いや` 和 T5 的硬結尾先列人格自然度風險，不與 T1 合包追分；上批 sweet-core audit 缺口仍是另一獨立項。正式同模型控制、人評、temporal holdout、完整 VRM／Function Calling 仍 pending，整體 Goal 遠未完成。

## 原件與證據邊界

- 本機隔離 raw `web_logs/conversation.jsonl` 六筆，SHA256 `0df3d8ce4b1f0ca790728f6f7995a9d9f89a88f2996b2e085b9517056f94dd42`；凍結六輸入對 raw `user_text` 逐字 6/6。`browser_bubble_observed=false` 是 log 本身不能作瀏覽器見證，真 Safari 觀察另行核對。
- `evidence/snapshot-t0_before.json` SHA256 `c4cb0a55bf6a8a3934d77ada647623a3818599a88303905f892d328fc5e55e47`；`snapshot-t3_after.json` 與 `snapshot-t3_restarted.json` SHA256 同為 `66c13233eeead9ee64e1a68f95faaabaf2bba33f50c71977ecdb6d83aa13e0d5`；`snapshot-t6_after.json` 與 `snapshot-t6_stopped.json` 同為 `744c4a58a21da18e55a36e93c723eb54e288aa43189c94a2f8f641802ff907d9`。T1–T5 快照與兩次 stop JSON 亦留在同 root。
- 隔離 raw／DB 不進 Git；報告僅保留短例、可重算摘要與限制。Safari 的泡泡／節點由當輪可見畫面核對並在此轉錄，未另保存可重播的瀏覽器截圖。沒有獨立日文母語盲評，也沒有官方認定的整體人類理解量尺；本批 strict FAIL 同時保留自然日文反例與未達成的全 profile 內容 hash 證據條件。
