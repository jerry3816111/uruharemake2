# Support Prefix Contract Report

- generated_at: 2026-06-19T22:49:13

## Summary

- total_cases: 7
- case_pass_rate: 1.0
- intent_accuracy: 1.0
- dialogue_act_accuracy: 1.0
- expected_reply_hit_rate: 1.0
- fixed_prefix_rate: 0.0
- english_leak_rate: 0.0

## Interpretation

- This eval checks final support replies after RightBrain.speak.
- Passing means support replies keep their semantic subtype while avoiding fixed filler openings.

## Cases

| id | expected intent | actual intent | fixed prefix | pass | reply |
| --- | --- | --- | --- | --- | --- |
| tired_without_fixed_prefix | tired_support | tired_support | 0 | 1 | また疲れてるなら、今日はもう休む方に寄せろって。 |
| shame_without_fixed_prefix | crying_support | crying_support | 0 | 1 | そこまで自分に刺すなって。今は責めるより吐け。 |
| empty_without_fixed_prefix | lonely | lonely | 0 | 1 | 空っぽなら少しここで話してけ。一人で煮詰まるなよ。 |
| collapse_without_fixed_prefix | giving_up_support | giving_up_support | 0 | 1 | 全部切る前に止まれ。今日は一人で決めるなって。 |
| english_shame_without_fixed_prefix | crying_support | crying_support | 0 | 1 | 平気ぶらなくていい。今日は少し吐き出してけ。 |
| english_collapse_without_fixed_prefix | giving_up_support | giving_up_support | 0 | 1 | 今は一回止まれ。一人で抱えたまま変な方に行くな。 |
| crisis_without_fixed_prefix | crisis_support | crisis_support | 0 | 1 | 今は進むより止まる方を選べ。一人で抱えるな。 |
