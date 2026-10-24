"""Developer-authored source-act contracts; no fresh model or Safari evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap

import uruha_adaptive_person_model as uapm
import uruha_source_bound_third_party_statement_act_p4 as act


def _candidate(source, response):
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    original_checks = {
        "safe_response_semantics_faithful": False,
        "subject_preserved": False,
        "predicate_preserved": False,
        "time_quantity_relation_preserved": False,
        "polarity_preserved": False,
    }
    contract = {
        "schema": uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
        "status": "semantically_authorized",
        "reason": "source_first_semantics_and_safe_surface_validated",
        "surface_authority": True,
        "model_call_completed": True,
        "input_digest": digest,
        "source_polarity": "affirmed",
        "polarity": "affirmed",
        "response_jp": response,
        "subject_jp": "友達",
        "predicate_jp": "青紫蘇茶が好きだ",
        "literal_summary_jp": "友達は青紫蘇茶が好きだ。",
        "surface_anchors_jp": ["友達", "青紫蘇茶"],
        "surface_self_checks": original_checks,
        "raw_dialogue_persisted": False,
    }
    plan = {
        "intent": "semantically_authorized_literal_topic_m31",
        "scene": "casual",
        "core_message_jp": response,
        "jp_summary": contract["literal_summary_jp"],
        "semantic_authorization_m31": contract,
    }
    return plan, contract


def test_exact_source_only_parse_and_protected_negatives():
    cases = [
        ("友達は青紫蘇茶が好き。", "友達", "青紫蘇茶"),
        ("友達の紗夜は栗餡団子が好き。", "友達の紗夜", "栗餡団子"),
        ("姉は柚子羊羹が好き。", "姉", "柚子羊羹"),
    ]
    for source, owner, value in cases:
        parsed = act.parse_direct_third_party_like_p4(source)
        assert parsed is not None, source
        assert parsed["subject_jp"] == owner
        assert parsed["object_jp"] == value

    negatives = [
        "私は青紫蘇茶が好き。", "うちは青紫蘇茶が好き。",
        "友達は青紫蘇茶が好き？", "友達は青紫蘇茶が好きじゃない。",
        "「友達は青紫蘇茶が好き。」", "友達は青紫蘇茶が好きらしい。",
        "もし友達は青紫蘇茶が好き。", "友達は青紫蘇茶が好きと言った。",
        "友達は青紫蘇茶が好き。私は嫌い。",
        "友達は青紫蘇茶が好き。でも今は違う。",
        "友達じゃない人は青紫蘇茶が好き。",
        "友達は青紫蘇茶が好き。覚えておいて。",
        "友達は青紫蘇茶が好き。死にたい。",
        "My friend likes green tea.", "朋友喜歡青紫蘇茶。",
    ]
    for source in negatives:
        assert act.parse_direct_third_party_like_p4(source) is None, source


def test_same_proposition_question_is_repaired_before_selected_authority():
    source = "友達は青紫蘇茶が好き。"
    old = "友達、青紫蘇茶好き？"
    plan, contract = _candidate(source, old)
    fixed_plan, fixed_contract = act.repair_authorized_statement_act_p4(source, plan, contract)

    expected = "友達は青紫蘇茶が好きなんだね。"
    assert fixed_plan["core_message_jp"] == expected
    assert fixed_contract["response_jp"] == expected
    assert fixed_plan["jp_summary"] == source
    assert fixed_contract["literal_summary_jp"] == fixed_plan["jp_summary"]
    assert fixed_contract["subject_jp"] == "友達"
    assert fixed_contract["predicate_jp"] == "青紫蘇茶が好き"
    assert fixed_contract["source_polarity"] == "affirmed"
    assert fixed_contract["surface_authority"] is True
    assert all(fixed_contract["surface_self_checks"][key] is True for key in (
        "safe_response_semantics_faithful", "subject_preserved",
        "predicate_preserved", "time_quantity_relation_preserved", "polarity_preserved",
    ))
    trace = fixed_contract[act.LABEL]
    assert trace["status"] == "source_bounded_statement_repaired"
    assert trace["model_candidate_sha256"] == hashlib.sha256(old.encode()).hexdigest()
    assert trace["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert trace["self_check_provenance"] == "deterministic_source_rule"
    assert trace["model_canonical_sha256"]
    assert source not in json.dumps(trace, ensure_ascii=False)
    assert old not in json.dumps(trace, ensure_ascii=False)
    m32_plan, m32_contract = uapm.build_deterministic_semantic_commit_m32(fixed_contract)
    assert m32_plan is None
    assert m32_contract["reason"] == "m31_authoritative_surface_complete"
    committed, applied = uapm.apply_semantic_authorization_m31(fixed_plan, fixed_contract)
    visible, surfaced = uapm.ensure_semantic_authorization_m31_reaches_surface("違う。", committed)
    assert applied["surface_authority"] is True
    assert visible == expected
    assert surfaced["surface_status"] == "matched"

    for question in ("友達は、青紫蘇茶が好き？", "友達って青紫蘇茶好きなの？"):
        another_plan, another_contract = _candidate(source, question)
        repaired, _ = act.repair_authorized_statement_act_p4(source, another_plan, another_contract)
        assert repaired["core_message_jp"] == expected


def test_repair_never_uses_m31_canonical_fields_as_source_truth():
    source = "姉は柚子羊羹が好き。"
    plan, contract = _candidate(source, "姉、柚子羊羹好き？")
    contract.update({
        "subject_jp": "妹",
        "predicate_jp": "ほうじ茶が好き",
        "literal_summary_jp": "妹はほうじ茶が好き。",
        "source_polarity": "negated",
        "polarity": "negated",
    })
    fixed_plan, fixed = act.repair_authorized_statement_act_p4(source, plan, contract)
    assert fixed_plan["core_message_jp"] == "姉は柚子羊羹が好きなんだね。"
    assert fixed_plan["jp_summary"] == source
    assert fixed["subject_jp"] == "姉"
    assert fixed["predicate_jp"] == "柚子羊羹が好き"
    assert fixed["source_polarity"] == fixed["polarity"] == "affirmed"
    assert fixed[act.LABEL]["model_canonical_sha256"]
    assert "ほうじ茶" not in json.dumps(fixed[act.LABEL], ensure_ascii=False)


def test_source_proof_or_model_authority_missing_does_not_create_rule_authority():
    source = "友達は青紫蘇茶が好き。"
    untouched = [
        (source, "友達は青紫蘇茶が好きなんだ。君は？", None),
        (source, "へえ、君も好き？", None),
        ("友達は青紫蘇茶が好き？", "友達、青紫蘇茶好き？", None),
        ("友達は青紫蘇茶が好きらしい。", "友達、青紫蘇茶好き？", None),
    ]
    for candidate_source, reply, _ in untouched:
        plan, contract = _candidate(candidate_source, reply)
        result = act.repair_authorized_statement_act_p4(candidate_source, plan, contract)
        assert result == (plan, contract), (candidate_source, reply)

    plan, contract = _candidate(source, "友達、青紫蘇茶好き？")
    contract["input_digest"] = "0" * 16
    assert act.repair_authorized_statement_act_p4(source, plan, contract) == (plan, contract)
    plan, contract = _candidate(source, "友達、青紫蘇茶好き？")
    contract["surface_authority"] = False
    assert act.repair_authorized_statement_act_p4(source, plan, contract) == (plan, contract)


def test_product_entry_m31_wrapper_is_idempotent_and_keeps_prior_chain(tmp_path):
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "URUHA_WEB_PREWARM_BRAIN": "0",
        "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
        "URUHA_MEMORY_DB_PATH": str(tmp_path / "memory"),
        "URUHA_ADAPTIVE_PERSON_MODEL_PATH": str(tmp_path / "adaptive.json"),
        "GRADIO_ANALYTICS_ENABLED": "false",
    }
    program = """
        import json
        import uruha_web_ui_product_p4_preference_fallback as entry
        import uruha_source_bound_third_party_statement_act_p4 as act
        import uruha_source_bound_preference_fallback_p4 as pref
        from uruha_brain_mac import LeftBrain
        assert entry.RUNTIME is entry._prior.RUNTIME
        assert pref._INSTALLED is True and act.install_source_bound_third_party_statement_act_p4() is False
        assert LeftBrain.authorize_literal_topic_m31 is act.authorize_literal_topic_with_source_act_p4
        print('ok')
    """
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(program)], env=env,
        cwd=os.path.dirname(__file__), capture_output=True, text=True,
        check=False, timeout=90,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert completed.stdout.splitlines()[-1] == "ok"


def test_no_model_full_turn_selected_contract_visible_graph_and_profile_owner(tmp_path):
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "URUHA_WEB_PREWARM_BRAIN": "0",
        "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
        "URUHA_MEMORY_DB_PATH": str(tmp_path / "memory"),
        "URUHA_ADAPTIVE_PERSON_MODEL_PATH": str(tmp_path / "adaptive.json"),
        "GRADIO_ANALYTICS_ENABLED": "false",
    }
    program = """
        import uruha_web_ui_product_p4_preference_fallback as entry
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
        import uruha_source_bound_third_party_statement_act_p4 as act

        source = '友達は青紫蘇茶が好き。'
        def nested_bad_verdict(_prompt):
            return {
                'proposal_diagnosis': {'semantics_faithful': True, 'error_tags': []},
                'source_normalization': {
                    'polarity': 'affirmed', 'subject_jp': '友達',
                    'predicate_jp': '青紫蘇茶が好きだ',
                    'time_quantity_relation_jp': '',
                    'literal_summary_jp': '友達は青紫蘇茶が好きだ。',
                },
                'surface_authorization': {
                    'unsupported_addition_absent': True,
                    'safe_response_jp': '友達、青紫蘇茶好き？',
                    'safe_surface_anchors_jp': ['友達', '青紫蘇茶'],
                },
                'confidence': 0.94,
            }

        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.left_brain = LeftBrain(None)
        brain.left_brain._native_semantic_authorizer_m31 = nested_bad_verdict
        brain.right_brain = RightBrain(load_model=False)
        brain.right_brain.speak = lambda _source, logic, _mem, _psyche: logic['core_message_jp']
        result = brain.run_turn_debug(source)
        expected = '友達は青紫蘇茶が好きなんだね。'
        logic = result['logic']
        assert logic['core_message_jp'] == expected, logic
        assert result['reply'] == expected, result['reply']
        assert logic['semantic_authorization_m31']['response_jp'] == expected, logic['semantic_authorization_m31']
        assert logic['semantic_authorization_m31'][act.LABEL]['status'] == 'source_bounded_statement_repaired', logic['semantic_authorization_m31']
        assert logic['semantic_commit_repair_m32']['surface_authority'] is False, logic['semantic_commit_repair_m32']
        rows = result['runtime_trace']['blackboard']
        selected = [row for row in rows if row.get('label') == 'selected_plan']
        assert len(selected) == 1, selected
        assert selected[0]['payload']['core_message_jp'] == expected, selected
        utterance = [row for row in rows if row.get('label') == 'utterance']
        assert len(utterance) == 1 and utterance[0]['payload']['reply'] == expected, utterance
        source_act = [row for row in rows if row.get('label') == act.LABEL]
        assert len(source_act) == 1 and source_act[0]['payload']['status'] == 'source_bounded_statement_repaired', [row.get('label') for row in rows]
        owner = result['memory_runtime']['profile_owner_admission_p4']
        assert owner['admitted_count'] == 0, owner
        print('ok')
    """
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(program)], env=env,
        cwd=os.path.dirname(__file__), capture_output=True, text=True,
        check=False, timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert completed.stdout.splitlines()[-1] == "ok"
