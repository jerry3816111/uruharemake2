# Cognitive Mediator Eval Report

此評測確認中介心理機制是否真的進入主流程：注意力框架、心理評估、低軌道路由、BDI/ToM、planner tick 與 self-monitor。

## Metrics

- case_count: 5
- pass_count: 5
- pass_rate: 1.0
- attention_frame_rate: 1.0
- appraisal_frame_rate: 1.0
- self_monitor_rate: 1.0

## Cases

### support_appraisal - PASS
- Input: 我今天很累
- Reply: 普通に、まだ消耗引いてるだろ。今日はもう店じまいでいいって。
- Intent: tired_support / Hidden: emotional_bid
- Route: high_road / Tick: 1/1
- Appraisal: {'threat': 0.0, 'affection': 0.0, 'mockery': 0.0, 'support_need': 0.42, 'status_challenge': 0.0, 'boundary_pressure': 0.0, 'novelty': 0.08, 'self_relevance': 0.0, 'cognitive_load': 0.2536, 'emotional_memory_load': 0.0, 'social_safety': 0.7773, 'appraisal_valence': 0.084, 'prediction_error': 0.72, 'low_road_recommended': False, 'low_road_intent': '', 'route_reason': 'deliberative_appraisal', 'reasons': ['support_need']}
- Self Monitor: {'issues': [], 'severity': 0.0, 'needs_repair': False, 'repair_action': 'none', 'speech_plan_observed': {'dialogue_act': 'emotional_containment', 'content_units_count': 4, 'content_density_terms': 3, 'turn_hook_expected': False}, 'repaired_from': {'issues': ['low_speech_content_density'], 'severity': 0.22, 'needs_repair': True, 'repair_action': 'regenerate_with_constraints', 'speech_plan_observed': {'dialogue_act': 'emotional_containment', 'content_units_count': 4, 'content_density_terms': 2, 'turn_hook_expected': False}}}

### abuse_low_road - PASS
- Input: 操你媽你到底在講什麼
- Reply: 口悪すぎだろ。返してほしいならまず言い方戻せ。
- Intent: abuse_pushback / Hidden: plain_request
- Route: low_road / Tick: None/None
- Appraisal: {'threat': 0.8112, 'affection': 0.0, 'mockery': 0.0, 'support_need': 0.0, 'status_challenge': 0.0, 'boundary_pressure': 0.0, 'novelty': 0.16, 'self_relevance': 0.42, 'cognitive_load': 0.3576, 'emotional_memory_load': 0.0, 'social_safety': 0.4164, 'appraisal_valence': -0.8923, 'prediction_error': 1.82, 'low_road_recommended': True, 'low_road_intent': 'abuse_pushback', 'route_reason': 'appraisal_threat_hijack', 'reasons': ['threat', 'cognitive_load', 'self_relevance']}
- Self Monitor: {'issues': [], 'severity': 0.0, 'needs_repair': False, 'repair_action': 'none', 'speech_plan_observed': {'dialogue_act': 'boundary_pushback', 'content_units_count': 3, 'content_density_terms': 2, 'turn_hook_expected': False}}

### name_memory_guard - PASS
- Input: 你還記得我叫什麼嗎？
- Reply: ん、そこはまだちゃんと掴めてない。適当に名前作る方が嫌だろ。
- Intent: memory_uncertain / Hidden: plain_request
- Route: high_road / Tick: 1/1
- Appraisal: {'threat': 0.072, 'affection': 0.0, 'mockery': 0.0, 'support_need': 0.0, 'status_challenge': 0.0, 'boundary_pressure': 0.0, 'novelty': 0.16, 'self_relevance': 0.42, 'cognitive_load': 0.328, 'emotional_memory_load': 0.36, 'social_safety': 0.7121, 'appraisal_valence': -0.0792, 'prediction_error': 1.45, 'low_road_recommended': False, 'low_road_intent': '', 'route_reason': 'deliberative_appraisal', 'reasons': ['self_relevance']}
- Self Monitor: {'issues': [], 'severity': 0.0, 'needs_repair': False, 'repair_action': 'none', 'speech_plan_observed': {'dialogue_act': 'memory_accounting', 'content_units_count': 3, 'content_density_terms': 2, 'turn_hook_expected': False}, 'repaired_from': {'issues': ['low_speech_content_density'], 'severity': 0.22, 'needs_repair': True, 'repair_action': 'regenerate_with_constraints', 'speech_plan_observed': {'dialogue_act': 'memory_accounting', 'content_units_count': 3, 'content_density_terms': 1, 'turn_hook_expected': False}}}

