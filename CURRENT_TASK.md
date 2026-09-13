# 目前任務卡

更新：2026-09-14。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B6 single-turn real product canary preregistration

狀態：**RELEASED_FOR_ONE_PRODUCT_CANARY／SELF_REVIEW_NOT_INDEPENDENT**。P3-B6 source/config、worker、preflight
與 release 已用 SHA 凍結；76 項 P3、32 項相鄰回歸通過。執行前仍是 0 product canary calls；唯一下一動作是
依 release 跑一次，不能再修改 canary、程式或門檻。

### P3-B6 before 與單一變因

before：token binding 與第一個 call normalization 均通過，但尚未有任何真實 product full-turn；模型回覆後可能出現
尚未觀察的 OpenAI/native shape、額外 calls、usage 超額或產品 fallback。直接跑 6 cases × 4 turns 會把 sealed developer
smoke 當整合除錯資料。

單一變因：事前鎖定 `p3-smoke-need-change-zh` 的第一輪 `p3-smoke-01-u1` 作為 product-only canary；只讀 source manifest
與該輪文字，不讀 annotations／future turns。fresh subprocess、ephemeral DB、同一 qwen2.5:7b digest，最多 4 provider
calls、aggregate completion 768、wall 60 秒、0 retry；保存 reply 與 runtime trace 供之後評分，但不在此階段打分。

成功：真實產品完成一輪且 visible reply 非空；所有實際 calls 的 model/options/usage 通過 gate，prompt／completion 與 wall
在共同 budget 內，無 fallback 掩蓋 transport failure；production DB 不可達，source/future/annotation access 可核對，
checkpoint 完整且不可重打。任何 unobserved shape、cap 缺失、usage 超額、timeout、intent-only 或產品錯誤都保留失敗，
不修改該 canary 或 release 追分。

canary config、crash-safe worker、tests、preflight 與 execution release 已建立。只能依
`research/p3_b6_product_canary_execution_release_2026-09-14.json` 執行一次；不得改 brain、P1/P2、P3 source／
annotations、comparison design/baseline/rubric/threshold，不得讀 future／confirmation／production DB。canary PASS 後
仍需另行 release 三條件 developer smoke，不能把單輪結果當品質或優勢。

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
- developer smoke 已 sealed、tokenizer binding 與第一個 native normalization 已通過；P3-B6 尚未 release，產品真實
  developer turn 與全部 response-dependent routes 仍為 0 evidence。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
