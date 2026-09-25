import json
from copy import deepcopy
from pathlib import Path

import p4_au_source_bound_current_action_delivery_gate as gate
import uruha_source_bound_current_action_delivery_p4 as p4_au


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_au_source_bound_current_action_delivery_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_au_source_bound_current_action_delivery_evidence_2026-09-26.json"


def test_p4_au_offline_evidence_passes_frozen_gate():
    evidence = p4_au.build_dataset_evidence_p4_au(DATASET)
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "pass", (evaluated, evidence["metrics"])
    assert evaluated["failed_gates"] == []


def test_p4_au_saved_evidence_passes_the_same_frozen_gate():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evidence["status"] == "pass"
    assert evidence["first_implementation_failure_preserved"].endswith(
        "p4_au_first_implementation_failure_2026-09-26.json"
    )
    assert evidence["informed_correction_batches_used"] == 1
    assert evaluated["status"] == "pass"
    assert evaluated["failed_gates"] == []


def test_p4_au_fresh_positives_link_exact_prior_user_source_and_reach_action_contract():
    evidence = p4_au.build_dataset_evidence_p4_au(DATASET)
    positives = [
        row for row in evidence["cases"] if row["partition"] == "fresh_positive_sequences"
    ]

    assert len(positives) == 6
    for row in positives:
        assert row["bridge_status"] == "prior_source_linked"
        assert row["prior_source_added"] is True
        assert row["exact_source_identity"] is True
        assert row["downstream_action_contract_passed"] is True
        assert row["predecessor_source_mutated"] is False


def test_p4_au_controls_fail_closed_at_the_frozen_causal_boundary():
    evidence = p4_au.build_dataset_evidence_p4_au(DATASET)
    controls = [
        row for row in evidence["cases"] if row["partition"] == "fresh_control_sequences"
    ]

    assert len(controls) == 9
    for row in controls:
        assert row["bridge_status"] == row["expected_bridge_status"]
        assert row["prior_source_added"] is False
        assert row["assistant_source_count"] == 0
        assert row["private_inference_source_count"] == 0


def test_p4_au_trace_is_raw_free_and_does_not_change_candidates_model_or_memory():
    evidence = p4_au.build_dataset_evidence_p4_au(DATASET)

    for row in evidence["cases"]:
        assert row["candidate_score_or_order_changed"] is False
        assert row["new_model_call_count"] == 0
        assert row["factual_memory_write_count"] == 0
        assert row["raw_dialogue_persisted"] is False


def test_p4_au_materializes_one_source_node_before_delivery_and_utterance():
    trace = {
        "schema": p4_au.SCHEMA,
        "status": "prior_source_linked",
        "raw_dialogue_persisted": False,
    }
    token = p4_au._TRACE.set(trace)
    try:
        result = {
            "logic": {},
            "runtime_trace": {
                "blackboard": [
                    {"label": "current_task_source_bundle_m50"},
                    {"label": "actionable_help_delivery_m45"},
                    {"label": "utterance"},
                ]
            },
        }
        p4_au.materialize_source_bound_current_action_delivery_p4(result)
        p4_au.materialize_source_bound_current_action_delivery_p4(result)
    finally:
        p4_au._TRACE.reset(token)

    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.count(p4_au.LABEL) == 1
    assert labels.index(p4_au.LABEL) < labels.index("current_task_source_bundle_m50")
    assert labels.index(p4_au.LABEL) < labels.index("actionable_help_delivery_m45")
    assert labels.index(p4_au.LABEL) < labels.index("utterance")
    assert result["logic"][p4_au.LABEL] == result["runtime_trace"][p4_au.LABEL]


def test_p4_au_source_has_no_frozen_complete_case_lookup():
    source = (ROOT / "uruha_source_bound_current_action_delivery_p4.py").read_text(
        encoding="utf-8"
    )
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    for partition in (
        "development_sequences",
        "fresh_positive_sequences",
        "fresh_control_sequences",
    ):
        for row in dataset[partition]:
            assert row["turn_1"] not in source
            assert row["turn_2"] not in source


def test_p4_au_product_entry_and_launcher_are_additive_after_p4_at():
    entry = (ROOT / "uruha_web_ui_product_p4_au.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_au_safe_isolated_product_launcher.py").read_text(
        encoding="utf-8"
    )

    assert "import uruha_web_ui_product_p4_at as _p4_at" in entry
    assert "install_source_bound_current_action_delivery_p4()" in entry
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_au.py"' in launcher
    assert "sandboxed_p4_au_probe" in launcher


def test_p4_au_binding_does_not_mutate_predecessor_source_packet():
    base = [{"id": "current:2", "kind": "current_user", "text": "current"}]
    original = deepcopy(base)
    sources, trace = p4_au.bind_prior_problem_source_p4_au(
        "current",
        {"recent_turns": []},
        {},
        2,
        base,
    )

    assert base == original
    assert sources == original
    assert trace["status"] == "blocked_exact_action_identity"
