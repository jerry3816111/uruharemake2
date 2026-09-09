# 目前任務卡

更新：2026-09-09。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：GPT6 審查 P3-A implementation freeze

狀態：**REVIEW_REQUIRED**。GPT5 已完成 P3-A 離線公平比較入口；真模型、網路、付費呼叫均為 0。
驗收：`analysis/p3_a_offline_harness_acceptance_2026-09-10.md`；contract／preflight／run-refusal／JUnit
均在 `analysis/p3_a_*_2026-09-09.*`。30 項 P3-A 測試與 32 項受影響既有回歸通過。

已交付：

- 同一 frozen 完整可見 prefix/input 建立 direct／deliberate／product 三個 allowlisted generation views。
- shared prompt/output/call/context/common-history/wall budget；OpenAI-compatible/native path 同 7B model gate。
- case state 隔離、6-case balanced order、intent-only no-retry、completed checkpoint reuse與不可覆寫 artifacts。
- `contract` deterministic fake；`preflight` 只讀 metadata；`run` 缺三份 release 時 exit 2、attempts 0。

GPT6 必須審查 view 隔離、共同歷史實作、所有模型路徑、逐輪累計 budget、checkpoint integrity、worker factory
與 claim boundary。未通過不可製作資料或真實生成；通過後才另建含 artifact hashes／split／資源上限的
implementation release，放行 P3-B developer smoke。不可自行前進 P3-C confirmation 或改 design／lock／門檻。

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
- 後續資料尚未製作／sealed。沒有implementation/data/review release，run mode必須0-call拒絕。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
