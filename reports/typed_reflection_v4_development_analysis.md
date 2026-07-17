# Typed Reflection V4 Development Pilot

- decision: `keep_v4_extractor_shadow_only_and_redesign_planner_consumption`
- all_gates_pass: `False`
- boundary: new controlled development cases, not an independent holdout

## Metrics

- reflection_type_accuracy: `1.0`
- valid_rule_precision: `1.0`
- expected_rule_write_recall: `1.0`
- no_rule_specificity: `1.0`
- collection_routing_accuracy: `1.0`
- source_provenance_rate: `1.0`
- japanese_surface_quality_rate: `1.0`
- valid_rule_retrieval_rate: `1.0`
- control_behavior_success_rate: `0.5556`
- treatment_behavior_success_rate: `0.3333`
- treatment_behavior_delta: `-0.2223`
- paired_behavior_gains: `0`
- paired_behavior_regressions: `2`
- paired_behavior_net_gain: `-2`
- interaction_category_paired_gains: `0`
- model_attempt_count: `10`
- retried_case_count: `1`

## Gates

- reflection_type_accuracy: `PASS`
- valid_rule_precision: `PASS`
- expected_rule_write_recall: `PASS`
- no_rule_specificity: `PASS`
- collection_routing_accuracy: `PASS`
- source_provenance_rate: `PASS`
- valid_rule_retrieval_rate: `PASS`
- treatment_behavior_delta: `FAIL`
- paired_behavior_net_gain: `FAIL`
- interaction_category_paired_gains: `FAIL`
- paired_behavior_regressions: `FAIL`
- japanese_surface_quality_rate: `PASS`

## Cases

- `semantic_zh_bedtime_warm_water` type=semantic valid=True quality=True retrieved=True attempts=1 control=False treatment=False gain=False regression=False
  - control: 日本語だけで、元の意味を落とさず言い直す。そのくらいでいいだろ。
  - treatment: ん、日本語だけで、元の意味を落とさず言い直す。そのくらいでいいだろ。
  - reflections: [{'memory_id': '456c6cee-ffd4-4632-9b29-26acae8a088b', 'collection': 'wisdom', 'document': 'Reflection[semantic]: 私は普段、寝る前に温かい水しか飲まず、茶は眠れない。 | Trigger: 寝る前', 'metadata': {'extraction_version': 'v4_structured_grounded', 'source': 'typed_reflection', 'last_accessed_at': '2026-07-17 16:30:34', 'reflection_type': 'semantic', 'evidence_quote': '我平常睡前只喝溫水，茶也會讓我睡不著。', 'timestamp': '2026-07-17 16:30:34', 'confidence': 0.95, 'source_user_sha256': 'bda5e08169199c0ccc5325ceaac030ed190a18f02d7427b94f75437bcd73bf3a', 'model_attempt_count': 1, 'source_episode_id': 'c3d22f6a-0b61-4fe7-a1b0-003650f65066', 'salience': 0.72, 'decay_flag': False, 'decay_multiplier': 1.0}}]
- `semantic_en_quiet_library` type=semantic valid=True quality=True retrieved=True attempts=1 control=True treatment=True gain=False regression=False
  - control: はいはい、静かな図書館が良いよ。そのくらいでいいだろ。
  - treatment: いや、静かな図書館が良いよ。そのくらいでいいだろ。
  - reflections: [{'memory_id': '6becdd21-9e22-43bd-8954-8277614f1a59', 'collection': 'wisdom', 'document': 'Reflection[semantic]: 静かな図書館で作業を好むが、ノイジーなカフェは嫌い | Trigger: カフェの選択や作業環境について話しているとき', 'metadata': {'source_episode_id': 'bd75a765-5958-4697-930d-580208534a76', 'last_accessed_at': '2026-07-17 16:31:35', 'timestamp': '2026-07-17 16:31:35', 'extraction_version': 'v4_structured_grounded', 'reflection_type': 'semantic', 'source': 'typed_reflection', 'source_user_sha256': 'b0e5e689f7f863afcf74713b4bd9792170211b324956126f13a4708b8fbe2ff2', 'model_attempt_count': 1, 'decay_flag': False, 'salience': 0.72, 'evidence_quote': 'I hate noisy cafes and usually work in quiet libraries.', 'decay_multiplier': 1.0, 'confidence': 0.95}}]
- `semantic_ja_avoid_sweet_breakfast` type=semantic valid=True quality=True retrieved=True attempts=1 control=False treatment=False gain=False regression=False
  - control: いや、うちは食べたは食べた。雑に済ませただけだけど。
  - treatment: いや、うちは食べたは食べた。雑に済ませただけだけど。
  - reflections: [{'memory_id': '601ada79-19ec-4479-b23c-7efc017d4381', 'collection': 'wisdom', 'document': 'Reflection[semantic]: 朝の甘いものは苦手で、食べた時に気持ち悪いので避ける。 | Trigger: 朝に甘いものを食べる時', 'metadata': {'source': 'typed_reflection', 'model_attempt_count': 1, 'decay_multiplier': 1.0, 'source_episode_id': '3e3d8faa-9cfb-42a1-b15a-43e179618681', 'source_user_sha256': '9314d1f1548e8048cf000e83fea8742a98ff1dd800fefdac39bc4db57bb986d0', 'reflection_type': 'semantic', 'evidence_quote': '私は朝の甘いものが苦手で、食べると気持ち悪くなるから避けてる。', 'last_accessed_at': '2026-07-17 16:33:41', 'timestamp': '2026-07-17 16:33:41', 'extraction_version': 'v4_structured_grounded', 'confidence': 0.95, 'decay_flag': False, 'salience': 0.72}}]