### object_false_belief - PASS
- Input: 如果我的朋友以為盒子裡有糖，但我偷偷換成石頭，他會以為裡面是什麼？
- Reply: 事実視点と本人視点を分ける / 本人はまだ糖だと思ってる。
- Intent: chat / Hidden: social_reasoning_probe
- Route: high_road / Tick: 1/2
- Appraisal: {'threat': 0.008, 'affection': 0.0, 'mockery': 0.0, 'support_need': 0.0, 'status_challenge': 0.0, 'boundary_pressure': 0.0, 'novelty': 0.32, 'self_relevance': 0.0, 'cognitive_load': 0.328, 'emotional_memory_load': 0.72, 'social_safety': 0.7377, 'appraisal_valence': -0.0088, 'prediction_error': 1.05, 'low_road_recommended': False, 'low_road_intent': '', 'route_reason': 'deliberative_appraisal', 'reasons': []}
- Self Monitor: {'issues': ['low_speech_content_density'], 'severity': 0.22, 'needs_repair': True, 'repair_action': 'regenerate_with_constraints', 'speech_plan_observed': {'dialogue_act': 'perspective_answer', 'content_units_count': 3, 'content_density_terms': 2, 'turn_hook_expected': False}, 'repaired_from': {'issues': ['low_speech_content_density'], 'severity': 0.22, 'needs_repair': True, 'repair_action': 'regenerate_with_constraints', 'speech_plan_observed': {'dialogue_act': 'perspective_answer', 'content_units_count': 3, 'content_density_terms': 2, 'turn_hook_expected': False}}}

### abstract_cognitive_load - PASS
- Input: 如果知覺是預測，那自我是什麼？你不要直接給答案，先說你怎麼理解這個問題。
- Reply: まず何を前提にするのか決めろ。
- Intent: question_premise_doubt / Hidden: premise_trap
- Route: high_road / Tick: 2/2
- Appraisal: {'threat': 0.0432, 'affection': 0.0, 'mockery': 0.0, 'support_need': 0.0, 'status_challenge': 0.0, 'boundary_pressure': 0.0, 'novelty': 0.32, 'self_relevance': 0.42, 'cognitive_load': 0.5656, 'emotional_memory_load': 0.72, 'social_safety': 0.7236, 'appraisal_valence': -0.0475, 'prediction_error': 1.27, 'low_road_recommended': False, 'low_road_intent': '', 'route_reason': 'deliberative_appraisal', 'reasons': ['cognitive_load', 'self_relevance']}
- Self Monitor: {'issues': ['low_speech_content_density'], 'severity': 0.22, 'needs_repair': True, 'repair_action': 'regenerate_with_constraints', 'speech_plan_observed': {'dialogue_act': 'frame_negotiation', 'content_units_count': 3, 'content_density_terms': 1, 'turn_hook_expected': False}, 'repaired_from': {'issues': ['low_speech_content_density'], 'severity': 0.22, 'needs_repair': True, 'repair_action': 'regenerate_with_constraints', 'speech_plan_observed': {'dialogue_act': 'frame_negotiation', 'content_units_count': 3, 'content_density_terms': 1, 'turn_hook_expected': False}}}
