# 現行右腦契約與正式訓練教材覆蓋率稽核 V1

## 結論

正式載入的 v10 右腦確實學過基本的語意契約、記憶可說性與輸出禁則，
但沒有學過現行條件式人格政策的完整結構，也沒有任何一筆教材同時包含
人格政策、語意義務、記憶政策、禁用詞與程序指引。這是可量化的教材／介面落差，
但尚未證明它就是生成失敗的因果來源。

| 檢查 | 結果 |
|---|---:|
| 可重建的契約階段訓練曝光 | 2086 次 |
| 去除 v8／v10 重複後的底層單元 | 1061 筆 |
| 現行 payload | 10 筆 |
| 全部現行路徑覆蓋 | 77.6% |
| 人格政策路徑覆蓋 | 40.0% |
| 人格政策值覆蓋 | 12.0% |
| 現行完整聯合契約 payload | 10 筆 |
| 教材中的完整聯合契約 | 0 筆 |
| 舊式靜態人格教材 | 1061 筆 |
| 與現行完全相同的 system prompt 教材 | 0 筆 |
| 仍教『不得使用私』的舊教材 | 2086 筆 |
| 目前本機模型嚴格通過 | 6/10 (60.0%) |

## 缺少的主要教學內容

- `context.persona_expression_brief.conditional_context`
- `context.persona_expression_brief.expression_policy`
- `context.persona_expression_brief.expression_policy.avoid`
- `context.persona_expression_brief.expression_policy.avoid[]`
- `context.persona_expression_brief.expression_policy.brevity`
- `context.persona_expression_brief.expression_policy.energy`
- `context.persona_expression_brief.expression_policy.operations`
- `context.persona_expression_brief.expression_policy.operations[]`
- `context.persona_expression_brief.expression_policy.social_distance`
- `context.persona_expression_brief.expression_policy.tone`
- `context.persona_expression_brief.protected_fields`
- `context.persona_expression_brief.protected_fields[]`

這表示模型過去看到的主要是固定的 `lazy_short / slightly_bratty` 靜態標籤，
而不是現行系統依情境給出的語氣、能量、社交距離、表達操作與避免規則。
此外，現行 structured provider 已不再禁止第一人稱，但舊教材仍全部包含 `no first person 私`，
所以模型學到的輸出限制也與現在的 system prompt 不完全一致。

## 已教過但仍會失敗的部分

| 失敗類型 | 實際失敗 | 有標註教材 |
|---|---:|---:|
| language_or_script_pollution | 1 | 24 |
| polite_register_drift | 2 | 6 |
| required_semantics_missing | 2 | 30 |

語言污染、敬語漂移與必要語意遺失都有早期修復教材，但模型仍會失敗。
因此下一輪不能只是重複增加同類句子，而要教它理解現行結構中每個角色欄位。

## 研究可信度

- Git 歷史來源與訓練紀錄可重建：通過。
- 五個開發情境與訓練教材重疊檢查：通過。
- v8 的前一代 v5 教材已無完整可重建紀錄，因此不能宣稱整條模型血統都具完整資料來源。
- 這些教材沒有完整的公開人物來源、日期、時間戳與 split；它們只能算通用右腦教材，不能作為一ノ瀬うるは人格相似度證據。

## 本輪授權

- 決策：`authorize_person_independent_role_specialization_curriculum_construction_only`
- 可以：建立並稽核不含目標人物原句、考題及固定答案的通用角色專門化教材。
- 不可以：直接訓練、切換正式模型、宣稱人格更像或上線正式聊天。
- 下一輪必須使用全新且來源分離的例子，之後再以 matched control 驗證教材是否真的改善生成。
