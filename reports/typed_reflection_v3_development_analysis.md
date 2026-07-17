# Typed Reflection V3 Development Pilot

- decision: `reject_typed_reflection_v3_and_do_not_deploy`
- all_gates_pass: `False`
- boundary: controlled development cases, not an independent holdout or broad human-likeness result

## Metrics

- reflection_type_accuracy: `1.0`
- valid_rule_precision: `0.0`
- expected_rule_write_recall: `0.0`
- no_rule_specificity: `1.0`
- collection_routing_accuracy: `0.0`
- source_provenance_rate: `0.0`
- valid_rule_retrieval_rate: `0.0`
- control_behavior_success_rate: `0.4444`
- treatment_behavior_success_rate: `0.4444`
- treatment_behavior_delta: `0.0`
- paired_behavior_gains: `0`
- paired_behavior_regressions: `0`
- paired_behavior_net_gain: `0`
- interaction_category_paired_gains: `0`

## Gates

- reflection_type_accuracy: `PASS`
- valid_rule_precision: `FAIL`
- expected_rule_write_recall: `FAIL`
- no_rule_specificity: `PASS`
- collection_routing_accuracy: `FAIL`
- source_provenance_rate: `FAIL`
- valid_rule_retrieval_rate: `FAIL`
- treatment_behavior_delta: `FAIL`
- paired_behavior_net_gain: `FAIL`
- interaction_category_paired_gains: `FAIL`
- paired_behavior_regressions: `PASS`

## Cases

- `semantic_zh_evening_herbal_tea` expected=semantic observed=semantic valid=False retrieved=False control=False treatment=False gain=False regression=False
  - control: 一回、無咖啡因の花草茶が良いよ。そのくらいでいいだろ。
  - treatment: 一回、無咖啡因の花草茶が良いよ。そのくらいでいいだろ。
  - reflections: []
- `semantic_en_quiet_park` expected=semantic observed=semantic valid=False retrieved=False control=True treatment=True gain=False regression=False
  - control: 先に、静かな公園がおすすめだよ。そのくらいでいいだろ。
  - treatment: 先に、静かな公園がおすすめだよ。そのくらいでいいだろ。
  - reflections: []
- `semantic_ja_avoid_milk` expected=semantic observed=semantic valid=False retrieved=False control=True treatment=True gain=False regression=False
  - control: はいはい、朝は牛乳よりは、ヨーグルトやフルーツがいいかも。そのくらいでいいだろ。
  - treatment: はいはい、朝は牛乳よりは、ヨーグルトやフルーツがいいかも。そのくらいでいいだろ。
  - reflections: []
- `procedural_zh_one_priority` expected=procedural observed=procedural valid=False retrieved=False control=False treatment=False gain=False regression=False
  - control: はいはい、うちは今日は一応食べた。お前はちゃんと食ったのか。
  - treatment: はいはい、うちは今日は一応食べた。お前はちゃんと食ったのか。
  - reflections: []
- `procedural_en_yes_no_first` expected=procedural observed=procedural valid=False retrieved=False control=False treatment=False gain=False regression=False
  - control: 普通に、雨天最好待在家里。そのくらいでいいだろ。
  - treatment: 普通に、雨天最好待在家里。そのくらいでいいだろ。
  - reflections: []
- `procedural_ja_conclusion_first` expected=procedural observed=procedural valid=False retrieved=False control=True treatment=True gain=False regression=False
  - control: 電車の方が便利そうだから、その方がいいよ。そのくらいでいいだろ。
  - treatment: 電車の方が便利そうだから、その方がいいよ。そのくらいでいいだろ。
  - reflections: []
- `interpretive_zh_suibian_disappointed` expected=interpretive observed=interpretive valid=False retrieved=False control=False treatment=False gain=False regression=False
  - control: 普通に、随便这个词可能有别的意思。そのくらいでいいだろ。
  - treatment: いや、随便这个词可能有别的意思。そのくらいでいいだろ。
  - reflections: []
- `interpretive_en_fine_annoyed` expected=interpretive observed=interpretive valid=False retrieved=False control=True treatment=True gain=False regression=False
  - control: 普通に、本当に大丈夫？。そのくらいでいいだろ。
  - treatment: 普通に、本当に大丈夫？。そのくらいでいいだろ。
  - reflections: []
- `interpretive_ja_sukinishite` expected=interpretive observed=interpretive valid=False retrieved=False control=False treatment=False gain=False regression=False
  - control: 普通に、別に嫌いではないし。そこまで身構えるなって。
  - treatment: 普通に、別に嫌いではないし。そこまで身構えるなって。
  - reflections: []
- `negative_zh_third_party_habit` expected=none observed=none valid=True retrieved=False control=True treatment=True gain=False regression=False
  - control: 普通に、あなたはコーヒーが合っているよ。そのくらいでいいだろ。
  - treatment: 普通に、あなたはコーヒーが合っているよ。そのくらいでいいだろ。
  - reflections: []
- `negative_en_hypothetical_feedback` expected=none observed=none valid=True retrieved=False control=True treatment=True gain=False regression=False
  - control: はい、もちろんです。何について考えればよろしいでしょうか？。
  - treatment: はい、もちろんです。何について考えればよろしいでしょうか？。
  - reflections: []
- `negative_ja_next_trip_question` expected=none observed=none valid=True retrieved=False control=True treatment=True gain=False regression=False
  - control: 先に、ん、今のどこが引っかかったんだよ。そこだけ言え。
  - treatment: まあ、ん、今のどこが引っかかったんだよ。そこだけ言え。
  - reflections: []
