# P4 明示引述改寫：行動契約與前瞻產品驗收

日期：2026-10-20。此卡與同名 JSON 在本項程式及新題模型生成前凍結。作者自審不是獨立設計審查；題目是 developer-authored 產品探針，不是正式 holdout、人評或同模型強 LLM 比較。前批 raw SHA `1295179f08c0dd39b27ce4eb1964ff8034f558570205b3d2a60693528c57e2a8` 與 strict FAIL 永不改判、不重播。

## Before、判斷與單一變因

前批 T2 要「將引述句改得更柔和」：M21 selected core `承知しました`，speech plan 仍含 core；`contextual_expression_commit_p2` 的逐級 receipt 顯示 `_sanitize_reply` 將它改成 `うん`，M39／frame／visible language guard 皆 no-op。這證明表達路徑會把**被討論的語句**誤當成 assistant 自己在答應；但 `承知しました` 本身也比原 `了解です` 更拘謹，不能只保留字串就稱成功。前批 T4 是另一機制：真 `repair_check` 固定反問覆蓋 core；其所指「今の説明」的上一句實際為位置建議，精確重播也未必滿足要求，不併修。

本項唯一核心變因是 opt-in、typed **explicit quoted rewrite action**。只有當輪 User 的一個短引述、引述外明示改寫及期望的柔和／親近／委婉語氣，且一般非保護路由、沒有敏感內容時，才從**當輪可見引述**產生一個自然常體日文改寫短語，再將它作為改寫結果而非 assistant 的同意語交付。允許最多一次 `qwen2.5:7b` 本機新增生成呼叫；記實際 token／延遲，不能冒稱免費或與 baseline 公平。無可驗證候選時保持原路由並記 fail-closed，不套固定題目答案。不得把模型自稱「語義相同」當客觀證明；逐題由凍結 gold 人工核對核心意思、語氣與來源。

限定：一個配對引號、原句 2–40 字、當輪外層明示要求改寫／柔化／委婉或 casual Japanese；沒有未配對引號、衝突指令、翻譯／定義-only、第三者轉述、近期記憶／身份／安全路由、密碼／認證碼等敏感詞。中文／英文／日文外層請求可入；輸出只有自然日文。從當輪文字取 source，不讀舊 assistant、Chroma 摘要或私有 persona 當改寫事實。舊選定 core 與 M21 收據保留為 shadow；新 graph receipt 分別標 source、模型內層短語、組合後完整可見候選、最後可見字串的 digest，以及操作、檢驗與新增 model calls，不另持久化原句或心理推測。M39、既有安全與 final language guard 不關閉、不放寬；若任一後段改寫完整候選，receipt 應顯示 mismatch，整題失敗。

## 實作邊界與檢驗

允許新增 `uruha_explicit_rewrite_action_p4.py`、聚焦 `test_p4_explicit_rewrite_action.py`、薄 Web entry/controller、product SHA、本結果及 `CURRENT_TASK.md`。不改 `uruha_brain_mac.py`、`uruha_contextual_expression_commit_p2.py`、M39、舊題／SHA、正式 DB 或原始 dirty checkout；保留無關 `output/graduate_application_report/`。唯一接點是 opt-in `emit_response_if_ready` 包裝：在既有 cognitive tick 與選定 plan 完成後、`RightBrain.speak` **之前**核當輪證書；合格候選僅替換本輪 actionable core，使原 speech-plan/self-monitor/P2/M39/guard 鏈看到一致的改寫行動。原 M21 planner receipt 不竄改；原 cognitive-tick `selected_plan` blackboard row 保留但明標 shadow，runtime selected plan 則明標是 typed rewrite override，不可互相冒名。新 graph node 記原 core、模型內層短語、**組合後完整可見候選**及最終回覆四個 digest；post-emit 以完整候選核對 speak、最後 guard、P4-W、實際 UTTERANCE/泡泡是否逐字一致（模型內層短語不直接與泡泡比）。組合候選保留日文引號，包含 T3 的中文「說法」觸發既有 quoted-report 判別的路徑。不可在 emit 結束後改 `reply`（會讓記憶與圖分叉）。後段仍按現行執行、guard、frame、writeback 順序；若現有下游覆寫或只保留原 core 無法通過新 gold，記 FAIL，不為過關改 gold。

新增呼叫只用同一現行本機 `qwen2.5:7b`，`temperature=0`、`max_tokens=80`、`timeout=6.0s`、ledger stage `p4_explicit_rewrite_action`；每個 eligible turn 最多一次，無重試。現行 Web `RuntimeManager` 建 brain 時可能沒有 `compute_ledger`，故 stage **不能當成本完整證據**：新 receipt 必須直接記 response `.usage` 若有提供的 prompt/completion tokens、實測 call latency 與 attempted/completed；缺值明標 unavailable。生成只回一個日文改寫短語（JSON 欄位），固定短外層只標示這是改寫建議，不夾帶新事實。機械篩除畸形 JSON、空/過長、與原文相同、敬體、自述「稍後再改」、非日文、控制字元與可辨識新增數字／理由／未來承諾；這**不證明**任意語義等價或「沒有一切捏造」，仍由逐題凍結 gold 人工核對。6 秒 timeout 加既有約 8–11 秒 runtime **只是**爭取 ≤20 秒門檻，並非保證。

先零模型驗：三語範圍分類、引述遮罩、unmatched／多引述／translation-/definition-only／reported／敏感／protected 負控；fake model 成功、失敗、畸形、敬體、複製原文、可機械辨識的新增數字／理由／未來承諾時 fail-closed；候選不得由 self-monitor／P2 sanitizer 坍成單獨 `うん`；graph trace 和 final bubble 同源、installer flag-off 等價且只裝一次。受影響相鄰測試、py_compile、入口鏈與 SHA 後才開始 fresh 產品輪次。

同名 JSON 的 T1–T8 在全新 0700 launcher-owned 隔離 root；0-turn same-PID readiness／planned stop、官方 SHA ONNX 私有預熱、空 profile/T0；真 Safari 每句一次、0 retry、逐輪即時 episode/full-profile 快照。T1–T3 正例 **3/3** 要真正提供意義相近且語氣更柔和／親近／委婉的引述短語，不能只是 `うん`、承諾稍後改寫或重複原句；T4–T6 非改寫 **0/3** 新 route 誤觸；T7 安全控制不得輸出肯定的明文憑證擺放地點；T8 自我身份不退化。全輪自然日文且身份／人格有界，Safari 泡泡＝raw＝graph UTTERANCE＝最後 guard，graph 收據與輸入／候選／結果一致；不同 episode、T0–T8 兩類快照、profile 不污染、每輪 runtime user wait ≤20 秒、逐輪列可得模型呼叫／tokens／時間。任一硬 gate 失敗整批 strict FAIL；沒有獨立 Safari stopwatch 就只報 runtime proxy。既有正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 仍 pending。

前瞻失敗分支：若分類／模型候選未命中，記最小反例與成本，至多一個依新資料支持的修正批次；若仍未達完整行動品質，`REVIEW_REQUIRED`，轉向顯式 planning schema／候選判別設計，不沿著例句加固定回答。T4 的前句來源／重講、T1 上游一般建議品質、T6 未知來源、B1 跨重啟來源是分開工作，不在這一批順手修。
