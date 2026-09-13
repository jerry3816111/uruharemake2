# 目前任務卡

更新：2026-09-14。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B4 isolated product call-shape audit（0 generation）

狀態：**TOKEN_BINDING_PASS／PRODUCT_CALL_SHAPE_UNOBSERVED**。P3-B3 已依事前 release 執行：兩條 transport、
4 個 fixtures 的 HF/provider prompt tokens 逐列完全相等，offset 0；8 real/network calls、8 completion tokens、
6.052747 秒、0 paid。這只放行 token accounting，不代表產品品質或優勢。

### P3-B4 before 與單一變因

before：B1 只證明產品 import 與兩條 transport seam 被 gate 接住，沒有實例化 brain；既有產品 call sites 的
temperature、timeout、response_format、completion cap 與實際 call 數是否符合 frozen P3 比較契約仍未觀察。若直接跑
6 × 4 developer smoke，可能在第一次 call 才發現選項漂移，浪費 sealed 執行並留下不可重試的殘缺結果。

單一變因：在 fresh subprocess 與 ephemeral memory 中實例化真實 product brain，用一個不屬於 P3 smoke 的 synthetic
turn 走真實 `run_turn_debug`，但讓 transport 在生成前 fail closed；只記錄每個 call 的 stage、allowlisted option keys、
message/token digest、cap 與拒絕原因，不記 raw dialogue。任何網路或生成都是失敗。

成功：brain 真實實例化、production DB 不可達、至少觀察一個 pre-transport call shape、real/network/paid calls 皆 0，
且結果足以把現有 options/cap drift 列成有限 adapter 規格。失敗：產品在到達 call seam 前崩潰、接觸 production DB、
發出網路／生成、記錄 raw text 或無法得到任何 call shape；保留失敗，不以 6-case smoke 探路。

允許新增 call-shape observer／worker mode、相稱 tests 與零生成 artifact；不得改 brain、P1/P2、P3 smoke、
annotations、frozen comparison design/baseline/rubric/threshold。不得讀 confirmation／production DB 或執行 6-case
generation。得到 shape 後另行凍結 adapter normalization；不能從 audit 直接放行生成。

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
- developer smoke 已 sealed，tokenizer binding 已通過；產品 full-turn call shape 與 frozen P3 options 的相容性仍未觀察。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
