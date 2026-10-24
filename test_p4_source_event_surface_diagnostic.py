"""Source-only, zero-provider capture of the frozen P4 surface-boundary fixture.

The private artifact contains the *raw* post-M21 logic and route_info returned
by cognitive_tick, before surface emission or episode writeback.  Its raw SHA is
run-specific because the real route records wall-clock timing. Only the
separately named normalized projection SHA is expected to repeat across runs;
normalization removes known volatile timings and provisional timestamps from
a copy, never from either surface arm's input.

Explicit capture: .venv/product_checks/bin/python
    test_p4_source_event_surface_diagnostic.py --capture
The command refuses product/source drift and writes one full JSON into a new
0700 directory outside the worktree collection, with a 0600 file.  It makes
no provider, model, Web, Safari, or formal-DB call.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent.resolve()
ORIGINAL_DIRTY_CHECKOUT = Path("/Users/jerrychang/Desktop/uruharemake2").resolve()
DATA = HERE / "datasets/p4_source_event_surface_diagnostic_probe_2026-10-24.json"
FREEZE = HERE / "research/p4_source_event_surface_diagnostic_source_freeze_2026-10-24.sha256"
BASELINE_HEAD = "52f852fa46afaa749b71ffd533c937a8e512514d"
SCHEMA = "p4_source_event_surface_preimplementation_snapshot_v1"
_HISTORICAL_PRODUCT_FILES = frozenset({
    "uruha_brain_mac.py",
    "p4_direct_reply_act_m29_priority_detached_control.py",
})


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _freeze_entries() -> dict[str, str]:
    expected = {}
    for line in FREEZE.read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        if not separator or not relative or relative in expected:
            raise RuntimeError("source_manifest_invalid")
        expected[relative] = digest
    if len(expected) != 10:
        raise RuntimeError("source_manifest_not_ten_entries")
    return expected


def _frozen_data(*, allow_historical_product_drift: bool = False) -> dict:
    expected = _freeze_entries()
    for relative, digest in expected.items():
        path = (HERE / relative).resolve(strict=True)
        if not path.is_relative_to(HERE) or _sha(path.read_bytes()) != digest:
            if allow_historical_product_drift and relative in _HISTORICAL_PRODUCT_FILES:
                continue
            raise RuntimeError(f"source_manifest_mismatch:{relative}")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if data.get("schema") != "p4_source_event_surface_diagnostic_probe_v1":
        raise RuntimeError("source_probe_schema_mismatch")
    if len(data.get("fixed_compact_plans") or []) != 3:
        raise RuntimeError("source_probe_candidate_count_mismatch")
    for plan in data["fixed_compact_plans"]:
        if set(plan) != {"scene", "response_mode", "core_message_jp"}:
            raise RuntimeError("source_probe_not_raw_compact_schema")
    return data


@contextmanager
def _fixture_flags():
    import uruha_brain_mac as runtime

    flags = {
        "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
        "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "0",
        "URUHA_P4_REPAIR_CUE_BOUNDARY": "1",
        "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT": "0",
    }
    previous = {key: os.environ.get(key) for key in flags}
    previous_budget = runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS
    os.environ.update(flags)
    runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
    try:
        yield
    finally:
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = previous_budget
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _normalized_projection(raw_boundary: dict) -> dict:
    """Copy the boundary and strip only known volatile metadata.

    Provisional timestamps are generated during this synthetic capture, not
    frozen evidence dates. Unexpected fields remain and break the repeatability
    check. This projection is never supplied to either surface arm.
    """
    projection = deepcopy(raw_boundary)
    m21 = projection["logic"]["bounded_slow_path_m21"]
    m21.pop("planner_seconds", None)
    m21.pop("stage_seconds", None)
    projection["logic"]["supported_feedback_closure_m43"].pop("added_seconds", None)
    projection["logic"]["feedback_topic_transition_m28"]["supported_feedback_closure_m43"].pop("added_seconds", None)
    lexical = projection["logic"]["semantic_route_m22"]["lexical_boundary_route_m40"]
    for key in ("added_audit_seconds", "baseline_seconds", "guarded_seconds"):
        lexical.pop(key, None)
    projection["logic"]["semantic_route_m22"]["cjk_relationship_evidence_m42"].pop("added_seconds", None)
    for estimate in projection["logic"]["longitudinal_user_model_context"]["current_provisional"]:
        estimate.pop("first_seen_at", None)
        estimate.pop("last_updated_at", None)
        for source in estimate["source_history"]:
            source.pop("timestamp", None)
    return projection


def _build_snapshot() -> tuple[dict, dict]:
    """Run exactly one isolated cognitive tick with the frozen fake M21 plans."""
    import uruha_brain_mac as runtime
    import uruha_compact_planner_p2 as compact
    import uruha_contextual_expression_commit_p2 as expression
    import uruha_web_ui_product_p4_direct_reply_act_m29_priority as product_entry
    from uruha_brain_mac import LeftBrain, RightBrain
    from test_p4_source_event_core_utility_f7 import _handoff
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    data = _frozen_data()
    source = data["planner_comparison_source"]
    plans = deepcopy(data["fixed_compact_plans"])
    fixture_before = _canonical(plans)
    handoff = _handoff(source)
    if not isinstance(handoff, dict):
        raise RuntimeError("source_handoff_unavailable")
    requests: list[dict] = []

    def fake_create(**kwargs):
        requests.append(deepcopy(kwargs))
        if len(requests) != 1:
            raise AssertionError("second_provider_call_prohibited")
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
            finish_reason="stop",
        )])

    with _fixture_flags():
        compact.install_compact_planner_p2()
        expression.install_contextual_expression_commit_p2()
        product_entry.install_product_chain()
        brain = _IsolatedContractBrain()
        left = LeftBrain(SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
        ))

        def fit(plan, *_args):
            return 1.0 if plan.get("core_message_jp") == plans[0]["core_message_jp"] else 0.75

        for name in (
            "_persona_fit_score", "_psyche_fit_score", "_continuity_fit_score",
            "_human_fit_score", "_belief_gap_fit_score", "_procedural_fit_score",
        ):
            setattr(left, name, fit)
        left._critique_plan = lambda *_args: {
            "needs_revision": False, "issues": [], "internal_note": ""
        }
        brain.left_brain = left
        brain.right_brain = RightBrain(load_model=False)
        brain.right_brain.model_blend_enabled = False
        if brain.right_brain.model is not None:
            raise RuntimeError("right_brain_model_loaded")
        if brain.persona_policy_provider is not None or brain.right_brain.persona_policy_provider is not None:
            raise RuntimeError("persona_provider_not_null")
        if brain.right_brain.history:
            raise RuntimeError("right_brain_history_not_empty")
        event = brain.ingest_event(source)
        initial = {
            "source": source,
            "handoff": deepcopy(handoff),
            "memory_data": deepcopy(event["memory_data"]),
            "memory_runtime": deepcopy(event["memory_before"]),
            "psyche": deepcopy(event["psyche_before"]),
            "persona": {
                "brain_policy_provider": None,
                "right_brain_policy_provider": None,
                "right_brain_model_blend": brain.right_brain.model_blend_enabled,
            },
            "right_brain_history": deepcopy(brain.right_brain.history),
        }
        if left._rule_based_plan(source, deepcopy(initial["psyche"]), deepcopy(initial["memory_data"])) is not None:
            raise RuntimeError("source_not_full_planner")
        logs = io.StringIO()
        with redirect_stdout(logs):
            tick = brain.cognitive_tick(event)

    if "Ollama Left Brain Error" in logs.getvalue():
        raise RuntimeError("fake_compact_planner_fell_back")
    if len(requests) != 1 or requests[0].get("response_format", {}).get("type") != "json_schema":
        raise RuntimeError("fake_compact_request_invalid")
    if _canonical(plans) != fixture_before or _canonical(data["fixed_compact_plans"]) != fixture_before:
        raise RuntimeError("frozen_compact_fixture_mutated")
    if brain.memory.saved_episodes or brain.right_brain.history:
        raise RuntimeError("surface_or_episode_executed_during_capture")

    raw_boundary = {
        "logic": deepcopy(tick["logic"]),
        "route_info": deepcopy(tick["route_info"]),
    }
    logic = raw_boundary["logic"]
    m21 = logic.get("bounded_slow_path_m21") or {}
    compact_audit = m21.get("compact_general_plan_p2") or {}
    source_audit = logic.get("source_event_core_utility_p4") or {}
    expectation = data["fixed_boundary_expectation"]
    actual = {
        "m21_route": m21.get("route"),
        "m21_status": m21.get("status"),
        "compact_completed": compact_audit.get("completed"),
        "candidate_count": compact_audit.get("candidate_count"),
        "selected_original_index": source_audit.get("new_index"),
        "selected_core_message_jp": logic.get("core_message_jp"),
        "right_brain_model_blend": initial["persona"]["right_brain_model_blend"],
        "persona_policy_provider": initial["persona"]["brain_policy_provider"],
        "initial_right_brain_history": initial["right_brain_history"],
    }
    if actual != expectation or m21.get("fallback_used") is not False:
        raise RuntimeError(f"fixed_boundary_expectation_failed:{actual!r}")
    if source_audit.get("status") != "no_grounded_candidate" or source_audit.get("old_index") != 0:
        raise RuntimeError("baseline_no_grounded_candidate_boundary_missing")

    snapshot = {
        "schema": SCHEMA,
        "capture_phase": "after_cognitive_tick_before_surface_or_episode",
        "evidence_class": "source_only_fake_provider_not_model_or_web",
        "frozen_plans": deepcopy(plans),
        "initial": initial,
        "raw_post_m21": raw_boundary,
        "normalized_post_m21": _normalized_projection(raw_boundary),
        "request_argument_sha256": _sha(_canonical(requests[0])),
    }
    hashes = {
        "initial_sha256": _sha(_canonical(initial)),
        "raw_post_m21_sha256": _sha(_canonical(raw_boundary)),
        "normalized_post_m21_sha256": _sha(_canonical(snapshot["normalized_post_m21"])),
        "full_private_json_sha256": _sha(_canonical(snapshot)),
    }
    return snapshot, hashes


def _two_surface_copies(raw_boundary: dict) -> tuple[dict, dict, str]:
    original_bytes = _canonical(raw_boundary)
    off, on = deepcopy(raw_boundary), deepcopy(raw_boundary)
    if _canonical(off) != original_bytes or _canonical(on) != original_bytes:
        raise RuntimeError("surface_arm_initial_raw_sha_mismatch")
    return off, on, _sha(original_bytes)


def test_historical_nondiagnostic_source_contract_remains_frozen():
    data = _frozen_data(allow_historical_product_drift=True)
    assert data["schema"] == "p4_source_event_surface_diagnostic_probe_v1"
    assert len(data["fixed_compact_plans"]) == 3


def test_source_only_snapshot_rebuild_and_immutable_surface_copies(monkeypatch):
    import openai

    # Preserve all 8/8 frozen plan/dataset/review/dependencies even after the
    # two intended product files change. Only the old-code rebuild is skipped.
    _frozen_data(allow_historical_product_drift=True)
    expected = _freeze_entries()
    if any(
        _sha((HERE / relative).read_bytes()) != expected[relative]
        for relative in _HISTORICAL_PRODUCT_FILES
    ):
        pytest.skip("historical preimplementation product code changed; see ce24a2d freeze")
    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: (_ for _ in ()).throw(
        AssertionError("real_provider_client_forbidden")
    ))
    first, first_hashes = _build_snapshot()
    second, second_hashes = _build_snapshot()
    assert first["initial"] == second["initial"]
    assert first_hashes["initial_sha256"] == second_hashes["initial_sha256"]
    assert first_hashes["normalized_post_m21_sha256"] == second_hashes["normalized_post_m21_sha256"]
    raw = first["raw_post_m21"]
    before = _canonical(raw)
    off, on, copy_sha = _two_surface_copies(raw)
    assert copy_sha == first_hashes["raw_post_m21_sha256"]
    assert _sha(_canonical(off)) == _sha(_canonical(on)) == copy_sha
    on["logic"]["core_message_jp"] = "changed_only_in_test_copy"
    assert _canonical(raw) == before and _canonical(off) == before
    assert _canonical(on) != before
    assert first["frozen_plans"] == _frozen_data()["fixed_compact_plans"]


@pytest.mark.parametrize("forbidden_parent", [HERE, ORIGINAL_DIRTY_CHECKOUT])
def test_capture_does_not_place_private_artifact_in_code_checkouts(forbidden_parent):
    with pytest.raises(ValueError, match="outside_worktrees_and_original_checkout"):
        _private_root(forbidden_parent)


def _private_root(parent: Path | None) -> Path:
    base = (parent or Path(tempfile.gettempdir())).resolve(strict=True)
    if not base.is_dir() or base.is_relative_to(COLLECTION) or base.is_relative_to(ORIGINAL_DIRTY_CHECKOUT):
        raise ValueError("private_parent_must_be_outside_worktrees_and_original_checkout")
    root = Path(tempfile.mkdtemp(prefix="uruha-p4-surface-snapshot-", dir=base))
    root.chmod(0o700)
    if root.stat().st_mode & 0o077:
        raise RuntimeError("private_root_permission_failure")
    return root


def _write_private(path: Path, snapshot: dict, hashes: dict) -> None:
    payload = {"snapshot": snapshot, "canonical_sha256": hashes}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    if path.stat().st_mode & 0o077:
        raise RuntimeError("private_file_permission_failure")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="write one private full snapshot")
    parser.add_argument("--private-parent", type=Path, help="existing parent outside all worktrees")
    args = parser.parse_args(argv)
    if not args.capture:
        parser.error("explicit --capture required; otherwise use pytest")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=HERE, check=True, capture_output=True, text=True
    ).stdout.strip()
    if head != BASELINE_HEAD:
        raise RuntimeError("preimplementation_head_mismatch")
    snapshot, hashes = _build_snapshot()
    off, on, raw_sha = _two_surface_copies(snapshot["raw_post_m21"])
    if _canonical(off) != _canonical(on) or raw_sha != hashes["raw_post_m21_sha256"]:
        raise RuntimeError("surface_copy_parity_failed")
    root = _private_root(args.private_parent)
    path = root / "preimplementation_full_snapshot.json"
    _write_private(path, snapshot, hashes)
    print(json.dumps({
        "status": "source_only_preimplementation_snapshot_captured",
        "private_json": str(path),
        "private_dir_mode": "0700",
        "private_file_mode": "0600",
        **hashes,
        "off_on_raw_copy_sha_equal": True,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
