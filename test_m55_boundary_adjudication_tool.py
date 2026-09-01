from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

import m55_boundary_adjudication_tool as adjudication_m55
import m55_boundary_extension_tool as boundary_m55
import m55_temporal_row_contract as temporal_m55
import public_persona_target_calibration_coding_v9 as v9


def write_v7_lock(root: Path) -> Path:
    path = root / "v7-reliability-lock.json"
    path.write_text(
        json.dumps(
            {
                "decision": v9.REQUIRED_V7_DECISION,
                "reliability_passed": True,
                "persona_score_computed": False,
                "frozen_artifacts": {"codebook": v9._binding(v9.DEFAULT_CODEBOOK)},
            }
        ),
        encoding="utf-8",
    )
    return path


def v9_payload(slot, codebook, coder_index: int):
    start = slot["search_start_seconds"]
    return {
        "sampling_slot_id": slot["sampling_slot_id"],
        "slot_status": "selected_event",
        "first_eligible_event_attestation": True,
        "timestamp_locator_start_seconds": start,
        "timestamp_locator_end_seconds": start + 20,
        "context_family": codebook["context_families"][coder_index],
        "observable_context_paraphrase": f"synthetic whole event context {coder_index}",
        "observable_behavior_paraphrase": f"synthetic behavior summary {coder_index}",
        "primary_dimension": codebook["dimensions"][coder_index],
        "secondary_dimensions": [],
        "dialogue_act_or_action_label": codebook["dialogue_act_or_action_labels"][coder_index],
        "observable_audience_relation": codebook["audience_relations"][coder_index],
        "evidence_strength": codebook["evidence_strengths"][coder_index],
        "ambiguity_notes": "",
        "alternative_interpretations": "",
        "paraphrase_and_no_quote_attestation": True,
    }


def make_source_v9_ledger(root: Path, coder: str, coder_index: int, slot_count: int = 2):
    private_root = root / f"v9-{coder}"
    lock = write_v7_lock(root)
    ledger_path, ledger = v9.initialize_target_ledger(
        coder, f"{coder}.json", lock, private_root
    )
    frame = v9.load_json(v9.DEFAULT_FRAME)
    codebook = v9.load_json(v9.DEFAULT_CODEBOOK)
    for slot in frame["sampling_slots"][:slot_count]:
        ledger = v9.save_target_entry(
            ledger_path, v9_payload(slot, codebook, coder_index), private_root
        )
    return ledger_path, ledger, private_root, lock


def boundary_payload(source_entry, offset: int = 0):
    start = source_entry["timestamp_locator_start_seconds"]
    return {
        "sampling_slot_id": source_entry["sampling_slot_id"],
        "observable_input_start_seconds": start + offset,
        "prediction_cutoff_seconds": start + 5 + offset,
        "observable_behavior_start_seconds": start + 8 + offset,
        "observable_behavior_end_seconds": start + 15 + offset,
        "observable_input_paraphrase": f"precutoff synthetic input offset {offset}",
        "completed_event_summary": f"completed synthetic history offset {offset}",
        "annotation_confidence": 0.8,
        "prediction_boundary_attestation": True,
        "outcome_excluded_from_input_attestation": True,
        "paraphrase_and_no_quote_attestation": True,
    }


def make_boundary_ledger(root: Path, coder: str, source_v9, offsets=(0, 0), data_kind=boundary_m55.SYNTHETIC_KIND):
    private_root = root / "boundaries"
    path, ledger = boundary_m55.initialize_boundary_ledger(
        coder,
        f"{coder}.json",
        source_v9,
        authorization_lock=root / "v7-reliability-lock.json",
        private_root=private_root,
        data_kind=data_kind,
    )
    selected = list(boundary_m55._selected_v9_entries(source_v9).values())
    for entry, offset in zip(selected, offsets):
        ledger = boundary_m55.save_boundary_entry(
            path, source_v9, boundary_payload(entry, offset), private_root=private_root
        )
    return path, ledger, private_root


