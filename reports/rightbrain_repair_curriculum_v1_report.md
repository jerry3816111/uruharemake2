# RightBrain Contract Repair Curriculum v1

## 一句話結論

建立 720 筆通用修復資料；11 題 holdout 的輸入、契約指紋與標準回覆重疊均為 0。

## 研究門檻

| 檢查 | 結果 |
|---|---:|
| source rows | 1025 |
| eligible rows | 1025 |
| repair curriculum rows | 720 |
| holdout cases | 11 |
| holdout input overlap | 0 |
| holdout contract overlap | 0 |
| holdout target overlap | 0 |

## 修復原因分布

| 原因 | 筆數 |
|---|---:|
| semantic_slots_missing:0/2 | 172 |
| nonstandard_cjk_surface | 111 |
| polite_tone_drift | 111 |
| unexpected_ascii_leak | 111 |
| instruction_or_plan_leak | 110 |
| over_max_chars | 110 |
| cjk_language_leak | 56 |
| duplicate_candidate | 55 |
| must_avoid_violation | 55 |
| semantic_slots_missing:0/3 | 38 |
| semantic_slots_missing:0/1 | 11 |

## 情境分布

| 情境 | 筆數 |
|---|---:|
| absurdity_mirror | 77 |
| anxiety | 61 |
| birthday_repair | 4 |
| boundary | 26 |
| clarify_previous | 4 |
| concrete_offer | 60 |
| direct_answer | 85 |
| direct_social_action | 4 |
| direct_status | 4 |
| emotional_support | 93 |
| identity | 4 |
| memory_accounting | 50 |
| minimal_clarification | 11 |
| protective_brake | 75 |
| reference_probe | 45 |
| relationship_temperature | 42 |
| repair | 44 |
| reply_anxiety | 31 |

## 設計邊界

- runtime 與訓練共用相同 repair system prompt、task 與 feedback schema。
- 不提供失敗草稿，模型只能從左腦計畫與語意契約重新生成。
- 不含 11 題 holdout 的輸入、完整契約或標準回覆。
- 這是通用 denoising / revision 能力訓練，不是加入測驗答案。
