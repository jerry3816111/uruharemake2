# 目前任務卡

更新：2026-09-13。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B2 developer-smoke source／annotation freeze（0 generation）

狀態：**READY_FOR_DATA_DESIGN／SELF_REVIEW_NOT_INDEPENDENT**。P3-B1 的 isolated product worker 在限定範圍
PASS；release：`research/p3_b1_product_worker_release_2026-09-13.json`。42 項 P3 contract、32 項相鄰回歸通過，
真模型／network／paid calls 仍為 0，confirmation／formal case access 為 0。

### P3-B2 before 與單一變因

before：config 仍為 `source_manifest_present=false`，沒有可執行的 6-case developer-smoke source 或分離 scorer
annotations。單一變因：依 frozen P3 spec 建立 6 cases × 4 user turns；每 family 一 case，zh/en/ja 各兩 case，
且每 case 至少一個可觀察的確認／否定／需要改變。這批資料只能修 smoke 接線，不是 confirmation 或 holdout。

source 只允許 case/source/session/turn/language/family/provenance 與使用者原文／hash；不得有答案、期待、評分、
future annotation。annotations 必須分檔，寫 acceptable actions、unsupported claims、可見 evidence turn IDs、
correction eligibility，不指定唯一漂亮句子。generation view 只能逐輪由當時已可見 prefix + current input 新建。

允許改 `p3_product_comparison.py`、`run_p3_product_comparison.py`、`test_p3_product_comparison.py`、本卡；允許新增
兩份 P3 smoke JSON、一份 validation artifact、一份 acceptance 與一份 data freeze。不得改 brain、P1/P2、frozen
design、baseline prompt、family/language quota、rubric、threshold 或正式資料。

成功：schema exact allowlist、24 個唯一 turn/source hashes、6 family 各1、三語各2、每 case 4 turns 且至少
跨兩 session、每 case 有 verification/correction event；所有 annotation evidence 只指當時或過去 turn，所有 exact
source spans 真為原文 substring；source 與 annotations hash 分離且 annotation 不進 generation view。需有 future／
gold leak、錯 hash、跨 case ID、future evidence、翻譯換皮重複等負測試。全程 0 generation/network/paid calls。

完成後下一 gate 才能設計一次性的 tokenizer provider-binding probe 與 6-case product smoke execution release；
仍不能讀 confirmation、不能開 production DB、不能以資料驗證通過宣稱產品品質。

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