def make_pair(root: Path, offsets_a=(0, 0), offsets_b=(0, 1), slot_count=2):
    source_path_a, source_a, source_root_a, lock = make_source_v9_ledger(
        root, "coder-a", 0, slot_count
    )
    source_path_b, source_b, source_root_b, _ = make_source_v9_ledger(
        root, "coder-b", 1, slot_count
    )
    boundary_path_a, boundary_a, boundary_root = make_boundary_ledger(
        root, "coder-a", source_a, offsets_a
    )
    boundary_path_b, boundary_b, _ = make_boundary_ledger(
        root, "coder-b", source_b, offsets_b
    )
    return {
        "source_path_a": source_path_a,
        "source_a": source_a,
        "source_root_a": source_root_a,
        "source_path_b": source_path_b,
        "source_b": source_b,
        "source_root_b": source_root_b,
        "boundary_path_a": boundary_path_a,
        "boundary_a": boundary_a,
        "boundary_path_b": boundary_path_b,
        "boundary_b": boundary_b,
        "boundary_root": boundary_root,
        "lock": lock,
    }


def decision_payload(slot_id: str, decision: str):
    return {
        "sampling_slot_id": slot_id,
        "decision": decision,
        "adjudication_reason": "Explicitly reviewed both complete synthetic observations.",
        "adjudication_confidence": 0.85,
        "both_independent_records_reviewed_attestation": True,
        "no_automatic_merge_attestation": True,
        "paraphrase_and_no_quote_attestation": True,
    }


def manual_payload(slot_id: str, source_entry):
    start = source_entry["timestamp_locator_start_seconds"]
    return {
        **decision_payload(slot_id, "manual_resolution"),
        "event_start_seconds": start,
        "observable_input_start_seconds": start + 1,
        "prediction_cutoff_seconds": start + 6,
        "observable_behavior_start_seconds": start + 9,
        "observable_behavior_end_seconds": start + 16,
        "event_end_seconds": start + 20,
        "observable_input_paraphrase": "independently resolved precutoff synthetic input",
        "completed_event_summary": "independently resolved completed synthetic event",
        "behavior_label": "repair_or_clarify",
        "acceptable_behavior_labels": ["repair_or_clarify", "ask_or_check"],
        "context_family": "casual_social_interaction",
        "observable_audience_relation": "familiar_peer",
    }


def initialize(root: Path, pair):
    private_root = root / "adjudication"
    path, ledger = adjudication_m55.initialize_adjudication_ledger(
        "adjudicator-01",
        "adjudication.json",
        pair["source_a"],
        pair["boundary_a"],
        pair["source_b"],
        pair["boundary_b"],
        private_root=private_root,
    )
    return path, ledger, private_root


def test_contract_is_hash_bound_private_and_forbids_automatic_merge():
    report = adjudication_m55.validate_contract()
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["binding_count"] == 7
    assert report["required_entry_field_count"] == 17
    contract = adjudication_m55.load_contract()
    assert contract["adjudication"]["exact_pairs_auto_accepted"] is False
    assert contract["adjudication"]["automatic_timestamp_average_allowed"] is False
    assert contract["authorization"]["adjudication_or_pack_alone_authorizes_m56"] is False


def test_implementation_freeze_binds_tool_without_claiming_human_rows():
    freeze = adjudication_m55.load_json(
        adjudication_m55.ROOT
        / "research/m55_boundary_adjudication_tool_implementation_freeze_2026-09-01.json"
    )
    assert freeze["status"] == "tool_ready_human_gate_blocked"
    assert freeze["formal_human_adjudicated_rows_at_freeze"] == 0
    for relative_path, expected_hash in freeze["frozen_files"].items():
        assert adjudication_m55.sha256_file(adjudication_m55.ROOT / relative_path) == expected_hash


def test_initialization_is_private_atomic_canonical_and_creates_zero_entries_even_for_exact_pairs():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        pair = make_pair(root, offsets_a=(0, 0), offsets_b=(0, 0))
        path, ledger, private_root = initialize(root, pair)
        assert path.is_file()
        assert path.parent.resolve() == private_root.resolve()
        assert ledger["entries"] == {}
        assert ledger["coder_a_pseudonym"] == "coder-a"
        assert ledger["coder_b_pseudonym"] == "coder-b"
        assert adjudication_m55.validate_adjudication_ledger(
            ledger, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"]
        ) == []
        outside = root / "outside.json"
        with pytest.raises(ValueError):
            adjudication_m55.initialize_adjudication_ledger(
                "adjudicator-02", outside, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"], private_root=private_root
            )


