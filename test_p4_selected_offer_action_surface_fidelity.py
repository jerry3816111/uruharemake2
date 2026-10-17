"""Developer-only, zero-model contracts for a selected food-offer action.

The diagnostic source and food below are not the exposed Safari T2 and are
not prospective Safari gold.  These tests establish only a narrow product
mechanism, not general pragmatic understanding or a model comparison.
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


def test_selected_offer_contract_requires_direct_grounded_selected_action(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import uruha_selected_offer_action_surface_fidelity_p4 as fidelity

        source = '塩ポテト、一口いる？'
        logic = {
            'intent': 'food_offer_generic',
            'scene': 'casual',
            'surface_act': 'named_offer_accept',
            'dialogue_act': 'concrete_offer_response',
            'core_message_jp': 'ポテトなら普通にもらう。',
            'grounding': {'offered_item': 'ポテト'},
            'constraints': {'max_chars': 80},
            'memory_use_expected': False,
        }
        contract = fidelity.selected_offer_contract_p4(source, logic)
        assert isinstance(contract, dict), contract
        assert fidelity.offer_reply_status_p4(
            'ポテトなら普通にもらう。', contract)['status'] == 'action_preserved'

        # A matching source alone cannot replace a different selected act.
        for key, value in (
            ('intent', 'chat'),
            ('surface_act', 'plain_reply'),
            ('dialogue_act', 'topic_proposal'),
        ):
            changed = deepcopy(logic)
            changed[key] = value
            assert fidelity.selected_offer_contract_p4(source, changed) is None, (key, value)
        for item in ('', 'おにぎり', None):
            changed = deepcopy(logic)
            changed['grounding']['offered_item'] = item
            assert fidelity.selected_offer_contract_p4(source, changed) is None, item
        changed = deepcopy(logic)
        changed['memory_use_expected'] = True
        assert fidelity.selected_offer_contract_p4(source, changed) is None
        for core in (
            'ポテトはいらない。', '焼き栗ならもらう。',
            'ポテトなら食べるな。', 'ポテトならもらう。いや、いらん。',
        ):
            changed = deepcopy(logic)
            changed['core_message_jp'] = core
            assert fidelity.selected_offer_contract_p4(source, changed) is None, core
        for scene in ('crisis', 'boundary', 'refusal', 'ooc_defense'):
            changed = deepcopy(logic)
            changed['scene'] = scene
            assert fidelity.selected_offer_contract_p4(source, changed) is None, scene
        print('ok')
    """)


def test_offer_source_admission_fails_closed_on_other_speech_acts(tmp_path):
    _isolated(tmp_path, """
        import uruha_selected_offer_action_surface_fidelity_p4 as fidelity

        logic = {
            'intent': 'food_offer_generic',
            'scene': 'casual',
            'surface_act': 'named_offer_accept',
            'dialogue_act': 'concrete_offer_response',
            'core_message_jp': 'ポテトなら普通にもらう。',
            'grounding': {'offered_item': 'ポテト'},
            'constraints': {'max_chars': 80},
            'memory_use_expected': False,
        }
        negatives = [
            '先生は塩ポテト、一口いる？',
            '先生は塩ポテトが好き？',
            '先生は塩ポテトが好き。',
            '私は塩ポテトが好き。',
            '塩ポテトって好き？',
            '「塩ポテト、一口いる？」',
            '誰かが「塩ポテト、一口いる？」と言った。',
            'もし塩ポテトなら、一口いる？',
            '塩ポテトじゃないけど、一口いる？',
            '塩ポテト、一口いる？今日は寒いね。',
            '塩ポテト、一口いる？\\nそれとも飲み物？',
            '前に話した塩ポテト、一口いる？',
            '死にたい。塩ポテト、一口いる？',
            '毒ポテト、一口いる？',
            '腐敗ポテト、一口いる？',
            '你要吃一口鹽薯條嗎？',
            'Would you like a bite of salted fries?',
        ]
        for source in negatives:
            assert fidelity.selected_offer_contract_p4(source, logic) is None, source
        assert fidelity.selected_offer_contract_p4('塩ポテト、一口いる？', {}) is None
        print('ok')
    """)


