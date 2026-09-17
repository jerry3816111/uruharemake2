# 目前任務卡

更新：2026-09-17。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B51 prospective temporal forecast protocol freeze

狀態：**P3-B50 explicit conversational-act fidelity 完成。** 曝光輸入
`現在先別分析，陪我吐槽一下這些註解怎麼會一直長出來。` 的可見輸出由泛用陪伴
`うん。今は質問しないで、ちょっとここにいる。` 改為隔離本機真實模型輸出
`これらの注釈、うざい、またかよ`。跨中英日明示共同吐槽、否定、普通負面文字、陪伴、吐槽使用者、
危機與participant-as-topic邊界均有contract測試；48 focused／125 affected regression通過。
開發過程共13次本機qwen3.5:9b calls，失敗與`私と君`錯誤輸出保留；token未掛ledger。
完整證據見`analysis/p3_b50_explicit_conversation_act_acceptance_2026-09-17.md`。
這仍是曝光dev機制證據，不是fresh holdout、人評、Safari或正式優勢。

### P3-B51 before 與單一交付

到B50為止，產品已能改善已知對話失敗，但仍不能回答長期研究最重要的問題：加入可追溯的人物狀態、
記憶與關係模型後，是否能在**看不到未來答案**時，比相同模型的context-only／persona-prompt／retrieval
條件更準確預測特定人物接下來的response category。若沒有時間切割與預先承諾，對已看過對話的修正只能證明
工程能修case，不能證明「人類反應方程式」具有預測價值。

B51只建立不可偷看答案的Task A protocol與機器可檢查schema，依
`research/2026_related_work_module_map_2026-09-17.md`引用的2026工作，固定：歷史cutoff、future-context、
四個matched-model條件、response／speech-act機率分布、bounded rationale variables、unlock前後狀態、
資源上限與失敗判準。此步不得讀取或寫入future response，不執行生成，也不選有利case；先用純合成fixture
驗證封存、雜湊、機率與leakage fail-closed。真正來源選擇與future unlock留到下一個經設計審查的task。

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
- developer smoke僅逐案推進，case06在B27仍為0 generation；未執行的cases／turns、case06評分、真人與formal confirmation仍不可宣稱。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
