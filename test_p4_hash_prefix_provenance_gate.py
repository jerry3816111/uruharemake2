"""Development-exposed zero-model contracts; not a fresh Safari result."""

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


def test_launcher_cli_and_product_entry_are_bound(tmp_path):
    _isolated(tmp_path, """
        from pathlib import Path
        import p4_hash_prefix_gate_detached_control as controller
        import p4_reported_offer_scope_detached_control as prior
        import p4_offer_action_detached_control as action
        import p4_preference_fallback_detached_control as base
        import p4_preference_fallback_safe_isolated_product_launcher as launcher

        target = Path.cwd() / 'uruha_web_ui_product_p4_hash_prefix_gate.py'
        assert controller.ENTRYPOINT == target
        assert prior.ENTRYPOINT == action.ENTRYPOINT == base.ENTRYPOINT == launcher.ENTRYPOINT == target
        print('ok')
    """)
    completed = subprocess.run(
        [sys.executable, "p4_hash_prefix_gate_detached_control.py", "--help"],
        cwd=os.path.dirname(__file__), capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "verify-ready" in completed.stdout


def test_only_hash_added_prefix_is_removed_and_upstream_connective_survives(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question
        import uruha_selected_offer_action_surface_fidelity_p4 as offer
        import uruha_reported_offer_source_scope_p4 as reported
        import uruha_hash_prefix_provenance_gate_p4 as gate
        from uruha_brain_mac import RightBrain

        assert authority.install_current_statement_source_authority_p4()
        assert question.install_third_party_question_evidence_p4()
        assert offer.install_selected_offer_action_surface_fidelity_p4()
        assert reported.install_reported_offer_source_scope_p4()
        assert gate.install_hash_prefix_provenance_gate_p4()
        assert gate.install_hash_prefix_provenance_gate_p4() is False
        right = RightBrain(load_model=False)
        core = 'わかった。'
        observed = set()
        for n in range(1, 33):
            source = 'a' * n
            logic = {'intent': 'chat', 'scene': 'casual', 'surface_act': 'plain_reply'}
            legacy = gate._ORIGINAL_FINALIZE(right, core, logic, source, max_chars=80)
            added = next((p for p in gate._FIXED_PREFIXES if legacy == p + core), None)
            assert added is not None, (source, legacy)
            observed.add(added)
            actual = right._finalize_surface_reply(core, logic, source, max_chars=80)
            assert actual == core, (source, legacy, actual)
            assert logic[gate._EVENT_KEY][-1]['prefix'] == added
        assert observed == set(gate._FIXED_PREFIXES), observed

        for preauthored in ('先に、予定を確認しよ。', '一回、落ち着いてから話そ。'):
            logic = {'intent': 'chat', 'scene': 'casual', 'surface_act': 'plain_reply'}
            actual = right._finalize_surface_reply(preauthored, logic, '先に確認してから決めよう。', max_chars=80)
            assert actual == preauthored
        print('ok')
    """)


def test_new_final_audit_rejects_legacy_false_positive(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import uruha_reported_offer_source_scope_p4 as reported
        import uruha_hash_prefix_provenance_gate_p4 as gate

        core = '同僚におにぎりを一口勧められたのか。で、なんて返した？'
        logic = {'planner_path': reported.LABEL, 'core_message_jp': core}
        def result_with(reply):
            return {
                'logic': deepcopy(logic), 'reply': reply,
                'runtime_trace': {
                    'selected_plan': {'core_message_jp': core},
                    reported.LABEL: {
                        'status': 'visible_report_preserved',
                        'admission_proof_matches': True,
                        'selected_plan_matches_logic': True,
                        'utterance_matches_reply': True,
                        'final_report_faithful': True,
                    },
                    'blackboard': [
                        {'label': 'selected_plan', 'payload': {'core_message_jp': core}},
                        {'label': reported.LABEL, 'payload': {'status': 'visible_report_preserved'}},
                        {'label': 'utterance', 'payload': {'reply': reply}},
                    ],
                },
            }
        bad = result_with('先に、' + core)
        gate.materialize_hash_prefix_provenance_p4(bad)
        assert bad['runtime_trace'][gate.LABEL]['status'] == 'unlicensed_fixed_prefix_visible'
        assert bad['runtime_trace'][gate.LABEL]['visible_core_exact'] is False
        assert bad['runtime_trace'][reported.LABEL]['status'] == 'visible_report_preserved'
        good = result_with(core)
        gate.materialize_hash_prefix_provenance_p4(good)
        assert good['runtime_trace'][gate.LABEL]['status'] == 'visible_core_exact'
        assert good['runtime_trace'][gate.LABEL]['utterance_matches_reply'] is True
        good['runtime_trace'][reported.LABEL]['admission_proof_matches'] = False
        gate.materialize_hash_prefix_provenance_p4(good)
        assert good['runtime_trace'][gate.LABEL]['status'] == 'selected_or_visible_mismatch'
        good['runtime_trace'][reported.LABEL]['admission_proof_matches'] = True
        good['runtime_trace']['blackboard'][-1]['payload']['reply'] = '別の文。'
        gate.materialize_hash_prefix_provenance_p4(good)
        assert good['runtime_trace'][gate.LABEL]['status'] == 'selected_or_visible_mismatch'
        print('ok')
    """)


def test_isolated_turn_graph_and_direct_control(tmp_path):
    _isolated(tmp_path, """
        import uruha_web_ui_product_p4_preference_fallback
        import uruha_current_statement_source_authority_p4 as authority
        import uruha_third_party_question_evidence_p4 as question
        import uruha_selected_offer_action_surface_fidelity_p4 as offer
        import uruha_reported_offer_source_scope_p4 as reported
        import uruha_hash_prefix_provenance_gate_p4 as gate
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
        from uruha_memory_observatory import collect_cognitive_graph

        assert authority.install_current_statement_source_authority_p4()
        assert question.install_third_party_question_evidence_p4()
        assert offer.install_selected_offer_action_surface_fidelity_p4()
        assert reported.install_reported_offer_source_scope_p4()
        assert gate.install_hash_prefix_provenance_gate_p4()
        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)
        brain.right_brain = RightBrain(load_model=False)
        before = set(brain.memory.profile_col.get()['ids'])
        source = '同僚に「味噌焼きおにぎり、一口いる？」って言われた。'
        result = brain.run_turn_debug(source)
        core = result['logic']['core_message_jp']
        assert result['reply'] == core, result['reply']
        assert result['runtime_trace'][reported.LABEL]['status'] == 'visible_report_preserved', result['runtime_trace'][reported.LABEL]
        assert result['runtime_trace'][gate.LABEL]['status'] == 'visible_core_exact', result['runtime_trace'][gate.LABEL]
        # This fake-generation contract already yields the core. The separate
        # finalizer test exercises removal; Safari must measure the live path.
        assert result['runtime_trace'][gate.LABEL]['final_related_hash_additions_removed'] == 0
        graph = collect_cognitive_graph(result)
        nodes = [n for n in graph['nodes'] if str(n.get('trace_id') or '').endswith(':' + gate.LABEL)]
        prior_nodes = [n for n in graph['nodes'] if str(n.get('trace_id') or '').endswith(':' + reported.LABEL)]
        assert len(nodes) == 1, nodes
        assert len(prior_nodes) == 1, prior_nodes
        assert any(e['source'] == prior_nodes[0]['id'] and e['target'] == nodes[0]['id']
                   for e in graph['edges']), graph['edges']
        assert graph['nodes'][-1]['signal'] == result['reply']
        assert set(brain.memory.profile_col.get()['ids']) == before

        direct = brain.run_turn_debug('塩ポテト、一口いる？')
        assert direct['logic']['surface_act'] == 'named_offer_accept'
        assert reported.LABEL not in direct['runtime_trace']
        assert gate.LABEL not in direct['runtime_trace']
        assert direct['runtime_trace'][offer.LABEL]['status'] == 'visible_action_preserved'
        assert set(brain.memory.profile_col.get()['ids']) == before
        print('ok')
    """, timeout=240)
