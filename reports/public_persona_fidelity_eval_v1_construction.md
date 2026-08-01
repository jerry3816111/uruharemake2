# 公開人格重現評測 V1 建構稽核

- 評測協定完整：`True` (17/17)
- 正式執行就緒：`False` (1/19)
- 人格分數已計算：`False`
- 決策：`authorize_provenance_only_reference_manifest_and_consented_rater_protocol_construction`
- 本輪模型呼叫、runtime 修改、holdout 檢視：`0 / 0 / 0`

## 現在具備什麼

評測尺的比較條件、資料隔離、盲評主指標、真人參考範圍、同主題控制、非退步界線與單一部件消融規則已凍結。
目前只有 5 筆開發觀察與 2 個未開封來源；因此沒有產生或暗示任何一ノ瀬うるは人格相似分數。

## 正式執行缺口

| 證據 | 現有 | 最低需求 | 就緒 |
|---|---:|---:|---:|
| 目標開發觀察 | 5 | 40 | False |
| 目標校準事件 | 0 | 30 | False |
| 最終目標 holdout 事件 | 0 | 50 | False |
| 相近人物 | 0 | 3 | False |
| 同主題參考配對 | 0 | 30 | False |
| 反事實新情境 | 0 | 50 | False |
| 多輪事件 | 0 | 20 | False |
| 目標熟悉評分者 | 0 | 3 | False |
| 一般日語評分者 | 0 | 3 | False |

## 公平比較

| 條件 | 作用 |
|---|---|
| `s0_full_cognitive_persona` | 凍結的完整認知型公開人格代理；使用正式聊天管線，但不能讀取評測 holdout 或真人參考答案。 |
| `c1_matched_prompt_only` | 使用與 S0 相同本機基礎模型、開發人格資訊、輸入內容、總上下文預算、解碼參數及輸出預算，但以單次 prompt-only 方式回答，不使用結構化認知管線。 |
| `c2_matched_persona_disabled` | 保留與 S0 相同架構、模型與預算，只把目標公開人格證據替換成等長度的中性公開對話契約，用於驗證增益是否真的來自目標人格層。 |

主比較是 `S0 完整系統` 對 `C1 同模型、同人格資訊、同預算的 prompt-only`。
`C2 人格關閉` 只驗證差異是否來自目標人格層；單一部件貢獻仍要另外逐一消融。

## 五條互補證據

1. 熟悉目標人物的知情同意匿名盲評。
2. 目標人物跨時期的自然差異作參考範圍。
3. 至少三位相近人物的同主題對照，防止話題捷徑。
4. 來源獨立的新情境與多輪動態事件。
5. 語意、推理、記憶、拒答、多樣性、延遲、記憶體與動作安全不退步。

## 主成功門檻

S0 對 C1 的非平手人格盲評勝率至少 60%，95% 信賴區間下界高於 50%，並以評分者與情境相依的配對模型確認。
單一向量、單一 benchmark 或 LLM judge 即使很高，也不能單獨通過。

## 校準公式示意，不是真實結果

若代理對目標相似度為 0.70、目標跨期中位數 0.90、相近人物中位數 0.40，校準值為 0.60。
其中 0 代表相近人物基準，1 代表目標跨期自身基準；數值不截斷，大於 1 不代表比真人更像真人。

## 方法來源

| 方法 | 本研究採用 | 不代表 |
|---|---|---|
| [incharacter_acl_2024](https://aclanthology.org/2024.acl-long.102/) | Use open-ended interviews and human-perceived target profiles instead of treating direct self-report answers as sufficient personality evidence. | The paper's reported character-level accuracy is not reused as an UruhaBrain score or success threshold. |
| [charactereval_acl_2024](https://aclanthology.org/2024.acl-long.638/) | Keep conversational quality, character consistency, role-play quality, and personality-related evidence as separate dimensions with human calibration. | Its Chinese fictional-character dataset is not treated as a direct benchmark for a Japanese public persona. |
| [personagym_emnlp_2025](https://aclanthology.org/2025.findings-emnlp.368/) | Test persona behavior in dynamic, persona-relevant environments across expected action, justification, linguistic habits, consistency, and control tasks. | PersonaScore is not used as a sole automatic judge and no benchmark answer is copied into the system. |
| [emocharacter_naacl_2025](https://aclanthology.org/2025.naacl-long.316/) | Evaluate emotional response fidelity separately in single-turn and multi-turn contexts because general capability does not guarantee emotional fidelity. | Its source dialogues or labels are not imported and emotional fidelity is not equated with complete persona fidelity. |
| [raven_tacl_2024](https://aclanthology.org/2024.tacl-1.75/) | Report same-topic and cross-topic verification separately and construct heterogeneous topic controls so topic words cannot masquerade as speaker style. | Authorship verification is supporting language evidence, not proof of identity or complete persona reproduction. |

## 證據邊界

V1 protocol construction can prove only that a falsifiable, source-disjoint, matched-control and human-calibrated evaluation design exists. It cannot produce a persona score, establish target fidelity, authorize model or runtime changes, unseal the V2 holdout, import copyrighted transcripts, or claim that the system reproduces the person.

下一步：建立只含來源、日期、分割、權利邊界與雜湊的參考資料 manifest，補足目標校準、相近人物同主題對照及知情同意評分者流程；在全部 readiness gate 通過前不執行模型或打開 holdout。
