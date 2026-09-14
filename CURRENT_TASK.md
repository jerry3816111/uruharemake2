# 目前任務卡

更新：2026-09-15。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B9 fresh product＋baseline canary lock

狀態：**P3-B8.1 PASS（只限四種 stage token binding）**。事前 release commit `41285f8` 後，fresh synthetic direct／draft／
critique／revise 的 offline/provider prompt counts 為 244/244、223/223、241/241、250/250；4 intents／4 completes／
4 real＋network calls／958 prompt＋4 completion tokens／3.186574 秒／0 paid。P3-B8 與 P3-B7 的失敗都保留，仍沒有品質比較。

### P3-B9 before 與單一變因

before：目前唯一一組 product output 是 `p3-smoke-01-u1`；其 P3-B7 baselines 因計量 failure 未形成可比較 pair，而且不得重跑。
P3-B8.1 已把新 baseline 四階段所需的 exact accounting gate 補齊，但還沒有第二個完整三條件 output lock。

單一變因：機械選取尚未執行的下一個 source turn `p3-smoke-02-u1`，先凍結同一 qwen2.5:7b、persona、options、token/call
上限與隔離狀態，再依序鎖定 product、direct、deliberate final。輸出全部鎖定前不得讀 annotation；不沿用P3-B7 checkpoint或回答。

成功：三條件都有非空最終日文輸出，所有 provider calls、實際 tokens、wall、模型與 options 可對帳，無 retry、無 annotation／future／
production DB access；baseline deliberate 的四 stage exact gate 全通過。失敗照 checkpoint 保留且不重跑該 turn，再決定是否review。

不得改 product brain、P1/P2、既有 P3-B7 checkpoints/result、frozen source/annotations、baseline prompt/rubric/threshold；不得讀
future／confirmation／production DB。這仍是實驗基礎設施 gate，不是使用者感受或一般優勢證據。

## 工作環境

- 安全 worktree：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。
- 分支：`codex/v2-15-pragmatic-research-showcase`，PR #435。查實際 HEAD，不碰原始 dirty checkout。
- Python：產品測試用 `.venv/product_checks/bin/python`；純標準庫 verifier 可用系統 python3。
  不全域安裝依賴。Gradio／Torch／brain 的 import 留在 isolated worker，不放純資料 module 的頂層。
- 長期目標檔：`LONG_TERM_GOAL.md`。2026-09-09 Goal 工具讀到 usageLimited；文件更新不等於 app 已恢復。
  不清除／假完成／改內部 DB 來換 Goal。使用者手動回合仍可執行已授權工作。
- 本機 Safari 目前有既知工具拒絕記錄，驗收 pending；不以其他 UI 技術繞過。P3-A 不依賴瀏覽器。

## 已完成、不要重做

- P1 prediction identity 跨重啟保存；P2 compact planner、表達 core commit、當輪求助、婉拒、
  獨處要求與 speaker-qualified recall 的有限產品 baseline 已凍結：
  `research/p2_integrated_product_baseline_freeze_2026-09-09.json`。4 mechanism＋1 abstention、結構4/4。
- P3成本記錄收尾 commit：`34bef3d01d236873b4aa384b76aba2893ff9949d`。
  `research/p3_compute_accounting_freeze_2026-09-09.json`；121 passed／8 dependency warnings。
  `analysis/p3_complete_product_compute_accounting_acceptance_2026-09-09.md`。
- P3-A fail-closed comparison harness 與自審修正已凍結；P3-B1 isolated product worker 將產品真實 OpenAI／
  native M31 globals 綁到同一 gate，兩次 lazy import、same-case restart、cross-case refusal 均通過。驗收：
  `analysis/p3_b1_product_worker_acceptance_2026-09-13.md`。仍為 0 real model/network/paid calls。
- P3-B2 developer smoke source／annotations 已分離凍結：6 cases、24 user turns、12 sessions、三語各2、
  六 family 各1，建立 72 個 allowlisted views。驗收：
  `analysis/p3_b2_developer_smoke_acceptance_2026-09-13.md`；未執行任何生成。
- P3-B3 provider/tokenizer binding 在既有四種 fixture 通過；P3-B4 找到產品 call shape drift；P3-B5 adapter 已補齊並驗證
  seed/top_p/num_ctx。P3-B6 單一 product canary 工程通過，但品質未定。P3-B7 baseline 執行保留負結果：3 calls、2 complete、
  1 prompt-count failure，沒有三條件比較。詳見 `analysis/p3_b7_canary_baselines_acceptance_2026-09-14.md`。
- 真實本機run2：5 sessions／9輪，與P2可見回覆9/9相同；ledger 2生成＋130記憶操作，
  2,901生成tokens、30.834245秒；四個結構checks通過。兩次run均保存。
- native M31只mocked transport驗證，這九輪未實際觸發；Chroma embedding token／CPU/RSS/energy未量測。
  HTML是runtime graph產物，Safari未驗收。開發控制不是新holdout或全面能力證據。
- 不為新純資料harness重跑未變動的121項或M57.9八分鐘套件。

## 仍需保留的限制

- P2只在已曝光開發案例通過，不等於open-world對話、50輪可靠、人評、強LLM優勢或人腦方程式。
- 原生M31預設qwen3.5:9b，而一般planner是qwen2.5:7b；P3必須按config在isolated worker import前統一，
  transport核對所有路徑。不是改永久產品預設。
- P3共同歷史目前是system-anchored paired；報告必須揭露其條件性，不能當獨立對話偏好實驗。
- 正式研究依據上次封存紀錄仍缺真人／真實temporal資料；此輪未新讀私人ledger。M57.9 partial，
  M58沒有新授權。產品比較不能補造正式結果。
- 只有第一個 product turn 有真實證據；其兩個 baseline 尚未生成，其餘 23 developer turns、評分、Safari、真人與 formal
  confirmation 仍未執行。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
