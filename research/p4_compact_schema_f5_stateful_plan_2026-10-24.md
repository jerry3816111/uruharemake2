# P4 f5：JSON Schema carrier 的新題、無交錯產品驗收

狀態：**事前 source-only 凍結，尚無 f5 真模型或 Safari Send**。f3 真模型 candidate 欄位缺失／品質 FAIL；f4 schema-arm code/zero-model 153/153 PASS，但真 Safari 因 Tpre 後背景 tick 交錯而在 pre-Send strict FAIL、0 provider／0 Send。兩者及其 gold 不重判、不重送。f4 的失敗是操作時序，不能拿它證明 schema 成敗。

## 問題、單一變因與範圍

仍驗證**既有** opt-in compact JSON Schema carrier 在一個真正產品輪次是否能產生三個 strict-valid candidates，讓日文最終回覆給到明示的一句鼓勵。產品程式、基礎模型/digest、prompt、temperature、max_tokens=256、M29/M39、strict parser、guard、背景、記憶、Web 和同模型 baseline 完全不變；本批不再改碼或修 fallback。相對 f4 只修**實驗操作順序**：所有靜態核對放 Tpre 前，監看到一組完整無 mutation/error 的背景 pair 後立即落 Tpre，立即以原生 Safari 一次 Send，事後用單調時鐘及完整 journal 判斷是否無 interleave。若仍有交錯，**保留 f5 pre-Send/attribution FAIL，不重送**。不關閉或改寫背景以美化證據。

新作者題／固定 gold／資源上限在 `datasets/p4_compact_schema_f5_probe_2026-10-24.json`。凍結前完整句及 `初めて自分でシャツのボタンを付け直せた` 在 tracked py/md/json（排除無關 output）精確命中 0；source-only M29 classifier 為 `brief_encouragement`、不宣稱私下狀態。這是 developer diagnostic，**不是 formal holdout、不是同題 A/B**。f3/f5 不同輸入，單輪成功也不得宣稱 schema 的因果增益或對強 LLM 的全面優勢。

## Go/no-go 與驗收

先核本計畫／題／現行十檔 SHA、scoped diff/status，只提交推送 source-only freeze 並核 PR #435 exact head。之前 f4 code/contract 153/153 已可重用，不重跑無關大套件；新題只做 M29 source-only 和隔離真 RightBrain＋假 LeftBrain full-turn 1 輪，核 M29 brief encouragement、M33 not_applicable、M21 full/compact completed、scene support、act direct_chat_answer、final＝隔離 episode、恰 1 fake call 且帶 JSON Schema。只有此 gate 全過才准真產品。

真產品用新 port 7932、全新 controller-owned 0700 私有 root、官方 ONNX archive 私有不同 inode／封網 warm；同 PID zero-turn HTTP ready/planned stop/port vacant，再同 root 正式帶 `--direct-act-arm control --repair-cue-boundary --turn-admission-journal --compact-json-schema` 起同 PID ready。T0 及 Tpre 0600+fsync 私有 DB/receipt/journal 快照，T0/Tpre DB tree byte-equal、同 PID/session/reset0/finish0/DB；Tpre 前完整 pair 均無 mutation/error/unknown worker、tick>0 明列。原生 Safari 新 tab 正確 root/session，預填 frozen input 不算 Send；全部靜態核對及 Send 控件辨識**先**完成，再等待下一個完整 background pair，Tpre 後不做耗時靜態分析、立即一次 Send。事後核 Tpre→arrival≤10秒且無 background/proactive interleave，同 opaque ID arrival→admission_snapshot→cognition_start/end completed→terminal delivered；若任何硬 gate 失敗 strict FAIL、0 retry。

產品通過還需三個**真** strict-valid compact plans，M29→M21→表面保留鼓勵；Safari 泡泡短自然日文承接第一次自己縫回襯衫鈕扣、無教學/追問/捏造，泡泡＝raw＝guard＝graph utterance＝隔離 episode，圖至少 input→retrieval→decision→utterance→writeback 真連線可核。原生 PNG/AX 如工具不能持久留檔則標 visual gate 缺證，不能用終端重畫代替。上限 3 completed generations／2000 provider tokens／20 秒 user wait／1 Send；Brain、背景、Web delivery 額外 Chroma 成本分列，unknown 不冒充已核。正式 DB、原始 dirty checkout、無關 output／外部部署不碰。格式成功但行動錯仍整體產品 FAIL；Goal 不因 f5 狹義結果完成。
