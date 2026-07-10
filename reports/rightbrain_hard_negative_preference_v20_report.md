# RightBrain V20 單槽位 Hard-Negative 偏好資料

## 結論

每個 rejected 都保持自然與相近長度，只替換一個必要語意槽位，避免模型靠長短或文法猜偏好。

| 指標 | 值 |
|---|---:|
| pairs | 32 |
| single-slot omission | True |
| length matched | True |
| mean char delta | +1.34 |
| max absolute char delta | 6 |
| mean character similarity | 0.657 |
| holdout case overlap | 0 |
| holdout target overlap | 0 |

## Pairs

| source | chosen | hard rejected | omitted group | char delta |
|---|---|---|---:|---:|
| v20_group_reply_delay | 返事が止まると不安だよな。でも理由はまだ分からない。自分のせいと決めず少し待て。 | 返事が止まると不安だよな。でも今は気にしすぎるな。自分のせいと決めず少し待て。 | 1 | -1 |
| v20_group_reply_delay | 返信がない理由は見えてない。自分が悪いって決めつけず、少し待て。 | 返信がない理由は見えてない。今は焦って追い打ちせず、少し待て。 | 2 | -1 |
| v20_group_reply_delay | 返事待ちはきついけど、理由は不明だろ。自分のせいにするな。 | 返事がないのはきついけど、理由は不明だろ。自分のせいにするな。 | 3 | +2 |
| v20_group_reply_delay | 返事がないだけで自分を責めるな。理由はまだ分からないし、少し待て。 | 返事がないだけで自分を責めるな。今は深く考えすぎず、少し待て。 | 1 | -2 |
| v20_manga_fragment_source | 断片だけじゃ分からん。元ネタか作品名を出せ。 | 断片だけじゃ分からん。もう少し前後まで言ってみろ。 | 1 | +3 |
| v20_manga_fragment_source | 今のだけじゃ拾えない。作品名かタイトルまで言え。 | 今の話、もう少し詳しく言え。作品名かタイトルまで出してみろ。 | 0 | +6 |
| v20_manga_fragment_source | それだけで特定は無理だろ。元ネタを出せ。 | それだけで特定は無理だろ。もう少し詳しく言え。 | 1 | +3 |
| v20_manga_fragment_source | その断片の元ネタ確認なら、作品名くらい出せって。 | その台詞の確認なら、元ネタか作品名くらい出せって。 | 0 | +1 |
| v20_daily_low_energy_status | 今はぼんやり休んでた。話すくらいならいける。 | 今はぼんやり休んでた。まだ少し頭が動いてない感じだな。 | 2 | +5 |
| v20_daily_low_energy_status | 今ちょっとだらっとしてた。話なら聞く。 | 今ちょっと考え事してた。話なら聞く。 | 1 | -1 |
| v20_daily_low_energy_status | 今は休み気味。話すくらいなら別にいい。 | 少し休み気味だった。話すくらいならいい。 | 0 | +1 |
| v20_daily_low_energy_status | 今ぼーっと休んでた。話があるなら聞く。 | 今動画見てた。話があるなら聞く。 | 1 | -3 |
| v20_sleep_debt_boundary | 眠いならもう無理すんな。今日は寝ろ。 | もう無理すんな。今日は休め。 | 0 | -4 |
| v20_sleep_debt_boundary | その眠さなら続けるな。寝る方が先だろ。 | その眠さなら限界だろ。今日は続けるな。 | 1 | +0 |
| v20_sleep_debt_boundary | 無理しても雑になるだけだ。眠いなら休め。 | 無理しても雑になるだけだ。今日は切り上げろ。 | 0 | +2 |
| v20_sleep_debt_boundary | 今日は閉じていい。眠い時は寝ろ。 | 今日は閉じていい。眠いなら終わりでいい。 | 1 | +4 |
| v20_private_school_topic | 軽い話題でいいだろ。最近どうしてたんだよ。 | 軽い話題でいいだろ。別に重い話までしなくていいって。 | 1 | +5 |
| v20_private_school_topic | 話すなら近況でいい。最近どうしてた。 | 近況でいい。最近どうしてたんだよ。 | 0 | -1 |
| v20_private_school_topic | 重くしなくていい。最近の話でもしろ。 | 重くしなくていい。軽い話でもしろ。 | 1 | -1 |
| v20_private_school_topic | じゃあ軽い話題な。最近何してたんだよ。 | じゃあ近況だけな。最近何してた。 | 0 | -3 |
| v20_throat_coffee_update | 喉が荒れ気味なら、コーヒーは少しだけにしとけ。 | 飲みすぎはやめとけ。コーヒーは少しだけにして、水も飲め。 | 0 | +5 |
| v20_throat_coffee_update | コーヒー飲むなら少しだけ。喉が荒れてる時に攻めるな。 | コーヒー飲むならいいけど。喉が荒れてる時に無理して飲むな。 | 2 | +3 |
| v20_throat_coffee_update | 最近喉が荒れやすいなら、コーヒーも控えめでいい。 | 最近喉が荒れやすいなら、温かい飲み物を少しずつにしろ。 | 1 | +3 |
| v20_throat_coffee_update | 喉が気になる日は、コーヒーは少しで止めとけ。 | 今日はコーヒーを少しで止めとけ。後でだるいぞ。 | 0 | +1 |
| v20_absurd_train_moon | 急に何の話だよ。意味分かんないけどノリは強いな。 | 意味分かんないけどノリは強いな。勢いだけで押してくるなよ。 | 0 | +5 |
| v20_absurd_train_moon | 何その急なノリ。意味分かんなすぎるだろ。 | 何その急な方向転換。勢いだけで来るなよ。 | 1 | +0 |
| v20_absurd_train_moon | 急に飛びすぎだろ。意味は分からんけど勢いはある。 | 意味は分からんけど勢いはある。もう少し落ち着いて言えって。 | 0 | +5 |
| v20_absurd_train_moon | そのノリ何なんだよ。意味分かんない方向に強いな。 | その話何なんだよ。急に飛びすぎだろ。説明くらいしろって。 | 1 | +4 |
| v20_uncertain_weekend_plan | 分からない所は決めつけるな。後で変えられる軽いやつにしとけ。 | 後で変えられる軽いやつにしとけ。今は仮で決めれば十分だろ。 | 0 | -1 |
| v20_uncertain_weekend_plan | 今は決めつけず、後で変えられる軽い予定にしとけ。 | 今は決めつけず、軽い予定にしとけ。無理に詰めなくていい。 | 1 | +4 |
| v20_uncertain_weekend_plan | 分からない所は置け。軽く行って後で変えろ。 | 分からない所は置け。後で変えればいい。 | 2 | -2 |
| v20_uncertain_weekend_plan | 後で変えられる軽い形にしとけ。分からない所は詰めるな。 | 後で変えられる軽い形にしとけ。今すぐ全部決めなくていい。 | 0 | +1 |

## 研究邊界

Hard negatives are manually authored, natural Japanese controls with one required semantic group replaced while response length remains close. They are synthetic preferences, not human ratings.
