# P4 時序行為者／作用域：新題真產品驗收計畫

狀態：2026-10-17，首輪 Safari 輸入前。唯一產品因果變因是 opt-in
`uruha_temporal_actor_scope_p4.py` 的當輪 actor/source/action/time seam，經新產品入口
`uruha_web_ui_product_p4_temporal_actor_scope.py` 啟用。原七輪 T3、前批五輪 strict FAIL、
舊 gold/SHA/raw 不修改不重播；未知偏好尾句自然度是另一風險，不合包。逐字新題與逐輪
gold 在 `datasets/p4_temporal_actor_scope_fresh_probe_2026-10-17.json`；此八題由開發者
事前寫成並經靜態文法核對，非獨立 holdout。

## 首輪前凍結與零模型證據

1. 審查 before 與單一變因見 `research/p4_temporal_actor_scope_design_review_2026-10-17.md`。
   M25 基層 `calibrate_need` 只在本輪明確要求**助手問目前使用者回覆形式**時授權；
   使用者自行查後回覆、明示第三者受詞／引述、否定或歸屬不明不由該 cue 授權。
   已辨識 self-defer 需交付尊重順序的日文行動；報告第三者時不得把引述當命令。
   同輪另有獨立任務時，不得以本層固定承接句覆蓋。不是任意自然語言主語解析器。
2. 零模型聚焦需涵蓋中英日正例、第三者引述、自述／第三者主詞／受詞、否定、
   protected、同輪獨立任務、P4-AT／M18／實際 selected 與 graph/final 一致；
   並跑受影響的舊 M25/M36/P4 路徑、Python compile、既有凍結 SHA。
   新題不得 exact 複製聚焦 fixture 或先前 dataset/result。
3. diff review，將本產品碼／測試、新八句/gold、本計畫、SHA manifest 先 commit、push、
   核 PR #435 head。凍結後零 answer-driven 修改、零 retry、零換題；失敗保留。

## 隔離與逐輪判準

1. 新 launcher-owned 0700 root；HOME/memory/session/log 隔離，正式 DB 與原始 dirty
   checkout 不動。唯一 0-turn readiness：同 PID、單一 localhost listener、HTTP 200；
   planned stop 後同 PID exited／port vacant。已備的官方 SHA ONNX 只可私有複製至
   新 root、離線預熱並記成本，不是一般模型生成。顯式 0-row profile setup 使用本項
   **exact** 入口路徑及 0600 receipt；全 profile 內容 digest 用既有 snapshot helper
   從 setup 後開始逐次核對。helper 是隔離 DB 的邏輯讀，非 OS 層不可寫保證。
2. T0 profile/episode 先存。T1–T4 用真 Safari、同一 session 各送一次，0 retry，
   每輪最多等 20 秒並存 raw/graph、profile 全內容、episode IDs、泡泡逐字及 M19
   等待。T4 後 planned stop/restart：同 root/DB 不同 PID、新 session、episode
   仍為 4；T5–T8 各送一次，最後 planned stop。預期 episode 0→1→2→3→4→4
   （停／重啟）→5→6→7→8→8（終停），八個相異 IDs。UI/runtime error 則停止
   後續，保留程序 FAIL；語義失敗可照固定次序完成未曝光輪次，但不得改規則追分。
3. 每輪核 actor node 在 M25 前、同一證據穿過 P4-AT/M18 selected/selected plan
   到最終 utterance；raw `assistant_reply`＝blackboard utterance＝graph UTTERANCE，
   真泡泡當輪目視對齊。self-defer 必須在使用者自己先查、稍後回覆的方向上；
   助手直接請求不得被誤擋；第三者引述不得作為當輪命令；不明不得假報已授權。
   final 不傾倒技術分析、自然日文、無來源／人格誇張或未經證實的記憶事實。
   新節點的 `surface_status` 需綁真正 selected action 與最終字串，不以單個問號
   作成功證據。逐輪 profile `status/count/full_content_digest` 必須與 setup after 相同。
4. **整批 strict PASS** 需要 8/8 真輪、0 retry、兩 session、same-DB planned restart、
   八個 episode、各輪 bubble＝graph、等待 ≤20 秒、逐輪路由與語義均符事前 gold、
   完整 profile digest 不變、自然日文與來源邊界全過。任一缺失整批 strict FAIL，
   同時另列可重算的局部機制通過項。沒有操作錄影時 bubble 與 0 retry 只能報
   當輪目視，raw 不能獨立重算這兩者。成本分設施／啟停／回覆等待、model calls
   與可用 token 欄位；0 model call 不冒充 fresh generation。

即使通過，也僅是有限 actor/scope 在此 opt-in 本機產品路徑的證據，不代表
同模型 LLM 優勢、完整語用理解、人格／人評、正式 temporal holdout 或生物腦方程式。
未過則保存最小反例、同一變因最多兩個有理由修正批次；不改已曝題或重播追分。
