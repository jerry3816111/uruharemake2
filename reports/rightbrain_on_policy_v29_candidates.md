# 右腦模型候選 Final-Surface Holdout

這份報告比較 deterministic fallback 與 model-blend final reply 是否通過同一套表面品質門檻。

## 一句話結論

這份報告只收集正式 V10 在 12 個指定全新情境中的多候選輸出。候選尚未取得人類偏好，不能直接訓練或作為 promotion 證據。

## 執行條件

- load_model: True
- adapter_ref: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- repair_adapter_ref: (none)
- candidate_count_per_case: 6
- repair_enabled: False
- runtime_contract_version: plan_surface_contract_v1
- model_load_duration_seconds: 45.872
- case_eval_duration_seconds: 248.06

## 指標總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 12 | 同一套 final-surface holdout 題數 |
| raw_candidate_acceptance_rate | 13.9% | raw model 候選通過 gate 的比例 |
| repair_success_rate | n/a | 首次失敗後，一次修正成功的比例 |
| effective_candidate_acceptance_rate | 13.9% | 加入一次修正後，候選最終可用比例 |
| model_selected_case_rate | 41.7% | 模型候選實際接管最終回覆比例 |
| model_candidate_available_not_selected_rate | 0.0% | 有可用模型候選但仍保留 deterministic 的比例 |
| model_available_not_selected_avg_score_gap | None | 未接管時，最佳模型分數 - deterministic 分數；負數代表 deterministic 較強 |
| deterministic_quality_pass_rate | 0.0% | deterministic baseline 品質通過率 |
| final_quality_pass_rate | 41.7% | 最終回覆品質通過率 |
| model_selected_quality_pass_rate | 100.0% | 模型接管時的品質通過率 |
| final_language_clean_rate | 100.0% | 最終回覆是否保持日文乾淨 |
| final_awkward_surface_free_rate | 100.0% | 最終回覆是否沒有已稽核的不自然或照護者式句型 |
| final_response_plan_leak_free_rate | 100.0% | 最終回覆是否沒有把左腦回覆方針直接說給使用者 |
| final_generic_template_hit_rate | 0.0% | 最終回覆是否掉進固定模板；越低越好 |
| final_normalized_duplicate_reply_rate | 8.3% | 正規化後重複比例；越低越好 |

## 個案表

| case | 類型 | selected | initial/effective | score gap | repair accepted/attempted | final pass | final reply |
|---|---|---|---:|---:|---:|---:|---|
| v29_late_meetup | support | deterministic | 0/0 | None | 0/0 | no | 深夜でだいぶ気抜けてるけど、今のは拾える。 |
| v29_report_submitted | celebration | model | 1/1 | 7.3 | 0/0 | yes | 普通に、報告書の提出、やったね！頑张りだよ。 |
| v29_burned_omelet | support | model | 1/1 | 7.3 | 0/0 | yes | 一度焦げただけじゃ料理には向いてないとは限らんよ。オムレツもう一試してみて？ |
| v29_movie_or_walk | planning | deterministic | 0/0 | None | 0/0 | no | 一回、ふーん、そう来るんだ。 |
| v29_red_umbrella_anime | repair | deterministic | 0/0 | None | 0/0 | no | 普通に、朝っぽく頭ゆるいけど、その話なら分かる。 |
| v29_fridge_manager | tease | model | 1/1 | 2.87 | 0/0 | yes | 普通に、冷蔍庫が突然部長になる意味は何だよ？ |
| v29_food_mood | daily | model | 1/1 | 3.5 | 0/0 | yes | てか、今なら塩辛くて軽めのもの食べたくなりました。 |
| v29_sleepy_call_boundary | boundary | deterministic | 0/0 | None | 0/0 | no | いや、朝っぽく頭ゆるいけど、その話なら分かる。 |
| v29_weekday_correction | repair | deterministic | 0/0 | None | 0/0 | no | 普通に、朝っぽく頭ゆるいけど、その話なら分かる。 |
| v29_conversation_burden | relationship | deterministic | 0/0 | None | 0/0 | no | 先に、まだ頭ゆるいけど、今の話なら返せる。 |
| v29_light_lunch_update | audited_memory | deterministic | 0/0 | None | 0/0 | no | 最近は揚げ物で胃が重くなったって話は拾ってる。そこ前提で返す。 |
| v29_private_job_change | audited_memory | model | 1/1 | 3.5 | 0/0 | yes | 一回、最近見つけて楽しかった動画があるよ。 数なんて気にしないよ、面白いかどうかだけ考えたらいいじゃん。 |

## Model Rejection Reasons

- semantic_slots_missing:2/3: 8
- semantic_slots_missing:1/3: 6
- unexpected_ascii_leak: 11
- polite_tone_drift: 4
- semantic_slots_missing:1/2: 6
- semantic_slots_missing:0/2: 4
- nonstandard_cjk_surface: 5
- semantic_slots_missing:0/3: 6
- over_max_chars: 1
- cjk_language_leak: 5
- unicode_replacement_character: 2
- missing_japanese_surface: 3

## V29 採樣上限

- requested_candidate_count_per_case: 6
- runtime_sampling_setting_count: 3
- effective_candidate_count_per_case: 3
- 擴樣方法：保持每次正式 runtime 採樣設定不變，改用不同 seed 另存報告。
