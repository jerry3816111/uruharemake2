from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import m55_temporal_row_contract as temporal_m55
import m56_blinded_execution_capsule as capsule_m56
import m56_fair_comparison_preflight as preflight_m56
from test_m55_temporal_row_contract import synthetic_pack


def artifacts():
    compiled = temporal_m55.compile_temporal_dataset_m55(synthetic_pack())
    split = preflight_m56.build_blinded_artifacts(compiled)
    packet = split["prediction_packet"]
    manifest = preflight_m56.build_fixture_run_manifest(packet)
    capsule = capsule_m56.build_execution_capsule(packet, manifest)
    return split, packet, manifest, capsule


def submission_artifacts():
    split, packet, manifest, capsule = artifacts()
    submission = capsule_m56.build_synthetic_fixture_submission(capsule, packet, manifest)
    receipt = capsule_m56.create_commitment_receipt(submission, capsule, packet, manifest)
    return split, packet, manifest, capsule, submission, receipt


def rehash_submission(submission):
    submission["submission_hash"] = capsule_m56.digest(
        {key: value for key, value in submission.items() if key != "submission_hash"}
    )


def remove_ours_fit_hash(submission):
    row = next(
        row for row in submission["prediction_rows"]
        if row["condition_id"] == "OURS_HYBRID"
    )
    row["fit_artifact_hash"] = None


def test_contract_freezes_bindings_isolation_commitment_and_no_authority():
    report = capsule_m56.validate_contract()
    assert report == {
        "valid": True,
        "errors": [],
        "contract_hash": report["contract_hash"],
        "binding_count": 9,
        "condition_count": 7,
    }
    contract = capsule_m56.load_contract()
    assert tuple(contract["condition_views"]) == capsule_m56.CONDITION_IDS
    assert contract["view_invariants"]["B5_and_Ours_source_information_hash_equal"] is True
    assert contract["ordering_and_commitment"]["outcome_key_access_before_commitment_forbidden"] is True
    assert all(value is False for value in contract["authorization"].values())


def test_capsule_separates_all_views_and_primary_source_is_identical():
    _, packet, manifest, capsule = artifacts()
    report = capsule_m56.validate_execution_capsule(capsule, packet, manifest)
    assert report["valid"] is True
    assert report["task_count"] == packet["sample_count"] * 7
    assert report["summary_task_count"] == 2
    assert report["forbidden_key_count"] == 0
    tasks = {(row["sample_id"], row["condition_id"]): row for row in capsule["prediction_tasks"]}
    for sample_id in ("synthetic-m55-01", "synthetic-m55-02"):
        b1 = tasks[(sample_id, "B1_BASE_LLM")]["view"]
        b2 = tasks[(sample_id, "B2_PERSONA_PROMPT")]["view"]
        forbidden_history_fields = {
            "available_history", "all_pre_cutoff_history", "source_history",
            "deterministic_top4_pre_cutoff_history",
            "pre_cutoff_historical_behavior_counts", "summary_task_id",
        }
        assert not (set(b1) & forbidden_history_fields)
        assert not (set(b2) & forbidden_history_fields)
        b3 = tasks[(sample_id, "B3_RAG")]["view"]
        assert len(b3["deterministic_top4_pre_cutoff_history"]) <= 4
        b4 = tasks[(sample_id, "B4_FULL_HISTORY_SUMMARY")]["view"]
        assert set(b4) == capsule_m56._expected_view_keys("B4_FULL_HISTORY_SUMMARY")
        assert "source_history" not in b4 and "all_pre_cutoff_history" not in b4
        b5 = tasks[(sample_id, "B5_STRUCTURED_HISTORY")]["view"]
        ours = tasks[(sample_id, "OURS_HYBRID")]["view"]
        assert b5["source_information"] == ours["source_information"]
        assert b5["source_information_hash"] == ours["source_information_hash"]
        assert "equation_definition_binding" not in b5
        assert ours["required_pre_outcome_artifacts"] == [
            "fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash"
        ]


def test_capsule_task_order_exactly_follows_packet_rotation_and_contains_no_outcome():
    _, packet, manifest, capsule = artifacts()
    expected = [
        (row["sample_id"], condition)
        for row in packet["model_inputs"]
        for condition in row["condition_order"]
    ]
    actual = [(row["sample_id"], row["condition_id"]) for row in capsule["prediction_tasks"]]
    assert actual == expected
    serialized = capsule_m56.canonical(capsule)
    for key in capsule_m56.OUTCOME_KEYS:
        assert f'"{key}"' not in serialized
    assert capsule["model_call_count"] == 0
    assert capsule["outcome_access_count"] == 0