def test_visible_offer_validator_rejects_nonanswers_and_contradictions(tmp_path):
    _isolated(tmp_path, """
        import uruha_selected_offer_action_surface_fidelity_p4 as fidelity

        logic = {
            'intent': 'food_offer_generic', 'scene': 'casual',
            'surface_act': 'named_offer_accept',
            'dialogue_act': 'concrete_offer_response',
            'core_message_jp': 'ポテトなら普通にもらう。',
            'grounding': {'offered_item': 'ポテト'},
            'constraints': {'max_chars': 80},
        }
        contract = fidelity.selected_offer_contract_p4('塩ポテト、一口いる？', logic)
        assert contract is not None
        for reply in (
            'ポテトなら普通にもらう。',
            'ポテトなら一口くれ。',
            'ポテトなら少し食べる。',
            'まあ、ポテトなら一口ほしい。今それくらいがちょうどいい。',
            'ポテトなら普通にあり。少しもらう。',
        ):
            audit = fidelity.offer_reply_status_p4(reply, contract)
            assert audit['status'] == 'action_preserved', (reply, audit)
            assert audit['item_present'] is True and audit['affirmative_acceptance'] is True

        negatives = [
            '今は昼のゆるい感じだけど、その話なら普通に分かる。',
            'ポテトは普通にあり。',  # "あり" by itself is not an acceptance.
            'ポテト、一口？',
            'ポテトなら食べない。',
            'ポテトならもらわない。',
            'ポテトなら欲しくない。',
            'ポテトなら食べる？',
            'ポテトを食べてくれ。',  # Asks the user to eat; not my acceptance.
            'ポテトを分けてあげる。',  # Offers mine away; not taking this offer.
            'ポテトなら食べるつもりはない。',
            'ポテトなら食べるな。',
            'ポテトはもらうな。',
            'ポテト、食べるのはやめよう。',
            'ポテトの話はいいから、焼き栗ならもらう。',
            '君はポテトを食べる。',
            '弟はポテトならもらう。',
            '子供はポテトならもらう。',
            'ポテトならもらう。いや、いらん。',
            'ポテトならもらう。いや、焼き栗にする。',
            'ポテトならもらう。いや、食べない。',
            'ポテトは食べないけど、少しもらう。',
            '焼き栗ならもらう。',  # An affirmative answer about the wrong item.
            '「ポテトならもらう」って言った。',
            'もしポテトならもらう。',
            '先生はポテトをもらう。',
            'またポテトならもらう。',  # No repeat evidence in the source.
            'さっきからポテトをもらう。',
        ]
        for reply in negatives:
            audit = fidelity.offer_reply_status_p4(reply, contract)
            assert audit['status'] == 'action_mismatch', (reply, audit)
        wrong_item = fidelity.offer_reply_status_p4('焼き栗ならもらう。', contract)
        assert wrong_item['item_present'] is False
        same_item_negation = fidelity.offer_reply_status_p4('ポテトなら食べない。', contract)
        assert same_item_negation['item_present'] is True
        assert same_item_negation['affirmative_acceptance'] is False
        print('ok')
    """)


