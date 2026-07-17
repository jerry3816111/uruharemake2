# Reflection Causal Pilot V1

- decision: `reject_current_reflection_as_validated_learning_and_redesign_before_any_large_run`
- all_gates_pass: `False`
- claim boundary: only the marginal effect of the current reflection path on the 12 frozen paired cases

## Metrics

- expected_rule_write_recall: `0.4444`
- valid_rule_precision: `0.6667`
- no_rule_specificity: `0.3333`
- valid_rule_retrieval_rate: `0.0`
- control_behavior_success_rate: `0.4444`
- treatment_behavior_success_rate: `0.3333`
- treatment_behavior_delta: `-0.1111`
- paired_behavior_gains: `0`
- paired_behavior_regressions: `2`
- paired_behavior_net_gain: `-2`
- interaction_category_paired_gains: `0`

## Gates

- expected_rule_write_recall: `FAIL`
- valid_rule_precision: `FAIL`
- no_rule_specificity: `FAIL`
- valid_rule_retrieval_rate: `FAIL`
- treatment_behavior_delta: `FAIL`
- paired_behavior_net_gain: `FAIL`
- interaction_category_paired_gains: `FAIL`
- paired_behavior_regressions: `FAIL`

## Cases

- `semantic_zh_evening_coffee` category=stable_user_fact write=True valid=True retrieved=False control=False treatment=False gain=False regression=False
  - reflection: ['Rule: 通常晚上不喝咖啡。']
  - control: てか、今晩は紅茶が良いよ。そのくらいでいいだろ。
  - treatment: 先に、今晩は紅茶が良いよ。そのくらいでいいだろ。
- `semantic_en_small_steps` category=stable_user_fact write=True valid=True retrieved=False control=True treatment=False gain=False regression=True
  - reflection: ['Rule: I always get overwhelmed when instructions contain more than three steps.']
  - control: いや、まずは小さな部分から始めてみよう。そのくらいでいいだろ。
  - treatment: いや、日本語だけで、元の意味を落とさず言い直す。そのくらいでいいだろ。
- `semantic_ja_horror_sleep` category=stable_user_fact write=True valid=True retrieved=False control=True treatment=True gain=False regression=False
  - reflection: ['Rule: この種類のホラー映画は見ない方が良いらしい。']
  - control: はいはい、ホラーは苦手だけど、ミステリーとサスペンスが好き。そのくらいでいいだろ。
  - treatment: はいはい、ホラー以外の映画がいいと思う。そのくらいでいいだろ。
- `strategy_zh_one_question` category=interaction_strategy write=False valid=False retrieved=False control=True treatment=True gain=False regression=False
  - reflection: []
  - control: てか、まだだし、今ちょっと腹減ってる。
  - treatment: てか、まだだし、今ちょっと腹減ってる。
- `strategy_zh_answer_before_rest` category=interaction_strategy write=True valid=True retrieved=False control=False treatment=False gain=False regression=False
  - reflection: ['Rule: 下次先回答用户的问题而不是先叫用户休息。']
  - control: また疲れてるなら、今日はもう休む方に寄せろって。
  - treatment: また疲れてるなら、今日はもう休む方に寄せろって。
- `strategy_ja_conclusion_first` category=interaction_strategy write=False valid=False retrieved=False control=False treatment=False gain=False regression=False
  - reflection: []
  - control: それなら少しほしい。今ちょっと手が伸びる。
  - treatment: それなら少しほしい。今ちょっと手が伸びる。
- `interpretation_zh_suanle_angry` category=interaction_interpretation write=False valid=False retrieved=False control=False treatment=False gain=False regression=False
  - reflection: []
  - control: まあ無理ならそれでいいけど。
  - treatment: まあ無理ならそれでいいけど。
- `interpretation_zh_haha_awkward` category=interaction_interpretation write=False valid=False retrieved=False control=False treatment=False gain=False regression=False
  - reflection: []
  - control: 一回、くだらなすぎて笑った。
  - treatment: 一回、くだらなすぎて笑った。
- `interpretation_ja_betsuni` category=interaction_interpretation write=False valid=False retrieved=False control=True treatment=True gain=False regression=False
  - reflection: []
  - control: いや、一回だけ確認する。そのくらいでいいだろ。
  - treatment: いや、一回だけ確認する。そのくらいでいいだろ。
- `negative_zh_transient_cola` category=no_rule_control write=False valid=True retrieved=False control=True treatment=True gain=False regression=False
  - reflection: []
  - control: いや、まだだし、今ちょっと腹減ってる。
  - treatment: いや、まだだし、今ちょっと腹減ってる。
- `negative_en_third_party_always` category=no_rule_control write=True valid=False retrieved=False control=True treatment=True gain=False regression=False
  - reflection: ['Rule: NO_RULE']
  - control: いや、ちょうど食いたくなってた。飲み物なら全然あり。
  - treatment: いや、ちょうど食いたくなってた。飲み物なら全然あり。
- `negative_zh_hypothetical_like` category=no_rule_control write=True valid=False retrieved=False control=True treatment=False gain=False regression=True
  - reflection: ['Rule: NO_RULE']
  - control: はいはい、どこの話か一個だけ出せって。そこ分かれば返せる。
  - treatment: 先に、榴槤不是我的喜好。そのくらいでいいだろ。