def test_materialized_model_request_contains_only_one_authorized_view():
    _, packet, manifest, capsule, submission, _ = submission_artifacts()
    task = next(row for row in capsule["prediction_tasks"] if row["condition_id"] == "B1_BASE_LLM")
    request = capsule_m56.materialize_generation_request(
        task["task_id"], capsule, packet, manifest
    )
    serialized = capsule_m56.canonical(request)
    assert request["condition_id"] == "B1_BASE_LLM"
    assert request["source_view_hash"] == task["view_hash"]
    assert "available_history" not in request["model_input"]
    assert "persona_summary" not in serialized
    assert "synthetic-m55-02" not in serialized
    assert "OUTCOME-SUMMARY" not in serialized
    b4_task = next(row for row in capsule["prediction_tasks"] if row["condition_id"] == "B4_FULL_HISTORY_SUMMARY")
    b4_request = capsule_m56.materialize_generation_request(
        b4_task["task_id"], capsule, packet, manifest,
        summary_artifacts=submission["summary_artifacts"],
    )
    assert "frozen_model_summary_artifact" in b4_request["model_input"]
    assert "source_history" not in capsule_m56.canonical(b4_request)
    b0_task = next(row for row in capsule["prediction_tasks"] if row["condition_id"] == "B0_PRIOR")
    with pytest.raises(ValueError, match="deterministic"):
        capsule_m56.materialize_generation_request(b0_task["task_id"], capsule, packet, manifest)


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda c: c["prediction_tasks"].reverse(), "task_order_or_matrix"),
        (lambda c: c["prediction_tasks"].append(deepcopy(c["prediction_tasks"][0])), "task_order_or_matrix"),
        (lambda c: c["prediction_tasks"][0]["view"].update(actual_observed_behavior="leak"), "forbidden_key"),
        (lambda c: c["prediction_tasks"][0].update(view_hash="0" * 64), "view_hash"),
        (lambda c: c["prediction_tasks"][0]["view"].update(available_history=[]), "view_fields"),
    ],
)
def test_capsule_tampering_fails_closed(mutate, expected):
    _, packet, manifest, capsule = artifacts()
    mutate(capsule)
    capsule["capsule_hash"] = capsule_m56.digest(
        {key: value for key, value in capsule.items() if key != "capsule_hash"}
    )
    report = capsule_m56.validate_execution_capsule(capsule, packet, manifest)
    assert report["valid"] is False
    assert any(expected in error for error in report["errors"])


def test_synthetic_submission_commitment_and_separate_scorer_complete_all_rows():
    split, packet, manifest, capsule, submission, receipt = submission_artifacts()
    validation = capsule_m56.validate_submission(submission, capsule, packet, manifest)
    assert validation["valid"] is True
    assert validation["row_count"] == 14
    assert validation["summary_artifact_count"] == 2
    assert validation["unauthorized_evidence_count"] == 0
    assert validation["same_model_artifact"] is True
    assert validation["same_hardware"] is True
    resources = validation["condition_resource_totals"]
    assert resources["B0_PRIOR"]["prediction_model_calls"] == 0
    assert resources["B5_STRUCTURED_HISTORY"]["prediction_model_calls"] == 2
    assert resources["OURS_HYBRID"]["prediction_model_calls"] == 0
    assert resources["OURS_HYBRID"]["semantic_model_calls"] == 2
    assert validation["b4_summary_build_resource_totals"]["model_calls"] == 1
    assert capsule_m56.validate_commitment_receipt(receipt, submission, capsule)["valid"] is True
    score = capsule_m56.score_committed_submission(
        submission,
        receipt,
        capsule,
        packet,
        manifest,
        split["split_report"],
        split["outcome_key"],
    )
    assert score["status"] == "synthetic_engineering_score_only"
    assert score["formal_result"] is False
    assert score["decision"] == "synthetic_engineering_only_no_formal_claim"
    assert set(score["condition_metrics"]) == set(capsule_m56.CONDITION_IDS)
    assert score["primary_comparison"]["sample_count"] == 2
    assert score["evidence_audit"]["unauthorized_or_post_cutoff_evidence_rate"] == 0
    assert "not human evidence" in score["claim_boundary"]


def test_b0_is_exact_smoothed_frequency_prior_and_cannot_be_replaced():
    _, packet, manifest, capsule, submission, _ = submission_artifacts()
    for row in submission["prediction_rows"]:
        if row["condition_id"] != "B0_PRIOR":
            continue
        task = next(task for task in capsule["prediction_tasks"] if task["task_id"] == row["task_id"])
        labels = task["view"]["candidate_behavior_labels"]
        counts = task["view"]["pre_cutoff_historical_behavior_counts"]
        denominator = sum(counts[label] + 1 for label in labels)
        assert row["probabilities"] == {
            label: (counts[label] + 1) / denominator for label in labels
        }
    changed = deepcopy(submission)
    b0 = next(
        row for row in changed["prediction_rows"]
        if row["condition_id"] == "B0_PRIOR" and row["sample_id"] == "synthetic-m55-02"
    )
    labels = list(b0["probabilities"])
    b0["probabilities"] = {label: 1 / len(labels) for label in labels}
    b0["selected_behavior"] = labels[0]
    rehash_submission(changed)
    report = capsule_m56.validate_submission(changed, capsule, packet, manifest)
    assert report["valid"] is False
    assert any("B0_prior" in error for error in report["errors"])