def test_post_refine_fallback_preserves_action_without_changing_other_routes(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question_gate
        from uruha_brain_mac import RightBrain

        assert authority.install_current_statement_source_authority_p4() is True
        assert question_gate.install_third_party_question_evidence_p4() is True

        # Install against a deterministic legacy candidate in this process.
        # The product overlay may choose an existing speech variant or core;
        # it must not synthesize a new promise or rewrite a non-admitted reply.
        original_refine = RightBrain._refine_conversational_reply
        def legacy_refine(self, reply, logic_data, user_input, memory_data=None):
            return 'その話なら普通に分かる。'
        RightBrain._refine_conversational_reply = legacy_refine
        try:
            import uruha_selected_offer_action_surface_fidelity_p4 as fidelity
            assert fidelity.install_selected_offer_action_surface_fidelity_p4() is True
            assert fidelity.install_selected_offer_action_surface_fidelity_p4() is False
            right = RightBrain(load_model=False)
            logic = {
                'intent': 'food_offer_generic', 'scene': 'casual',
                'surface_act': 'named_offer_accept',
                'dialogue_act': 'concrete_offer_response',
                'core_message_jp': 'ポテトなら普通にもらう。',
                'grounding': {'offered_item': 'ポテト'},
                'constraints': {'max_chars': 80},
                'memory_use_expected': False,
            }
            selected = {key: deepcopy(logic[key]) for key in (
                'intent', 'surface_act', 'dialogue_act', 'grounding', 'core_message_jp')}
            source = '塩ポテト、一口いる？'
            repaired = right._refine_conversational_reply(
                '元の候補。', logic, source, memory_data={})
            contract = fidelity.selected_offer_contract_p4(source, logic)
            assert contract is not None
            assert fidelity.offer_reply_status_p4(repaired, contract)['status'] == 'action_preserved', repaired
            assert 'また' not in repaired and 'さっきから' not in repaired
            assert {key: logic[key] for key in selected} == selected

            for negative in (
                '「塩ポテト、一口いる？」',
                '先生は塩ポテトが好き？',
                '你要一口鹽薯條嗎？',
                'Would you like a bite of salted fries?',
            ):
                unchanged = right._refine_conversational_reply(
                    '元の候補。', deepcopy(logic), negative, memory_data={})
                assert unchanged == 'その話なら普通に分かる。', (negative, unchanged)
        finally:
            RightBrain._refine_conversational_reply = original_refine
        print('ok')
    """)


def test_model_candidate_eligibility_is_not_reopened_by_offer_overlay(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question_gate
        from uruha_brain_mac import RightBrain
        import uruha_selected_offer_action_surface_fidelity_p4 as fidelity

        assert authority.install_current_statement_source_authority_p4() is True
        assert question_gate.install_third_party_question_evidence_p4() is True

        right = RightBrain(load_model=False)
        right.model_blend_enabled = True
        right.model, right.tokenizer = object(), object()
        logic = {
            'intent': 'food_offer_generic', 'scene': 'casual',
            'surface_act': 'named_offer_accept',
            'dialogue_act': 'concrete_offer_response',
            'core_message_jp': 'ポテトなら普通にもらう。',
            'grounding': {'offered_item': 'ポテト'},
            'constraints': {'max_chars': 80},
        }
        groups_before = right._model_required_semantic_groups(logic)
        reason_before = right._model_surface_disabled_reason(logic)
        assert groups_before == [] and reason_before == 'missing_semantic_contract'
        assert fidelity.install_selected_offer_action_surface_fidelity_p4() is True
        assert right._model_required_semantic_groups(logic) == groups_before
        assert right._model_surface_disabled_reason(logic) == reason_before
        assert right._model_surface_candidates_allowed(logic) is False
        print('ok')
    """)


