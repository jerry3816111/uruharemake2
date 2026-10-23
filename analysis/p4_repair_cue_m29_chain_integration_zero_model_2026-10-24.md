# P4 repair-cue × M29 產品鏈接線：零模型結果

狀態：**局部 code PASS；真產品／回覆品質未驗收**。依事前計畫 `research/p4_repair_cue_m29_chain_integration_plan_2026-10-24.md`，單一功能變因是將既有、預設關閉的 repair-cue overlay 接入現行 M29 優先 Web 入口，並只讓顯式 `--repair-cue-boundary start --mode product` 的正式 product child 設 `URUHA_P4_REPAIR_CUE_BOUNDARY=1`。未改詞彙規則、核心認知、planner、候選、guard、記憶、背景 scheduler、模型參數或 f1 題本／gold。

## 實際差異與可歸因證據

| 同一 frozen f1 原句、同一產品鏈、同一假模型 plans | flag OFF | flag ON |
|---|---|---|
| M29 requested act | `brief_encouragement` | `brief_encouragement` |
| M33 / M18 | `not_applicable` / 未接管 | 同左 |
| M21 | `full`、compact completed | 同左 |
| 最終 speech-plan act | `repair_check`（錯把「終えた」詞中的 `え` 當追問） | `direct_chat_answer` |
| 假模型呼叫／episode | 1／final＝唯一 episode | 同左 |

兩臂是獨立隔離 subprocess 的 `run_turn_debug`，不是實際 provider generation；開關是其唯一輸入差異。產品入口 wrapper 安裝一次、flag OFF 時回原 act。聚焦正／負控確認真獨立「え？」與英語 `Huh?` 仍是 `repair_check`，引號內「え？」與詞中「え」不誤觸。controller 測試確認 shell 偽造 flag 不流入隔離環境、預設／非 product action 不啟用、preflight probe 不見 flag、port-scoped allowlist 與正式 child env 才有 flag，與既有 journal／direct-act arm／port 同時使用無衝突。

變更前新聚焦斷言 **3 failed**（產品入口未裝、f1 act 未修、controller 未消化 flag）。首次接線後 3 passed，但獨立審查發現 preflight 環境外溢與缺 full-turn OFF 對照；修正後聚焦 **4/4 passed**。使用專案 `.venv/product_checks/bin/python` 的七個受影響檔案合併回歸 **140 passed、9 既有 warnings**，`git diff --check` 無問題；獨立只讀 diff 複審無阻擋。曾誤用系統 `pytest` 得到 `colorama` 未安裝的環境失敗，未計入產品結果，改用專案 venv 後通過。產品來源與測試雜湊見同名前綴的 `research/*product_2026-10-24.sha256`（6/6）。

## 嚴格限制／下一步

- 原 f1 零模型 go/no-go **FAIL**、f0 送出前 **FAIL**、2026-10-20 repair-cue Safari 六輪整批 strict FAIL 都不改判；f1 修後只作開發 regression，不重送、不稱產品 PASS。
- 這批 **0 真 provider calls、0 新 Safari Send**；沒有自然日文可見回覆、真模型成本、native node graph、DB 寫回或使用者被理解感的新證據。選對 act 不能推論最終 utterance 品質或省 token。
- 下一個必要交付是另凍結未曝光、source-disjoint 的 f2 題／gold／資源上限與真 Safari 逐輪歸因 gate；先 source-only commit/push，零模型預檢通過後才啟全新隔離 root，0 retry。若 Web 背景與使用者輪交錯、圖／來源／日文／成本任一門檻缺證，就保留 FAIL。正式強 LLM 對照、人評、temporal holdout、VRM／Function Calling 統一驗收與整個 Goal 仍未完成。

僅在安全 worktree 修改；正式資料、原始 dirty checkout 與無關 `output/graduate_application_report/` 未動。
