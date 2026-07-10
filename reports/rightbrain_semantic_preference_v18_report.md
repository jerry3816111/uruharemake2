# RightBrain v18 語意完整度偏好資料

## 結論

這份資料不再只示範正確答案，而是對同一份左腦契約建立「完整回答 > 自然但漏掉必要語意的回答」配對。

| 指標 | 值 |
|---|---:|
| preference pairs | 32 |
| family specs | 8 |
| chosen 全部完整 | True |
| rejected 全部漏槽位 | True |
| rejected 保持乾淨直接日文 | True |
| chosen 平均比 rejected 長 | 10.3 chars |
| holdout case overlap | 0 |
| holdout target overlap | 0 |

## Pair 範例

| family | chosen | rejected | omitted groups |
|---|---|---|---|
| v18_group_reply_delay | 返事が止まると不安だよな。でも理由はまだ分からない。自分のせいと決めず少し待て。 | 理由はまだ分からない。自分のせいと決めず少し待て。 | [0] |
| v18_group_reply_delay | 返信がない理由は見えてない。自分が悪いって決めつけず、少し待て。 | 返信がない理由は見えてない。少し待て。 | [2] |
| v18_group_reply_delay | 返事待ちはきついけど、理由は不明だろ。自分のせいにするな。 | 返事待ちはきついけど、自分のせいにするな。 | [1] |
| v18_group_reply_delay | 返事がないだけで自分を責めるな。理由はまだ分からないし、少し待て。 | 返事がないだけで自分を責めるな。少し待て。 | [1] |
| v18_manga_fragment_source | 断片だけじゃ分からん。元ネタか作品名を出せ。 | 元ネタか作品名を出せ。 | [0] |
| v18_manga_fragment_source | 今のだけじゃ拾えない。作品名かタイトルまで言え。 | 今のだけじゃ拾えない。 | [1] |
| v18_manga_fragment_source | それだけで特定は無理だろ。元ネタを出せ。 | 元ネタを出せ。 | [0] |
| v18_manga_fragment_source | その断片の元ネタ確認なら、作品名くらい出せって。 | 作品名くらい出せって。 | [0] |
| v18_daily_low_energy_status | 今はぼんやり休んでた。話すくらいならいける。 | 今はぼんやり休んでた。 | [2] |
| v18_daily_low_energy_status | 今ちょっとだらっとしてた。話なら聞く。 | 今ちょっとだらっとしてた。 | [2] |
| v18_daily_low_energy_status | 今は休み気味。話すくらいなら別にいい。 | 今は休み気味。 | [2] |
| v18_daily_low_energy_status | 今ぼーっと休んでた。話があるなら聞く。 | 今ぼーっと休んでた。 | [2] |
| v18_sleep_debt_boundary | 眠いならもう無理すんな。今日は寝ろ。 | 今日は寝ろ。 | [0] |
| v18_sleep_debt_boundary | その眠さなら続けるな。寝る方が先だろ。 | その眠さなら続けるな。 | [1] |
| v18_sleep_debt_boundary | 無理しても雑になるだけだ。眠いなら休め。 | 無理しても雑になるだけだ。 | [0] |
| v18_sleep_debt_boundary | 今日は閉じていい。眠い時は寝ろ。 | 今日は閉じていい。 | [0, 1] |
| v18_private_school_topic | 軽い話題でいいだろ。最近どうしてたんだよ。 | 最近どうしてたんだよ。 | [0] |
| v18_private_school_topic | 話すなら近況でいい。最近どうしてた。 | 最近どうしてた。 | [0] |
| v18_private_school_topic | 重くしなくていい。最近の話でもしろ。 | 重くしなくていい。 | [0, 1] |
| v18_private_school_topic | じゃあ軽い話題な。最近何してたんだよ。 | じゃあ軽い話題な。 | [1] |
| v18_throat_coffee_update | 喉が荒れ気味なら、コーヒーは少しだけにしとけ。 | コーヒーは少しだけにしとけ。 | [0] |
| v18_throat_coffee_update | コーヒー飲むなら少しだけ。喉が荒れてる時に攻めるな。 | コーヒー飲むなら少しだけ。 | [0] |
| v18_throat_coffee_update | 最近喉が荒れやすいなら、コーヒーも控えめでいい。 | コーヒーも控えめでいい。 | [0] |
| v18_throat_coffee_update | 喉が気になる日は、コーヒーは少しで止めとけ。 | コーヒーは少しで止めとけ。 | [0] |
| v18_absurd_train_moon | 急に何の話だよ。意味分かんないけどノリは強いな。 | 意味分かんないけどノリは強いな。 | [0] |
| v18_absurd_train_moon | 何その急なノリ。意味分かんなすぎるだろ。 | 意味分かんなすぎるだろ。 | [0] |
| v18_absurd_train_moon | 急に飛びすぎだろ。意味は分からんけど勢いはある。 | 意味は分からんけど勢いはある。 | [0] |
| v18_absurd_train_moon | そのノリ何なんだよ。意味分かんない方向に強いな。 | 意味分かんない方向に強いな。 | [0] |
| v18_uncertain_weekend_plan | 分からない所は決めつけるな。後で変えられる軽いやつにしとけ。 | 後で変えられる軽いやつにしとけ。 | [0] |
| v18_uncertain_weekend_plan | 今は決めつけず、後で変えられる軽い予定にしとけ。 | 後で変えられる軽い予定にしとけ。 | [0] |
| v18_uncertain_weekend_plan | 分からない所は置け。軽く行って後で変えろ。 | 軽く行って後で変えろ。 | [0] |
| v18_uncertain_weekend_plan | 後で変えられる軽い形にしとけ。分からない所は詰めるな。 | 後で変えられる軽い形にしとけ。 | [0] |

## 研究邊界

Pairs are deterministically constructed from holdout-separated synthetic contract families. They encode semantic completeness, not broad human preference, and cannot be evaluated on their source targets.
