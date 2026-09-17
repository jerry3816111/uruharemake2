# 目前任務卡

更新：2026-09-17。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B50 explicit conversational-act fidelity

狀態：**P3-B49 semantic-preserving Japanese repair完成。** self-monitor不再以「請用日文重說」覆蓋原語意；一般非protected turn可在final guard前走既有M31 source-first授權，topic、共享anchors、可觀察conversation act與日文guard全過才取得surface authority。B47 before `ん、その話もう少し聞かせて。`；隔離本機after `また新しい注釈が来たのはうざいだろ`。第一個中性翻譯失敗也保留。8新測、164擴大回歸通過；4次本機dev model calls，沒有外網，token未掛ledger所以不做成本結論。這仍是曝光dev機制證據，不是fresh／人評／正式優勢。

### P3-B50 before 與單一交付

B47 u4的當輪明示要求是`陪我吐槽`，但既有cross-lingual desired-response分類只落成泛用`share_arousal`；固定realization成為「うん。今は質問しないで、ちょっとここにいる」，雖然日文與陪伴形式成立，卻沒有執行共同吐槽／抱怨這個conversation act。B48/B49都不應替這個更早的分類錯誤背書。

B50只處理明示conversation-act fidelity：將「要系統一起吐槽／抱怨」與「只要陪伴／聽著」分開，先建立可觀察、跨中英日且有negation boundary的act evidence，再讓既有explicit-current-turn authority選到能執行該act的response policy。不得從一般負面語句自行推斷使用者要共同吐槽，不得新增case全文固定回覆，也不得改弱危機／拒絕／explicit-space guards。

驗收先保留u4曝光before，再以未使用case全文的中文／英文／日文合成明示要求與相同topic的非要求／否定反例核對：只有明示共同吐槽才取得act authority；可見日文必須同時含當輪topic與共同抱怨行為；泛用陪伴不能假標performed。曝光u4只能當dev replay，不得當fresh evidence；不得重跑v3 release。完成這個最後已知case01根因後，才設計全新source做prospective比較。

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
