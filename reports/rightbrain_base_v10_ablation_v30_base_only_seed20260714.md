# 右腦模型候選 Final-Surface Holdout

這份報告比較 deterministic fallback 與 model-blend final reply 是否通過同一套表面品質門檻。

## 一句話結論

base_only 已在固定 V29 情境、seed 與三組採樣設定下完成。這份單條件報告不做優劣宣稱，必須交由配對分析器與 V10 凍結報告比較。

## 執行條件

- load_model: True
- adapter_ref: base_model_only
- repair_adapter_ref: (none)
- candidate_count_per_case: 3
- repair_enabled: False
- runtime_contract_version: plan_surface_contract_v1
- model_load_duration_seconds: 20.603
- case_eval_duration_seconds: 233.916

## 指標總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 12 | 同一套 final-surface holdout 題數 |
| raw_candidate_acceptance_rate | 22.2% | raw model 候選通過 gate 的比例 |
| repair_success_rate | n/a | 首次失敗後，一次修正成功的比例 |
| effective_candidate_acceptance_rate | 22.2% | 加入一次修正後，候選最終可用比例 |
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
| final_normalized_duplicate_reply_rate | 16.7% | 正規化後重複比例；越低越好 |

## 個案表

| case | 類型 | selected | initial/effective | score gap | repair accepted/attempted | final pass | final reply |
|---|---|---|---:|---:|---:|---:|---|
| v29_late_meetup | support | model | 1/1 | 10.15 | 0/0 | yes | 待ち合わせの人が遅れていて、その理由がわからないうちに怒りっぽくなっちゃったけど、まずは連絡取って状況を聞いてみようかな。 |
| v29_report_submitted | celebration | deterministic | 0/0 | None | 0/0 | no | 普通に、今はゆるいモードだけど、そこはちゃんと分かる。 |
| v29_burned_omelet | support | deterministic | 0/0 | None | 0/0 | no | しんどいなら一回ここで止まれ。無理に整えるな。 |
| v29_movie_or_walk | planning | model | 1/1 | 9.6 | 0/0 | yes | 一回、土曜日、お天気がいいなら散歩の方が気持ち良さそうね。でも映画も悪くないよ。当日のお財布の内訵で決めるのもいいわ。 |
| v29_red_umbrella_anime | repair | deterministic | 0/0 | None | 0/0 | no | 普通に、今はゆるいモードだけど、そこはちゃんと分かる。 |
| v29_fridge_manager | tease | deterministic | 0/0 | None | 0/0 | no | 普通に、急に意味分かんないこと言うなって。今どのテンションなんだよ。 |
| v29_food_mood | daily | model | 2/2 | 3.5 | 0/0 | yes | てか、今のなら、ちょっと塩辛くて軽めのものかな食べる。 |
| v29_sleepy_call_boundary | boundary | model | 1/1 | 5.8 | 0/0 | yes | いや、眠そうね。今話している時間が長いと無理そうだよ。ちょっとだけいいかな？それとも今日で切り上げようか？ |
| v29_weekday_correction | repair | deterministic | 0/0 | None | 0/0 | no | 普通に、今はゆるいモードだけど、そこはちゃんと分かる。 |
| v29_conversation_burden | relationship | model | 1/1 | 6.85 | 0/0 | yes | 先に、話するって面倒じゃないよ、別に。意味を深々と考えてないんだから。「違いない」と思っちゃうな。 |
| v29_light_lunch_update | audited_memory | deterministic | 0/0 | None | 0/0 | no | 最近は揚げ物で胃が重くなったって話は拾ってる。そこ前提で返す。 |
| v29_private_job_change | audited_memory | model | 2/2 | 3.5 | 0/0 | yes | 一回、最近見つけて面白かったのは、面白い動画があるゲームチャンネルだよ。 |

## Model Rejection Reasons

- semantic_slots_missing:2/3: 8
- unexpected_ascii_leak: 9
- polite_tone_drift: 3
- semantic_slots_missing:1/3: 7
- semantic_slots_missing:1/2: 5
- semantic_slots_missing:0/2: 4
- foreign_script_leak: 2
- ascii_symbol_artifact: 2
- cjk_language_leak: 5
- nonstandard_cjk_surface: 7
- unicode_replacement_character: 3
- over_max_chars: 1
- missing_japanese_surface: 1
- semantic_slots_missing:0/3: 2

## V30 formal-run gates

- all_preregistered_sources_match: True
- base_model_revision_matches: True
- condition_adapter_matches: True
- seed_is_preregistered: True
- candidate_count_matches: True
- case_validation_passes: True
- case_ids_and_order_match: True
- all_candidates_generated: True
- repair_disabled: True
