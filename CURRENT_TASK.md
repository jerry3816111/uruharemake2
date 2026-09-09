# 目前任務卡

更新：2026-09-09。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-A（可交 GPT5）

狀態：READY_FOR_GPT5_OFFLINE_IMPLEMENTATION。使用者已授權 GPT6 定案、GPT5 實作。
先讀 `GPT5_HANDOFF.md`、`research/p3_product_comparison_spec_v1.md`、
`configs/p3_product_comparison_v1.json`，執行：

```sh
git status --short --branch
python3 scripts/verify_p3_handoff.py
```

目標：建立同一完整可見歷史下的 direct／deliberate／product 比較入口，用 fake transport 驗證資訊、
模型、資源、記憶隔離。P3-A 真模型／付費呼叫預算均為 0。不是再加回覆規則，不新增 M 或 dashboard。

允許：新增 `p3_product_comparison.py`、`run_p3_product_comparison.py`、`test_p3_product_comparison.py`；
必要 P3 worker helper 至多一個且先說明。更新本卡與一份 acceptance、contract JSON／JUnit。
不得改 source baseline、P1/P2、正式 M、persona data、設計／lock／門檻。全部細節與負測試在 handoff。

完成：負案例通過＋0-call contract result＋diff review＋commit/push/PR核對，更新為 REVIEW_REQUIRED，
通知使用者切回 GPT6 做生成前審查。先前的「不停止」不授權跳過此審查，也不能把整個 Goal 標為 complete。
P3-B smoke、P3-C data freeze、P3-D confirmation、P3-E long dialogue／P4 依 spec 的後續 gates 執行。

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
