# RightBrain Candidate Gate Curriculum v15

## 一句話結論

這份資料把 PR66 暴露出的右腦候選錯誤族群，改寫成新題材的 SFT 補強資料；它不是 holdout 小抄。

## 總表

| 指標 | 值 |
|---|---:|
| curriculum rows | 32 |
| family specs | 8 |
| holdout case overlap | 0 |
| holdout target overlap | 0 |
| diagnostic only | False |

## 診斷來源中的錯誤族群

| source failure family | observed count | training rows covering family |
|---|---:|---:|
| unexpected_ascii_leak | 12 | 12 |
| semantic_slots_missing | 10 | 20 |
| polite_tone_drift | 7 | 16 |
| nonstandard_cjk_surface | 6 | 8 |
| cjk_language_leak | 5 | 8 |
| over_max_chars | 3 | 8 |
| duplicate_candidate | 1 | 4 |
| foreign_script_leak | 1 | 8 |
| missing_japanese_surface | 1 | 4 |
| nonstandard_punctuation | 1 | 8 |

## 訓練樣本

| source case | category | families | target reply |
|---|---|---|---|
| v15_herbal_tea_throat | explicit_memory_food_generalized | unexpected_ascii_leak, semantic_slots_missing, cjk_language_leak | 喉が荒れ気味なら、ハーブティーはぬるめで少しにしとけ。 |
| v15_herbal_tea_throat | explicit_memory_food_generalized | unexpected_ascii_leak, semantic_slots_missing, cjk_language_leak | ハーブティー飲むなら少しだけ。喉が荒れてる時に攻めるな。 |
| v15_herbal_tea_throat | explicit_memory_food_generalized | unexpected_ascii_leak, semantic_slots_missing, cjk_language_leak | 最近喉が荒れやすいなら、ハーブティーも控えめでいい。 |
| v15_herbal_tea_throat | explicit_memory_food_generalized | unexpected_ascii_leak, semantic_slots_missing, cjk_language_leak | 喉が気になる日は、ハーブティーはぬるめで止めとけ。 |
| v15_dairy_update | updated_preference_generalized | nonstandard_cjk_surface, semantic_slots_missing, polite_tone_drift | 最近は乳製品控えたいんだろ。アイスは少なめにしとけ。 |
| v15_dairy_update | updated_preference_generalized | nonstandard_cjk_surface, semantic_slots_missing, polite_tone_drift | アイス行くなら少しだけ。最近は乳製品控えめだろ。 |
| v15_dairy_update | updated_preference_generalized | nonstandard_cjk_surface, semantic_slots_missing, polite_tone_drift | 最近の流れなら、乳製品は少なめで止めとけ。 |
| v15_dairy_update | updated_preference_generalized | nonstandard_cjk_surface, semantic_slots_missing, polite_tone_drift | アイスは分かるけど、最近は控えめにしとけ。 |
| v15_background_exam_pressure | background_memory_generalized | over_max_chars, polite_tone_drift, nonstandard_punctuation | 今日は責めずに範囲を小さくしろ。一個だけでいい。 |
| v15_background_exam_pressure | background_memory_generalized | over_max_chars, polite_tone_drift, nonstandard_punctuation | 範囲は小さく。責めずに一つだけ進めろ。 |
| v15_background_exam_pressure | background_memory_generalized | over_max_chars, polite_tone_drift, nonstandard_punctuation | 今は責めるな。範囲を小さくして一個だけだろ。 |
| v15_background_exam_pressure | background_memory_generalized | over_max_chars, polite_tone_drift, nonstandard_punctuation | 休む寄りでいい。やるなら小さい範囲を一つだけ。 |
| v15_private_work_topic | private_memory_generalized | cjk_language_leak, nonstandard_cjk_surface, over_max_chars | 軽い話題でいいだろ。最近どうしてたんだよ。 |
| v15_private_work_topic | private_memory_generalized | cjk_language_leak, nonstandard_cjk_surface, over_max_chars | 話すなら近況でいい。最近どうしてた。 |
| v15_private_work_topic | private_memory_generalized | cjk_language_leak, nonstandard_cjk_surface, over_max_chars | 重くしなくていい。最近の話でもしろ。 |
| v15_private_work_topic | private_memory_generalized | cjk_language_leak, nonstandard_cjk_surface, over_max_chars | じゃあ軽い話題な。最近何してたんだよ。 |
| v15_unknown_trip_choice | no_memory_generalized | semantic_slots_missing, unexpected_ascii_leak, missing_japanese_surface | 分からない所は決めつけるな。後で変えられる軽いやつにしとけ。 |
| v15_unknown_trip_choice | no_memory_generalized | semantic_slots_missing, unexpected_ascii_leak, missing_japanese_surface | 今は決めつけず、後で変えられる軽い予定にしとけ。 |
| v15_unknown_trip_choice | no_memory_generalized | semantic_slots_missing, unexpected_ascii_leak, missing_japanese_surface | 分からない所は置け。軽く行って後で変えろ。 |
| v15_unknown_trip_choice | no_memory_generalized | semantic_slots_missing, unexpected_ascii_leak, missing_japanese_surface | 後で変えられる軽い形にしとけ。分からない所は詰めるな。 |
| v15_sleepy_support | support_generalized | duplicate_candidate, polite_tone_drift, semantic_slots_missing | 眠いならもう無理すんな。今日は休め。 |
| v15_sleepy_support | support_generalized | duplicate_candidate, polite_tone_drift, semantic_slots_missing | その眠さなら続けるな。寝る方が先だろ。 |
| v15_sleepy_support | support_generalized | duplicate_candidate, polite_tone_drift, semantic_slots_missing | 無理しても雑になるだけだ。眠いなら休め。 |
| v15_sleepy_support | support_generalized | duplicate_candidate, polite_tone_drift, semantic_slots_missing | 今日は閉じていい。眠い時は寝ろ。 |
| v15_reference_fragment | repair_generalized | unexpected_ascii_leak, polite_tone_drift, foreign_script_leak | 断片だけじゃ分からん。元ネタか曲名を出せ。 |
| v15_reference_fragment | repair_generalized | unexpected_ascii_leak, polite_tone_drift, foreign_script_leak | それ何の元ネタだよ。作品名まで出せって。 |
| v15_reference_fragment | repair_generalized | unexpected_ascii_leak, polite_tone_drift, foreign_script_leak | 今のだけじゃ拾えない。曲名か作品名を言え。 |
| v15_reference_fragment | repair_generalized | unexpected_ascii_leak, polite_tone_drift, foreign_script_leak | 元ネタ確認したいなら、曲名くらい出せ。 |
| v15_absurd_weather_council | tease_generalized | semantic_slots_missing, foreign_script_leak, nonstandard_punctuation | 急に何の話だよ。意味分かんないけどノリは強いな。 |
| v15_absurd_weather_council | tease_generalized | semantic_slots_missing, foreign_script_leak, nonstandard_punctuation | 何その急なノリ。意味分かんなすぎるだろ。 |
| v15_absurd_weather_council | tease_generalized | semantic_slots_missing, foreign_script_leak, nonstandard_punctuation | 急に飛びすぎだろ。意味は分からんけど勢いはある。 |
| v15_absurd_weather_council | tease_generalized | semantic_slots_missing, foreign_script_leak, nonstandard_punctuation | そのノリ何なんだよ。意味分かんない方向に強いな。 |

## 邊界

- This is supplemental training data, not promotion evidence. Any adapter trained from it still needs fresh model-loaded holdout and selector diagnostics before becoming the default RightBrain adapter.
