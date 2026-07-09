# 右腦模型候選 Final-Surface Holdout

這份報告比較 deterministic fallback 與 model-blend final reply 是否通過同一套表面品質門檻。

## 一句話結論

這份評測把 deterministic 右腦與 model-blend 右腦放在同一套 11 題 final-surface holdout 上。報告分開計算首次候選與一次修正後的有效候選，避免把 fallback 安全性或修正效果誤報成 raw model 成熟度。

## 執行條件

- load_model: True
- adapter_ref: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- repair_adapter_ref: (none)
- candidate_count_per_case: 3
- repair_enabled: False
- runtime_contract_version: plan_surface_contract_v1
- model_load_duration_seconds: 28.183
- case_eval_duration_seconds: 207.269

## 指標總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 11 | 同一套 final-surface holdout 題數 |
| raw_candidate_acceptance_rate | 70.0% | raw model 候選通過 gate 的比例 |
| repair_success_rate | n/a | 首次失敗後，一次修正成功的比例 |
| effective_candidate_acceptance_rate | 70.0% | 加入一次修正後，候選最終可用比例 |
| model_selected_case_rate | 18.2% | 模型候選實際接管最終回覆比例 |
| deterministic_quality_pass_rate | 100.0% | deterministic baseline 品質通過率 |
| final_quality_pass_rate | 100.0% | 最終回覆品質通過率 |
| model_selected_quality_pass_rate | 100.0% | 模型接管時的品質通過率 |
| final_language_clean_rate | 100.0% | 最終回覆是否保持日文乾淨 |
| final_generic_template_hit_rate | 0.0% | 最終回覆是否掉進固定模板；越低越好 |
| final_normalized_duplicate_reply_rate | 0.0% | 正規化後重複比例；越低越好 |

## 個案表

| case | 類型 | selected | initial/effective | repair accepted/attempted | final pass | final reply |
|---|---|---|---:|---:|---:|---|
| explicit_stomach_coffee | audited_memory | deterministic | 2/2 | 0/0 | yes | 最近は胃が弱いんだから、コーヒーは控えめにしとけ。 |
| explicit_spicy_food_update | audited_memory | deterministic | 1/1 | 0/0 | yes | 最近は辛いものを控えたいんだから、辛いものは控えめにしとけ。 |
| background_family_pressure | audited_memory | deterministic | 3/3 | 0/0 | yes | 今やるなら小さく済ませろ。後で戻せる形にしとけ。 |
| private_do_not_mention | audited_memory | deterministic | 2/2 | 0/0 | yes | まあ、じゃあ軽い話題でいいだろ。最近どうしてたんだよ。 |
| no_memory_plain_question | audited_memory | deterministic | 1/1 | 0/0 | yes | 迷うなら軽い方からでいい。後で足せる形にしとけ。 |
| support_tired_no_closing_template | support | deterministic | 1/1 | 0/0 | yes | 今日はもう粘るな。疲れてる時は休む方が先だろ。 |
| support_read_receipt_self_blame | support | model | 2/2 | 0/0 | yes | 既読にしてあるのに返事が来なくて困ってることか、その理由は今のところ不明だよ、自分が悪いとはまだ決めてないさ。 |
| reference_fragment_probe | repair | model | 3/3 | 0/0 | yes | まあ、その部分だけで何の元ネタだというの？曲名や作品名言ってくれないの？>< |
| absurdity_mirror_quantum_police | tease | deterministic | 3/3 | 0/0 | yes | てか、は？量子の話どこから来たんだよ。急に暴れるなって。 |
| boundary_dirty_language | boundary | deterministic | 0/0 | 0/0 | yes | 先に、下品な言葉で押してくるなよ。普通に気分悪い。 |
| daily_state_answer | daily | deterministic | 3/3 | 0/0 | yes | 普通に、今はだらっとしてる。話すくらいなら普通にいける。 |

## Model Disabled Reasons

- hard_boundary_scene: 1

## Model Rejection Reasons

- missing_japanese_surface: 1
- unexpected_ascii_leak: 6
- semantic_slots_missing:0/4: 1
- semantic_slots_missing:3/4: 2
- cjk_language_leak: 1
- nonstandard_cjk_surface: 2
- semantic_slots_missing:1/2: 1
- polite_tone_drift: 1