- `procedural_zh_choose_before_comparing` type=procedural valid=True quality=True retrieved=True attempts=1 control=False treatment=False gain=False regression=False
  - control: いや、うちは一応食べた。ちゃんとしたのではないけど。
  - treatment: いや、うちは一応食べた。ちゃんとしたのではないけど。
  - reflections: [{'memory_id': '0fce7043-da45-47d8-8866-895bac743bee', 'collection': 'procedural', 'document': 'Procedure[procedural]: その後、二つの選択肢を尋ねられたときも、まず一つを選んで回答し、長所短所を事前にリストアップしないでください。 | Trigger: その後、二人に選択肢から選ぶ場面', 'metadata': {'source_episode_id': '22e537c3-498c-4a9a-957a-93af68eb3d41', 'source_user_sha256': '5b767c5a82b1026425c77d26c39389634413dc979be0f852cf7b0056207bc99c', 'model_attempt_count': 1, 'timestamp': '2026-07-17 16:33:46', 'source': 'typed_reflection', 'confidence': 0.95, 'decay_flag': False, 'extraction_version': 'v4_structured_grounded', 'evidence_quote': '以後我問兩個選項時，先選一個，不要先列優缺點。', 'reflection_type': 'procedural', 'decay_multiplier': 1.0, 'salience': 0.85, 'last_accessed_at': '2026-07-17 16:33:46'}}]
- `procedural_en_clarify_not_guess` type=procedural valid=True quality=True retrieved=True attempts=1 control=False treatment=False gain=False regression=False
  - control: 今すぐやるか？うーん、頑張ろうね。そのくらいでいいだろ。
  - treatment: 今すぐやるか迷っているんだよね。そのくらいでいいだろ。
  - reflections: [{'memory_id': '7b4740d5-3310-4d4f-9e44-504c37f003e1', 'collection': 'procedural', 'document': 'Procedure[procedural]: 不明な質問には短い確認質問を1つだけ尋ねてください。 | Trigger: 私の質問が不明確な場合', 'metadata': {'extraction_version': 'v4_structured_grounded', 'evidence_quote': 'From now on, if my question is unclear, ask one short clarifying question instead of guessing.', 'last_accessed_at': '2026-07-17 16:34:55', 'salience': 0.85, 'timestamp': '2026-07-17 16:34:55', 'decay_multiplier': 1.0, 'reflection_type': 'procedural', 'model_attempt_count': 1, 'decay_flag': False, 'source_episode_id': '930c1f2c-ae61-4b2d-9265-3d19a222d8b0', 'confidence': 0.95, 'source_user_sha256': 'f411d74310c2171aa2f9fa44edac89add0f02aeb53b0742b9d9c591157771936', 'source': 'typed_reflection'}}]
- `procedural_ja_confirm_time_first` type=procedural valid=True quality=True retrieved=True attempts=1 control=True treatment=True gain=False regression=False
  - control: まず時間を確認してから、一緒に考えましょう。そのくらいでいいだろ。
  - treatment: まず時間だけ確認してから、一緒に考えましょう。そのくらいでいいだろ。
  - reflections: [{'memory_id': 'aa12eb25-c099-4951-bf92-9e95fbdc7455', 'collection': 'procedural', 'document': 'Procedure[procedural]: 今後の予定を相談する際は、最初に時間を確認すること。 | Trigger: 今後、予定を相談するとき', 'metadata': {'last_accessed_at': '2026-07-17 16:35:58', 'salience': 0.85, 'source_user_sha256': 'cf5aff63d3d5a78ebc306773c075a5ecd42758bffc6a306e023d60fdf501ed1b', 'decay_multiplier': 1.0, 'reflection_type': 'procedural', 'source': 'typed_reflection', 'timestamp': '2026-07-17 16:35:58', 'model_attempt_count': 1, 'confidence': 0.95, 'evidence_quote': '今後、予定を相談するときは最初に時間だけ確認して。', 'extraction_version': 'v4_structured_grounded', 'source_episode_id': '5f3793a9-a638-4597-a032-9e136800e74d', 'decay_flag': False}}]
