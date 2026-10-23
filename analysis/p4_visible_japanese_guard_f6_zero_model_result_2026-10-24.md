# P4 f6：共用簡體字 guard 的零模型結果

狀態：**deterministic/隔離 fake-model route PASS；真模型、Safari、產品語義品質 pending**。事前陶藝小碟 source/gold 已於 `dff1efa` 凍結推 PR #435，f5 原始真 Safari strict FAIL 及其 raw 不重判、不重送。唯一產品改動是共用 `AUDITED_NONSTANDARD_CJK_RE` 加 `继/续`；prompt、schema、M29/M39、模型/預算、fallback 與凍結資料都不動。程式/測試/freeze SHA 在 `research/p4_visible_japanese_guard_f6_product_2026-10-24.sha256`。

## 前後差異

- f5 實際 raw `頑張ったね。頑張り继续！そのくらいでいいだろ。`：改前 `has_bad_language=false`、候選 reasons `[]`、可見 guard `changed=false`；改後 shared check 為 true、候選及最終 guard 都得 `nonstandard_cjk_surface`。三項聚焦紅測改前 **2 failed/1 passed**，改後 **3/3 passed**。
- 以同一 f5 raw 做 deterministic guard replay，改後輸出 `しんどいなら、今日は無理すんな。`，guard `changed=true`、reasons 含 `nonstandard_cjk_surface`。這安全擋住 `继续`，卻沒有承接「第一次縫回鈕扣」，甚至臆測「しんどい」。所以這不是使用者需要的合格回覆，只能算 **language-leak safety fix，visible quality FAIL**；f5 的原產品結果維持原判。
- 正常日文 `継続`、`続けて`、`頑張ったね` 不因本次字元擴充誤擋。支持場景 M49 仍 protected、沒有新授權模型呼叫，最後由可見 guard fail-closed；隔離完整 RightBrain＋假 LeftBrain、假 JSON Schema 候選故意混 `继续` 的新陶藝題，最後回覆不含這兩字且與唯一隔離 episode 相同。這是**注入故障的契約路由**，不是 fresh qwen 生成、真 Safari 或模型實際觸發證據。

## 測試及歷史 lock 界線

受影響七檔聚焦／路由 **99 passed、9 既有 warnings**；共用規則的修復選擇器、記憶 surface/cue、typed action 五檔相鄰：**59 passed、1 frozen-lock failed**。唯一失敗是 V86 `test_harness_lock_hashes_match`：舊凍結 lock 期望 `uruha_brain_mac.py` SHA `efc030...`，本批開始前 HEAD 已是 `404f846...`；本批又讓 `rightbrain_language_quality.py` 從凍結 `34c20d...` 變 `9671e3...`。19 個 frozen artifact 中 17 仍一致、2 個不一致；**不改 lock、不重算 V86 舊分數、不稱 V86 現版可重現**。排除該歷史 lock 但保留其失敗紀錄的相鄰行為測試為 **59 passed、1 deselected**。獨立只讀 diff 複核確認僅一處產品 regex 變因，所有新增/修改測試均屬測試檔。

0 真 provider calls、0 Safari Send、0 正式記憶寫入；pytest/fake 路由時間不能替代真 token、使用者延遲、背景和 Web 成本。新 source-disjoint 陶藝題還沒有真模型回覆；若模型自然產生乾淨日文且 trace 沒有 candidate/guard `nonstandard_cjk_surface`，產品操弄記為 `not_exercised`，不得宣稱本次 guard 在真輪產生增益。即使 guard 被觸發，語義未接住小碟事件仍是整體產品 strict FAIL。下一步：核 SHA/diff/status，只提交推送本項碼/測試/報告/任務卡並核 PR exact head；再依事前 7933 計畫作全新隔離原生 Safari 一次 Send，逐層保留結果。