def test_final_surface_audit_reports_late_mismatch_instead_of_candidate_success(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import uruha_selected_offer_action_surface_fidelity_p4 as fidelity

        source = '塩ポテト、一口いる？'
        logic = {
            'intent': 'food_offer_generic', 'scene': 'casual',
            'surface_act': 'named_offer_accept',
            'dialogue_act': 'concrete_offer_response',
            'core_message_jp': 'ポテトなら普通にもらう。',
            'grounding': {'offered_item': 'ポテト'},
            'constraints': {'max_chars': 80},
            fidelity.LABEL + '_candidate': {
                'candidate_selection': 'existing_speech_or_core_candidate',
                'returned_candidate_status': 'action_preserved',
            },
        }
        selected = deepcopy(logic)
        # Simulate a later surface guard replacing an accepted candidate.
        final = 'その話なら普通に分かる。'
        result = {
            'logic': logic, 'reply': final,
            'runtime_trace': {
                'selected_plan': selected,
                'blackboard': [
                    {'label': 'selected_plan', 'payload': deepcopy(selected)},
                    {'label': 'utterance', 'payload': {'reply': final}},
                ],
            },
        }
        fidelity.materialize_selected_offer_action_surface_fidelity_p4(result, source)
        audit = result['runtime_trace'][fidelity.LABEL]
        assert audit['status'] == 'selected_or_visible_action_mismatch', audit
        assert audit['candidate_status'] == 'action_preserved', audit
        assert audit['utterance_matches_reply'] is True, audit
        assert audit['affirmative_acceptance'] is False, audit

        # Even a positive surface cannot override a different selected item.
        result['reply'] = 'ポテトなら普通にもらう。'
        result['runtime_trace']['blackboard'][-1]['payload']['reply'] = result['reply']
        result['runtime_trace']['selected_plan']['grounding']['offered_item'] = 'おにぎり'
        fidelity.materialize_selected_offer_action_surface_fidelity_p4(result, source)
        audit = result['runtime_trace'][fidelity.LABEL]
        assert audit['status'] == 'selected_or_visible_action_mismatch', audit
        assert audit['selected_plan_matches_logic'] is False, audit
        print('ok')
    """)


def test_no_model_full_turn_final_reply_and_graph_agree(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question_gate
        import uruha_selected_offer_action_surface_fidelity_p4 as fidelity
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
        from uruha_memory_observatory import collect_cognitive_graph

        assert authority.install_current_statement_source_authority_p4() is True
        assert question_gate.install_third_party_question_evidence_p4() is True
        assert fidelity.install_selected_offer_action_surface_fidelity_p4() is True
        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)
        brain.right_brain = RightBrain(load_model=False)
        source = '塩ポテト、一口いる？'
        before_profile = set(brain.memory.profile_col.get()['ids'])
        result = brain.run_turn_debug(source)
        logic, trace = result['logic'], result['runtime_trace']
        assert logic['intent'] == 'food_offer_generic', logic
        assert logic['surface_act'] == 'named_offer_accept', logic
        assert logic['dialogue_act'] == 'concrete_offer_response', logic
        assert logic['grounding']['offered_item'] == 'ポテト', logic
        contract = fidelity.selected_offer_contract_p4(source, logic)
        assert contract is not None
        assert fidelity.offer_reply_status_p4(result['reply'], contract)['status'] == 'action_preserved', result
        selected_index = next(i for i, row in enumerate(trace['blackboard'])
                              if row.get('label') == 'selected_plan')
        audit_row = trace['blackboard'][selected_index + 1]
        assert audit_row['label'] == fidelity.LABEL, audit_row
        assert audit_row['payload']['status'] == 'visible_action_preserved', {
            'audit': audit_row['payload'],
            'selected': {key: trace['selected_plan'].get(key) for key in
                         ('intent', 'surface_act', 'core_message_jp')},
            'selected_row': {key: trace['blackboard'][selected_index]['payload'].get(key)
                             for key in ('intent', 'surface_act', 'core_message_jp')},
            'logic': {key: logic.get(key) for key in
                      ('intent', 'surface_act', 'core_message_jp')},
        }
        utterances = [r for r in trace['blackboard'] if r.get('label') == 'utterance']
        assert len(utterances) == 1 and utterances[0]['payload']['reply'] == result['reply']
        assert brain.right_brain.history[-1]['content'] == result['reply']
        graph = collect_cognitive_graph(result)
        # Graph labels are UI-truncated; exact provenance lives in trace_id.
        nodes = [n for n in graph['nodes']
                 if str(n.get('trace_id') or '').endswith(':' + fidelity.LABEL)]
        assert len(nodes) == 1, [n.get('trace_id') for n in graph['nodes']]
        selected_nodes = [n for n in graph['nodes']
                          if str(n.get('trace_id') or '').endswith(':selected_plan')]
        assert len(selected_nodes) == 1
        assert any(edge['source'] == selected_nodes[0]['id']
                   and edge['target'] == nodes[0]['id']
                   and edge['class'] == 'is-main' for edge in graph['edges'])
        assert set(brain.memory.profile_col.get()['ids']) == before_profile
        print('ok')
    """, timeout=180)