def test_probability_metric_is_primary_one_hot_and_acceptable_only_affects_rank():
    split, packet, manifest, capsule, submission, receipt = submission_artifacts()
    outcome_key = deepcopy(split["outcome_key"])
    first = outcome_key["outcomes"][0]
    labels = packet["model_inputs"][0]["model_input"]["candidate_behavior_labels"]
    alternate = next(label for label in labels if label != first["actual_observed_behavior"])
    first["acceptable_behavior_labels"] = [first["actual_observed_behavior"], alternate]
    split_report = deepcopy(split["split_report"])
    split_report["outcome_key_hash"] = capsule_m56.digest(outcome_key)
    score = capsule_m56.score_committed_submission(
        submission, receipt, capsule, packet, manifest, split_report, outcome_key
    )
    b5_rows = [row for row in submission["prediction_rows"] if row["condition_id"] == "B5_STRUCTURED_HISTORY"]
    expected_brier = 0.0
    for row in b5_rows:
        outcome = next(item for item in outcome_key["outcomes"] if item["sample_id"] == row["sample_id"])
        expected_brier += sum(
            (row["probabilities"][label] - float(label == outcome["actual_observed_behavior"])) ** 2
            for label in labels
        )
    expected_brier /= len(b5_rows)
    joined_b5 = score["condition_metrics"]["B5_STRUCTURED_HISTORY"]
    assert joined_b5["brier_score"] == pytest.approx(expected_brier)
    assert score["formal_result"] is False


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda s: s["prediction_rows"].reverse(), "row_order_or_completeness"),
        (lambda s: s["prediction_rows"].append(deepcopy(s["prediction_rows"][0])), "row_order_or_completeness"),
        (lambda s: s["prediction_rows"][0].update(actual_observed_behavior="leak"), "forbidden_key"),
        (lambda s: s["prediction_rows"][0].update(view_hash="0" * 64), "view_hash"),
        (lambda s: s["prediction_rows"][0]["probabilities"].update({next(iter(s["prediction_rows"][0]["probabilities"])): 3.0}), "probability_mass"),
        (lambda s: s["prediction_rows"][0].update(selected_behavior="wrong"), "selected_behavior"),
        (lambda s: s["prediction_rows"][0].update(retry_count=1), "retry_or_fallback"),
        (lambda s: s["prediction_rows"][-1].update(model_artifact_digest="d" * 64), "model_artifact_digest"),
        (remove_ours_fit_hash, "fit_artifact_hash"),
    ],
)
def test_submission_tampering_fails_closed(mutate, expected):
    _, packet, manifest, capsule, submission, _ = submission_artifacts()
    mutate(submission)
    rehash_submission(submission)
    report = capsule_m56.validate_submission(submission, capsule, packet, manifest)
    assert report["valid"] is False
    assert any(expected in error for error in report["errors"])


def test_unauthorized_evidence_is_rejected_even_with_fresh_submission_hash():
    _, packet, manifest, capsule, submission, _ = submission_artifacts()
    row = next(row for row in submission["prediction_rows"] if row["condition_id"] == "B1_BASE_LLM")
    row["authorized_evidence_ids"] = ["m55-history::synthetic-m55-01"]
    rehash_submission(submission)
    report = capsule_m56.validate_submission(submission, capsule, packet, manifest)
    assert report["valid"] is False
    assert report["unauthorized_evidence_count"] == 1
    assert any("unauthorized_evidence" in error for error in report["errors"])


def test_post_commitment_change_or_wrong_outcome_hash_prevents_scoring():
    split, packet, manifest, capsule, submission, receipt = submission_artifacts()
    changed = deepcopy(submission)
    changed["prediction_rows"][0]["brief_evidence"] = "changed after commitment"
    rehash_submission(changed)
    with pytest.raises(ValueError, match="receipt.submission_hash"):
        capsule_m56.score_committed_submission(
            changed, receipt, capsule, packet, manifest, split["split_report"], split["outcome_key"]
        )
    wrong_split = deepcopy(split["split_report"])
    wrong_split["outcome_key_hash"] = "0" * 64
    with pytest.raises(ValueError, match="outcome_key.split_hash"):
        capsule_m56.score_committed_submission(
            submission, receipt, capsule, packet, manifest, wrong_split, split["outcome_key"]
        )