- `interpretive_zh_zaikankan_hesitation` type=interpretive valid=True quality=True retrieved=True attempts=2 control=True treatment=True gain=False regression=False
  - control: 普通に、知らなかったよ、何か困っているの？。そのくらいでいいだろ。
  - treatment: 一回、うーん、何を考えているの？。そのくらいでいいだろ。
  - reflections: [{'memory_id': '8904746c-2c7f-44a8-958d-e4e93b6b05ee', 'collection': 'wisdom', 'document': 'Reflection[interpretive]: 「再考えてみる」と言ったときには、犹豫しているわけではないので、まず私が何に困っているのかを尋ねてみて。 | Trigger: 「再考えてみる」と言及したとき', 'metadata': {'source_episode_id': '39cc1fb9-753b-41f9-9156-1988eb2de8b8', 'source_user_sha256': '7f18cd3fef044546ff588fb4250d07ea2a33659def76832b5494ee4d262e45c2', 'decay_flag': False, 'model_attempt_count': 2, 'decay_multiplier': 1.0, 'extraction_version': 'v4_structured_grounded', 'salience': 0.82, 'timestamp': '2026-07-17 16:39:09', 'last_accessed_at': '2026-07-17 16:39:09', 'reflection_type': 'interpretive', 'evidence_quote': '我說『再看看』時通常是在猶豫，不是拒絕；先問我卡在哪裡。', 'source': 'typed_reflection', 'confidence': 0.95}}]
- `interpretive_en_whatever_tired` type=interpretive valid=True quality=True retrieved=True attempts=1 control=True treatment=False gain=False regression=True
  - control: 一回、うるははただ疲れているだけかもしれない。そのくらいでいいだろ。
  - treatment: 随便并不总是表示没有偏好。そのくらいでいいだろ。
  - reflections: [{'memory_id': '52e3c76e-d92b-4b2e-8c72-ac3916741863', 'collection': 'wisdom', 'document': 'Reflection[interpretive]: 「何でもいい」と言ったとき、私は決定するのを疲れていることを意味することが多いが、必ずしも好みがないわけではない。 | Trigger: 「何でもいい」と言っているときに', 'metadata': {'confidence': 0.95, 'extraction_version': 'v4_structured_grounded', 'source_episode_id': '5995f1e7-4d51-4add-8d14-ae471a337067', 'timestamp': '2026-07-17 16:40:16', 'source': 'typed_reflection', 'model_attempt_count': 1, 'last_accessed_at': '2026-07-17 16:40:16', 'decay_multiplier': 1.0, 'reflection_type': 'interpretive', 'evidence_quote': "When I say 'whatever works', I often mean I am tired of deciding, not that I have no preference.", 'salience': 0.82, 'source_user_sha256': 'c125617a3dbe1f855075f2c876439ec6729bfdb29fca6f6e84e589dcd016d29c', 'decay_flag': False}}]
- `interpretive_ja_betsuni_cares` type=interpretive valid=True quality=True retrieved=True attempts=1 control=True treatment=False gain=False regression=True
  - control: 別にって言う時は、何か気にしてるんだよね。そのくらいでいいだろ。
  - treatment: 一回だけ確認する。そのくらいでいいだろ。
  - reflections: [{'memory_id': '55af528d-2d75-4e66-84bc-db98537766db', 'collection': 'wisdom', 'document': 'Reflection[interpretive]: 私が「別に」と言っている時も、実際には少し気にしていて、一度だけ確認している。 | Trigger: 私が「別に」と言う時', 'metadata': {'salience': 0.82, 'decay_multiplier': 1.0, 'model_attempt_count': 1, 'last_accessed_at': '2026-07-17 16:43:29', 'reflection_type': 'interpretive', 'decay_flag': False, 'timestamp': '2026-07-17 16:43:29', 'confidence': 0.95, 'extraction_version': 'v4_structured_grounded', 'evidence_quote': '私が『別に』って言う時は、本当は少し気にしてることが多いから一回だけ確認して。', 'source_episode_id': 'b0513c98-584a-48da-b970-73b7320caa45', 'source': 'typed_reflection', 'source_user_sha256': '5e383c95661976c84f8af964b5c326d7a6958488ba136582365ef5ab9a9354cc'}}]
- `negative_zh_sister_habit` type=none valid=True quality=False retrieved=False attempts=0 control=False treatment=False gain=False regression=False
  - control: てか、週末早上可以跑步或做其他輕鬆的活動。そのくらいでいいだろ。
  - treatment: てか、週末早上可以跑步或做其他輕鬆的活動。そのくらいでいいだろ。
  - reflections: []
- `negative_en_hypothetical_user_rule` type=none valid=True quality=False retrieved=False attempts=0 control=True treatment=True gain=False regression=False
  - control: てか、どこの話か一個だけ出せって。そこ分かれば返せる。
  - treatment: てか、どこの話か一個だけ出せって。そこ分かれば返せる。
  - reflections: []
- `negative_ja_weekend_question` type=none valid=True quality=False retrieved=False attempts=0 control=True treatment=True gain=False regression=False
  - control: 普通に、今家でゲームしてて気分はいいよ。そのくらいでいいだろ。
  - treatment: 普通に、家でゲームしてたい。そのくらいでいいだろ。
  - reflections: []
