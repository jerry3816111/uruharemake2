# 目前任務卡

更新：2026-09-14。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B3 tokenizer/provider binding probe 單次執行

狀態：**RELEASED_FOR_EXACTLY_8_LOCAL_CALLS／SELF_REVIEW_NOT_INDEPENDENT**。P3-B3 config、程式與 preflight
已用 SHA 凍結；66 項 P3 contract、32 項相鄰回歸通過。執行前仍是 0 real model/network/paid calls，不代表產品
品質或優勢。

### P3-B3 before 與單一變因

before：本機已找到 offline `Qwen2TokenizerFast` + chat template，但
`provider_usage_equivalence_validated=false`；real product transport 因此 fail closed。單一變因：事前鎖定極小的
tokenizer binding probe，將 HF chat-template count 與同一 `qwen2.5:7b` digest 的 OpenAI-compatible／native Ollama
prompt usage 比較；只驗 token accounting，不評回覆內容。

prereg config 與 execution release 已建立，不能邊跑邊改規則。固定 4 個不含 P3 smoke／annotations 的 synthetic
fixtures：前 3 個 fit 每條 transport 的整數 offset，第 4 個為未參與 fit 的 verification fixture；兩 transport 各跑
4 次，最多 8 local calls、每 call 最多 1 completion token、temperature 0、seed 20260909、top_p 1、num_ctx 8192、
think false、concurrency 1、0 retry。output 只留 hash，不留文字；先驗 model digest，intent 後中斷不可自動重打。

成功：每 transport 的前三 fixture offset 必須完全一致，且預先凍結的第 4 fixture 使用該 offset 精確預測 provider
prompt count；兩 transport 都有 exact usage、model/digest/options 對帳。任一 mismatch、unknown usage、非 localhost、
額外 call、timeout 或殘缺 intent 都保留為 failed binding，不放行 product smoke，不調 tolerance 或換 fixture。

唯一允許的下一動作是依
`research/p3_b3_tokenizer_binding_probe_execution_release_2026-09-14.json` 執行一次；只能產生 8 個本機低 token
evidence calls。不得改 P3 smoke、annotations、brain、P1/P2、frozen comparison design/baseline/rubric/threshold；
不能讀 confirmation、production DB 或執行 6-case smoke。

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
- developer smoke 已 sealed；tokenizer execution release 已凍結但尚未執行，因此 provider binding 尚未成立。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
