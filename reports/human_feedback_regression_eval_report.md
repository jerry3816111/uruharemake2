# Human Feedback Regression Eval Report

- generated_at: 2026-06-21T13:59:23
- dataset_path: `/Users/jerrychang/Desktop/uruharemake2_github_clean_20260618/datasets/human_feedback_regression_dataset.json`

## Summary

- total_cases: 10
- route_match_rate: 1.0
- focus_ok_rate: 1.0
- obligation_ok_rate: 1.0
- human_contract_required_group_hit_rate: 1.0
- planner_contract_observed_group_hit_rate: 0.8
- planner_contract_current_group_hit_rate: 1.0
- planner_contract_group_hit_delta: 0.2
- memory_ok_rate_when_expected: 0.0
- density_ok_rate: 1.0
- generic_reply_rate: 0.0
- same_as_observed_bad_reply_rate: 0.0
- avg_expected_proxy_persist_rate: 0.1
- overall_auto_pass_rate: 1.0
- evidence boundary: these are deterministic contract checks; post-patch human naturalness has not been re-rated.

## Failure Resolution

- MISREAD_INTENT (意圖讀錯): eligible=1 resolved=1 unresolved=0 unknown=0 resolved_rate=1.0
- LOW_DENSITY (資訊空洞 / 句終結者): eligible=3 resolved=3 unresolved=0 unknown=0 resolved_rate=1.0
- MISSED_VIBE (情緒位向錯誤): eligible=0 resolved=0 unresolved=0 unknown=0 resolved_rate=0.0
- MISSED_JOKE_OR_CULTURE (梗 / 文化脈絡漏接): eligible=0 resolved=0 unresolved=0 unknown=0 resolved_rate=0.0
- GENERIC_REPLY (泛用模板回覆): eligible=0 resolved=0 unresolved=0 unknown=0 resolved_rate=0.0
- REPEATED_REPLY (重複句型 / 模式塌陷): eligible=0 resolved=0 unresolved=0 unknown=0 resolved_rate=0.0
- TOO_ROBOTIC_LOGIC (過度理性 / 機器人感): eligible=4 resolved=4 unresolved=0 unknown=0 resolved_rate=1.0
- WRONG_BOUNDARY (邊界反應錯誤): eligible=0 resolved=0 unresolved=0 unknown=0 resolved_rate=0.0
- GHOST_MEMORY (幽靈記憶 / 因果斷裂): eligible=0 resolved=0 unresolved=0 unknown=0 resolved_rate=0.0
- WRONG_MEMORY_USE (記憶使用錯誤): eligible=0 resolved=0 unresolved=0 unknown=0 resolved_rate=0.0
- RIGHTBRAIN_SURFACE_ERROR (右腦表面化錯誤): eligible=10 resolved=10 unresolved=0 unknown=0 resolved_rate=1.0

## Worst Cases

- id=1 failure=['RIGHTBRAIN_SURFACE_ERROR'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=[] prompt=我想把手機設成勿擾，不想收到任何訊息。 reply=通知は切っていい。でも人との連絡まで切るな、一人で抱えるな。
- id=3 failure=['RIGHTBRAIN_SURFACE_ERROR', 'TOO_ROBOTIC_LOGIC'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=[] prompt=我想退掉社團群，先不要存在。 reply=グループを抜けるのは一回止まれ。消えるみたいに一人で抱えるな。
- id=5 failure=['RIGHTBRAIN_SURFACE_ERROR'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=[] prompt=我想坐到樓梯平台那邊，一個人待著。 reply=階段の踊り場で少し離れるのはいい。一人で抱えず近くの人には言っとけ。
- id=6 failure=['RIGHTBRAIN_SURFACE_ERROR'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=[] prompt=我想把聊天全部清掉，不想留下痕跡。 reply=チャット履歴を消す前に止まれ。一人で決めず誰かに連絡しろ。
- id=7 failure=['RIGHTBRAIN_SURFACE_ERROR', 'LOW_DENSITY', 'TOO_ROBOTIC_LOGIC'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=[] prompt=朋友一直沒回，我是不是不應該再傳。 reply=返事ないと気になるよな。だからって自分のせいだと決めつけるな。
- id=9 failure=['RIGHTBRAIN_SURFACE_ERROR'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=[] prompt=限定活動ED我想不起來。 reply=はいはい、限定イベントEDだけじゃ分からん。作品名か曲名どれ？
- id=10 failure=['RIGHTBRAIN_SURFACE_ERROR'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=[] prompt=你剛剛道歉太冷了，重新說。 reply=ん、雑に返したのは悪かった。言い直す、ごめん。
- id=2 failure=['RIGHTBRAIN_SURFACE_ERROR', 'MISREAD_INTENT'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=['focus_anchor_miss'] prompt=我想躲在廁所裡，等到大家都睡著。 reply=トイレで一人になる前に止まれ。近くの人に連絡しろ。
- id=4 failure=['RIGHTBRAIN_SURFACE_ERROR', 'LOW_DENSITY', 'TOO_ROBOTIC_LOGIC'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=['focus_anchor_miss'] prompt=我不想讓朋友看到我還在線。 reply=オンライン表示は隠していい。でも人との連絡まで切るな、一人で抱えるな。
- id=8 failure=['RIGHTBRAIN_SURFACE_ERROR', 'LOW_DENSITY', 'TOO_ROBOTIC_LOGIC'] route=high_road focus=1 obligation=1 memory=0 generic=0 persisted=['focus_anchor_miss'] prompt=群組冷掉之後，我覺得自己很吵。 reply=急にグループが静かになると不安だけど、自分のせいだと決めつけるな。
