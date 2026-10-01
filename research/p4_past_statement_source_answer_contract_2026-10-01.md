# P4 過去陳述來源問答：受限產品介面設計

狀態：根據已曝光的 10 輪現行產品 before 制定的**開發設計**；不是凍結
holdout，不能用同題修後重跑當獨立證據。before 細節見
`analysis/p4_current_relation_recall_probe_result_2026-10-01.md`。

## 單一可歸因變因

把「明確問之前某偏好陳述是我說的嗎、若非由誰說」視為一個受限的來源問答
transaction，而不是一般聊天政策：query detection → 當輪**已檢索且傳給左腦**
的 episode/recent source → actor/value/引文角色核對 → unique 或 abstain →
同一日文可見表面／trace。這是整體**介面變因**，不是宣稱每個子環節各有獨立
因果增益；既有 M22/M18/M39 實作不改舊研究資料或通用安全規則。

## 受限授權與失敗判準

- 僅選完整句、明確過去第一人稱「最喜歡」問句，且有可抽出的具體 value；
  中文入口必須是緊接「我／本人＋以前／之前／曾經＋說過」的封閉句型，
  「沒有說過」「聽她說過」與否定／轉述不得混入第一人稱肯定主張；
  後接別的指令、第二個值、引文或假設即不選。不處理模糊的「你懂我嗎」、
  語氣推測、任意關係抽取。中文、英文、日文**問句**各設保守入口；這不
  表示三語任意來源敘述皆可解析。不匹配完全保留原產品路徑。
- 候選只能是本輪 `memory_provenance.passed_to_leftbrain` 的
  `direct_episode` / `selected_working_memory` 或 `recent_turns`，需含持久
  `memory_id` / `trace_id`；不得暗查整庫、使用同輪尚未寫回的當前問句、
  或把無來源 summary 當獨立事實。對 episode 需原始 User 與 Summary
  同時明示相同 value 與 actor。舊 episode 的原句是**未跳脫的文字欄位**，
  故欄位分隔符與不受支援來源句型一律 fail closed；目前僅接受完整匹配的
  少量中文／日文直接敘述型（人物和值為變數），**不是開放領域的來源理解**。
  第三者偏好主體不等於第三者親自發言；需要緊接該主張的明示本人發言訊號，
  否則只能說記錄提到此人、本人是否說過未知。引文、假設、改口、複合敘述
  與否定要 abstain；只見模型摘要而沒有原句支持不能授權。
  人物必須是單一具名者、值必須是單一值；「紗枝和美紀」、「玄米茶或
  桑の葉茶」、代詞或「某人」不能被當成唯一 actor/value。摘要不能只擷取
  一段正向片語而忽略後面的不確定、否定或同值第二人物。
  若已送達的另一筆原句含相同 value、卻不符合這個狹窄語法，即使第一筆
  合法也不能假裝只有一位可能說話者；trace 記其 unresolved source ID 並棄答。
- 唯一已確認第三者、且已檢索紀錄沒有本人同 value 的明示紀錄時，回覆
  僅說「**目前確認得到的記錄**中使用者曾轉述某人自己說過」；這是
  **使用者先前報告的發言**，不證明現實中本人確實說過、也不聲稱全生命／
  所有未檢索記憶都沒有。若本人也說過、兩個第三者、
  正反矛盾、來源缺少、值不同或不能安全日文化，就明確承認範圍或
  無法判定，不能補名字。不得寫 user profile／episodic factual 推測。
- 當安全 route 選中時完全不得覆蓋；即使原中文問題帶有「誰」也不能
  改寫低路安全結果。surface guard 只有在同一 contract 的 source ID、
  value、actor、`factual_or_memory/matched/deterministic_rule_plan` route 與
  final core 一致、且通過既有語言拒絕器時才取得權限；若此路徑完整性
  失敗，輸出來源中立的日文棄答並同步 final trace，不能沿用前一層已洩出
  人名的候選。已選問句若誤入一般 route 或 plan intent 漂移，也棄答；真正
  safety/protected route 則保留原安全回覆。graph 顯示查詢、來源、判斷及
  最終句；recent-turn 的 persisted episode ID 與實際傳入左腦的 derived trace
  ID 分別記錄，不能把兩者偽稱為同一 ID。語言拒絕器只擋明顯
  script/格式錯，**不證明所有詞彙已自然日文化**，仍需 Safari 人眼觀察。
- 為避免既有 selected plan 將 core 截成 40 字，受限 contract 的核心日文句
  超過 40 字即改為棄答；來源完整 ID 僅在 contract/node，不放到會截字串
  的 `grounding` 欄。

## 驗收順序

1. 離線契約：第三者肯定、自我肯定、引文假證據、否定、雙方／多來源衝突、
   value 不同、沒有持久 ID、沒有檢索到、純閒聊、安全路由；精確證據 ID
   和 zero write/mode gate。測相鄰 route、speaker、memory、surface 回歸。
2. 假記憶 full product 一輪：經既有 product entry 能走 factual/memory
   而非 generic fast path、final Japanese == contract core、node graph 有同一
   source trace；0 新模型 call 僅限本介面，不宣稱全產品 0。
3. 另建未曝光的新隔離多輪資料，定稿／hash freeze 才開真實本機模型與
   Safari，至少跨重啟、視窗外來源、人名/值與本次不同，保留失敗、
   逐輪日文／graph／持久 ID／end-to-end 秒數，0 retry。

若離線 contract 無法在受限證據內唯一歸屬，保留 `REVIEW_REQUIRED`；
不得放寬安全路由、憑模型自報的 `confidence` 或重跑已曝光 T10 追分。
即使新案例成功，仍只支持此受限問句族的產品能力，不推出普遍人類理解、
強 LLM 比較勝利或正式 temporal holdout。
