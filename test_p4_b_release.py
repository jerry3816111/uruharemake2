import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_b_safe_isolated_product_launcher_release_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_release_binds_original_failure_repair_and_result():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_launch_chat_graph_pass_after_one_sandbox_repair"
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]


def test_release_preserves_passed_and_missing_scope():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["passed_scope"]["actual_chat_and_same_turn_graph"] is True
    assert release["passed_scope"]["repository_write_sandbox"] is True
    assert release["actual_turn"]["selected_policy"] == "listen_presence"
    assert release["actual_turn"]["negated_policy"] == "solve_regulation"
    assert release["actual_turn"]["runtime_node_count"] == 69
    assert release["not_passed_or_not_present"]["vrm_3d"] == "absent"
    assert release["not_passed_or_not_present"]["function_calling"] == "not_integrated"
    assert release["next_stage"]["id"] == "P4-C"
    assert release["next_stage"]["shell_file_write_external_network_or_vrm_execution_authorized"] is False
