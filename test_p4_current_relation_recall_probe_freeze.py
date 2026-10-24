"""Zero-call integrity checks for the current-product relation-recall probe."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research/p4_current_relation_recall_probe_freeze_2026-10-01.json"


def test_probe_bindings_match_frozen_commit_and_current_files():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["schema"] == "uruha_p4_current_relation_recall_probe_freeze_v1"
    assert freeze["status"] == "frozen_before_first_product_turn"
    commit = freeze["checkpoint_commit"]
    assert len(commit) == 40
    for binding in freeze["bindings"].values():
        path = ROOT / binding["path"]
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == binding["sha256"]
        historical = subprocess.check_output(
            ["git", "show", f"{commit}:{binding['path']}"], cwd=ROOT,
        )
        assert historical == content


def test_probe_is_answer_absent_and_source_outside_recent_eight():
    data = json.loads((ROOT / "datasets/p4_current_relation_recall_probe_2026-10-01.json")
                      .read_text(encoding="utf-8"))
    turns = data["turns"]
    assert data["status"] == "developer_authored_prospective_product_probe_not_holdout"
    assert data["turn_count"] == len(turns) == 10
    assert [row["turn"] for row in turns] == list(range(1, 11))
    assert data["restart_after_turn"] == 5
    assert data["query_turn"] - data["source_turn_outside_recent_eight_at_query"] > 8
    assert "紗枝" in turns[0]["input"] and "桑の葉茶" in turns[0]["input"]
    assert all("紗枝" not in row["input"] and "桑の葉茶" not in row["input"]
               for row in turns[1:9])
    assert "紗枝" not in turns[9]["input"] and "桑の葉茶" in turns[9]["input"]
    assert data["source_only_expected"]["owner"] == "friend_紗枝"
