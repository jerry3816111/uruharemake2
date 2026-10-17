"""Developer-only, zero-model contracts for bounded reported-offer scope.

A passing contract does not prove a fresh browser turn or human understanding.
These examples are development-exposed, not prospective gold.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap


def _isolated(tmp_path, program, *, timeout=180):
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


def test_detached_controller_binds_final_argv_to_new_entrypoint(tmp_path):
    _isolated(tmp_path, """
        from pathlib import Path
        import p4_reported_offer_scope_detached_control as scope_controller
        import p4_offer_action_detached_control as prior_wrapper
        import p4_preference_fallback_detached_control as base_controller
        import p4_preference_fallback_safe_isolated_product_launcher as launcher

        target = Path.cwd() / 'uruha_web_ui_product_p4_reported_offer_scope.py'
        assert scope_controller.ENTRYPOINT == target
        assert prior_wrapper.ENTRYPOINT == target
        assert base_controller.ENTRYPOINT == target
        assert launcher.ENTRYPOINT == target
        assert base_controller.main is prior_wrapper.controller.main
        print('ok')
    """)

    # Import-time identity alone missed a previous bad wrapper.main call.
    # Execute the real CLI, but use --help so no service or DB is started.
    completed = subprocess.run(
        [sys.executable, "p4_reported_offer_scope_detached_control.py", "--help"],
        cwd=os.path.dirname(__file__), capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "verify-ready" in completed.stdout


def test_certificate_is_a_narrow_whole_sentence_report_not_quote_presence(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import uruha_reported_offer_source_scope_p4 as scope

        positives = [
            '同僚に「塩ポテト、一口いる？」と聞かれた。',
            '先輩に『焼きポテト、一口いる？』って言われた。',
        ]
        seed = scope._reproducible_prior_seed(positives[0])
        for source in positives:
            cert = scope.reported_offer_certificate_p4(source, seed)
            assert cert is not None, source
            assert cert['reported_item_sha256'] == scope._sha('ポテト')
            assert cert['addressee'] == 'reported_user'
            assert cert['event_truth'] == 'unknown_user_report_only'
            assert cert['profile_write_authority'] == 'none'
            plan = scope.reported_offer_plan_p4(source, seed)
            assert plan['intent'] == 'chat' and plan['surface_act'] == 'plain_reply'
            assert plan['core_message_jp'].endswith('なんて返した？')
            assert 'ほしい' not in plan['core_message_jp']

        negatives = [
            '塩ポテト、一口いる？',  # Actual direct offer.
            '友人に「塩ポテト、一口いる？」と言われた。でも、焼きおにぎり、一口いる？',
            '「新作」チーズピザ、一口いる？',  # Quoted product name.
            '友人に「一口いる？」と聞かれた。どう返す？',  # Advice request.
            '友人に「塩ポテト、一口いる？」と言われた。どう返そう？',
            '友人に「塩ポテト、一口いる？」と言われた。いや、断った。',
            'もし友人に「塩ポテト、一口いる？」と言われたら？',
            '友人に「塩ポテト、一口いる？」と言ってほしい。',
            '友人に「塩ポテト、一口いる？と言われた。',  # Unpaired quote.
            '友人に「塩ポテト、一口いる？」と聞かれた？',
            '友人に「毒ポテト、一口いる？」と聞かれた。',
            '死にたい。友人に「塩ポテト、一口いる？」と聞かれた。',
            '友人は塩ポテトが好き？',
            '友人は塩ポテトが好き。',
            '私は塩ポテトが好き。',
            '朋友問我要不要吃一口薯條。',
            'A coworker asked if I wanted some fries.',
        ]
        for source in negatives:
            assert scope.reported_offer_certificate_p4(source, seed) is None, source
        for key, value in [
            ('intent', 'chat'), ('scene', 'support'), ('surface_act', 'plain_reply'),
        ]:
            changed = deepcopy(seed)
            changed[key] = value
            assert scope.reported_offer_certificate_p4(positives[0], changed) is None
        changed = deepcopy(seed)
        changed['grounding']['offered_item'] = 'おにぎり'
        assert scope.reported_offer_certificate_p4(positives[0], changed) is None
        changed = deepcopy(seed)
        changed['core_message_jp'] = 'ポテトなら普通にもらう。'
        assert scope.reported_offer_certificate_p4(positives[0], changed) is None
        print('ok')
    """)


