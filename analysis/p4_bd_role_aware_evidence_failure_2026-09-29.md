# P4-BD：事前列舉的 role-aware 證據評分，正式 FAIL

P4-BD 的新評分器與凍結資料／契約先在 `26fb89821d7d1b846ff3d83aa4209f8ecd8384e8` 固定；一次性 runner 與假模型測試先在 `b6362cd` 固定。2026-09-29 才對本機 `qwen3.5:9b`、`qwen3.5:4b` 各送 14 個全新 developer-authored cases（6 positive、8 controls），合計 **28/28 完成、28/28 JSON 可解析、retry 0**。原始逐案資料是 [`p4_bd_role_aware_evidence_2026-09-29.json`](p4_bd_role_aware_evidence_2026-09-29.json)；兩模型皆 **FAIL、沒有 selected model、產品 runtime 未改**。這不是 Safari、完整對話、人評或獨立 holdout 結果。

## 為什麼做與何者沒變

前一個 P4-BC 正式實驗中，兩模型的 unique-gold evidence exact 都是 `0/6`；有些輸出是同角色的長／短片段差異，也有明顯錯角色的例子。P4-BD 只檢查一個假設：在**看到模型答案之前**，對每個語意角色列出 1–2 個可接受的 source-exact 片段，是否可以辨別「只是邊界不同」與「來源／角色／語意錯」，同時讓原先上游和下游 gate 都通過。舊 strict single-gold 指標仍報告，只是不再作本次新評分邊界的 eligibility gate；沒有把 P4-BC 改判為 PASS。

模型、prompt、dynamic schema、六種 action template、完整日文 slots、P4-BB compiler、8 種 unavailable reason、M2 Pro 32GB、temperature `0`、seed `20260927`、`num_ctx=4096`、`num_predict=480`、20 秒 single-call 上限與 0 retry 均按凍結契約保持。9B、4B 依固定順序各 prewarm 一次，prewarm 不計 case latency；沒有架設外部 server，只用已在本機運作的 Ollama。P4-BC 已曝光題沒有重跑，P4-BD 的完整 source 與 P4-BB／BC 不重複，但仍共享六種 ontology，故不能稱獨立語義 holdout。

標註候選由開發者設計；兩次分開的 LLM-proxy 判斷對 `18 role × 3 source-exact candidates` 的 binary agreement=`48/54`、完整 role-set agreement=`12/18`。六個分歧候選在正式輸出前保守排除，並未看答案後補值。這**不是兩位真人的標註一致性**；排除本身可能造成假陰性。評分器離線測試證明：18 個故意換錯的 source-exact role/span mutant 雖可通過下游 compiler，仍被新 scorer 全部拒絕。這只證明 evaluator 對已列舉反例的契約行為，不證明其金標覆蓋所有合理自然語言片段。

## 預先 gate 與實測

每個模型必須同時達到 JSON `14/14`、所有 positive 的 normalized typed／非 span exact／template／role-aware evidence／完整 packet／slots／下游 compile／mechanism／自然日文各 `6/6`，controls unavailable＋reason 各 `8/8`、false spec/source violation `0`、token 完整、max call `≤20s`。任一必要項失敗就不選模型。

| 指標 | 9B | 4B |
|---|---:|---:|
| 完成且 JSON 可解析 | 14/14 | 14/14 |
| positive normalized typed／非 span exact | 5/6、5/6 | 5/6、4/6 |
| positive template／canonical slots | 5/6、5/6 | 5/6、4/6 |
| role-aware evidence／完整 packet | **0/6、0/6** | **0/6、0/6** |
| 已接受 role atoms（normalized） | 5/18 | 2/18 |
| 原 strict evidence／整包 exact（僅報告） | 0/6、0/6 | 0/6、0/6 |
| downstream compile／mechanism／自然日文 | 5/6、5/6、5/6 | 4/6、4/6、4/6 |
| controls unavailable＋reason | 8/8、8/8 | 8/8、8/8 |
| false typed spec／assistant 或 private source | 0、0 | 0、0 |
| max／median scored call | 15.05412／10.12816 秒 | 9.38962／6.02785 秒 |
| prompt／completion tokens | 12,758／3,655 | 12,758／3,116 |