def test_explicit_accept_a_and_b_copy_one_complete_record_without_cross_coder_merge():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        pair = make_pair(root)
        path, ledger, private_root = initialize(root, pair)
        slots = sorted(pair["boundary_a"]["entries"])
        ledger = adjudication_m55.save_adjudication_entry(
            path, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"],
            decision_payload(slots[0], "accept_coder_a_complete_record"), private_root=private_root
        )
        ledger = adjudication_m55.save_adjudication_entry(
            path, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"],
            decision_payload(slots[1], "accept_coder_b_complete_record"), private_root=private_root
        )
        first = ledger["entries"][slots[0]]["resolution_record"]
        second = ledger["entries"][slots[1]]["resolution_record"]
        assert first["observable_input_paraphrase"] == pair["boundary_a"]["entries"][slots[0]]["observable_input_paraphrase"]
        assert first["behavior_label"] == pair["source_a"]["entries"][slots[0]]["dialogue_act_or_action_label"]
        assert second["observable_input_paraphrase"] == pair["boundary_b"]["entries"][slots[1]]["observable_input_paraphrase"]
        assert second["behavior_label"] == pair["source_b"]["entries"][slots[1]]["dialogue_act_or_action_label"]
        assert first["review_status"] == temporal_m55.SYNTHETIC_REVIEW
        assert first["independent_coder_count"] == 0
        pack = adjudication_m55.assemble_record_pack(
            ledger, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"]
        )
        assert temporal_m55.validate_record_pack_m55(pack)["valid"] is True
        report = adjudication_m55.build_export_report(
            ledger, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"]
        )
        assert report["record_count"] == 2
        assert report["human_coder_count_claimed"] == 0
        assert report["model_call_count"] == 0
        assert report["m55_complete"] is False
        assert report["m56_authorized"] is False


def test_manual_resolution_requires_valid_record_reason_attestations_and_rejects_auto_merge_request():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        pair = make_pair(root, slot_count=1, offsets_a=(0,), offsets_b=(1,))
        path, ledger, private_root = initialize(root, pair)
        slot_id = next(iter(pair["boundary_a"]["entries"]))
        source_entry = pair["source_a"]["entries"][slot_id]
        payload = manual_payload(slot_id, source_entry)
        forbidden = deepcopy(payload)
        forbidden["automatic_timestamp_average"] = True
        with pytest.raises(ValueError, match="forbidden adjudication payload"):
            adjudication_m55.save_adjudication_entry(
                path, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"], forbidden, private_root=private_root
            )
        invalid = deepcopy(payload)
        invalid["prediction_cutoff_seconds"] = invalid["observable_behavior_start_seconds"]
        invalid["no_automatic_merge_attestation"] = False
        invalid["adjudication_reason"] = ""
        with pytest.raises(ValueError) as error:
            adjudication_m55.save_adjudication_entry(
                path, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"], invalid, private_root=private_root
            )
        assert "prediction_boundary_order_invalid" in str(error.value)
        assert "no_automatic_merge_attestation:required" in str(error.value)
        assert "adjudication_reason:required" in str(error.value)
        ledger = adjudication_m55.save_adjudication_entry(
            path, pair["source_a"], pair["boundary_a"], pair["source_b"], pair["boundary_b"], payload, private_root=private_root
        )
        assert ledger["entries"][slot_id]["decision"] == "manual_resolution"
        assert ledger["entries"][slot_id]["resolution_record"]["behavior_label"] == "repair_or_clarify"


def test_incomplete_same_coder_different_kind_and_stale_sources_fail_closed():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        pair = make_pair(root)
        incomplete = deepcopy(pair["boundary_b"])
        incomplete["entries"].pop(next(iter(incomplete["entries"])))
        with pytest.raises(ValueError, match="incomplete"):
            adjudication_m55.initialize_adjudication_ledger(
                "adjudicator-01", "x.json", pair["source_a"], pair["boundary_a"], pair["source_b"], incomplete, private_root=root / "adj"
            )
        with pytest.raises(ValueError, match="distinct"):
            adjudication_m55.initialize_adjudication_ledger(
                "adjudicator-01", "x.json", pair["source_a"], pair["boundary_a"], deepcopy(pair["source_a"]), deepcopy(pair["boundary_a"]), private_root=root / "adj"
            )
        mixed = deepcopy(pair["boundary_b"])
        mixed["data_kind"] = boundary_m55.REAL_KIND
        with pytest.raises(ValueError, match="same data kind"):
            adjudication_m55.initialize_adjudication_ledger(
                "adjudicator-01", "x.json", pair["source_a"], pair["boundary_a"], pair["source_b"], mixed, private_root=root / "adj"
            )
        _, ledger, _ = initialize(root, pair)
        changed_source = deepcopy(pair["source_a"])
        next(iter(changed_source["entries"].values()))["observable_behavior_paraphrase"] += " stale"
        errors = adjudication_m55.validate_adjudication_ledger(
            ledger, changed_source, pair["boundary_a"], pair["source_b"], pair["boundary_b"]
        )
        assert any("source_pair:" in error or "source_v9_a_hash" in error for error in errors)
        changed_boundary = deepcopy(pair["boundary_a"])
        next(iter(changed_boundary["entries"].values()))["completed_event_summary"] += " stale"
        errors = adjudication_m55.validate_adjudication_ledger(
            ledger, pair["source_a"], changed_boundary, pair["source_b"], pair["boundary_b"]
        )
        assert any("boundary_ledger_a_hash" in error for error in errors)


