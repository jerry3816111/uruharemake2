# P2 Explicit Space Authority：有界驗收

日期：2026-09-08
結論：**PASS（僅限產品端、明確要求獨處的 action authority）**。這份結果不是人評、holdout、正式公平比較、全面 P2 完成，也不能證明理解人類或得到人類方程式。

## 這次真正修正的問題

隔離控制是：

1. `今日はただ聞いてほしい。`
2. `違う。今日は一人にしてほしい。`

修改前，semantic route 與 pragmatic label 都已把第二句辨識成 `explicit_correction`，但 M18 的既有六種回覆政策沒有「尊重獨處要求並停止互動」的 action。ordinary `calibrate_need` 因而勝出，最後輸出：

> あ、そっちか。さっきは読みすぎた。今の言い方で直す。 寝てないのか、考え事で止まんないのか、まずそこだけどっち？

它不只表面答錯，還把這個無來源二選一保存成新的 pending prediction。修改前因果證據見 `p2_explicit_space_authority_prechange_gap_probe_2026-09-08.json`；目標輪為 0 model calls，active validation 也沒有新增問題，因此根因不在 qwen 生成或 active-validation question，而在 action vocabulary／authority ordering。

## 唯一核心變因

新增 product-only `uruha_explicit_space_authority_p2.py`。它只把中、英、日當輪可直接觀察到的第一人稱／祈使式獨處要求轉為 typed `respect_space` action：

`observable request → legacy proposal retained → current request authority → acknowledge and withdraw → Japanese surface`

- 不推測悲傷、生氣、睡眠不足、拒絕關係或長期偏好。
- 帶 correction cue 才承認前面理解錯；today／now／unspecified 只依當輪文字決定短期範圍。
- 否定、第三人稱引述、翻譯／詞義問題與 protected safety／factual route 不接管。
- 保留舊 `calibrate_need` candidate 與歷史 calibration trace，但把其 plan application 標為未採用，所以不寫入錯誤 pending prediction。
- 不增加 model call、fact-memory write 或 raw-dialogue trace 複製；凍結 M18–M54 source 與正式研究鏈不變。

## 單元／契約證據

- focused：`15/15 passed`，6.78 秒；JUnit：`p2_explicit_space_authority_focused_tests_2026-09-08.xml`。
- affected adjacent：`145/145 passed`，35.04 秒；JUnit：`p2_explicit_space_authority_adjacent_tests_2026-09-08.xml`。
- 覆蓋中／英／日 source-disjoint positive、negation／attribution／metalinguistic negatives、protected route、pending suppression、graph order／idempotence／raw-free，以及完整產品 adapter 安裝路徑。

這些是開發者撰寫的契約測試，不是 holdout 或人類偏好證據。

## 本機 qwen 完整產品實測

後端：Ollama `qwen2.5:7b`；5 個隔離 sessions、9 輪；正式 DB／formal holdout 均未使用。原始 JSON／互動圖：

- `p2_explicit_space_authority_local_run1_2026-09-08.json`
- `p2_explicit_space_authority_local_run1_2026-09-08.html`

四個既有結構 checks 全部為 true。目標第二輪變為：

> あ、そっちか。分かった。今日は一人にしとく。

同時：

- pending：`p1-4-3abd28d3797f06eb → null`
- sequence：`4 → 3`，證明本輪沒有新增錯誤 prediction event
- 下一個隔離 session 的第一輪不再被該錯誤 pending 誤導成「さっきは読みすぎた」；恢復普通 listening response
- 9 輪中 7 輪逐字相同；2 輪差異分別是目標修正與移除錯誤狀態後的直接下游效果
- OpenAI-compatible call count：`3 → 3`
- total tokens：`4,434 → 4,459`
- elapsed：`37.056903 → 37.827457` 秒

token／elapsed 來自兩次 stochastic 本機生成，不作因果成本主張。目標 action 本身新增 0 model calls。
三個 compact model calls 中 2 個完成、1 個在既有 quoted-source control 出現 `ValueError` 後走 bounded fallback；
修改前同一輪也是相同的 error-fallback 狀態，因此不把這個 bounded run 說成全流程全綠，並留待後續獨立處理。

## 圖像證據

HTML 的 Session 3 · Turn 2 有唯一且有連線的 `explicit_space_authority_p2` node，位於既有候選後、`selected_plan` 前。節點可展開檢查：

- observable request 與 span digest
- rejected legacy policy：`calibrate_need`
- selected action：`acknowledge_and_withdraw`／`respect_space`
- selected Japanese core 與 final surface digest
- `final_visible_surface_matches_selected_action=true`
- `raw_dialogue_persisted=false`

它呈現真正的 runtime 選擇與狀態變化，不是把實驗結果另畫成靜態示意圖。

## 尚未完成與下一步

- Safari 真實畫面驗收仍 pending：既有 CUA session 拒絕目前網址並結束，外部狀態未變前不繞過工具限制。
- 沒有真人盲評、未見 holdout、同模型正式公平比較或 production evidence。
- 下一個單一產品問題應先定位 stale cross-session feedback association：新 session 的普通 `今日はただ聞いてほしい。` 不應被舊 session 的 correction 誤標成新一輪自我修正。quoted-source recall（`「ありがとう」は誰の言葉だった？`）是下一層，不能與它混成同一修正。
