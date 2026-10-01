# P4-BE `REVIEW_REQUIRED` 設計處置：封存失敗路徑，先驗證 reviewer 的必要性

狀態：2026-09-29 的**非獨立設計審查**；本文不改寫 P4-BA／BB／BC／BD／BE 的正式結果，不是新的能力 PASS，也沒有新增模型呼叫。P4-BE formal evidence 固定於 `c1c00a29143b8f6855974a41104186cab65101b3`，原始逐案結果見 `p4_be_role_value_prompt_evidence_2026-09-29.json`。審查的目的不是把第三個小 prompt 修正換個名字，而是判斷哪條路徑還有足夠可反駁的產品價值。

## 已知 before 與因果限制

- P4-AZ 隔離兩輪 Safari 已證明 exact prior source 能到達 M51；T2 有兩個候選、其中一個結構通過，但 M46 第二次模型 review timeout，M45 fail closed，最後沒有交付可立即做的一步。該正式路徑不能重跑。
- P4-BA 的四種 generator/reviewer 大小組合，full accept 均 `0/2`。縮小 reviewer 的 0.8B 是 `0/4` accepted 的 always-reject，9B reviewer 判對 `3/4` 但兩階段最慢 `29.86752–35.71618s`（視 generator 組合）。只換小模型未解決可用性與品質。
- P4-BB deterministic compiler 在**已給正確且授權 typed spec**的六個 bounded positive `6/6`，但沒有證明 raw dialogue 能提供該 spec。P4-BC、BD、BE 三批已曝光 developer cases 不能互相比較當因果趨勢；其中 BE 同題 prompt 對照只有 `1/6` full accept，候選 compile 反而 `3/6` 對原 prompt `6/6`。兩次有根據修正 BD、BE 後仍失敗，不能再追 prompt／gold。

## 架構選擇與明確否決

| 選項 | 可修範圍 | 此刻決定與理由 |
|---|---|---|
| 單獨 canonical 日文 slot materializer | 可能補 `items_jp`、`unknown_constraint_jp` 等 packet 欄位 | **不作下一批**。即使事後把 BE 的 slots 全修成 6/6，本批 role/value evidence 仍只 `2/6`；這個修正不足以使完整入口可信。將來若為別的已確認 typed source 做 materializer，需另定單變因與新資料。 |
| 在同一個錯誤 packet 後加 deterministic verifier | 可拒絕非來源／錯結構輸出，增加保守 abstention | **不作正例改善 claim**。固定同一 packet 的 verifier 只能接受或拒絕，無法產生被漏掉的角色、條件或合法日文；若日後測試，應獨立評 valid retention 與 hard-negative rejection，不得把 abstention 包裝成 full packet 提升。 |
| 另建結構化 producer＋verifier 一體方案 | 可能分離來源角色、任務完成條件與表面語言 | **暫不直接建**。這是新架構，不是 P4-BE 的第三次小修；須先確認它相對直接回覆／現有 reviewer 有可測的價值，並另凍結未曝光題、品質與額外 token／latency。 |
| 封存目前 raw dialogue→typed-spec 自動接產品的路徑 | 保留 P4-BB 作條件式 compiler、BC–BE 作失敗證據 | **採用**。BC–BE 尚未進產品 runtime，維持不接入；既有 fail-closed 不改、資料不刪除、問題不宣稱解決。這是 scope／安全決策，非新產品能力。 |

這個決策並未否認「結構化認知」的研究方向，而是拒絕從 6 題 developer proxy 的 `1/6` 成功直接宣稱上游已能理解並接入真實使用者。是否重啟該路徑，應由獨立的新架構假設和更強前瞻證據觸發，不由修同一批題觸發。

## 接下來唯一必要的設計問題

目前對使用者可見的 practical action 最早仍被 M46 review timeout／內容判別卡住；在要求使用者自架 server 前，先回答：「**第二次模型 review 是否真的提高安全且來源綁定的可見行動品質，值得它的 latency／tokens？**」下一張卡只比較 review stage 的必要性，**不**同時改 generator、prompt、資料來源、記憶、人格、日文 guard 或產品 timeout。

可歸因設計候選：用新的隔離中／英／日 source-bound practical-action cases，對每題只生成一次 frozen M51 候選，離線重放相同候選到 A=既有 M46 review、B=無 model reviewer 但保留完全相同的 deterministic structural／source／safety fail-closed checks；因此 generator 輸入與輸出相同，差異只在 review stage。對事前標註的 valid、wrong-task、unsupported specificity、private-inference、non-action、非日文／表面不合格案例，分開量 reviewer 是否真能拒絕錯案且留住對案，並逐 arm 記錄實際 token／latency；B 若放出任何不安全或無來源行動，就**不能**為了速度直接接產品。A 若沒有可測的正確性增益、卻持續超時，才有依據審查 reviewer 的保留／替代；兩者都不合格則停止行動交付路徑並保留 fail-closed，不偷偷旁通。

此處只是**設計方向**，尚未放行任何 scored call：必須先寫新 task card，固定 case、independent gold/評分、baseline、品質和成本 gate、最大呼叫數、0 retry、模型 digest、隔離／source 邊界、失敗分支，並先 commit freeze／runner。開發者題與 LLM proxy 不是人評或正式 holdout。離線即使 PASS，也需全新隔離 runtime／Safari 輪次檢查 visible Japanese、node graph、durability、source、latency 才可接產品；舊 P4-AZ 句不得重跑。若要聲稱優於強 LLM，還須同模型同資訊同資源的獨立對照，而本處置不提供該證據。
