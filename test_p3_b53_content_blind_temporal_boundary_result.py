import hashlib
import json
from pathlib import Path

import p3_b53_content_blind_temporal_boundary as b53


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "research" / "p3_b53_content_blind_temporal_boundary_release_2026-09-17.json"


def load_result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_bindings_are_content_addressed():
    result = load_result()
    for binding in result["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["sha256"]


def test_release_matches_deterministic_recomputation():
    result = load_result()
    recomputed = b53.select_temporal_boundary()
    assert result["source_id"] == recomputed["source_id"]
    assert result["selection"]["candidate_set_hash"] == recomputed[
        "candidate_set_hash"
    ]
    assert result["boundary"] == {
        key: recomputed[key]
        for key in result["boundary"]
    }
    assert result["receipt_hash"] == recomputed["receipt_hash"]


def test_boundary_is_strict_and_future_remains_unaccessed():
    result = load_result()
    boundary = result["boundary"]
    assert (
        boundary["event_start_seconds"]
        <= boundary["observable_input_start_seconds"]
        < boundary["prediction_cutoff_seconds"]
        < boundary["observable_behavior_start_seconds"]
        < boundary["observable_behavior_end_seconds"]
        <= boundary["event_end_seconds"]
    )
    counts = result["evidence_counts"]
    assert counts["boundary_selection_count"] == 1
    assert all(
        value == 0
        for key, value in counts.items()
        if key != "boundary_selection_count"
    )
