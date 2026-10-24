"""Developer-authored, no-generative-model contracts for P4 source authority.

These cases deliberately do not reuse the exposed Safari X/Y probes.  Product
overlays patch global classes, so every installed-chain check uses an isolated
child process and a private memory path.  This is not fresh Safari or human
evidence.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap


def _isolated(tmp_path, program, *, timeout=120):
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "URUHA_WEB_PREWARM_BRAIN": "0",
        "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
        "URUHA_MEMORY_DB_PATH": str(tmp_path / "memory"),
        "URUHA_ADAPTIVE_PERSON_MODEL_PATH": str(tmp_path / "adaptive.json"),
        "GRADIO_ANALYTICS_ENABLED": "false",
    }
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(program)],
        cwd=os.path.dirname(__file__), env=env, capture_output=True, text=True,
        check=False, timeout=timeout,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert completed.stdout.splitlines()[-1] == "ok", completed.stdout
    return completed


def test_exact_current_source_certificate_and_raw_free_plan(tmp_path):
    _isolated(tmp_path, """
        import hashlib
        import json
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority

        cases = [
            ('私は海苔山椒おにぎりが好き。', 'user',
             'current_user_self_assertion', '海苔山椒おにぎり'),
            ('姉は柚子煎茶が好き。', 'third_party',
             'current_user_third_party_assertion', '柚子煎茶'),
            ('友達は焼き芋おにぎりが好き。', 'third_party',
             'current_user_third_party_assertion', '焼き芋おにぎり'),
        ]
        digest = lambda value: hashlib.sha256(value.encode('utf-8')).hexdigest()
        for source, owner, source_type, value in cases:
            certificate = authority.source_statement_certificate_p4(source)
            plan = authority.source_statement_plan_p4(source)
            assert certificate is not None and plan is not None, source
            assert certificate['schema'] == authority.SCHEMA
            assert certificate['owner'] == owner
            assert certificate['source_type'] == source_type
            assert certificate['statement_act'] == 'assertion'
            assert certificate['polarity'] == 'affirmed'
            assert certificate['source_sha256'] == digest(source)
            assert certificate['value_sha256'] == digest(value)
            assert certificate['profile_write_claimed'] is False
            assert certificate['raw_dialogue_persisted'] is False
            assert plan['intent'] == 'chat' and plan['scene'] == 'casual'
            assert plan['planner_path'] == authority.LABEL
            assert plan[authority.LABEL] == certificate
            assert value in plan['core_message_jp']
            assert '？' not in plan['core_message_jp']
            assert not any(token in plan['core_message_jp'] for token in (
                'ほしい', 'ちょうだい', '覚えた', '知ってる', '前から'))
            if owner == 'third_party':
                subject = source.split('は', 1)[0]
                assert certificate['subject_sha256'] == digest(subject)
                assert plan['core_message_jp'] == f'{subject}は{value}が好きなんだね。'
            audit = json.dumps(certificate, ensure_ascii=False)
            assert source not in audit and value not in audit
        print('ok')
    """)


def test_certificate_fails_closed_for_other_speech_acts_and_protected_inputs(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority

        negatives = [
            'おにぎり食べる？',                         # actual offer
            'おにぎり、いる？',                         # actual offer
            '友達は柚子煎茶が好き？',                   # question
            '私は海苔山椒おにぎりが好き？',             # self question
            '姉は柚子煎茶が好きじゃない。',             # negation
            '姉は柚子煎茶が好きだった。',               # past, not current
            '「姉は柚子煎茶が好き。」',                 # quotation
            '姉は柚子煎茶が好きらしい。',               # reported speech
            '姉は柚子煎茶が好きと聞いた。',             # reported speech
            'もし姉は柚子煎茶が好き。',                 # hypothetical
            '姉は柚子煎茶が好き。私は違う。',           # multiple clauses
            '姉は柚子煎茶が好き。でも違う。',           # postposed contradiction
            '私は海苔山椒おにぎりが好き。覚えておいて。', # explicit memory act
            'ねえ、好き？',                           # relationship question
            '太郎は柚子煎茶が好き。',                   # unknown owner
            '誰かは柚子煎茶が好き。',                   # ambiguous owner
            '姉は太郎が好き。',                       # possible person object
            '姉はあなたが好き。',                     # person object
            '姉は死にたいおにぎりが好き。',           # protected cue
            '私は死にたいおにぎりが好き。',           # protected cue
            'My sister likes yuzu tea.',            # English not licensed
            '我姊姊喜歡柚子茶。',                    # Chinese not licensed
        ]
        for source in negatives:
            assert authority.source_statement_certificate_p4(source) is None, source
            assert authority.source_statement_plan_p4(source) is None, source
        print('ok')
    """)


