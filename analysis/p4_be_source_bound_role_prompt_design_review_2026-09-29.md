# P4-BE 事前設計審查：來源綁定的角色／限制擷取

狀態：**設計選擇，非正式評測；P4-BE 模型呼叫 0**。本文由開發代理與只讀代理審查，不是獨立人類設計審查或使用者人評。P4-BC、P4-BD 正式 FAIL、已曝光原句與已凍結分數不改寫。P4-BD 9B／4B 的 role-aware evidence 各 `0/6`，但混有標註集合過窄、真正錯角色／漏限制、和獨立的 canonical slot 漏填；因此只調整 evaluator 或只測 compiler 都不足以推出 upstream 已正確。

## 這一批要反駁的主張

假設：**同一 9B 模型、同一全新 raw dialogue、schema、normalizer、compiler、硬體與生成上限下，只把 evidence 擷取指示從「最短 exact substring」改成「保留該角色完整的對象／謂詞／數量／停止或完成義務」，會比 frozen P4-BC prompt 更常產生 source-exact、角色正確、完整且可編譯的 typed packet，同時不增加 false action、不超過 20 秒上限。**

這是 bounded 六模板上游能力測試，不是普遍人類語用理解，也不是 9B 對 4B 的模型選型。9B 是前一批 positive normalized／downstream `5/6`、max `15.05412s` 的較有希望候選；4B 尚未取得 9B 此卡結果的授權。只測 9B 可把 scored calls 限為 `2 prompts × 14 cases=28`；若最後需要比較 4B，必須另設計新的前瞻評測，不能在看見本批結果後臨時加跑或重用本批稱 holdout。

## 候選架構與選擇

| 候選 | 能解決什麼 | 主要風險 | 決定 |
|---|---|---|---|
| A. 原 schema 下只更改系統 prompt 的 role/value 指示 | 直接對準 `draft email` 代替 subject、`project name` 漏 containment predicate、日文 screen/tab/limit 角色交換、one/stop/completion 漏失；保持一次呼叫與可歸因變因 | 仍可能翻譯 source 或漏 `unknown_constraint_jp`；prompt 不是通用架構 | **選此作最後一次有界修正** |
| B. 模型輸出 source character offsets 或候選 ID，由程式還原 exact quote | 機械阻止輸出 `会議メモ` 這類原文不存在片段 | 不能阻止選錯角色／目標／限制；中日文位置數、Unicode、候選覆蓋與延遲新增錯誤面 | 本卡不採 |
| C. 依六模板寫 deterministic 關鍵詞 parser | 可精確覆蓋作者規則且低成本 | 對 phrasing 過擬合，易把研究目標變成六題規則；不檢驗模型的語用泛化 | 本卡不採 |

候選 A 不應用全模板通用的「操作對象=最窄實體」規則：`close_one_named_obstacle` 的 `task_object` 是使用者工作畫面／情境，`obstacle` 才是要關閉的項；`verify_one_named_condition` 的 `task_object` 是待查欄位；`extract_one_by_named_rule` 的 `task_object` 是筆記集合。新 prompt 只可把既有六模板各 role 的語義說清楚；不能加入 P4-BE 新題的詞句或按題特製答案。`unknown_constraint_jp` 仍由模型填、原 slots 與 schema／normalizer 不變；若漏填就是正式失敗，不能偷偷加 deterministic 補洞。

## 前瞻成對驗收規格（詳細數值須在 freeze contract 寫死）

