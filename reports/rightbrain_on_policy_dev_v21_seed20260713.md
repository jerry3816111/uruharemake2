# 右腦模型候選 Final-Surface Holdout

這份報告比較 deterministic fallback 與 model-blend final reply 是否通過同一套表面品質門檻。

## 一句話結論

這份報告只記錄 V10 在 16 個新開發情境中的真實候選分布；後續 preference dataset 只會使用同一批 V10 產生、且通過完整品質檢查的 chosen，搭配同策略產生的 rejected。

## 執行條件

- load_model: True
- adapter_ref: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- repair_adapter_ref: (none)
- candidate_count_per_case: 3
- repair_enabled: False
- runtime_contract_version: plan_surface_contract_v1
- model_load_duration_seconds: 24.968
- case_eval_duration_seconds: 304.128

## 指標總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 16 | 同一套 final-surface holdout 題數 |
| raw_candidate_acceptance_rate | 43.8% | raw model 候選通過 gate 的比例 |
| repair_success_rate | n/a | 首次失敗後，一次修正成功的比例 |
| effective_candidate_acceptance_rate | 43.8% | 加入一次修正後，候選最終可用比例 |
| model_selected_case_rate | 50.0% | 模型候選實際接管最終回覆比例 |
| model_candidate_available_not_selected_rate | 25.0% | 有可用模型候選但仍保留 deterministic 的比例 |
| model_available_not_selected_avg_score_gap | 0.0175 | 未接管時，最佳模型分數 - deterministic 分數；負數代表 deterministic 較強 |
| deterministic_quality_pass_rate | 31.2% | deterministic baseline 品質通過率 |
| final_quality_pass_rate | 68.8% | 最終回覆品質通過率 |
| model_selected_quality_pass_rate | 87.5% | 模型接管時的品質通過率 |
| final_language_clean_rate | 100.0% | 最終回覆是否保持日文乾淨 |
| final_awkward_surface_free_rate | 100.0% | 最終回覆是否沒有已稽核的不自然或照護者式句型 |
| final_response_plan_leak_free_rate | 100.0% | 最終回覆是否沒有把左腦回覆方針直接說給使用者 |
| final_generic_template_hit_rate | 0.0% | 最終回覆是否掉進固定模板；越低越好 |
| final_normalized_duplicate_reply_rate | 0.0% | 正規化後重複比例；越低越好 |

## 個案表

| case | 類型 | selected | initial/effective | score gap | repair accepted/attempted | final pass | final reply |
|---|---|---|---:|---:|---:|---:|---|
| v21_project_reply_delay | support | deterministic | 0/0 | None | 0/0 | no | グループが静かだと不安だよな。理由は分からないし、自分のせいと決めつけず少し待て。 |
| v21_invitation_reply_delay | support | deterministic | 1/1 | 0.0 | 0/0 | yes | 返事がないと不安になるよな。理由は分からない。自分が悪いと決めつけず、少し置け。 |
| v21_sleepy_assignment | support | model | 3/3 | 4.0 | 0/0 | yes | 強烈な眠気が来ているんだよね。今無理しないでいいよ、一休みするといいと思うな。 |
| v21_headache_work | support | model | 1/1 | 6.2 | 0/0 | yes | 頭痛だから、今 **)&*休んだりするのもいいじゃん。 |
| v21_song_fragment | repair | model | 1/1 | 3.5 | 0/0 | no | 先に、あ、断片の歌詞じゃわからないよ。曲名に近い言葉使えればいいね。 |
| v21_game_quote_fragment | repair | deterministic | 0/0 | None | 0/0 | no | まあ、朝でまだ頭ゆるいけど、その話なら返せる。 |
| v21_recent_activity | daily | deterministic | 2/2 | 0.0 | 0/0 | yes | いや、今はだらだらしてる。まだ本気出してない。 |
| v21_current_mood | daily | model | 2/2 | 4.3 | 0/0 | yes | 一回、今日は気分なくなって、ちょっとダルいなあ。 |
| v21_toaster_mayor | tease | deterministic | 2/2 | 0.07 | 0/0 | yes | はいはい、急に意味分かんないこと言うなって。今どのテンションなんだよ。 |
| v21_cat_moon_tax | tease | model | 1/1 | 1.7 | 0/0 | yes | まあ、その冗談、もうちょっと説明できる？何の関係があるんだ、「猫」と「月」そして「税金」って…何か狙いがあって？” |
| v21_weather_plan | planning | model | 1/1 | 7.3 | 0/0 | yes | 先に、天気が分からんなら、変わりやすい軽めの予定にしとこうね。 |
| v21_reservation_wait | planning | model | 3/3 | 6.85 | 0/0 | yes | 一回、まだ返事が来ないなら、仮の予約をしててもいいよ。ちょっとだけ待っても大丈夫だね。 |
| v21_sleep_schedule_game | audited_memory | deterministic | 0/0 | None | 0/0 | no | 最近は睡眠を整えたいって話は拾ってる。そこ前提で返す。 |
| v21_dairy_icecream | audited_memory | deterministic | 0/0 | None | 0/0 | no | さっきの乳製品でお腹が重くなる。の流れまだ残ってるな。で、今はどうしたんだよ。 |
| v21_background_deadline_pressure | audited_memory | model | 2/2 | 3.1 | 0/0 | yes | まあ、一つ始めようかな。少しづつ進めていこうね。 |
| v21_private_relationship_topic | audited_memory | deterministic | 2/2 | 0.0 | 0/0 | yes | 普通に、じゃあ軽い話題でいいだろ。最近どうしてたんだよ。 |

## Model Rejection Reasons

- polite_tone_drift: 8
- semantic_slots_missing:2/4: 2
- semantic_slots_missing:3/4: 3
- ascii_symbol_artifact: 2
- unexpected_ascii_leak: 11
- semantic_slots_missing:1/2: 8
- cjk_language_leak: 3
- nonstandard_cjk_surface: 3
- semantic_slots_missing:0/2: 2
- foreign_script_leak: 3
