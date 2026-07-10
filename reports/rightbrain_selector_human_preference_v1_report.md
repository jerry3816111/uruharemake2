# 右腦 Selector 人類偏好 Gate v1

## 結論

不可接管：learned selector 在零文字重疊人類盲評中仍落後現行 heuristic 或完整 S0 候選，維持 observe-only。

## 資料隔離

- 已完成人類盲評：19 題 / 76 候選
- 因 selector 訓練文字重疊而排除：7 題
- 嚴格評測：12 題 / 48 候選

## 嚴格零文字重疊結果

| 方法 | 命中該題最高人類分數 | 選中平均分 | 自然度 | 語意 | 可直接聊天 |
|---|---:|---:|---:|---:|---:|
| 盲化順序第一個 | 3/12 (25.0%) | 2.312/5 | 2.500/5 | 2.167/5 | 25.0% |
| 目前 learned selector v1 | 3/12 (25.0%) | 2.417/5 | 2.500/5 | 2.333/5 | 16.7% |
| 目前 runtime heuristic（重建） | 7/12 (58.3%) | 2.958/5 | 3.167/5 | 2.917/5 | 50.0% |
| 完整 S0 系統候選 | 9/12 (75.0%) | 3.125/5 | 3.167/5 | 3.250/5 | 50.0% |
| 人類分數上限 | 12/12 (100.0%) | 3.208/5 | 3.250/5 | 3.333/5 | 58.3% |

## Learned Selector 對照

- 對 runtime heuristic：`{'first_wins': 1, 'ties': 5, 'first_losses': 6}`
- 對完整 S0 候選：`{'first_wins': 0, 'ties': 6, 'first_losses': 6}`

## 接管門檻

| 條件 | 結果 |
|---|---|
| strict_task_count_at_least_10 | PASS |
| strict_candidate_text_overlap_is_zero | PASS |
| learned_top_score_hit_rate_not_below_runtime_heuristic | FAIL |
| learned_mean_naturalness_not_below_runtime_heuristic | FAIL |
| learned_top_score_hit_rate_not_below_s0_candidate | FAIL |
| learned_mean_naturalness_not_below_s0_candidate | FAIL |

## 來源分開結果

| 盲評來源 | 題數 | learned 自然度 | heuristic 自然度 | S0 自然度 |
|---|---:|---:|---:|---:|
| v15_fresh_after_reply_priority_repair_partial_2026_05_24 | 6 | 2.333/5 | 3.000/5 | 3.000/5 |
| v16_followup_compact_partial_2026_05_24 | 6 | 2.667/5 | 3.333/5 | 3.333/5 |

## Learned Selector 實際落後案例

| task | learned 選擇 | 人類分數 | heuristic 選擇 | 人類分數 |
|---|---|---:|---|---:|
| rb_unseen15_0003 | 孤立する前に止め、一人にならず誰かか連絡先を使うように返す。 | 2.00 | 浴室で一人になる前に止まれ。近くの人に連絡しろ。 | 2.50 |
| rb_unseen15_0009 | 返事がない不安を認め、自分で決めつけないように返す。 | 2.50 | 既読で止まると不安になるよな。でも煩いって決めつけるな。 | 4.75 |
| rb_unseen15_0010 | 返事がない不安を認め、自分で決めつけないように返す。 | 2.00 | 返事が静かだと不安になるよな。でも尷尬にしたって決めつけるな。 | 3.75 |
| rb_unseen15_0013 | 返事がない不安を認め、自分で決めつけないように返す。 | 2.00 | 返事がなくて不安でも、自分が余計だって決めつけるな。 | 3.00 |
| rb_unseen15_0016 | 返事がない不安を認め、自分で決めつけないように返す。 | 2.00 | 返事がないと不安でも、空気を壊したって決めつけるな。 | 3.00 |
| rb_unseen15_0017 | 八期EDだけでは特定できないので、作品名か曲名を聞き返す。 | 2.00 | 何の元ネタ？ | 3.00 |

## 方法與邊界

- 同時保留整體分數、自然度、語意完整度與可直接聊天率，不把它們混成單一自動指標。
- v15 與 v16 的整體量表不同；跨來源接管判斷只使用共同的自然度欄位與逐題最高分命中。
- learned selector 的候選順序保持原始盲化順序；runtime heuristic 使用正式程式的分數與 tie-break。
- 這批只有單一評分者，沒有評分者間一致度，因此只足以阻止接管，不能證明廣泛的人類自然度。
- 每題四個候選來自完整系統與控制組，不等同目前 v10 的即時抽樣分布；仍需獨立 actual-model shadow。

研究邊界：Ratings come from two partial blind-rating packages completed by one rater on the same date, so there is no inter-rater reliability estimate and this is not an official benchmark. The packages use different overall rubrics; cross-package promotion therefore relies on their shared naturalness dimension and within-task top-score hits, while the overall mean is descriptive only. Exact selector-training candidate text overlaps are removed for the strict result, but semantic-family overlap may remain. The runtime heuristic is reconstructed from stored contract fields and is a proxy, not a replay of hidden runtime state. This gate can block takeover, not prove broad human naturalness. The four candidates per task are blinded system/control outputs rather than the current v10 model's runtime candidate distribution; actual-model shadow evidence remains a separate requirement.

## 方法來源

- [Twenty Years of Confusion in Human Evaluation](https://aclanthology.org/2020.inlg-1.23/): 分開報告自然度、語意與整體分數，避免未定義的單一品質分數。
- [Disentangling the Properties of Human Evaluation Methods](https://aclanthology.org/2020.inlg-1.24/): 明確區分評估對象、評估方式與實驗設計。
- [Perturbation CheckLists for Evaluating NLG Evaluation Metrics](https://aclanthology.org/2021.emnlp-main.575/): 不假設單一自動指標能同時代表流暢度、內容覆蓋與整體品質。
