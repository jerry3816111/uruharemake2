"""Immutable outcome checks for the first one-shot M46 generation failure."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARTIFACT = ROOT / "analysis/p4_m46_reviewer_necessity_generation_2026-09-30.json"
CONTRACT = ROOT / "configs/p4_m46_reviewer_necessity_v1.json"


def test_first_generation_failure_is_preserved_without_review_or_retry():
    raw = ARTIFACT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "3b9556db4b337bd0ccef3305b108d1c53a9742884178cf81812e0d41dc171446"
    )
    result = json.loads(raw)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert result["status"] == "generation_call_failed_partial_no_resume"
    assert result["prewarm"]["completed"] is True
    assert result["retry_count"] == result["review_calls"] == 0
    assert result["gold_labels_present"] is False
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["case_id"] == "p4_m46_gen_zh_scaffold_001"
    assert row["batch"] is None
    assert row["call"]["attempted"] is row["call"]["completed"] is True
    assert row["call"]["json_parse_success"] is False
    assert row["call"]["error_type"] == "JSONDecodeError"
    assert row["call"]["completion_tokens"] == contract["controlled_constants"]["m51_num_predict"]
    assert result["production_database_access"] is False
    assert result["product_runtime_changed"] is False
