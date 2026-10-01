from __future__ import annotations

import json
from pathlib import Path

import pytest

from p3_product_comparison import P3ContractError, canonical_sha256
import p3_product_worker as worker
import p3_prospective_v3_execution_contract as contract
import p3_prospective_v3_output_lock as output_lock


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_prospective_v3_execution_contract_v1.json"


def test_real_adapter_preflight_is_zero_call_and_keeps_annotations_closed(monkeypatch):
    original = Path.read_text

    def guarded_read(path, *args, **kwargs):
        if path.name == "p3_prospective_developer_annotations_v3.json":
            raise AssertionError("preflight must not read annotations")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read)
    result = output_lock.build_preflight(CONFIG)
    assert result["status"] == "ready_for_real_adapter_release_review"
    assert all(result["checks"].values())
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == 0


def test_run_commitment_is_signed_and_changes_with_release_bytes(tmp_path):
    config = contract.load_config(CONFIG)
    schedule = contract.build_schedule(config)
    release = tmp_path / "release.json"
    release.write_text('{"version": 1}\n', encoding="utf-8")
    first = output_lock.build_run_commitment(config, release, schedule)
    unsigned = dict(first)
    digest = unsigned.pop("record_sha256")
    assert digest == canonical_sha256(unsigned)
    release.write_text('{"version": 2}\n', encoding="utf-8")
    second = output_lock.build_run_commitment(config, release, schedule)
    assert second["release_sha256"] != first["release_sha256"]
    assert second["record_sha256"] != first["record_sha256"]


def test_logical_product_intent_without_complete_is_terminal(tmp_path):
    paths = output_lock._logical_paths(tmp_path, "case", "turn")
    views = {
        "product_system": {"view_sha256": "p" * 64},
        "full_history_direct": {"view_sha256": "d" * 64},
    }
    turn = {"turn_id": "turn", "session_id": "session"}
    output_lock._write_product_intent(paths, "r" * 64, turn, views)
    with pytest.raises(P3ContractError, match="p3_b46_logical_intent_without_complete_terminal"):
        output_lock._read_product_complete(paths, "r" * 64, "turn", "p" * 64)


def test_logical_complete_reuse_validates_run_and_view_hashes(tmp_path):
    paths = output_lock._logical_paths(tmp_path, "case", "turn")
    result = {"visible_reply": "分かった。", "visible_reply_sha256": canonical_sha256("分かった。")}
    output_lock.write_new_json(paths["complete"], output_lock._signed({
        "schema": "uruha_p3_b46_logical_product_turn_complete_v1",
        "run_commitment_sha256": "r" * 64,
        "turn_id": "turn", "product_view_sha256": "p" * 64,
        "result": result,
    }))
    assert output_lock._read_product_complete(
        paths, "r" * 64, "turn", "p" * 64
    ) == result
    with pytest.raises(P3ContractError, match="p3_b46_logical_complete_source_mismatch"):
        output_lock._read_product_complete(paths, "r" * 64, "turn", "x" * 64)


def test_workspace_path_and_cleanup_are_exact_and_sentinel_gated(tmp_path, monkeypatch):
    monkeypatch.setattr(output_lock.tempfile, "gettempdir", lambda: str(tmp_path))
    release = {
        "authorization": {
            "workspace_root_basename": "uruha-p3-b46-prospective-v3-workspace-v1"
        }
    }
    workspace = output_lock._workspace_path(release)
    worker.initialise_ephemeral_workspace(workspace)
    output_lock._safe_remove_workspace(workspace)
    assert not workspace.exists()

    wrong = tmp_path / "wrong"
    wrong.mkdir()
    with pytest.raises(P3ContractError, match="p3_b46_workspace_cleanup_refused"):
        output_lock._safe_remove_workspace(wrong)


def _surface():
    return {
        "nonempty": True,
        "contains_japanese_script": True,
        "no_han_dominant_non_japanese": True,
        "not_whole_reply_quoted": True,
        "no_language_version_wrapper": True,
        "no_meta_analysis_dump": True,
    }


def test_aggregate_result_counts_calls_and_does_not_grade_quality(tmp_path):
    config = contract.load_config(CONFIG)
    release = tmp_path / "release.json"
    release.write_text("{}\n", encoding="utf-8")
    schedule = contract.build_schedule(config)
    commitment = output_lock.build_run_commitment(config, release, schedule)
    cases = []
    for case_index, case_id in enumerate(contract.CASE_IDS):
        product_rows, direct_rows = [], []
        for turn_index in range(4):
            source_sha = f"source-{case_index}-{turn_index}"
            input_sha = f"input-{case_index}-{turn_index}"
            call = {
                "real_model_calls": 1, "network_calls": 1,
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            }
            product_rows.append({
                "visible_reply": "分かった。", "surface_contract": _surface(),
                "source_history_sha256": source_sha, "input_sha256": input_sha,
                "calls": [call],
            })
            direct_rows.append({
                "final": {"content": "そうだな。"}, "surface_contract": _surface(),
                "source_history_sha256": source_sha, "input_sha256": input_sha,
                "calls": [call],
            })
        cases.append({
            "status": "case_outputs_locked", "case_id": case_id,
            "product_turns": product_rows, "direct_turns": direct_rows,
            "checks": {"production_database_unreachable": True, "localhost_only": True},
            "total_wall_seconds": 1.0,
        })
    result = output_lock.aggregate_result(config, release, commitment, cases, True)
    assert result["status"] == "prospective_v3_outputs_locked"
    assert result["real_model_calls"] == result["network_calls"] == 24
    assert result["actual_prompt_tokens"] == 240
    assert result["quality_result"] == "not_yet_scored_against_predeclared_rubric"
    assert result["annotations_accessed"] == 0