1. 先建立與 BB／BC／BD 完整 source 逐字不重複的 6 positive（繁中、英文、日文各2，六模板各1）與 8 種不同 reason control；新題僅是 developer-authored development proxy，不是 temporal／人類 holdout。每案 source、expected template、canonical slots、role semantics、完整 gold、hard negatives 在模型輸出前固定。
2. 避免 BD「只列 1–2 個片段」的假陰性：每個 role 事前指定 source 中唯一可辨的 allowed window 與必需 exact anchors（對象／predicate／肯否、one／stop／completion 等）；role/value gate 只要求 atom 是 window 內連續 exact substring 且包含全部 anchors。owner 可以由 current-user source 與該 window 提供，短 atom 不必重複所有格。資料另有短／長良性邊界，供 quote-shape **診斷**，但不作 gate；否則評分又退化成兩個 literal aliases。此取捨允許含完整 anchors、卻語法不漂亮的來源碎片通過；因此主指標只能叫「bounded role/value anchor coverage」，不能叫完整語義／自然片段品質。模型不能用譯文、其他角色、旁物或任意整句塞過去。資料記錄 excluded distractors，但目前窄 window 已排除它們，不可另報成被獨立驗證的 polarity guard。至少 18 個逐 role hard-negative mutant 應在編譯可過的條件下仍被 scorer 拒絕，並另測 window 內漏 predicate／數量／完成條件的片段被拒絕。這仍是作者標註的 proxy，不能宣稱 atom 的唯一 source offset 或一般語義金標。若自然語言案例無法定出不歧義的 source window，就在 freeze 前換案例或提出 `REVIEW_REQUIRED`，不能邊跑邊補。
3. 使用 **同一新 dataset／同一預凍結 evaluator** 比較 arm `BC original prompt` 與 `BE role/value prompt`。兩 arm 只差 system prompt 的 evidence-role 指示；同一 9B digest、dynamic JSON schema、完整 canonical slots、source_id/span、normalizer、P4-BB compiler、temperature `0`、seed `20260927`、`num_ctx=4096`、`num_predict=480`、M2 Pro 32GB、單 call 20 秒 gate、0 retry。按 case 交替先跑哪個 arm，避免一個 arm 永遠先受熱／cache 順序影響；每 arm 的實際 prompt/completion tokens 和 wall time 獨立記錄。固定 model prewarm 不計分。
4. 主結果是**成對每案完整 packet**：normalized typed、source identity/exact、template、非 evidence slots exact、角色／語意 evidence、downstream compile、mechanism、自然日文同時為真，BE positive 必須 `6/6`；BE controls unavailable＋reason `8/8`、false spec/source violation `0`、token 完整、max scored call `≤20s`。baseline controls、token、latency 全部如實報告，但不作 BE eligibility gate；兩 arm 的所有 14 calls 均須完成並 JSON 可解析，否則成對差異不可解釋。另外逐案報 `BE-only pass`、`BC-only pass`、兩者皆通過／皆失敗、role-atom 分數與原 strict single-gold exact。要稱「prompt intervention 有增益」，BE 必須通過完整 gate、沒有 paired regression，且至少 1 案 BE-only full pass；另須至少一案 **BC raw role/value evidence FAIL → BE raw role/value evidence PASS 且兩 arm source identity 都合法**，避免僅因 BE 恰好補好 canonical slot 就假稱 evidence 提升。若兩 arm 均通過且無 BE-only win，不能宣稱額外機制有價值，應比較實際成本並簡化。
5. 對 prewarm、timeout、JSON parse、slot 遺失、source 翻譯、role 錯、control false action 皆保留原樣，不 retry。每 arm/case 唯一 call；結果檔逐案 checkpoint、不可覆寫／續跑。先提交 dataset／evaluator／prompt／contract／freeze tests 的 freeze commit，再提交一次性 runner 與 fake transport tests，完成 preflight 才准 28 次正式 scored calls。原 P4-BD runner／結果絕不重跑。

## 決策邊界

即使 BE 過全部 bounded gate，也只能說這個 prompt intervention 在這組六模板開發 proxy、9B、本機硬體上比 frozen prompt 有可重查差異；接產品需另做 fresh full runtime、Safari 及真實圖像／記憶流程驗收。沒有 4B、真人偏好、長對話、強 LLM 相同資源 baseline、正式 temporal holdout 或 VRM／Function Calling 證據，就不能擴張到那些層。

若 BE 仍未達**完整** gate，即使部分 evidence atoms 改善，保持 FAIL；把兩輪修正的最小反例、標註效度風險與後續 architecture options 寫成 `REVIEW_REQUIRED`。不靠新增 `P4-BF`、事後加 gold alias、改弱 baseline 或改寬 latency／control 標準追分。可另在設計審查中評估「slot materializer」或 source-offset 方案，但不能把它們偽裝成本卡同一變因。
