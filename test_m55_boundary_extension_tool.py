from copy import deepcopy
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

import m55_boundary_extension_tool as boundary_m55
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
        "observable_context_paraphrase": f"whole event context {coder_index}",
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
        coder,
        f"{coder}.json",
        lock,
        private_root,
    )
    frame = v9.load_json(v9.DEFAULT_FRAME)
    codebook = v9.load_json(v9.DEFAULT_CODEBOOK)
    for slot in frame["sampling_slots"][:slot_count]:
        ledger = v9.save_target_entry(
            ledger_path,
            v9_payload(slot, codebook, coder_index),
            private_root,
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


def make_boundary_ledger(root: Path, coder: str, source_v9, offsets=(0, 0)):
    private_root = root / "boundaries"
    path, ledger = boundary_m55.initialize_boundary_ledger(
        coder,
        f"{coder}.json",
        source_v9,
        private_root=private_root,
        data_kind=boundary_m55.SYNTHETIC_KIND,
    )
    selected = list(boundary_m55._selected_v9_entries(source_v9).values())
    for entry, offset in zip(selected, offsets):
        ledger = boundary_m55.save_boundary_entry(
            path,
            source_v9,
            boundary_payload(entry, offset),
            private_root=private_root,
        )
    return path, ledger, private_root


def test_contract_is_hash_bound_private_and_fail_closed():
    report = boundary_m55.validate_contract()
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["binding_count"] == 7
    assert report["required_entry_field_count"] == len(boundary_m55.ENTRY_FIELDS)
    contract = boundary_m55.load_contract()
    assert contract["authorization"]["synthetic_demo_authorizes_m55_completion"] is False
    assert contract["authorization"]["tool_or_comparison_alone_authorizes_m56"] is False


def test_implementation_freeze_binds_the_tool_without_claiming_human_rows():
    freeze = boundary_m55.load_json(
        boundary_m55.ROOT
        / "research/m55_boundary_extension_tool_implementation_freeze_2026-09-01.json"
    )
    assert freeze["status"] == "tool_ready_human_gate_blocked"
    assert freeze["formal_human_boundary_rows_at_freeze"] == 0
    for relative_path, expected_hash in freeze["frozen_files"].items():
        assert boundary_m55.sha256_file(boundary_m55.ROOT / relative_path) == expected_hash


def test_real_initialization_and_serving_are_blocked_without_real_v7_lock():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, source, _, _ = make_source_v9_ledger(root, "coder-a", 0, slot_count=1)
        missing = root / "missing-v7-lock.json"
        with pytest.raises(PermissionError, match="absent"):
            boundary_m55.initialize_boundary_ledger(
                "coder-a",
                "coder-a.json",
                source,
                authorization_lock=missing,
                private_root=root / "boundaries",
                data_kind=boundary_m55.REAL_KIND,
            )
        with pytest.raises(PermissionError, match="absent"):
            boundary_m55.serve_boundary(
                "coder-a",
                "coder-a.json",
                "coder-a.json",
                0,
                authorization_lock=missing,
                private_root=root / "boundaries",
                v9_private_root=root / "v9-coder-a",
            )


def test_synthetic_boundary_ledger_is_private_atomic_and_valid():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, source, _, _ = make_source_v9_ledger(root, "coder-a", 0)
        path, ledger, private_root = make_boundary_ledger(root, "coder-a", source)
        assert path.is_file()
        assert boundary_m55.validate_boundary_ledger(
            ledger, source, expected_coder="coder-a", require_complete=True
        ) == []
        assert ledger["data_boundary"]["other_coder_ledger_visible"] is False
        outside = root / "outside.json"
        with pytest.raises(ValueError):
            boundary_m55.initialize_boundary_ledger(
                "coder-b",
                outside,
                source,
                private_root=private_root,
                data_kind=boundary_m55.SYNTHETIC_KIND,
            )


def test_invalid_order_whole_event_reuse_forbidden_field_and_false_attestation_fail_closed():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, source, _, _ = make_source_v9_ledger(root, "coder-a", 0, slot_count=1)
        source_entry = next(iter(boundary_m55._selected_v9_entries(source).values()))
        payload = boundary_payload(source_entry)
        entry = boundary_m55.normalize_boundary_entry(payload, source_entry, "coder-a")
        entry["prediction_cutoff_seconds"] = entry["observable_behavior_start_seconds"]
        entry["observable_input_paraphrase"] = source_entry["observable_context_paraphrase"]
        entry["outcome_excluded_from_input_attestation"] = False
        entry["raw_text"] = "forbidden"
        errors = boundary_m55.validate_boundary_entry(entry, source_entry, "coder-a")
        assert "prediction_boundary_order_invalid" in errors
        assert "observable_input_paraphrase:whole_event_context_reuse_forbidden" in errors
        assert "outcome_excluded_from_input_attestation:required" in errors
        assert any(error.startswith("forbidden_content_key:") for error in errors)
        assert any("raw_text" in error for error in errors)

        nonfinite = boundary_m55.normalize_boundary_entry(
            boundary_payload(source_entry), source_entry, "coder-a"
        )
        nonfinite["prediction_cutoff_seconds"] = float("inf")
        nonfinite_errors = boundary_m55.validate_boundary_entry(
            nonfinite, source_entry, "coder-a"
        )
        assert "prediction_cutoff_seconds:finite_nonnegative_number_required" in nonfinite_errors


def test_source_v9_entry_change_invalidates_existing_boundary_digest():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, source, _, _ = make_source_v9_ledger(root, "coder-a", 0, slot_count=1)
        _, ledger, _ = make_boundary_ledger(root, "coder-a", source, offsets=(0,))
        changed = deepcopy(source)
        source_entry = next(iter(changed["entries"].values()))
        source_entry["observable_behavior_paraphrase"] += " changed"
        errors = boundary_m55.validate_boundary_ledger(ledger, changed)
        assert any("source_v9_entry_hash:stale_or_mismatch" in error for error in errors)


def test_two_complete_distinct_ledgers_compare_without_text_and_never_auto_merge():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, source_a, _, _ = make_source_v9_ledger(root, "coder-a", 0)
        _, source_b, _, _ = make_source_v9_ledger(root, "coder-b", 1)
        _, ledger_a, _ = make_boundary_ledger(root, "coder-a", source_a, offsets=(0, 0))
        _, ledger_b, _ = make_boundary_ledger(root, "coder-b", source_b, offsets=(0, 1))
        report = boundary_m55.build_boundary_comparison(
            ledger_a, source_a, ledger_b, source_b
        )
        assert report["paired_slot_count"] == 2
        assert report["exact_four_boundary_match_count"] == 1
        assert report["divergent_boundary_count"] == 1
        assert report["explicit_human_adjudication_required_count"] == 2
        assert report["automatic_average_or_merge_performed"] is False
        assert report["automatic_record_pack_authorized"] is False
        assert report["m55_complete"] is False
        assert report["m56_authorized"] is False
        serialized = json.dumps(report, ensure_ascii=False)
        assert "precutoff synthetic input" not in serialized
        assert "completed synthetic history" not in serialized
        assert "whole event context" not in serialized
        assert "observable_input_paraphrase" not in serialized


def test_comparison_rejects_same_human_and_incomplete_ledgers():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, source_a, _, _ = make_source_v9_ledger(root, "coder-a", 0)
        _, ledger_a, _ = make_boundary_ledger(root, "coder-a", source_a, offsets=(0, 0))
        with pytest.raises(ValueError, match="distinct"):
            boundary_m55.build_boundary_comparison(
                ledger_a, source_a, deepcopy(ledger_a), deepcopy(source_a)
            )
        incomplete = deepcopy(ledger_a)
        incomplete["entries"].pop(next(iter(incomplete["entries"])))
        with pytest.raises(ValueError, match="incomplete"):
            boundary_m55.build_boundary_comparison(
                incomplete, source_a, ledger_a, source_a
            )


def test_comparison_and_real_server_reject_synthetic_real_kind_confusion():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_path_a, source_a, source_root_a, lock = make_source_v9_ledger(
            root, "coder-a", 0, slot_count=1
        )
        _, source_b, _, _ = make_source_v9_ledger(
            root, "coder-b", 1, slot_count=1
        )
        ledger_path_a, ledger_a, private_root = make_boundary_ledger(
            root, "coder-a", source_a, offsets=(0,)
        )
        _, ledger_b, _ = make_boundary_ledger(
            root, "coder-b", source_b, offsets=(0,)
        )
        mixed = deepcopy(ledger_b)
        mixed["data_kind"] = boundary_m55.REAL_KIND
        with pytest.raises(ValueError, match="same data kind"):
            boundary_m55.build_boundary_comparison(
                ledger_a, source_a, mixed, source_b
            )
        with pytest.raises(ValueError, match="real-human boundary ledger"):
            boundary_m55.serve_boundary(
                "coder-a",
                ledger_path_a,
                source_path_a,
                0,
                authorization_lock=lock,
                private_root=private_root,
                v9_private_root=source_root_a,
            )


def test_collection_server_requires_token_and_reads_only_supplied_coder_ledger():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_path, source_a, source_root, _ = make_source_v9_ledger(
            root, "coder-a", 0, slot_count=1
        )
        ledger_path, _, private_root = make_boundary_ledger(
            root, "coder-a", source_a, offsets=(0,)
        )
        token = "synthetic-test-token"
        handler = boundary_m55.make_boundary_handler(
            ledger_path, private_root, token, source_path
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(f"{base}/health") as response:
                assert response.read() == b"ok"
            with pytest.raises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(f"{base}/?slot=1")
            assert denied.value.code == 403
            with urllib.request.urlopen(f"{base}/?token={token}&slot=1") as response:
                page = response.read().decode("utf-8")
            assert "Coder: coder-a" in page
            assert "不載入另一位 coder" in page
            assert "在官方 YouTube 開啟自己的事件時間點" in page
            assert "whole event context" not in page
            assert "coder-b" not in page
            assert "M56" in page
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        assert source_path.parent.resolve() == source_root.resolve()


def test_collection_server_fails_closed_if_source_v9_entry_changes_after_start():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_path, source_a, _, _ = make_source_v9_ledger(
            root, "coder-a", 0, slot_count=1
        )
        ledger_path, _, private_root = make_boundary_ledger(
            root, "coder-a", source_a, offsets=(0,)
        )
        token = "synthetic-stale-source-token"
        handler = boundary_m55.make_boundary_handler(
            ledger_path, private_root, token, source_path
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        changed = deepcopy(source_a)
        next(iter(changed["entries"].values()))["observable_behavior_paraphrase"] += " changed"
        source_path.write_text(json.dumps(changed), encoding="utf-8")
        try:
            with pytest.raises(urllib.error.HTTPError) as stale:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{server.server_port}/?token={token}&slot=1"
                )
            assert stale.value.code == 409
            body = stale.value.read().decode("utf-8")
            assert "資料已失效" in body
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def test_dashboard_is_outsider_readable_and_explicitly_synthetic():
    page = boundary_m55.render_demo_dashboard()
    for phrase in (
        "合成工具示範，不是真人結果",
        "Coder A · 私人帳本",
        "Coder B · 私人帳本",
        "雙方都完成後才比較",
        "自動合併",
        "禁止",
        "Uruha boundary rows = 0",
        "M56 禁止",
    ):
        assert phrase in page
    assert "token=" not in page
    assert "youtube.com" not in page
    assert "transcript" not in page.lower()
