# P4 hash-prefix provenance：七輪真 Safari 前瞻產品驗收

**結論：整批 strict FAIL／REVIEW_REQUIRED。** 七句依首輪前凍結順序各送一次、0 retry，兩個 session 與同 DB planned restart 都完成；但事前 strict PASS 的三個必要條件未達：T3 把「使用者先確認自己的行程再答覆」誤接成「系統先問想要的回覆方式」；T1/T4/T7 的 `final_related_hash_additions_removed` 都是 0，Safari 真路徑沒有觸發本項欲驗的 hash-added-prefix 移除；T0 profile DB 不存在，T1 首輪 lazy 建立 DB/collection，使「從 T0 起 status／count／全內容 digest 全程不變」不能成立。這不是第三者偏好被寫入的證據，亦不能用 T1–T7 rows 全 0 把原 gate 改成 PASS。前批六輪 strict FAIL、原題/gold/raw 與本批首輪前凍結檔均不改、不重播。

## 事前凍結與執行邊界

- 單變因、gold、判準：`research/p4_hash_prefix_provenance_gate_design_2026-10-17.md`、`research/p4_hash_prefix_provenance_fresh_probe_plan_2026-10-17.md`、`datasets/p4_hash_prefix_provenance_fresh_probe_2026-10-17.json`；皆由首輪前 commit `4200900` 推至 PR #435。結果後重核 freeze manifest 10/10 SHA `OK`，PR 當時 head 為 `42009009fb7aa1d45bc6e7bc871c5c6c683f22d0`。首輪前聚焦零模型 12/12、相鄰 36/36（8 warnings）、六個新 Python 檔 compile，屬**契約/工程證據**，不是本批 Safari 成功。
- 全新 launcher-owned 0700 隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-okp487b3`。本機 Chroma ONNX archive 83,178,821 bytes，SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，預熱成本在七輪等待之外。沒有使用正式 memory DB，沒有外部部署、公網 share link 或模型下載作為本批生成證據。
- 產品入口 `uruha_web_ui_product_p4_hash_prefix_gate.py`。送題前另有 0-turn 預檢 run `ab4a6fd056a841a1`、PID 61458，ready HTTP 200、planned stop exited／port vacant，**不算對話 session 或語義證據**。七輪分兩段：run `8dfa0b98ec36141a`、PID 61990；重啟 run `810a3f20ac031bea`、PID 62772。兩段 ready receipt 均為同 PID 唯一 listener／localhost HTTP 200。T3 後 planned stop 原 PID exited、port vacant；同一 root/DB 重啟後 T4–T7；最終 planned stop 亦核 PID exited、port vacant。Safari 實際送七句並逐輪讀取泡泡、runtime node graph（selected/source/新舊 audit/UTTERANCE）。重啟後 UI 產生新 session，但沿用同一隔離 DB。
- 原始 `web_logs/conversation.jsonl` SHA-256：`77b0a8cc138b73176a4a1f47369442b5407d10ca88511da6f41d15d7552016b8`；兩個 planned-stop receipt SHA-256 依序為 `f2cd0250e88e670bef9d32382ea5fb7536a7c0687cc7934583d0b124bc2bd95a`、`4a432f7c4265265a3b1c7af70c3421c3057012f02d04de651b0f33ad0e34fac1`。完整 raw、readiness、stop 與 22 份 profile/episode 快照只在該隔離 root，未複製私人資料入 repo；快照工具讀取 Chroma 可能碰 SQLite metadata，不能稱 DB byte-read-only。

## 逐輪可見結果（T1–T3 第一 session；T4–T7 第二 session）

| 輪 | Safari 輸入 → 最終可見日文 | selected／graph 稽核 | M19 等待 |
|---|---|---|---:|
| T1 | `先生に「バター焼きおにぎり、一口いる？」と聞かれた。` → `先生におにぎりを一口勧められたのか。で、なんて返した？` | `chat/plain_reply`；舊 source `visible_report_preserved`、新 prefix `visible_core_exact`，selected core＝可見句，removed 0。沒有把老師的提議當成使用者邀請。 | 2.7363s |
| T2 | `海苔ポテト、一口いる？` → `ポテトなら一口ほしい。今それくらいがちょうどいい。` | `food_offer_generic/named_offer_accept`；action audit `visible_action_preserved`；reported/prefix audit 缺席。 | 2.6526s |
| T3 | `先に予定を確認して、それから返事してもいい？` → `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | `chat/plain_reply`；selected core 已是同一錯句，非 hash-prefix 修正刪掉了上游連接詞。使用者要先查**自己的行程**，系統卻先要求指定回覆方式；**事前順序語義控制 FAIL**。這輪未預註冊 intent label，不以 label 單獨判錯。 | 3.3806s |
| T4 | `父に「山椒チーズピザ、一口いる？」って言われた。` → `父にピザを一口勧められたのか。で、なんて返した？` | 重啟後 `chat/plain_reply`；舊 `visible_report_preserved`、新 `visible_core_exact`，removed 0；未借用 T1 老師/飯糰。 | 2.7171s |
| T5 | `後輩は梅ゼリーが好き？` → `後輩が梅ゼリーを好きかどうかは、今の話だけじゃ分からないな。そのくらいでいいだろ。` | `chat/plain_reply`；沒有憑問句捏造後輩偏好，reported/prefix audit 缺席。末句 `そのくらいでいいだろ` 有生硬/催促感，列非獨立自然度警訊，沒有真人評分。 | 3.0319s |
| T6 | `味噌ポテト、一口いる？` → `ポテトなら一口ほしい。今それくらいがちょうどいい。` | `food_offer_generic/named_offer_accept`；action `visible_action_preserved`；reported/prefix audit 缺席，沒有誤答先前父親的披薩。 | 2.9573s |
| T7 | `姉に「昆布焼きおにぎり、一口いる？」と言われた。` → `姉におにぎりを一口勧められたのか。で、なんて返した？` | `chat/plain_reply`；舊 `visible_report_preserved` 且 `admission_proof_matches=true`；新 `visible_core_exact`，`selected_core_agrees/prior_report_audit_matches/utterance_matches_reply=true`，`extra_fixed_prefix_visible=false`，removed 0。 | 3.2390s |