def test_product_gate_changes_only_certified_legacy_offer_seed(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question
        import uruha_selected_offer_action_surface_fidelity_p4 as offer
        import uruha_reported_offer_source_scope_p4 as scope
        from uruha_brain_mac import LeftBrain

        assert authority.install_current_statement_source_authority_p4()
        assert question.install_third_party_question_evidence_p4()
        assert offer.install_selected_offer_action_surface_fidelity_p4()
        assert scope.install_reported_offer_source_scope_p4()
        assert scope.install_reported_offer_source_scope_p4() is False
        left = LeftBrain(None)
        source = '同僚に「塩ポテト、一口いる？」と聞かれた。'
        before = scope._ORIGINAL_RULE_PLAN(left, source, {}, {})
        assert before['intent'] == 'food_offer_generic', before
        changed = left._rule_based_plan(source, {}, {})
        assert changed['intent'] == 'chat' and changed['surface_act'] == 'plain_reply', changed
        assert changed['grounding']['reported_role'] == '同僚', changed
        assert changed['grounding']['reported_item'] == 'ポテト', changed
        assert changed[scope.LABEL]['prior_selected_intent'] == 'food_offer_generic'

        for negative in (
            '塩ポテト、一口いる？',
            '友人に「塩ポテト、一口いる？」と言われた。でも、焼きおにぎり、一口いる？',
            '「新作」チーズピザ、一口いる？',
            '友人に「一口いる？」と聞かれた。どう返す？',
            '友人に「塩ポテト、一口いる？」と言われた。どう返そう？',
            '先生は塩ポテトが好き？',
            '先生は塩ポテトが好き。',
            '私は塩ポテトが好き。',
            '死にたい。塩ポテト、一口いる？',
            '你要吃一口薯條嗎？',
            'Would you like a bite of fries?',
        ):
            prior = scope._ORIGINAL_RULE_PLAN(left, negative, {}, {})
            current = left._rule_based_plan(negative, {}, {})
            assert current == prior, (negative, prior, current)
            assert scope.LABEL not in (current or {}), negative
        print('ok')
    """)


def test_refine_uses_selected_core_and_final_audit_fails_closed(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question
        import uruha_selected_offer_action_surface_fidelity_p4 as offer
        import uruha_reported_offer_source_scope_p4 as scope
        from uruha_brain_mac import RightBrain

        assert authority.install_current_statement_source_authority_p4()
        assert question.install_third_party_question_evidence_p4()
        assert offer.install_selected_offer_action_surface_fidelity_p4()
        assert scope.install_reported_offer_source_scope_p4()
        source = '同僚に「塩ポテト、一口いる？」と聞かれた。'
        seed = scope._reproducible_prior_seed(source)
        logic = scope.reported_offer_plan_p4(source, seed)
        logic['dialogue_act'] = 'direct_chat_answer'
        logic['bounded_slow_path_m21'] = {
            'route': 'deterministic_rule_plan', 'model_call_attempted': False,
        }
        right = RightBrain(load_model=False)
        refined = right._refine_conversational_reply(
            'ポテトなら一口ほしい。', logic, source, memory_data={})
        assert refined == logic['core_message_jp'], refined
        assert logic[scope.LABEL + '_candidate']['selection'] == 'existing_selected_core_candidate'
        selected = deepcopy(logic)
        result = {
            'logic': logic, 'reply': refined,
            'runtime_trace': {
                'selected_plan': deepcopy(selected),
                'blackboard': [
                    {'label': 'selected_plan', 'payload': deepcopy(selected)},
                    {'label': 'utterance', 'payload': {'reply': refined}},
                ],
            },
        }
        scope.materialize_reported_offer_scope_p4(result, source)
        audit = result['runtime_trace'][scope.LABEL]
        assert audit['status'] == 'visible_report_preserved', audit
        assert audit['browser_bubble_observed'] is False
        assert audit['final_direct_acceptance'] is False
        assert audit['admission_proof_matches'] is True
        assert result['runtime_trace']['blackboard'][1]['label'] == scope.LABEL

        # A self-consistent selected/logic/utterance triple is not enough:
        # dropped or altered admission proof must fail closed at final audit.
        for changed_key, changed_value in (
            ('admission_sha32', None),
            ('prior_core_sha32', '0' * 32),
            ('quoted_sha32', 'f' * 32),
        ):
            tampered = deepcopy(result)
            for container in (
                tampered['logic'],
                tampered['runtime_trace']['selected_plan'],
                tampered['runtime_trace']['blackboard'][0]['payload'],
            ):
                if changed_value is None:
                    container['grounding'].pop(changed_key)
                else:
                    container['grounding'][changed_key] = changed_value
            scope.materialize_reported_offer_scope_p4(tampered, source)
            failed = tampered['runtime_trace'][scope.LABEL]
            assert failed['status'] == 'selected_or_visible_mismatch', (changed_key, failed)
            assert failed['admission_proof_matches'] is False, (changed_key, failed)

        result['reply'] = 'ポテトなら一口ほしい。'
        result['runtime_trace']['blackboard'][-1]['payload']['reply'] = result['reply']
        scope.materialize_reported_offer_scope_p4(result, source)
        audit = result['runtime_trace'][scope.LABEL]
        assert audit['status'] == 'selected_or_visible_mismatch', audit
        assert audit['final_direct_acceptance'] is True
        assert audit['utterance_matches_reply'] is True
        result['runtime_trace']['blackboard'].pop()
        del result['runtime_trace'][scope.LABEL]
        scope.materialize_reported_offer_scope_p4(result, source)
        assert scope.LABEL not in result['runtime_trace']
        print('ok')
    """)


