import json
from copy import deepcopy
from pathlib import Path

import uruha_neutral_operational_role_authorization_p4 as p4_av


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_av_neutral_operational_role_authorization_v1.json"
CONFIG = ROOT / "configs" / "p4_av_neutral_operational_role_authorization_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_av_neutral_operational_role_authorization_evidence_2026-09-26.json"


def _load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_p4_av_evidence_passes_the_prospectively_frozen_gate():
    evidence = p4_av.build_dataset_evidence_p4_av(DATASET)
    evaluated = p4_av.evaluate_evidence_p4_av(_load_config(), evidence)

    assert evaluated == {"status": "pass", "failed_gates": []}


def test_p4_av_saved_evidence_preserves_the_same_frozen_metrics():
    generated = p4_av.build_dataset_evidence_p4_av(DATASET)
    saved = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert saved["status"] == "pass"
    assert saved["failed_gates"] == []
    assert saved["contract"]["dataset_sha256"] == generated["dataset_sha256"]
    for key, value in generated["metrics"].items():
        assert saved["metrics"][key] == value
    assert saved["metrics"]["full_positive_string_patch_count"] == 0
    assert saved["product_preflight"]["status"] == "ready"


def test_p4_av_fresh_multilingual_operational_roles_are_authorized():
    evidence = p4_av.build_dataset_evidence_p4_av(DATASET)
    rows = [row for row in evidence["cases"] if row["split"] == "fresh_positive"]

    assert len(rows) == 6
    for row in rows:
        assert row["predecessor_status"] == "blocked"
        assert row["p4_av_status"] == "authorized_operational_roles"
        assert row["final_m53_status"] == "authorized"
        assert row["remaining_unsupported_count"] == 0


def test_p4_av_invented_topic_private_and_feasibility_labels_stay_blocked():
    evidence = p4_av.build_dataset_evidence_p4_av(DATASET)
    rows = [row for row in evidence["cases"] if row["split"] == "fresh_control"]

    assert len(rows) == 7
    for row in rows:
        assert row["p4_av_status"] == "blocked_unsupported_label"
        assert row["final_m53_status"] == "blocked"
        assert row["remaining_unsupported_count"] > 0


def test_p4_av_predecessor_exact_source_neutral_and_unquoted_cases_are_unchanged():
    evidence = p4_av.build_dataset_evidence_p4_av(DATASET)
    rows = [row for row in evidence["cases"] if row["split"] == "predecessor_control"]

    assert len(rows) == 3
    for row in rows:
        assert row["p4_av_status"] == "predecessor_preserved"
        assert row["final_m53_status"] == row["predecessor_status"]


def test_p4_av_changes_no_plan_model_memory_review_or_visible_surface_fields():
    evidence = p4_av.build_dataset_evidence_p4_av(DATASET)
    metrics = evidence["metrics"]

    assert metrics["plan_mutation_count"] == 0
    assert metrics["candidate_score_or_order_change_count"] == 0
    assert metrics["added_model_call_count"] == 0
    assert metrics["factual_memory_write_count"] == 0
    assert metrics["raw_label_persisted_count"] == 0
    assert metrics["m46_review_bypass_count"] == 0
    assert metrics["m45_or_m39_gate_weakening_count"] == 0
    assert metrics["visible_reply_change_count"] == 0


def test_p4_av_materializes_one_raw_free_node_before_m53_and_delivery():
    trace = {
        "schema": p4_av.SCHEMA,
        "status": "authorized_operational_roles",
        "labels": [{"label_digest": "digest-only"}],
        "raw_candidate_label_persisted": False,
    }
    result = {
        "logic": {"source_neutral_scaffold_m53": {p4_av.LABEL: deepcopy(trace)}},
        "runtime_trace": {
            "blackboard": [
                {"label": "source_neutral_scaffold_m53"},
                {"label": "goal_progress_delivery_m46"},
                {"label": "actionable_help_delivery_m45"},
                {"label": "utterance"},
            ]
        },
    }

    p4_av.materialize_neutral_operational_role_authorization_p4(result)
    p4_av.materialize_neutral_operational_role_authorization_p4(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]

    assert labels.count(p4_av.LABEL) == 1
    assert labels.index(p4_av.LABEL) < labels.index("source_neutral_scaffold_m53")
    assert labels.index(p4_av.LABEL) < labels.index("actionable_help_delivery_m45")
    assert result["logic"][p4_av.LABEL] == result["runtime_trace"][p4_av.LABEL]


def test_p4_av_source_contains_no_frozen_complete_positive_or_control_label_patch():
    source = (ROOT / "uruha_neutral_operational_role_authorization_p4.py").read_text(
        encoding="utf-8"
    )
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    for case in dataset["cases"]:
        assert case["instruction_jp"] not in source
        for label in case["labels"]:
            assert label not in source


def test_p4_av_product_entry_and_launcher_are_additive_after_p4_au():
    entry = (ROOT / "uruha_web_ui_product_p4_av.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_av_safe_isolated_product_launcher.py").read_text(encoding="utf-8")

    assert "import uruha_web_ui_product_p4_au as _p4_au" in entry
    assert "install_neutral_operational_role_authorization_p4()" in entry
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_av.py"' in launcher
    assert "sandboxed_p4_av_probe" in launcher
