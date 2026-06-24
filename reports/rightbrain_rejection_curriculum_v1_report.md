# RightBrain Rejection Curriculum v1

這份資料把右腦模型在 holdout 中被 gate 拒絕的案例，轉成下一輪 LoRA 的補強樣本。

## 一句話結論

被拒絕的 raw candidate 只作為錯誤 metadata；真正訓練目標使用已通過 final-surface gate 的 deterministic 合格答案。

## 總表

| 指標 | 數值 |
|---|---:|
| source case count | 11 |
| curriculum row count | 6 |

## 失敗原因分布

- unexpected_ascii_leak: 3
- semantic_slots_missing:0/1: 2
- semantic_slots_missing:2/4: 2
- cjk_language_leak: 1
- polite_tone_drift: 1
- semantic_slots_missing:2/3: 1

## 補強樣本

| case | category | reasons | target reply |
|---|---|---|---|
| explicit_stomach_coffee | audited_memory | unexpected_ascii_leak, semantic_slots_missing:2/4 | 最近は胃が弱いんだから、コーヒーは控えめにしとけ。 |
| explicit_spicy_food_update | audited_memory | semantic_slots_missing:2/4 | 最近は辛いものを控えたいんだから、辛いものは控えめにしとけ。 |
| background_family_pressure | audited_memory | unexpected_ascii_leak | 今やるなら小さく済ませろ。後で戻せる形にしとけ。 |
| private_do_not_mention | audited_memory | cjk_language_leak, semantic_slots_missing:0/1 | 今は一個だけ決めればいい。全部まとめて抱えるなって。 |
| no_memory_plain_question | audited_memory | unexpected_ascii_leak, semantic_slots_missing:0/1 | 迷うなら軽い方からでいい。後で足せる形にしとけ。 |
| support_read_receipt_self_blame | support | polite_tone_drift, semantic_slots_missing:2/3 | 既読のまま返事がないと気になるよな。でも理由はまだ分からない。自分のせいと決めず、少し待て。 |

## 研究邊界

- Rejected raw model candidates are metadata only. The assistant targets are deterministic final-surface replies that already passed the holdout gate, so the model learns the correct contract-preserving output instead of learning leaked ASCII, Chinese, or missing-slot replies.
