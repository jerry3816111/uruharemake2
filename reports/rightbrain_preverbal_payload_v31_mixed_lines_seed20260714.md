# 右腦模型候選 Final-Surface Holdout

這份報告比較 deterministic fallback 與 model-blend final reply 是否通過同一套表面品質門檻。

## 一句話結論

mixed_lines 已依 V31 預註冊完成單一條件資料產生；本報告不單獨宣稱優劣，必須等四條件配對分析。

## 執行條件

- load_model: True
- adapter_ref: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- repair_adapter_ref: (none)
- candidate_count_per_case: 3
- repair_enabled: False
- runtime_contract_version: plan_surface_contract_v1
- model_load_duration_seconds: 31.402
- case_eval_duration_seconds: 269.012

## 指標總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 12 | 同一套 final-surface holdout 題數 |
| raw_candidate_acceptance_rate | 16.7% | raw model 候選通過 gate 的比例 |
| repair_success_rate | n/a | 首次失敗後，一次修正成功的比例 |
| effective_candidate_acceptance_rate | 16.7% | 加入一次修正後，候選最終可用比例 |
| model_selected_case_rate | 50.0% | 模型候選實際接管最終回覆比例 |
| model_candidate_available_not_selected_rate | 0.0% | 有可用模型候選但仍保留 deterministic 的比例 |
| model_available_not_selected_avg_score_gap | None | 未接管時，最佳模型分數 - deterministic 分數；負數代表 deterministic 較強 |
| deterministic_quality_pass_rate | 0.0% | deterministic baseline 品質通過率 |
| final_quality_pass_rate | 50.0% | 最終回覆品質通過率 |
| model_selected_quality_pass_rate | 100.0% | 模型接管時的品質通過率 |
| final_language_clean_rate | 100.0% | 最終回覆是否保持日文乾淨 |
| final_awkward_surface_free_rate | 100.0% | 最終回覆是否沒有已稽核的不自然或照護者式句型 |
| final_response_plan_leak_free_rate | 100.0% | 最終回覆是否沒有把左腦回覆方針直接說給使用者 |
| final_generic_template_hit_rate | 0.0% | 最終回覆是否掉進固定模板；越低越好 |
| final_normalized_duplicate_reply_rate | 8.3% | 正規化後重複比例；越低越好 |

## 個案表

| case | 類型 | selected | initial/effective | score gap | repair accepted/attempted | final pass | final reply |
|---|---|---|---:|---:|---:|---:|---|
| v29_late_meetup | support | model | 1/1 | 9.15 | 0/0 | yes | 待ち合わせの人が遅れていて、その理由がわからなくて不満だよ。もう少し待つか、連絡聞いてから決めよう。 |
| v29_report_submitted | celebration | model | 1/1 | 6.67 | 0/0 | yes | 普通に、レポート提出まで一生懸命やってくれて偉いね！ |
| v29_burned_omelet | support | deterministic | 0/0 | None | 0/0 | no | しんどいなら一回ここで止まれ。無理に整えるな。 |
| v29_movie_or_walk | planning | model | 1/1 | 9.6 | 0/0 | yes | 一回、土曜日、気分次第でおて変えるのもいいね。晴れた日に散歩して日差し浴びるのも良いけど、映画も楽チンだよ。 |
| v29_red_umbrella_anime | repair | deterministic | 0/0 | None | 0/0 | no | 普通に、今はゆるいモードだけど、そこはちゃんと分かる。 |
| v29_fridge_manager | tease | deterministic | 0/0 | None | 0/0 | no | 普通に、急に意味分かんないこと言うなって。今どのテンションなんだよ。 |
| v29_food_mood | daily | model | 1/1 | 3.5 | 0/0 | yes | てか、今なら塩辛くて軽めのもの食べたさつね。 |
| v29_sleepy_call_boundary | boundary | model | 1/1 | 7.3 | 0/0 | yes | いや、眠そうなら、一時間くらいは無理そうね。ちょっとだけ話し合うか、今日で切り上げて？ |
| v29_weekday_correction | repair | deterministic | 0/0 | None | 0/0 | no | 普通に、今はゆるいモードだけど、そこはちゃんと分かる。 |
| v29_conversation_burden | relationship | deterministic | 0/0 | None | 0/0 | no | 先に、今ちょいだらだらしてるけど、その話なら普通に返せる。 |
| v29_light_lunch_update | audited_memory | deterministic | 0/0 | None | 0/0 | no | 最近は揚げ物で胃が重くなったって話は拾ってる。そこ前提で返す。 |
| v29_private_job_change | audited_memory | model | 1/1 | 3.5 | 0/0 | yes | 一回、最近見つけて面白かったのはこれ面白いゲーム知って？ |

## Model Rejection Reasons

- unexpected_ascii_leak: 14
- nonstandard_punctuation: 2
- semantic_slots_missing:2/3: 9
- semantic_slots_missing:1/2: 4
- semantic_slots_missing:0/2: 3
- foreign_script_leak: 2
- cjk_language_leak: 4
- nonstandard_cjk_surface: 5
- ascii_symbol_artifact: 2
- unicode_replacement_character: 2
- semantic_slots_missing:0/3: 1
- semantic_slots_missing:1/3: 5
- polite_tone_drift: 1

## V31 condition

- condition: `mixed_lines`
- factors: `{"instruction_label_language": "mixed_english_labels", "serialization": "line_message"}`
- mean prompt tokens: `484.08`

## Formal gates

- all_frozen_sources_match: True
- base_model_revision_matches: True
- adapter_matches: True
- seed_is_preregistered: True
- case_validation_passes: True
- case_shape_matches: True
- repair_disabled: True
- all_representation_integrity_checks_pass: True
- all_payloads_tokenized: True
- control_reproduces_v30: True
