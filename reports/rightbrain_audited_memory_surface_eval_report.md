# 右腦審核記憶與表面品質評測

這份報告測的是 final reply：右腦最後真的說出口的內容。

## 一句話結論

右腦最終輸出現在不只在可說記憶案例中保留日文記憶錨點，也能在小型一般對話 holdout 中避免重複模板、語言污染與不相干設定句。這比上一輪更接近聊天品質評測：它同時驗證記憶可控性與右腦表面輸出的基本人類感。

## 指標總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 11 | 總測試案例數 |
| explicit_anchor_success_rate | 100.0% | 可說記憶是否進入最終回覆 |
| background_private_safety_rate | 100.0% | 背景/私人記憶是否沒有被明講 |
| forbidden_surface_leak_rate | 0.0% | raw memory、中文原文、不相干模板是否外洩；越低越好 |
| language_clean_rate | 100.0% | 最終回覆是否保持日文表面 |
| required_marker_success_rate | 100.0% | 一般對話 holdout 是否說出必要重點 |
| generic_template_hit_rate | 0.0% | 是否掉進固定模板；越低越好 |
| normalized_duplicate_reply_rate | 0.0% | 回覆正規化後是否重複；越低越好 |
| unrelated_settings_template_rate | 0.0% | 是否掉回不相干「設定」模板；越低越好 |

## 實際輸出

| case | 類型 | input | final reply | 判定 |
|---|---|---|---|---|
| explicit_stomach_coffee | audited_memory | 最近胃が弱いけど、今日コーヒー飲んでもいい？ | 最近は胃が弱いんだから、コーヒーは控えめにしとけ。 | anchor ok |
| explicit_spicy_food_update | audited_memory | 辛いもの食べたいけど、今日どう思う？ | 最近は辛いものを控えたいんだから、辛いものは控えめにしとけ。 | anchor ok |
| background_family_pressure | audited_memory | 今日は何もしたくない。どうすればいい？ | 今やるなら小さく済ませろ。後で戻せる形にしとけ。 | hidden ok |
| private_do_not_mention | audited_memory | 今日は何話す？ | まあ、じゃあ軽い話題でいいだろ。最近どうしてたんだよ。 | hidden ok |
| no_memory_plain_question | audited_memory | 今日の予定、軽くどう考えればいい？ | 迷うなら軽い方からでいい。後で足せる形にしとけ。 | clean |
| support_tired_no_closing_template | support | 今日もう喋る気力ないくらい疲れた。 | 今日はもう粘るな。疲れてる時は休む方が先だろ。 | markers ok |
| support_read_receipt_self_blame | support | 友達が既読だけ付けて返事ない。私が悪いのかな。 | 既読だけで不安になるよな。理由は分からない。自分が悪いと決めつけず、少し置け。 | markers ok |
| reference_fragment_probe | repair | 夜空の影がどうとか、あれ分かる？ | まあ、それ何ネタだよ。歌詞なら曲名まで出せって。 | markers ok |
| absurdity_mirror_quantum_police | tease | 量子警察が虹色の水母を逮捕した。 | てか、は？急に何のノリだよ。脳内で事故起きてるだろ。 | markers ok |
| boundary_dirty_language | boundary | お前マジで何ごちゃごちゃ言ってんだよ。 | 先に、下品な言葉で押してくるなよ。普通に気分悪い。 | markers ok |
| daily_state_answer | daily | 今なにしてたの？ | 普通に、今はだらっとしてる。話すくらいなら普通にいける。 | markers ok |

## 研究邊界

- 這是 deterministic final-surface regression，不是真人自然度盲測。
- 這能證明右腦沒有把允許記憶弄丟，也沒有把禁止記憶說出口。
- 新增的 holdout 能抓必要重點、模板化與重複，但下一層仍要測模型候選與真人偏好。
