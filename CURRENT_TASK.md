# 目前任務卡

更新：2026-09-07。這是唯一的當前工作順序；歷史各 M 的「下一步」只保留為當時紀錄。

## 狀態

- 安全 worktree：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`
- 分支：`codex/v2-15-pragmatic-research-showcase`，既有 PR #435。
- 已完成：M57.8；M57.9 focused 10/10（507.37 秒），但 freeze／相鄰／最後同 run Safari 驗收未完成，保存為 partial。
- P1：針對性 7/7、相鄰 39/39；隔離完整產品 contract 與本機 runtime 各 2 sessions／6 輪，identity assertions 8/8。
- P1 品質限制：本機 2 次模型呼叫均逾時，沒有完成 fresh generation；兩輪出現多餘澄清。Safari pending。
- 當前下一步：P2 第一修正批次，先限制「未知空白」產生無根據的二選一澄清；見下方前瞻計畫。
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
- 產品入口：`uruha_web_ui_product.py`，沿用 M54/M53 runtime 與既有 graph，只安裝 P1。
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

每次離開本輪前，用實際結果更新本卡；有未完成工作就寫清楚，不用「全部完成」代替剩餘清單。