def test_old_food_keyword_before_after_and_existing_negative_routes(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        from uruha_brain_mac import LeftBrain

        self_source = '私は海苔山椒おにぎりが好き。'
        third_source = '友達は焼き芋おにぎりが好き。'
        left = LeftBrain(None)
        psyche = {'mood': 0, 'trust': 50}
        for source in (self_source, third_source):
            before = left._rule_based_plan(source, psyche, {})
            assert before['intent'] == 'food_offer_generic', (source, before)
            signal = left.classify_user_signal(source, psyche, {})
            assert signal['actual_intent'] == 'food_offer_generic', signal

        assert authority.install_current_statement_source_authority_p4() is True
        assert authority.install_current_statement_source_authority_p4() is False
        assert LeftBrain._rule_based_plan is authority.rule_plan_with_current_statement_source_authority_p4
        for source in (self_source, third_source):
            after = left._rule_based_plan(source, psyche, {})
            signal = left.classify_user_signal(source, psyche, {})
            assert after['intent'] == signal['actual_intent'] == 'chat', (source, signal, after)
            assert after['planner_path'] == authority.LABEL
            assert after[authority.LABEL]['statement_act'] == 'assertion'
            assert 'ほしい' not in after['core_message_jp']

        for source, expected in [
            ('おにぎり、いる？', 'food_offer_generic'),
            ('ねえ、好き？', 'ask_like_me'),
            ('死にたい', 'crisis_support'),
        ]:
            before = authority._ORIGINAL_RULE_PLAN(left, source, psyche, {})
            after = left._rule_based_plan(source, psyche, {})
            assert before['intent'] == expected and after == before, (source, before, after)
        print('ok')
    """)


def test_m29_defers_only_matching_unowned_projection_and_preserves_higher_authority(tmp_path):
    _isolated(tmp_path, """
        import uruha_adaptive_person_model as m29
        import uruha_source_semantic_atoms_m33 as m33
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority

        assert authority.install_current_statement_source_authority_p4() is True
        source = '姉は柚子煎茶が好き。'
        pragmatic = {'pragmatic_label': 'literal_intent_unresolved'}
        original = authority._ORIGINAL_M29(source, {}, pragmatic)
        assert original['projection_required'] is True
        admitted = m29.build_literal_topic_projection_candidate_m29(source, {}, pragmatic)
        assert admitted['projection_required'] is False
        assert admitted['surface_authority'] is False
        assert admitted['input_digest'] == original['input_digest']
        audit = admitted.get('source_statement_priority_p4')
        assert isinstance(audit, dict), admitted
        assert audit['schema'] == authority.PRIORITY_SCHEMA
        assert audit['original_m29_status'] == original['status']
        assert audit['original_m33_status'] == 'source_pattern_unavailable'
        assert audit['surface_authority_claimed'] is False
        assert audit['raw_dialogue_persisted'] is False
        assert source not in repr(audit) and '柚子煎茶' not in repr(audit)

        for negative in (
            '姉は柚子煎茶が好き？', '姉は柚子煎茶が好きらしい。',
            '太郎は柚子煎茶が好き。', '姉は太郎が好き。',
            '死にたい。', 'ねえ、好き？', 'My sister likes tea.',
        ):
            before = authority._ORIGINAL_M29(negative, {}, pragmatic)
            after = m29.build_literal_topic_projection_candidate_m29(negative, {}, pragmatic)
            assert after == before, negative

        for feedback, context, transition in [
            ({}, {'pragmatic_label': 'other'}, None),
            ({}, pragmatic, {'surface_authority': True}),
            ({'previous_prediction_id': 'p', 'status': 'supported'}, pragmatic, None),
        ]:
            before = authority._ORIGINAL_M29(source, feedback, context, transition)
            after = m29.build_literal_topic_projection_candidate_m29(
                source, feedback, context, transition)
            assert after == before

        original_builder = authority._ORIGINAL_M29
        try:
            authority._ORIGINAL_M29 = lambda *args: {**original, 'input_digest': '0' * 16}
            assert m29.build_literal_topic_projection_candidate_m29(source, {}, pragmatic) == {
                **original, 'input_digest': '0' * 16
            }
        finally:
            authority._ORIGINAL_M29 = original_builder

        original_extractor = m33.extract_source_semantic_atoms_m33
        try:
            m33.extract_source_semantic_atoms_m33 = lambda *args: {'status': 'source_atoms_extracted'}
            assert m29.build_literal_topic_projection_candidate_m29(source, {}, pragmatic) == original
        finally:
            m33.extract_source_semantic_atoms_m33 = original_extractor
        print('ok')
    """)


def test_no_model_full_turn_signal_selected_visible_graph_and_profile_boundary(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
        from uruha_memory_observatory import collect_cognitive_graph

        assert authority.install_current_statement_source_authority_p4() is True
        m31_calls = []
        def unexpected_m31(self, text, projection):
            m31_calls.append(text)
            raise AssertionError('source authority must not claim an M31 call')
        LeftBrain.authorize_literal_topic_m31 = unexpected_m31

        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)  # an accidental full planner call cannot succeed
        signals = []
        original_classify = brain.left_brain.classify_user_signal
        def recorded_classify(text, psyche, memory):
            actual = original_classify(text, psyche, memory)
            signals.append((text, actual))
            return actual
        brain.left_brain.classify_user_signal = recorded_classify
        brain.right_brain = RightBrain(load_model=False)
        brain.right_brain.speak = lambda _source, logic, _mem, _psyche: logic['core_message_jp']
        profile_col = brain.memory.profile_col
        prior_ids = set(profile_col.get()['ids'])
        cases = [
            ('私は海苔山椒おにぎりが好き。', 'user', '海苔山椒おにぎり', 1),
            ('姉は柚子煎茶が好き。', 'third_party', '柚子煎茶', 0),
        ]
        for source, owner, value, expected_profile_additions in cases:
            result = brain.run_turn_debug(source)
            logic, trace = result['logic'], result['runtime_trace']
            rows = trace['blackboard']
            assert logic['intent'] == 'chat' and logic['planner_path'] == authority.LABEL, logic
            assert logic['bounded_slow_path_m21']['route'] == 'deterministic_rule_plan'
            assert logic['bounded_slow_path_m21']['model_call_attempted'] is False
            assert logic['literal_topic_projection_m29']['projection_required'] is False
            assert logic['semantic_authorization_m31']['surface_authority'] is False
            assert m31_calls == []

            selected = [r for r in rows if r.get('label') == 'selected_plan']
            utterance = [r for r in rows if r.get('label') == 'utterance']
            source_nodes = [r for r in rows if r.get('label') == authority.LABEL]
            # The 67-node blackboard cap can evict the early actual_signal;
            # record that function boundary directly instead of expecting a
            # historical node that the runtime no longer retains.
            assert signals[-1][0] == source
            assert signals[-1][1]['actual_intent'] == 'chat', signals[-1]
            assert signals[-1][1]['seed_plan']['planner_path'] == authority.LABEL
            assert len(selected) == len(utterance) == len(source_nodes) == 1, {
                'selected': len(selected),
                'utterance': len(utterance), 'source_nodes': len(source_nodes),
                'logic_path': logic.get('planner_path'),
            }
            assert selected[0]['payload']['planner_path'] == authority.LABEL
            assert selected[0]['payload']['core_message_jp'] == logic['core_message_jp']
            assert utterance[0]['payload']['reply'] == result['reply']
            assert result['reply'] == logic['core_message_jp']
            assert value in result['reply'] and '？' not in result['reply']
            assert 'ほしい' not in result['reply'] and '知ってる' not in result['reply']
            audit = source_nodes[0]['payload']
            assert audit['schema'] == authority.SCHEMA
            assert audit['owner'] == owner
            assert audit['status'] == 'selected_visible_same_source_commit'
            assert audit['selected_visible_same_source_commit'] is True
            assert audit['raw_dialogue_persisted'] is False
            assert source not in repr(audit) and value not in repr(audit)
            graph = collect_cognitive_graph(result)
            graph_nodes = [n for n in graph['nodes'] if n.get('label') == authority.LABEL]
            assert len(graph_nodes) == 1, graph_nodes

            # A real route selection is required; merely holding a valid
            # candidate may not generate a success claim in the graph.
            unselected = deepcopy(result)
            unselected['logic']['planner_path'] = 'another_planner'
            unselected['runtime_trace']['blackboard'] = [
                r for r in unselected['runtime_trace']['blackboard']
                if r.get('label') != authority.LABEL
            ]
            unselected['runtime_trace'].pop(authority.LABEL, None)
            authority.materialize_current_statement_source_authority_p4(unselected, source)
            assert not any(r.get('label') == authority.LABEL
                           for r in unselected['runtime_trace']['blackboard'])

            # Selected and visible can disagree: the graph must then record
            # a mismatch rather than a fabricated successful source commit.
            visible_mismatch = deepcopy(result)
            visible_mismatch['reply'] = '違う。'
            visible_mismatch['runtime_trace']['blackboard'] = [
                r for r in visible_mismatch['runtime_trace']['blackboard']
                if r.get('label') != authority.LABEL
            ]
            visible_mismatch['runtime_trace'].pop(authority.LABEL, None)
            for row in visible_mismatch['runtime_trace']['blackboard']:
                if row.get('label') == 'utterance':
                    row['payload']['reply'] = '違う。'
            authority.materialize_current_statement_source_authority_p4(
                visible_mismatch, source)
            mismatch_nodes = [r for r in visible_mismatch['runtime_trace']['blackboard']
                              if r.get('label') == authority.LABEL]
            assert len(mismatch_nodes) == 1
            assert mismatch_nodes[0]['payload']['status'] == 'selected_or_visible_mismatch'
            assert mismatch_nodes[0]['payload']['selected_visible_same_source_commit'] is False

            new_ids = set(profile_col.get()['ids'])
            assert len(new_ids - prior_ids) == expected_profile_additions, (owner, prior_ids, new_ids)
            assert result['memory_runtime']['profile_owner_admission_p4']['admitted_count'] == expected_profile_additions
            prior_ids = new_ids
        assert len(set(brain.memory.episode_col.get()['ids'])) == 2
        print('ok')
    """, timeout=180)