def test_real_initialization_and_serving_are_blocked_without_v7_lock():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        frame = v9.load_json(v9.DEFAULT_FRAME)
        slot_count = len(frame["sampling_slots"])
        source_path_a, source_a, _, lock = make_source_v9_ledger(root, "coder-a", 0, slot_count)
        source_path_b, source_b, _, _ = make_source_v9_ledger(root, "coder-b", 1, slot_count)
        offsets = tuple(0 for _ in range(slot_count))
        boundary_path_a, boundary_a, boundary_root = make_boundary_ledger(root, "coder-a", source_a, offsets, boundary_m55.REAL_KIND)
        boundary_path_b, boundary_b, _ = make_boundary_ledger(root, "coder-b", source_b, offsets, boundary_m55.REAL_KIND)
        missing = root / "missing-v7-lock.json"
        with pytest.raises(PermissionError, match="absent"):
            adjudication_m55.initialize_adjudication_ledger(
                "adjudicator-01", "adjudication.json", source_a, boundary_a, source_b, boundary_b,
                authorization_lock=missing, private_root=root / "adjudication"
            )
        with pytest.raises(PermissionError, match="absent"):
            adjudication_m55.serve_adjudication(
                "adjudicator-01", "adjudication.json", source_path_a, boundary_path_a,
                source_path_b, boundary_path_b, 0, authorization_lock=missing,
                private_root=root / "adjudication"
            )
        assert lock.is_file()
        assert boundary_root.is_dir()


def test_token_gated_page_requires_explicit_post_and_fails_closed_after_source_change():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        pair = make_pair(root, slot_count=1, offsets_a=(0,), offsets_b=(0,))
        ledger_path, ledger, private_root = initialize(root, pair)
        token = "synthetic-adjudication-token"
        handler = adjudication_m55.make_adjudication_handler(
            ledger_path,
            private_root,
            token,
            pair["source_path_a"],
            pair["boundary_path_a"],
            pair["source_path_b"],
            pair["boundary_path_b"],
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        slot_id = next(iter(pair["boundary_a"]["entries"]))
        try:
            with urllib.request.urlopen(f"{base}/health") as response:
                assert response.read() == b"ok"
            with pytest.raises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(base)
            assert denied.value.code == 403
            with urllib.request.urlopen(f"{base}/?token={token}") as response:
                page = response.read().decode("utf-8")
            assert "0/1 已裁決" in page
            assert "即使兩份完全一致" in page
            assert "precutoff synthetic input offset 0" in page
            encoded = urllib.parse.urlencode(
                {**decision_payload(slot_id, "accept_coder_a_complete_record"), "token": token}
            ).encode("utf-8")
            request = urllib.request.Request(base, data=encoded, method="POST")
            with urllib.request.urlopen(request) as response:
                saved = response.read().decode("utf-8")
            assert "1/1 已裁決" in saved
            assert len(adjudication_m55.load_json(ledger_path)["entries"]) == 1
            changed = deepcopy(pair["boundary_a"])
            next(iter(changed["entries"].values()))["completed_event_summary"] += " changed"
            pair["boundary_path_a"].write_text(json.dumps(changed), encoding="utf-8")
            with pytest.raises(urllib.error.HTTPError) as stale:
                urllib.request.urlopen(f"{base}/?token={token}")
            assert stale.value.code == 409
            assert "資料已失效" in stale.value.read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def test_outsider_dashboard_is_graphical_synthetic_and_contains_no_private_text():
    page = adjudication_m55.render_demo_dashboard()
    for phrase in (
        "合成工具示範，不是真人結果",
        "Coder A",
        "Coder B",
        "逐筆真人裁決",
        "Temporal record pack",
        "沒有自動平均",
        "0/18 + 0/18",
        "0/30",
        "M56 禁止",
    ):
        assert phrase in page
    assert "token=" not in page
    assert "precutoff synthetic input" not in page
    assert "completed synthetic history" not in page
