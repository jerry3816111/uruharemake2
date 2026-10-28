# P4 明確來源問句 v2：實作層驗證（Safari 前）

日期：2026-10-01。這是已曝光開發證據，不是 fresh product／正式 holdout 結果。
設計先在 commit `fc2e65b` 凍結；前一個獨立十輪 Safari 案的 T10 strict
`0/1` 原樣保留，不能用這份實作測試改寫。

## 實際介入

只在精確選中的「以前我說最喜歡 X 嗎；若不是誰說的」三語問句後，對本輪
`turn_episode` collection 做一次 `where_document:$contains` 原樣 value 查找，
最多 8 筆加第 9 筆 sentinel。全部完整、合法且沒有已送達同 ID 文本矛盾
才把真 episode ID/text 以 `bounded_source_lookup` channel 送到當輪
`passed_to_leftbrain`，同步 trace。summary 的 `友達の<姓名>` 只在原句本身
是朋友第三者時投影到同一姓名。來源答案只能說「找到的記錄裡使用者轉述
某人說過」，不推出真人偏好、user 本人偏好或全庫語義唯一性。查詢例外、
第 9 筆、損壞欄位／文件、同 ID 文本不一致、相關且不在 literal lookup
裡的已送達 episode、多個 actor、否定／更正都棄答。runtime graph 增
lookup→source→plan，可見 final 與 contract 對齊。

## 已有證據

- 新 fake collection、真隔離 Chroma 與 fake full-brain 的 29 個聚焦測試：literal CJK 命中、
  metadata、flat IDs、9 筆 sentinel、ID/文件/metadata/size 失敗、同 ID
  stale text、第三者／本人／引文／重複問句、summary 關係前綴、真 M22/M39
  route/surface 與 graph；full-brain 使用注入資料，非真產品記憶檢索。
- 聚焦＋相鄰 `151 passed, 8 dependency warnings in 38.05s`：
  `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q
  -p no:cacheprovider test_p4_bounded_source_delivery_v2.py
  test_p4_past_statement_source_answer.py test_p4_status_truth_entry_launcher.py
  test_memory_provenance_trace_v1.py
  test_p4_az_previous_turn_cjk_ellipsis_authority.py
  test_p4_ay_response_form_constraint_boundary.py
  test_speaker_attribution_recall_p2.py
  test_p4_k_typed_recall_surface_propagation.py
  test_semantic_persona_surface_m39.py test_semantic_route_taxonomy_m22.py`。
- 安全 launcher `check --port 7892` 通過，入口復用、sandbox probe 成功；
  這一步 `server_started=false`、0 model/Safari call，不能代替產品輪次。

## 尚未授權的結論

待新人物／新 value 的前瞻資料、答案標準與 hash 先凍結，才開隔離 Safari
真十輪、T5 後真重啟。即使通過，也只是單一來源問答界面的產品案例；
沒有同模型強 LLM 比較、人評、正式 temporal holdout、VRM/tool 驗收。
Chroma 原樣子串檢索不涵蓋 NFKC／語義等價異體、其他 collection 或
未檢索到的全部來源。`get` 實際耗時與完整產品模型 token 尚待真輪次記帳。