def test_malformed_outcome_row_and_generation_visible_split_fail_closed():
    split, packet, manifest, capsule, submission, receipt = submission_artifacts()
    wrong_key = deepcopy(split["outcome_key"])
    wrong_key["outcomes"][0]["acceptable_behavior_labels"] = ["unknown-label"]
    wrong_split = deepcopy(split["split_report"])
    wrong_split["outcome_key_hash"] = capsule_m56.digest(wrong_key)
    with pytest.raises(ValueError, match="acceptable_labels"):
        capsule_m56.score_committed_submission(
            submission, receipt, capsule, packet, manifest, wrong_split, wrong_key
        )
    exposed = deepcopy(split["split_report"])
    exposed["outcome_key_exposed_to_generation"] = True
    with pytest.raises(ValueError, match="outcome_exposure"):
        capsule_m56.score_committed_submission(
            submission, receipt, capsule, packet, manifest, exposed, split["outcome_key"]
        )


def test_prompt_token_difference_over_five_percent_requires_sensitivity():
    split, packet, manifest, capsule, submission, receipt = submission_artifacts()
    changed = deepcopy(submission)
    ours = next(row for row in changed["prediction_rows"] if row["condition_id"] == "OURS_HYBRID")
    ours["prompt_tokens"] = 1000
    rehash_submission(changed)
    validation = capsule_m56.validate_submission(changed, capsule, packet, manifest)
    assert validation["valid"] is True
    assert validation["exact_token_sensitivity_required"] is True
    changed_receipt = capsule_m56.create_commitment_receipt(changed, capsule, packet, manifest)
    score = capsule_m56.score_committed_submission(
        changed, changed_receipt, capsule, packet, manifest,
        split["split_report"], split["outcome_key"],
    )
    assert score["resource_audit"]["exact_token_sensitivity_required"] is True
    assert score["resource_audit"]["exact_token_sensitivity_passed"] is False


def test_sign_flip_switches_to_frozen_monte_carlo_above_twenty_pairs():
    labels = ["a", "b"]
    rows = []
    for index in range(21):
        actual = "a" if index % 2 == 0 else "b"
        for condition, probabilities in (
            ("B5_STRUCTURED_HISTORY", {"a": 0.55, "b": 0.45}),
            ("OURS_HYBRID", {actual: 0.8, ("b" if actual == "a" else "a"): 0.2}),
        ):
            rows.append({
                "sample_id": f"s-{index:02d}",
                "condition_id": condition,
                "probabilities": probabilities,
                "actual_observed_behavior": actual,
                "acceptable_behavior_labels": [actual],
            })
    comparison = capsule_m56._paired_primary(rows, capsule_m56.load_contract())
    assert comparison["sample_count"] == 21
    assert comparison["brier"]["sign_flip_method"] == "prospective_deterministic_monte_carlo"
    assert comparison["nll"]["sign_flip_method"] == "prospective_deterministic_monte_carlo"


def test_live_dashboard_explains_real_isolation_and_current_zero_state():
    report = capsule_m56.build_live_report()
    assert report["status"] == "capsule_protocol_ready_execution_blocked"
    assert report["current_execution_authorized"] is False
    assert report["model_call_count"] == 0
    assert report["target_outcome_access_count"] == 0
    assert report["formal_result_created"] is False
    page = capsule_m56.render_dashboard(report)
    for phrase in (
        "真正把資訊權限切開",
        "七組資訊視圖",
        "兩個隔離艙",
        "安全題包",
        "生成艙",
        "SHA-256 封存",
        "獨立計分艙",
        "B1/B2 偷看歷史",
        "B4 摘要成本漏算",
        "B5/Ours 原始資訊不同",
        "正式執行禁止",
        "沒有證明人類方程式",
    ):
        assert phrase in page
    assert "OUTCOME-SUMMARY" not in page
    assert "youtube.com" not in page


def test_implementation_freeze_matches_all_execution_capsule_files():
    freeze = json.loads(
        Path("research/m56_blinded_execution_capsule_implementation_freeze_2026-09-01.json")
        .read_text(encoding="utf-8")
    )
    assert freeze["status"] == "execution_capsule_ready_formal_execution_blocked"
    assert freeze["formal_model_calls_at_freeze"] == 0
    assert freeze["target_outcome_access_at_freeze"] == 0
    assert freeze["synthetic_fixture_model_calls_are_formal"] is False
    for relative_path, expected_sha256 in freeze["frozen_files"].items():
        assert hashlib.sha256(Path(relative_path).read_bytes()).hexdigest() == expected_sha256
