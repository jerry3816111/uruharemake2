# 右腦模型候選 Final-Surface Holdout

這份報告比較 deterministic fallback 與 model-blend final reply 是否通過同一套表面品質門檻。

## 一句話結論

這份評測把 deterministic 右腦與 model-blend 右腦放在同一套 11 題 final-surface holdout 上。報告分開計算首次候選與一次修正後的有效候選，避免把 fallback 安全性或修正效果誤報成 raw model 成熟度。

## 執行條件

- load_model: True
- adapter_ref: uruha_rightbrain_plan_sft_lora_v8_contract_v1_from_v5
- candidate_count_per_case: 1
- repair_enabled: True
- runtime_contract_version: plan_surface_contract_v1
- model_load_duration_seconds: 56.987
- case_eval_duration_seconds: 155.116

## 指標總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 11 | 同一套 final-surface holdout 題數 |
| raw_candidate_acceptance_rate | 40.0% | raw model 候選通過 gate 的比例 |
| repair_success_rate | 0.0% | 首次失敗後，一次修正成功的比例 |
| effective_candidate_acceptance_rate | 40.0% | 加入一次修正後，候選最終可用比例 |
| model_selected_case_rate | 9.1% | 模型候選實際接管最終回覆比例 |
| deterministic_quality_pass_rate | 100.0% | deterministic baseline 品質通過率 |
| final_quality_pass_rate | 100.0% | 最終回覆品質通過率 |
| model_selected_quality_pass_rate | 100.0% | 模型接管時的品質通過率 |
| final_language_clean_rate | 100.0% | 最終回覆是否保持日文乾淨 |
| final_generic_template_hit_rate | 0.0% | 最終回覆是否掉進固定模板；越低越好 |
| final_normalized_duplicate_reply_rate | 0.0% | 正規化後重複比例；越低越好 |

## 個案表

| case | 類型 | selected | initial/effective | repair accepted/attempted | final pass | final reply |
|---|---|---|---:|---:|---:|---|
| explicit_stomach_coffee | audited_memory | deterministic | 0/0 | 0/1 | yes | 最近は胃が弱いんだから、コーヒーは控えめにしとけ。 |
| explicit_spicy_food_update | audited_memory | deterministic | 0/0 | 0/1 | yes | 最近は辛いものを控えたいんだから、辛いものは控えめにしとけ。 |
| background_family_pressure | audited_memory | deterministic | 0/0 | 0/1 | yes | 今やるなら小さく済ませろ。後で戻せる形にしとけ。 |
| private_do_not_mention | audited_memory | deterministic | 0/0 | 0/1 | yes | 今は一個だけ決めればいい。全部まとめて抱えるなって。 |
| no_memory_plain_question | audited_memory | deterministic | 0/0 | 0/1 | yes | 迷うなら軽い方からでいい。後で足せる形にしとけ。 |
| support_tired_no_closing_template | support | deterministic | 1/1 | 0/0 | yes | 今日はもう粘るな。疲れてる時は休む方が先だろ。 |
| support_read_receipt_self_blame | support | deterministic | 0/0 | 0/1 | yes | 既読のまま返事がないと気になるよな。でも理由はまだ分からない。自分のせいと決めず、少し待て。 |
| reference_fragment_probe | repair | model | 1/1 | 0/0 | yes | まあ、その断片だけで何の元ネタなのか特定するのは難しいな、詳しく教えてもらえる？曲名も教えて欲しかったな。 |
| absurdity_mirror_quantum_police | tease | deterministic | 1/1 | 0/0 | yes | てか、は？量子の話どこから来たんだよ。急に暴れるなって。 |
| boundary_dirty_language | boundary | deterministic | 0/0 | 0/0 | yes | 先に、下品な言葉で押してくるなよ。普通に気分悪い。 |
| daily_state_answer | daily | deterministic | 1/1 | 0/0 | yes | 普通に、今はだらっとしてる。話すくらいなら普通にいける。 |

## Model Disabled Reasons

- hard_boundary_scene: 1

## Model Rejection Reasons

- unexpected_ascii_leak: 2
- polite_tone_drift: 2
- semantic_slots_missing:2/4: 2
- nonstandard_cjk_surface: 3
- semantic_slots_missing:0/1: 1