七輪當場 Safari 觀察的泡泡逐字等於對應 graph `UTTERANCE`；保存的 raw 可獨立重算 7/7 `assistant_reply`＝blackboard `utterance`，但沒有七輪完整 Safari 畫面/操作收據，**不能從持久原件獨立重算 browser-bubble 或 0 retry 的 UI 歷史**。這兩項是當輪 UI 觀察，不能冒充不可否認的瀏覽器證據。兩 session IDs `20261017_175914_6a37266c`、`20261017_180251_d81b8eeb`。等待範圍 2.6526–3.3806s，平均 2.9593s，7/7 ≤20s。七輪 M21 general LLM planner attempted/completed 都是 false，raw 未見任何 `model_call_attempted=true`；本批記錄到的生成呼叫／token 均為 0，但未量到 ONNX 預熱秒數與總能耗。這批**不能**算 fresh model generation，也沒有同模型 LLM 對照或人評。局部 deterministic route 的 3/3 reported source 與 2/2 direct offer fidelity 不會抵銷全批 FAIL。

## 記憶與重啟證據

獨立 profile-full receipt 的 T0 是 `db_status=absent`、collection `unavailable`、row count 0、digest null；T1 後 DB/collection 都 `present`，T1–T7（含 T3 stop/restart、T7 stop）每張 profile row count 0、全內容 digest 均 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。這只能支持「建立後觀察到的 profile 內容未變」，**不能**支持事前 T0→每輪 status/digest 不變的嚴格 gate。`turn_episode_ids` 數量按 T0–T7 是 0→1→2→3→3（停機）→3（重啟）→4→5→6→7，七個 distinct IDs；raw 每輪只記 `episodic_memory/turn_episode`，未觀察到 `user_profile` write。沒有把測試偏好寫進正式長期記憶。這是隔離 DB 的觀察，不是所有記憶安全性的普遍證明。

## Gate 判定、因果限制與下一步

| 事前 gate | 觀察 | 判定 |
|---|---|---|
| 七輪 0 retry／兩 session／同 DB restart／7 distinct episodes／7 泡泡＝graph／≤20s | 均符合；兩 PID 最終退出，port vacant | PASS（程序/局部） |
| T1/T4/T7 reported source 與 exact core、T2/T6 direct act、T5 未知不編 | 有界節點和可見句符合；T5 末句自然度警訊 | 局部 PASS／警訊 |
| 真 Safari 至少一輪 hash-added prefix **實際**被移除 | 三個 reported route 的 removal 皆 0 | **FAIL：修正機制未被真路徑觸發** |
| T3 尊重先查行程再回答 | 系統反而先問回覆類型 | **FAIL：順序語義** |
| profile status/count/全內容 digest 從 T0 全程不變 | T0 absent/null → T1 present/hash，T1 之後 rows/digest 穩定 | **FAIL：事前完整基線 gate** |

不做答後調 gold、重播這七句、用舊六句重跑追分或另加固定回覆。下個必要交付先以**只讀設計審查**分清：(a) hash 修正發生的 reachable 條件與如何在新未曝光真輪有正控制；(b) lazy DB 初始化在 T0 前完成的可檢驗 baseline，而不是事後放寬「全程不變」；(c) T3 的上游時間/主語語義錯讀作獨立單變因問題，不混入 prefix gate。新題與判準須再次首輪前凍結，受同一工作項最多兩個有根據修正批次限制。正式 temporal holdout、同模型公平比較、人類被理解感、VRM／Function Calling 完整產品、對完整人類反應方程式的證明皆仍 pending。