合計 scored prompt／completion tokens=`25,516/6,771`、scored call wall-time 加總=`252.95377s`（不是整個實驗的端到端 elapsed time）。9B／4B prewarm=`5.10184/3.59903s`，另列不計 case latency。這批題中兩者都滿足 controls、token、20 秒 gate，但 positive 品質 gate 明確不通過；與 P4-BC 題目不同，不能把 9B reason `7/8→8/8` 或較低 latency 當作因果改善。

## 具體失敗分層

1. **可能合理、但未在事前可接受集合的邊界**：中文收據案 9B 用 `我那疊收據`，凍結可接受值是 `那疊收據`；英文會議案 9B 用 `meeting minutes`，可接受值是 `my meeting minutes`；中文小步驟案 4B 用 `給我一個能馬上動手的小步驟`，可接受值不含句首 `給我`。這些可能是狹窄 gold 造成的假陰性，不能事後增列並把正式分數洗成 PASS；也不等於所有被拒絕片段都正確。
2. **確實丟失語意角色、限制或 source exactness**：4B 日文關閉分頁案把 `未使用のタブ` 放在 `task_object`（凍結目標是 `私の作業画面`），把 `閉じるのは一つだけ` 放在 `obstacle`，`limit=そこで止めたい` 又漏掉「只關一個」；下游仍能編譯，不能據此宣稱上游理解正確。4B 英文會議案把原文 `meeting minutes` 翻成 `会議メモ` 作 evidence，3-role packet 可 normalize，但這個 atom 並非 source substring，P4-BB compiler 以 source-exact check 擋下。9B 在英文 email 案用 `draft email` 而非 `its subject` 作 task object，會改變工作範圍。9B 的 18 個 raw atoms 都在來源內；4B 為 17/18，但「在來源內」顯然不是充分條件。
3. **另一個獨立的完整 packet 失敗**：9B 日文關閉分頁案與 4B 日文填日期案均缺必需的 `unknown_constraint_jp`，normalizer 因 `typed_spec_contract_mismatch` fail closed。9B 前案的 `obstacle_jp` 也與 frozen canonical 值不同。raw evidence 即使有部分正確，也不能讓 invalid packet 取得 eligibility。4B 中文收據案的非 span slots 同樣不 exact。這些不是調整 evidence span scorer 可以修好的問題。

## 判定與下一個必要工作

本次唯一評分邊界修正**未使 upstream raw dialogue → source-bound typed spec 達到凍結 gate**；甚至 evaluator 對自然變體本身可能仍過窄。因而 P4-BD 保持 FAIL、資料已曝光、不得以同題改 gold 或重跑追分，不接產品。可主張的是：在這組 bounded 開發代理案例，8/8 界外控制穩定拒絕、成本可量，且被 source-exact／role-aware／normalizer 分層揭露出不同錯；不能主張系統更懂使用者、建議有效、已優於強 LLM、能預測真人或接近完成「人類方程式」。

下一個單一能力變因應放在**來源綁定的 evidence 角色與限制擷取**，而不是再把「任意 source substring」放行。先作設計審查：建立與 evaluator 標註歧義分離的 source-bound role/value 表示（保留原文、數量／停止條件與角色），對新的 source-exact 角色錯誤及語義等價反例事前凍結；測試可以辨別「可接受邊界」與「錯目標／錯條件」且使上游 output 真的更正確。`unknown_constraint_jp` 的 deterministic materializer 是另一個獨立變因，不能同批悄悄加入。若兩次有根據修正後仍不過，依工作規則提出 `REVIEW_REQUIRED` 與架構取捨，不無限增加小編號。

驗收範圍：離線契約＋本機 fresh model **已完成且正式 FAIL**；產品 full runtime、Safari 圖像、VRM／Function Calling、真人及 temporal holdout **本卡未驗收**。這些層的既有證據不因本次重寫；不得用 `71+` pytest 數量代替產品能力。
