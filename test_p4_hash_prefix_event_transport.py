"""Zero-model transport contracts, separate from prospective Safari inputs."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap


_CHAIN = """
import uruha_web_ui_product_p4_preference_fallback
import uruha_current_statement_source_authority_p4 as authority
import uruha_third_party_question_evidence_p4 as question
import uruha_selected_offer_action_surface_fidelity_p4 as offer
import uruha_reported_offer_source_scope_p4 as reported
import uruha_hash_prefix_provenance_gate_p4 as gate
import uruha_hash_prefix_event_transport_p4 as transport
from uruha_brain_mac import RightBrain

assert authority.install_current_statement_source_authority_p4()
assert question.install_third_party_question_evidence_p4()
assert offer.install_selected_offer_action_surface_fidelity_p4()
assert reported.install_reported_offer_source_scope_p4()
assert gate.install_hash_prefix_provenance_gate_p4()
"""


def _isolated(tmp_path, program, *, timeout=240):
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


def test_opt_in_entry_and_detached_cli(tmp_path):
    _isolated(tmp_path, """
        from pathlib import Path
        import p4_hash_prefix_transport_detached_control as controller
        import p4_hash_prefix_gate_detached_control as prior
        import p4_reported_offer_scope_detached_control as reported
        import p4_offer_action_detached_control as action
        import p4_preference_fallback_detached_control as base
        import p4_preference_fallback_safe_isolated_product_launcher as launcher
        import uruha_hash_prefix_event_transport_p4 as transport

        target = Path.cwd() / 'uruha_web_ui_product_p4_hash_prefix_transport.py'
        assert controller.ENTRYPOINT == target
        assert prior.ENTRYPOINT == reported.ENTRYPOINT == action.ENTRYPOINT == base.ENTRYPOINT == launcher.ENTRYPOINT == target
        assert transport._INSTALLED is False
        try:
            transport.install_hash_prefix_event_transport_p4()
        except RuntimeError as exc:
            assert str(exc).endswith('prior_product_chain_changed')
        else:
            raise AssertionError('transport installed outside the prior chain')
        print('ok')
    """)
    completed = subprocess.run(
        [sys.executable, "p4_hash_prefix_transport_detached_control.py", "--help"],
        cwd=os.path.dirname(__file__), capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "verify-ready" in completed.stdout


def test_real_full_speak_crosses_copy_without_changing_reply_and_graph_binds_final(tmp_path):
    _isolated(tmp_path, _CHAIN + textwrap.dedent("""
        from copy import deepcopy
        import hashlib
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager
        from uruha_memory_observatory import collect_cognitive_graph

        # Already-exposed development input, never one of the next Safari cases.
        source = '同僚に「味噌焼きおにぎり、一口いる？」って言われた。'
        def plan():
            return reported.reported_offer_plan_p4(source, reported._reproducible_prior_seed(source))
        before_logic = plan()
        before_right = RightBrain(load_model=False)
        before_reply = before_right.speak(source, before_logic, {}, {})
        assert gate._EVENT_KEY not in before_logic

        assert transport.install_hash_prefix_event_transport_p4()
        assert transport.install_hash_prefix_event_transport_p4() is False
        after_logic = plan()
        after_right = RightBrain(load_model=False)
        after_reply = after_right.speak(source, after_logic, {}, {})
        assert after_reply == before_reply == after_logic['core_message_jp']
        assert after_logic.get('model_surface_selection') == before_logic.get('model_surface_selection')
        events = after_logic[gate._EVENT_KEY]
        assert len(events) == 1, events
        event = events[0]
        digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest()
        assert event['prefix'] == '先に、'
        assert event['selected_candidate_sha256'] == event['returned_candidate_sha256'] == digest(after_reply)
        assert event['legacy_candidate_sha256'] == digest(event['prefix'] + after_reply)
        assert all(isinstance(value, str) for value in event.values())
        assert source not in str(event) and after_reply not in str(event)

        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)
        brain.right_brain = RightBrain(load_model=False)
        before_profile = set(brain.memory.profile_col.get()['ids'])
        result = brain.run_turn_debug(source)
        assert result['reply'] == after_reply
        assert result['logic'][gate._EVENT_KEY] == events
        audit = result['runtime_trace'][gate.LABEL]
        assert audit['status'] == 'visible_core_exact', audit
        assert audit['final_related_hash_additions_removed'] == 1, audit
        assert audit['removed_prefixes'] == ['先に、']
        assert result['runtime_trace'][reported.LABEL]['admission_proof_matches'] is True
        graph = collect_cognitive_graph(result)
        assert graph['nodes'][-1]['signal'] == result['reply']
        assert set(brain.memory.profile_col.get()['ids']) == before_profile

        altered = deepcopy(result)
        altered['reply'] = '別の候補。'
        for row in altered['runtime_trace']['blackboard']:
            if row.get('label') == 'utterance':
                row['payload']['reply'] = altered['reply']
        gate.materialize_hash_prefix_provenance_p4(altered)
        assert altered['runtime_trace'][gate.LABEL]['final_related_hash_additions_removed'] == 0
        assert altered['runtime_trace'][gate.LABEL]['status'] == 'selected_or_visible_mismatch'
        print('ok')
    """))


def test_direct_unknown_existing_connective_and_unreturned_candidate_controls(tmp_path):
    _isolated(tmp_path, _CHAIN + textwrap.dedent("""
        assert transport.install_hash_prefix_event_transport_p4()
        right = RightBrain(load_model=False)

        # A connective already in the candidate is not a removed addition.
        preauthored = '先に、予定を確認しよ。'
        local_logic = {'intent': 'chat', 'scene': 'casual', 'surface_act': 'plain_reply'}
        assert right._finalize_surface_reply(preauthored, local_logic, '先に確認してから決めよう。', 80) == preauthored
        assert gate._EVENT_KEY not in local_logic

        source = '同僚に「味噌焼きおにぎり、一口いる？」って言われた。'
        logic = reported.reported_offer_plan_p4(source, reported._reproducible_prior_seed(source))
        observed = []
        old_finalize = right._finalize_surface_reply
        def return_another_candidate(reply, local_logic, user_input, max_chars):
            chosen = old_finalize(reply, local_logic, user_input, max_chars)
            observed.extend(local_logic.get(gate._EVENT_KEY) or [])
            return '別の候補。' if local_logic.get('planner_path') == reported.LABEL else chosen
        right._finalize_surface_reply = return_another_candidate
        assert right.speak(source, logic, {}, {}) == '別の候補。'
        assert len(observed) == 1
        assert gate._EVENT_KEY not in logic

        # Both controls run the real turn loop, but cannot acquire the reported
        # source gate or its final hash-prefix audit.
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager
        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)
        brain.right_brain = RightBrain(load_model=False)
        profile_ids = set(brain.memory.profile_col.get()['ids'])
        direct = brain.run_turn_debug('塩ポテト、一口いる？')
        assert direct['logic']['surface_act'] == 'named_offer_accept'
        assert reported.LABEL not in direct['runtime_trace']
        assert gate.LABEL not in direct['runtime_trace']
        unknown = brain.run_turn_debug('先生はオリーブが好き？')
        assert reported.LABEL not in unknown['runtime_trace']
        assert gate.LABEL not in unknown['runtime_trace']
        assert set(brain.memory.profile_col.get()['ids']) == profile_ids
        print('ok')
    """))


def test_duplicate_matching_events_count_only_once_per_speak(tmp_path):
    _isolated(tmp_path, _CHAIN + textwrap.dedent("""
        assert transport.install_hash_prefix_event_transport_p4()
        right = RightBrain(load_model=False)
        source = '同僚に「味噌焼きおにぎり、一口いる？」って言われた。'
        logic = reported.reported_offer_plan_p4(source, reported._reproducible_prior_seed(source))
        original_finalize = right._finalize_surface_reply
        def duplicate_event(reply, local_logic, user_input, max_chars):
            first = original_finalize(reply, local_logic, user_input, max_chars)
            second = original_finalize(reply, local_logic, user_input, max_chars)
            assert first == second
            return first
        right._finalize_surface_reply = duplicate_event

        actual = right.speak(source, logic, {}, {})
        assert actual == logic['core_message_jp']
        events = logic[gate._EVENT_KEY]
        assert len(events) == 1, events
        assert events[0]['returned_candidate_sha256'] == transport._sha(actual)

        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager
        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)
        brain.right_brain = right
        result = brain.run_turn_debug(source)
        assert result['reply'] == actual
        assert len(result['logic'][gate._EVENT_KEY]) == 1
        assert result['runtime_trace'][gate.LABEL]['final_related_hash_additions_removed'] == 1
        print('ok')
    """))


def test_stale_repeated_exception_nonstring_and_oversize_fail_closed(tmp_path):
    _isolated(tmp_path, _CHAIN + textwrap.dedent("""
        import hashlib

        assert transport.install_hash_prefix_event_transport_p4()
        right = RightBrain(load_model=False)
        source = '同僚に「味噌焼きおにぎり、一口いる？」って言われた。'
        def plan():
            return reported.reported_offer_plan_p4(source, reported._reproducible_prior_seed(source))
        logic = plan()
        stale = {'schema': gate.SCHEMA, 'action': 'removed_unlicensed_hash_addition',
                 'prefix': 'まあ、', 'selected_candidate_sha256': '0' * 64,
                 'legacy_candidate_sha256': '0' * 64, 'returned_candidate_sha256': '0' * 64}
        logic[gate._EVENT_KEY] = [stale]
        first = right.speak(source, logic, {}, {})
        assert len(logic[gate._EVENT_KEY]) == 1
        assert logic[gate._EVENT_KEY][0] != stale
        second = right.speak(source, logic, {}, {})
        assert second == first
        assert len(logic[gate._EVENT_KEY]) == 1  # not accumulated across calls

        seen = []
        original_remember = right._remember_turn
        def fail_after_finalize(*args):
            seen.extend(logic.get(gate._EVENT_KEY) or [])
            raise RuntimeError('deliberate post-finalizer failure')
        right._remember_turn = fail_after_finalize
        try:
            right.speak(source, logic, {}, {})
        except RuntimeError as exc:
            assert str(exc) == 'deliberate post-finalizer failure'
        else:
            raise AssertionError('expected failure')
        assert len(seen) == 1
        assert gate._EVENT_KEY not in logic
        right._remember_turn = original_remember

        # Isolate malformed returned states from the actual generator: they
        # must not make the transport publish a fabricated receipt.
        original_speak = transport._ORIGINAL_SPEAK
        def injected(self, user_input, local_logic, memory_data, current_psyche):
            assert local_logic[gate._EVENT_KEY] is not stale
            reply = '現在の返事。'
            digest = lambda value: hashlib.sha256(value.encode('utf-8')).hexdigest()
            event = {
                'schema': gate.SCHEMA, 'action': 'removed_unlicensed_hash_addition',
                'prefix': 'まあ、', 'selected_candidate_sha256': digest(reply),
                'legacy_candidate_sha256': digest('まあ、' + reply),
                'returned_candidate_sha256': digest(reply),
            }
            if user_input == 'oversize':
                local_logic[gate._EVENT_KEY].extend([event] * 17)
                return reply
            if user_input == 'nonstring':
                local_logic[gate._EVENT_KEY].append(event)
                return None
            if user_input == 'replaced':
                local_logic[gate._EVENT_KEY] = [event]
                return reply
            if user_input == 'stale-only':
                return reply
            raise AssertionError(user_input)
        transport._ORIGINAL_SPEAK = injected
        try:
            for case in ('oversize', 'nonstring', 'replaced', 'stale-only'):
                logic[gate._EVENT_KEY] = [stale]
                right.speak(case, logic, {}, {})
                assert gate._EVENT_KEY not in logic, case
        finally:
            transport._ORIGINAL_SPEAK = original_speak
        print('ok')
    """))
