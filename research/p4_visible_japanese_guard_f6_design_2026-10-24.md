# P4 f6：簡體字殘留的共用可見日文 guard

狀態：事前 source-only 設計；此檔不代表實作或產品驗收通過。

## Before 與問題邊界

f5 原生 Safari 唯一回覆為「頑張ったね。頑張り继续！そのくらいでいいだろ。」；私有 JSONL SHA `921d7a7f72aa1de6dae0c39c887108fc03dbe6f524b8b5153d4381e116c7edc5`。`logic.core_message_jp` 在可見輸出前已含 `继续`，最後 `visible_language_guard.changed=false`、reasons 空。來源事件也在 selected core 中缺失，這是**另一個**問題；f5 strict FAIL 不重判、不重送。f5 報告見 `analysis/p4_compact_schema_f5_fresh_product_failure_2026-10-24.md`。

## 唯一變因與不改邊界

只擴充共用 `rightbrain_language_quality.AUDITED_NONSTANDARD_CJK_RE`，納入已實測的中文專用簡體字 `继`、`续`。既有候選 gate、M49、最終 visible guard 共享同一規則，程式入口與既有 fallback 不改；不得把這兩字原樣轉寫成固定「頑張って」模板。禁止改 f5 題/gold/模型回覆、prompt、JSON Schema、parser、M29/M39、候選排序、event grounding、Persona、記憶、背景或正式 DB。此變因只能證明特定簡體字殘留會被拒／安全退回，**不能**證明語義承接、自然度、人類偏好或一般中文識別全面完成。

允許改：`rightbrain_language_quality.py`、`test_user_visible_japanese_guard_v2_11.py`、`test_rightbrain_model_candidate_gate.py`，必要的新聚焦測試與本研究/結果/任務卡。先寫紅測，驗證 shared `has_bad_language`、candidate rejection 和 final guard 對 f5 原句由漏檢變為拒絕；同時確認正常日文「継続」「続けて」「頑張ったね」不誤擋，且既有不相關表面測試保持。若 guard 最後只能產生泛稱 fallback，記錄為品質仍失敗，不得用 language-only PASS 包裝產品 PASS。

## 新題、成本與實測判準

新作者開發題與事前 gold 在 `datasets/p4_visible_japanese_guard_f6_probe_2026-10-24.json`；不能稱正式 holdout。初稿題與 f3 自行車破胎事件重疊，獨立設計複核在 freeze 前換為陶藝小碟；凍結前 HEAD tracked 內「陶芸の小皿」0 命中、source-only M29 為 `brief_encouragement`。凍結後不更換題、gold 或門檻。code gate：針對性紅→綠、相鄰 guard/候選回歸、compile/diff check；零模型 full route 若涉及真入口應核對 guard 與 episode 同句。真產品 gate 用新 7933、全新 0700 隔離 root、官方私有 ONNX 離線 warm、同 PID zero-turn、T0/Tpre 0600+fsync，先做好靜態核對；完整背景 pair 後快照，原生 Safari 一次 Send／0 retry，Tpre→arrival ≤10 秒且 0 interleave，single opaque ID 完整 delivered。若 pre-Send/attribution gate 失敗，保留 0 Send 或 off-gate 失敗，不重送。

可見 gate：泡泡、raw、guard、graph utterance、隔離 episode 同句；完全沒有 `继`/`续` 或其他可辨識非日文殘留，且短自然日文承接「第一次自己燒好陶藝小碟」、不給教學、不追問、不編造。graph 核實 input→retrieval→decision→utterance→writeback；native visual 原件若無法持久保存，明記缺證。上限 3 completed generations、2000 provider tokens、20 秒 user wait、1 Send；分列 background/Brain/Web 未 instrument 成本。任何可見語義或語言硬 gate 失敗，整體 strict FAIL。f5 及本題均不是同題強 LLM A/B、人評或 formal temporal holdout。

**操弄檢查分層：**新真模型可能本來就說乾淨日文；僅憑「無 `继/续`」不能聲稱 f6 guard 在產品輪次生效。只有持久 trace 可見候選因 `nonstandard_cjk_surface` 被拒，或最終 guard `initial_rejection_reasons` 含該理由且 `changed=true`，才可稱此輪實際觸發；否則記為 `not_exercised`，確定性紅綠測試仍只證 guard contract。即便觸發且無中文，若退回泛稱答覆、未承接陶藝事件，整體產品仍 FAIL。

若本變因可攔簡體字但仍不能承接具體事件，下一項先設計跨語系、來源對齊的 selected-plan evidence/utility 單變因，不再疊字元名單來追語義分數。
