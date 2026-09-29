# M46 固定封包辨別力：一次性實測 FAIL

## 凍結、執行與可核對結果

- 事前計畫／契約／零呼叫測試 commit：`41bb4f02edf1bab392a001e0043eda4368d57144`；一次性 runner／fake transport 測試 commit：`668be4b`。兩個 commit 均先於正式呼叫。原 M51 生成失敗 artifact 保持原樣，原 A/B 消融仍為 `INCONCLUSIVE / NOT RUN`。
- 新正式執行只有一次，結果位於 `analysis/p4_m46_fixed_challenge_discrimination_2026-09-30.json`，SHA-256 `e7b163957152a9ab05d20094e6d5061d134efa80d47c66274538932faaabedfa`。前檢確認原 9 個封包、9B 模型 digest、Apple M2 Pro／32 GB、原程式 hashes、8 個共同 guard 可交審與 1 個 guard control 阻擋。8/8 M46 calls 完成、JSON 可解析、來源 id/span 精確、prompt/completion tokens 完整；0 retry、0 M51 generation、0 產品／正式 DB 操作。
- 事前品質 gate **FAIL**：A 保留有效行動 `1/3`（要求 `3/3`），無效行動錯放 `0/5`（要求 `0/5`），但類別對應理由辨出 `4/5`（要求 `5/5`）。B 是隔離的無 reviewer 反事實，保留 `3/3` 有效、錯放 `5/5` 無效；後者是**封包刻意構造**，不能解釋為自然生成錯誤率或可上線比較。
- reviewer-only 8 次合計 prompt `6,568`、completion `2,304` tokens；wall 中位 `13.210155s`、最大 `14.4233s`。一次不計分 prewarm 為 `4.08774s`，各 call 均在原結果列出。這不是 M51＋M46＋M45／Web 延遲；舊 M51 失敗的 `17.63697s` 也不可和本次不同封包拼成成功的產品輪次。

| 原固定類別 | 開發者事前 gold | A 是否放行 | 模型可見的關鍵判斷 |
|---|---|---|---|
| valid 中文 | 接受 | 拒絕 | 內容 checks 全 true，但 `casual_japanese=false`；句尾「止めよ」可能與自然口語 gate 衝突。 |
| wrong-task | 拒絕 | 拒絕 | `criterion_advances_goal=false` 等，命中對應理由。 |
| valid 英文 | 接受 | 拒絕 | `no_unknown_prerequisites=false`；來源未給實際問題文字，但行動是請使用者從原筆記擷取，這個拒絕是否過保守需另審。 |
| unsupported specificity | 拒絕 | 拒絕 | `no_invented_facts=false` 等，命中對應理由。 |
| private inference | 拒絕 | 拒絕 | `goal_matches_source=false`、`no_invented_facts=false`。 |
| valid 日文 | 接受 | 接受 | 內容／表達 checks 全 true。 |
| non-action | 拒絕 | 拒絕 | `action_is_operationally_specific=false` 等。 |
| actor/surface | 拒絕 | 拒絕 | 指令聲稱「うちが…閉じておく」卻把 `no_identity_or_role_error=true`；它因 `no_unknown_prerequisites=false` 才被擋，未辨出預設的行動者錯置。 |
| deterministic guard | 拒絕 | 未送審 | A/B 都先阻擋，不能記為 reviewer 的功勞。 |

## 歸因與下一步

這組結果足以否定**本次凍結的固定封包辨別力 gate**，卻不足以歸咎單一原因：有效中文封包的「止めよ」也可能確實不合自然口語，而英文有效封包被標未知前提則可能是審核器過度保守；二者不能事後改 gold 追認通過。五個無效封包雖都被擋，actor/surface 錯誤沒有被對應欄位抓到，不能報稱五類理解均成功。這些 gold 與封包由開發者寫成且已曝光，每類負例只有一題，不是獨立 holdout 或真人標註。

產品維持 fail-closed，不移除 M46、不中途提高 timeout、不重跑這批題或更改既有凍結。下一個必要交付是非獨立**設計審查**：先明確區分「gold／自然日文表面標準不一致」與「審核器漏辨 action actor、對可由使用者執行的提取誤判未知前提」；選一個可歸因修正變因及成本，使用全新 source／封包事前凍結。若 reviewer 品質仍不可靠，就審查替代架構而非直接旁通。M51 真實生成在 360-token 上限截斷的上游問題也仍獨立存在；只有後續全新自然生成、相同候選 A/B、完整產品 runtime 與 Safari 都通過，才可談交付資格。本次沒有真人效用、強 LLM 優勢或「人類方程式」的證明。
