# P4 direct-act handoff：來源歸屬與證據語義修訂 2

日期：2026-10-23。此修訂在 `b0–b6` 任何新真模型／Safari 輸出之前。原題本、gold、同載體操縱、九 arm-turn／0 retry／20,000 token 上限與舊 `a0` strict FAIL 均不變。本修訂只收緊兩臂共同的 M29 來源准入，並澄清 trace 的證據層級，不藉此新增能力 claim。

## 實作前已觀察的零模型反例與修正界線

獨立只讀審查重現：`母が言った。今日はここまでやったから、今は一言だけ労って。` 在原共同 M29 gate 被標 `current_user_direct_request`，使 M29 veto 與新 handoff 都准入。原因是轉述詞典只列少數具名說話者。此錯誤若帶入產品，便把第三方語句當成當前 User 指令，違反原設計的 source-bound hard gate；所以本項在新模型生成前作一次有根據、雙臂相同的 fail-closed 修正。

首輪形態修正後的第二次只讀審查又找到 `母に言われた`、`母が言ってた`、`母から聞いた`、`母からのお願い` 四個漏網反例。這證明窮舉語尾不足以保證來源。因此本次有根據的修正批改採**保守准入**：最終明示命令之前如有 `言・話・聞・伝・頼・書・お願い・依頼・指示・要望・要求・引用・メモ・リクエスト` 等發話／傳話／請託線索，就標 `ambiguous`，不得送 handoff。既有具體形態檢查仍保留。這會犧牲召回：例如 `母に仕事の進捗を話した。…労って。` 即使可能是 User 自己敘述，也不授予來源證書；普通 planner 仍能讀原文。非發話近鄰 `母と仕事を終えた。…労って。` 仍直接准入。這是可測的有限日文 cue 政策，不保證識別所有日語轉述，更不可把未匹配句一律稱為來源已證實。新增 M29 與 handoff 回歸，不改事前 `b0–b6` 題本。

## trace 與真輪的可主張範圍

`treatment_prompt_injected` 和 native graph 節點只證當輪有效證書的約束段落已交到 full-planner 請求；不證選定 plan 實際依約束決策，也不證最終 utterance 更符合 User 期待。零模型的兩臂假 planner 候選相同，測得的是 delivery 與其他請求欄位相同，**不是** plan-use 或品質改善。真輪要另核完整模型完成、selected plan、最後日文 utterance／guard／episode 同字、原生圖與對照臂差異；即使單對品質改善，也仍不能外推普遍優勢、真人被理解感或下游記憶因果。

送出前／後資料庫硬 gate 依修訂 1 再加一個可觀察的 `human_submission_finish_count`：Send 前需 0，Send 後需精確增加 1，並重讀 live Chroma client path，而非沿用啟動時 receipt。若沒有新的同 PID receipt、path/status/tick/session/reset 世代有偏離，fail-closed、0 retry。此欄位只計 Web submission 完成，不是模型品質或記憶真值。
