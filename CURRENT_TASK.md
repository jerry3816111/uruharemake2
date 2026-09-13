# 目前任務卡

更新：2026-09-14。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B7 same-model canary baseline comparison

狀態：**PRODUCT_CANARY_ENGINEERING_PASS／QUALITY_UNDETERMINED**。P3-B6 真實 product canary 以 1 個 native call
完成：441 prompt、151 completion、turn 10.752605 秒、0 fallback/rejection/paid；future/annotations/production DB 均未
讀取。visible reply 已保存，但尚無 baseline 或品質結論。

### P3-B7 before 與單一變因

before：product canary 的回覆是 `最近退社後は常に不機嫌で何もしたくないんだね。`。它通過日文／整合 gate，
但 `退社後` 偏書面、`常に不機嫌` 可能過度定性，也未判明是否比強 baseline 更接住需求。沒有同模型輸出就不能把
產品工程成功外推成品質價值。

單一變因：保持完全相同 canary input、共享 persona、qwen2.5:7b digest、temperature/seed/top_p/num_ctx/think 與每條件
768 completion budget，只新增 `full_history_direct` 1-call 與 `full_history_deliberate` 3-call baseline；不重跑 product。
baselines 不讀 product trace、annotations、future 或答案，只能看同一空 prefix＋current input。

成功：兩 baseline 各自在 calls/wall/token budget 內完成，provider prompt usage 與 tokenizer reservation 精確一致，輸出鎖定
後才讀分離 annotation 做明示 proxy 描述；三輸出並列但不預設 product 勝。任一 transport／budget／checkpoint／source drift
保留失敗，不重跑或改 prompt。單一 canary 只能是受控例子，不能形成整批或普遍優勢結論。

先補 baseline localhost transport 的 exact prompt check、crash-safe runner、tests、preflight 與獨立 execution release；release
commit 前 0 新 generation。不得改 product result、brain、P1/P2、source／annotations、frozen baseline prompt/rubric/threshold，
不得讀 future／confirmation／production DB。輸出鎖定後的 proxy 分析必須清楚標示非真人偏好。

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