def test_no_model_full_turn_report_and_graph_agree_without_profile_write(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question
        import uruha_selected_offer_action_surface_fidelity_p4 as offer
        import uruha_reported_offer_source_scope_p4 as scope
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
        from uruha_memory_observatory import collect_cognitive_graph

        assert authority.install_current_statement_source_authority_p4()
        assert question.install_third_party_question_evidence_p4()
        assert offer.install_selected_offer_action_surface_fidelity_p4()
        assert scope.install_reported_offer_source_scope_p4()
        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)
        brain.right_brain = RightBrain(load_model=False)
        source = '同僚に「塩ポテト、一口いる？」と聞かれた。'
        before = set(brain.memory.profile_col.get()['ids'])
        result = brain.run_turn_debug(source)
        logic, trace = result['logic'], result['runtime_trace']
        assert logic['intent'] == 'chat' and logic['surface_act'] == 'plain_reply', logic
        assert logic['dialogue_act'] == 'direct_chat_answer', logic
        assert logic['planner_path'] == scope.LABEL, logic
        assert scope._surface_status(result['reply'], logic['core_message_jp']), result['reply']
        assert trace[scope.LABEL]['status'] == 'visible_report_preserved', trace[scope.LABEL]
        assert trace[scope.LABEL]['utterance_matches_reply'] is True
        assert trace[scope.LABEL]['final_direct_acceptance'] is False
        assert set(brain.memory.profile_col.get()['ids']) == before
        graph = collect_cognitive_graph(result)
        scope_nodes = [node for node in graph['nodes']
                       if str(node.get('trace_id') or '').endswith(':' + scope.LABEL)]
        selected_nodes = [node for node in graph['nodes']
                          if str(node.get('trace_id') or '').endswith(':selected_plan')]
        assert len(scope_nodes) == len(selected_nodes) == 1, graph
        assert any(edge['source'] == selected_nodes[0]['id']
                   and edge['target'] == scope_nodes[0]['id']
                   and edge['class'] == 'is-main' for edge in graph['edges'])
        assert graph['nodes'][-1]['signal'] == result['reply'], graph['nodes'][-1]

        direct = brain.run_turn_debug('塩ポテト、一口いる？')
        assert direct['logic']['intent'] == 'food_offer_generic', direct['logic']
        assert direct['logic']['surface_act'] == 'named_offer_accept', direct['logic']
        assert scope.LABEL not in direct['runtime_trace'], direct['runtime_trace'].get(scope.LABEL)
        assert direct['runtime_trace'][offer.LABEL]['status'] == 'visible_action_preserved'
        assert set(brain.memory.profile_col.get()['ids']) == before
        print('ok')
    """, timeout=240)
