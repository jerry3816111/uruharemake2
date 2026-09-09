# 目前任務卡

更新：2026-09-09。這是唯一的當前工作順序；歷史各 M 的「下一步」只保留為當時紀錄。

## 狀態

- 2026-09-09 最新：P3 成本記錄修正已收尾，121/121；最終九輪與 P2 逐字相同、4/4 結構通過。
  2 次生成＋130 個記憶操作可區分，native transport 僅契約驗證；Safari 仍 pending。
  見 `analysis/p3_complete_product_compute_accounting_acceptance_2026-09-09.md`。
  使用者授權 GPT6 先定案規格，再通知可交 GPT5 實作；當前先完成該交接準備，不提前跑比較結果。

- 安全 worktree：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`
- 分支：`codex/v2-15-pragmatic-research-showcase`，既有 PR #435。
- 已完成：M57.8；M57.9 focused 10/10（507.37 秒），但 freeze／相鄰／最後同 run Safari 驗收未完成，保存為 partial。
- P1：針對性 7/7、相鄰 39/39；隔離完整產品 contract 與本機 runtime 各 2 sessions／6 輪，identity assertions 8/8。
- P1 品質限制：本機 2 次模型呼叫均逾時，沒有完成 fresh generation；兩輪出現多餘澄清。Safari pending。
- P2 第一修正批次：typed 澄清資格 gate 已實作，10/10 focused、51/51 adjacent；本機原始兩個問題輪撤回無根據的二選一。
- P2 對話驗收仍 FAIL：通用追問仍在；新增 5 sessions／9 輪 mock 控制揭露候選問題不對題、忽略新請求等失敗。
- P2 第二批：compact planner 已接入產品，最後 62/62；本機六輪中的兩次一般生成 2/2 完成，6.73／8.62 秒。
- P2 表達層架構修正：預先條件通過；模型 selected core 不再被無來源 hash prefix、固定尾句或 density-only
  enrichment 覆蓋。最終完整相鄰組 95/95；本機六輪兩個目標
  final 修正、其他四輪與 M27 逐欄不變，P1 assertions 8/8。
- P2 現產品 5 sessions／9 輪控制已重跑：4 個結構 checks 通過、4 次實際 compact calls，但原控制目的只有
  無上下文指稱的保守追問可接受；其餘 4 sessions 仍 FAIL。當前唯一下一步：先修 current-turn explicit help
  request authority 的自然跨語言 grammar，讓它覆蓋前輪 listening 並交既有 M47→M46；不與其他錯誤同批。
- P2 current-request authority 已完成 bounded acceptance：focused 14/14、完整相鄰 119/119；本機目標輪從
  policy 空白／泛問改為 `solve_regulation`／`今、どの作業で困ってる？ そこだけ教えて。`，一般 planner call
  1→0、延遲 9.035225→1.749318 秒。5 sessions／9 輪總 calls 4→3、tokens 6,096→4,471，結構 4/4 保持。
- P2 repeated-refusal arbitration 已完成 bounded acceptance：修改前 compact core `また今度ね。` 被覆蓋成不相關
  listen／alone 二選一；修改後 final 為原 core、pending=null。最終 focused 9/9、完整相鄰 91/91；本機 5 sessions／9 輪
  只有目標 final 改變，其他 8 輪逐字相同，calls 3→3、結構 checks 4/4。runtime graph 已有可點擊仲裁節點。
- P2 explicit-space authority 已完成 bounded acceptance：focused 15/15、完整相鄰 145/145。本機目標從無來源
  sleep／thought 二選一改為 `あ、そっちか。分かった。今日は一人にしとく。`；錯誤 pending 被撤回，下一個隔離
  session 也不再受到該舊誤判影響。9 輪中 7 輪逐字相同、2 輪為目標與直接下游改善，calls 3→3、checks 4/4。
  runtime graph 已顯示 observable request→rejected candidate→`respect_space`→final。
- P2 speaker-qualified quoted recall 已完成 bounded acceptance：focused 17/17、完整相鄰 162/162。本機 target 從
  `ん、そこもう少しだけ聞かせて。` 改為 `それ、あんたが言ったやつ。前に中国語でお礼を言ってた。`；
  其餘 8/9 replies 逐字相同，calls 3→2、tokens 4,459→2,900、checks 4/4。graph 連接已選 episode 的
  speaker role、bounded gratitude atom、來源語言與 deterministic factual/memory plan；沒有新增 model call、fact write
  或 raw-dialogue contract copy。review 中的固定「中国語」錯誤也已改為依來源標示 zh/en/ja。
- P2 下一個唯一工作：不新增回答規則，重跑／判讀一份五組控制的整批整合 gate，確認五類機制共同安裝時沒有互相覆蓋；
  已完成：同一最終 5-session／9-turn run 中四個機制案例 PASS、一個無上下文指稱 bounded abstention PASS，結構 4/4；
  product commit、source/run/graph hashes 與成本已凍結。可稱 P2 bounded product baseline，不是 open-world P2。
- 當前唯一下一步進入 P3 規格凍結：先定公平比較的同模型 baseline/system 介面、actual-token 帳本、成功／失敗閾值與
  未參與 P2 開發的新案例來源；沒有凍結前不得生成比較結果，也不得把現有五組 developer cases 改名 holdout。
- Safari 存取：工具拒絕目前網址並結束控制階段；不得透過其他 UI 技術繞過。同意操作不是解除工具限制。
- 正式 M55/M56/M57：真人與正式結果仍未成立；不得執行 M58。產品 P1 不改動此授權鏈。

## P1 問題與單一變因

現行 `decide_response` 用 `m18-{turn_index}-{input_digest}` 當 prediction ID；重啟後 turn 1＋相同輸入
會重用 ID。`_upsert_m27_pending_prediction` 按 ID 覆寫，導致過去 supported 事件變回 pending。
隔離 before probe：舊事件數 1 → 1（應為 2）、舊 supported → pending、舊紀錄未保留。

只改**跨重啟持久化的 prediction event identity**。不改語用判斷、候選效用、回覆文字、模型、prompt、
人格、閾值或 M27 評分方法。給每個已提交事件持久遞增序號；同一未完成事件的相同提交可以冪等重驗，
已完成事件不可被誤當新事件。舊檔案沒有序號時保留所有紀錄，從已存在的 P1 序號恢復。

## 檔案與入口

- 實作：`uruha_prediction_identity_p1.py`，小型 opt-in adapter。
- 產品入口：`uruha_web_ui_product.py`，沿用 M54/M53 runtime 與既有 graph，安裝 P1＋P2 gate／compact planner。
- 產品資源：預設 20 秒／256 output tokens／0 retries；`URUHA_PRODUCT_PLANNER_BUDGET_SECONDS` 合法範圍 1–45 秒。
  不與正式研究共用 interpreter；凍結研究入口維持原 budget，不能說此次是同預算公平對照。
- 產品表達 commit：`uruha_contextual_expression_commit_p2.py`；只在 completed compact direct-chat 啟用，
  圖節點顯示 core→decorator gate→visible guard→final，不增加模型呼叫或長期記憶寫入。
- 測試：`test_prediction_identity_p1.py`。
- 報告：`analysis/p1_prediction_identity_acceptance_2026-09-07.md`。
- 不改：M1–M57 凍結契約／程式／結果、正式資料、原始 dirty checkout、系統設定。

## 成功条件

1. 完成一輪支持／否定後保存，重新載入並重設 turn 1，同句新事件得到不同 ID；舊紀錄逐欄保留。
2. 後續回饋只更新新事件。相同 pending 提交不多算；已解決事件的舊提交明確拒絕。
3. 經過多次 save/load 及 ledger 容量淘汰後，序號不倒退；既有檔案可載入。
4. 同一輸入狀態下，安裝前後除 ID／identity trace 以外的 decision 完全相同。
5. 既有圖可看到兩筆不同事件；無 raw dialogue 新增、推測不寫成事實、0 新增模型呼叫。
6. 真實模型與 Safari 分開驗收；沒有完成就明記 pending，單元通過不算產品完整交付。

## 精確檢查命令

在安全 worktree 執行。產品檢查環境：`.venv/product_checks/bin/python`，以既有 Python 3.12 的
system-site-packages 建立，額外依賴在 `configs/product_checks_additions.txt`。這是目前本機環境，不是完整可攜 lock。
系統預設 `python3` 是 3.14 且没有 pytest；裸 Python 3.12 缺 colorama/soxr/speech_recognition，勿全域安裝。

```sh
.venv/product_checks/bin/python -m pytest -q test_prediction_identity_p1.py
.venv/product_checks/bin/python -m pytest -q test_adaptive_person_model_m16.py test_context_scoped_adaptation_m17.py test_hierarchical_adaptive_policy_m18.py test_causal_outcome_calibration_ledger_m27.py
git diff --check
```

M57.9 獨立收尾檢查（不觸碰真人資料）：

```sh
PYTHONPATH="$PWD/.venv/m57_7_participant_runtime/lib/python3.12/site-packages" /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest -q test_m57_9_adjudicator_confirmed_manifest_export.py --junitxml=analysis/m57_9_focused_tests_2026-09-07.xml
```

## 接續規則

P1 證據與失敗見 `analysis/p1_prediction_identity_acceptance_2026-09-07.md`；M57.9 見
`analysis/m57_9_partial_status_2026-09-07.md`。既有 XML 已保存，未修改 source 不必重跑 8 分鐘的套件。
重跑產品 probe 必須指定新的 output，不能覆盖 run1／run2：

```sh
.venv/product_checks/bin/python run_product_restart_probe.py --backend contract --output /tmp/p1-new-contract.json
.venv/product_checks/bin/python run_product_restart_probe.py --backend local --output /tmp/p1-new-local.json
```

P2 第一批前瞻計畫：`research/p2_grounded_validation_plan_2026-09-07.md`。原始多餘追問已在 P1 本機六輪中重現；
原因是 V2.13 把 `literal_intent_unresolved` 的未知欄位當成 high-value hypothesis。
先以 typed inference eligibility 限制主動澄清，不加入測試句專用辨識／回覆，不改 M27 supported／unknown。
下一批再依据實測處理當前 act／既有經驗使用；不能預先宣稱整個 P2 跨 session 修正已通過。
M57.9 的最後 Safari 操作與原計畫後續驗證仍需補齊；不能宣稱它已完成或自動開始 M57.10。

P2 第一批結果：`analysis/p2_grounded_validation_acceptance_2026-09-07.md`。再次檢查只跑受影響的產品測試：

```sh
.venv/product_checks/bin/python -m pytest -q test_compact_planner_p2.py test_grounded_validation_p2.py test_prediction_identity_p1.py test_supported_feedback_closure_m43.py test_personhood_loop_v2_13.py
```

2026-09-07 使用者追加「高效率」：不要重跑未變動的 M57.9 長套件、增加新 dashboard 或只修飾報告。
先處理已重現的產品阻礙，跑最小實測再擴大；負結果照實保留，不能以省時間跳過影響範圍內的驗證。

最新報告：`analysis/p2_compact_planner_acceptance_2026-09-07.md`。同樣六輪 ledger 仍與 P1 原結果逐欄相同。
問題已縮小至：model core 被舊表達層補不合情境連接語／尾句；本輪輸出例「いや、ありがとう。そのくらいでいいよ。そのくらいでいいだろ。」
只讀定位：`uruha_brain_mac.py` 的 `RightBrain._finalize_surface_reply`（hash prefix）及 `direct_chat_answer` variants。
這是 2026-09-07 第二批結束時的狀態；後續 2026-09-08 結果如下，不再沿用這句作目前判定。

2026-09-08 表達層架構修正已完成，報告：
`analysis/p2_contextual_expression_commit_acceptance_2026-09-08.md`。同一六輪的兩個 compact direct-chat final
由 `先に、うん、そのとおりだ。そのくらいでいいだろ。`／
`いや、ありがとう。そのくらいでいいよ。そのくらいでいいだろ。` 變為
`うん、その通りだ。`／`うん、助かったよ。ありがとう`；其他四輪逐字相同，M27 逐欄相同。
第一次完整 re-run 暴露 self-monitor density repair 會再次裝飾，負結果已保存；最終圖的兩個 expression node
均為 `final_visible_surface_matched=true`。Safari 仍 pending。

現產品控制診斷：`analysis/p2_current_product_control_diagnosis_2026-09-08.md`。5 sessions／9 輪共 4 次
qwen2.5:7b compact calls、6,096 total tokens、45.554864 秒；結構 checks 4/4，但語用控制保守判定 4 個
session FAIL、1 個 bounded acceptable。最先處理 `謝謝。不過現在請幫我想一個做法。` 的 current-turn request
authority 缺口；這句目前未被既有 M47 grammar 辨識，所以上游仍以 chat 規劃。不得把其他三類錯誤一起修。

Current-request authority 結果：`analysis/p2_current_request_authority_acceptance_2026-09-08.md`。產品限定 adapter
擴充自然三語「幫我想／找／決定方法」句法，無 task 時沿既有 source gate 0 action model calls 澄清，未命中 route
與 source gate 不變。最終實測與相鄰測試已通過 bounded scope；Safari、人評、holdout 與正式比較仍 pending。

Repeated-refusal arbitration 結果：`analysis/p2_repeated_refusal_arbitration_acceptance_2026-09-08.md`。產品限定 adapter
在連續 indirect refusal 仍 uncertain 且 compact direct plan 已完成時，保留跨輪模型更新但讓較低干預 core 取得 action
authority。最終 91/91；本機目標 final 改正、其他 8 輪逐字相同。Safari、人評、holdout 與正式比較仍 pending。

Explicit-space authority 結果：`analysis/p2_explicit_space_authority_acceptance_2026-09-08.md`。產品限定 adapter 把明確的
當輪獨處要求視為可觀察 interaction action，而不是未知心理；保留舊候選 trace，但在 surface／writeback 前選擇
`respect_space` 並阻止錯誤 pending。下一個產品問題只定位 stale cross-session feedback association；完成前不得順便修
quoted-source recall。

Speaker-qualified quoted recall 結果：`analysis/p2_speaker_attribution_recall_acceptance_2026-09-09.md`。產品限定 adapter
只把明確引號來源問題接到已選 memory 的 user／Uruha role；exact match 之外目前只授權 bounded gratitude atom。唯一 role
直接回答、雙 role 澄清、無 evidence abstain，並將來源語言與 provenance 顯示在既有 runtime graph。最終 162/162；
五 session／九輪只有 target 改變，calls 3→2。Safari、holdout、人評、正式比較與 open-domain recall 仍未成立。

P2 整合收斂：`analysis/p2_integrated_product_baseline_acceptance_2026-09-09.md` 與
`research/p2_integrated_product_baseline_freeze_2026-09-09.json`。同一最終 run 的五組 gate 為 4 mechanism PASS +
1 bounded abstention PASS，結構 4/4；product commit `be59317` 與全部 source/evidence digest 已綁定。下一步只做 P3
比較規格與未見案例來源凍結，不先跑結果。

每次離開本輪前，用實際結果更新本卡；有未完成工作就寫清楚，不用「全部完成」代替剩餘清單。
