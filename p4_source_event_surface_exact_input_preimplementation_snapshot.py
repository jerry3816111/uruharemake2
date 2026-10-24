#!/usr/bin/env python3
"""Capture the new, source-disjoint A boundary before any capability product edit.

This is a fake-provider cognitive snapshot, not a visible-reply, model, or Web
result. Raw state goes only to a new private temporary directory outside both
checkouts. Public stdout contains hashes and route labels, not raw state.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

import openai

import test_p4_source_event_surface_diagnostic as old_snapshot


ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "datasets/p4_source_event_surface_exact_input_capability_probe_2026-10-24.json"
APPROVED = ROOT / "research/p4_source_event_surface_approved_input_manifest_2026-10-24.json"
FROZEN = ROOT / "research/p4_source_event_surface_exact_input_capability_source_freeze_2026-10-24.sha256"
EXPECTED_CODE_SHA = {
    "p4_direct_reply_act_m29_priority_detached_control.py": "7b1e055e5c8fa15a6e746ea46c2c6572d238fafeebb54cc13d14fcab6ce31e71",
    "test_p4_source_event_surface_diagnostic.py": "e963cf21cc357f41001dbe141897569b759f0e74ee318af2490753e9048c1e56",
    "test_p4_source_event_surface_diagnostic_route.py": "340e6d2b64d1c14679c0012afae146093263314b13f5339b34cae0282e7d558f",
    "uruha_brain_mac.py": "916ca62b6f39d251d3ab0620afefb69a9a715fbe6b0f843e103667a8d5a0c383",
    "uruha_source_event_surface_diagnostic_p4.py": "313f8ad75602bf6f23ae8595c3daa301dad7dd8f464d0916a1b4a4e95e28649c",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen_source() -> str:
    for line in FROZEN.read_text(encoding="utf-8").splitlines():
        digest, sep, relative = line.partition("  ")
        target = (ROOT / relative).resolve(strict=True)
        if not sep or not target.is_relative_to(ROOT) or _sha(target) != digest:
            raise RuntimeError(f"source_freeze_mismatch:{relative}")
    for relative, digest in EXPECTED_CODE_SHA.items():
        if _sha(ROOT / relative) != digest:
            raise RuntimeError(f"preimplementation_code_changed:{relative}")
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    approved = json.loads(APPROVED.read_text(encoding="utf-8"))
    if approved.get("probe_sha256") != _sha(PROBE):
        raise RuntimeError("approved_probe_sha_mismatch")
    case = probe["positive_cases"][0]
    if (
        case.get("id") != "cap_fixed_envelope"
        or approved.get("approved", [None])[0] != {
            "case_id": case["id"], "input_sha256": case["input_sha256"]
        }
        or hashlib.sha256(case["source"].encode("utf-8")).hexdigest() != case["input_sha256"]
    ):
        raise RuntimeError("first_approved_case_mismatch")
    return case["source"]


def _capture() -> dict:
    source = _frozen_source()
    old_data = old_snapshot._frozen_data(allow_historical_product_drift=True)
    substituted = deepcopy(old_data)
    substituted["planner_comparison_source"] = source
    original_frozen_data = old_snapshot._frozen_data
    original_openai_client = openai.OpenAI
    prior_surface_arm = os.environ.get("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM")
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    original_tick = _IsolatedContractBrain.cognitive_tick
    actual_sidecars = []

    def capture_tick(self, event):
        tick = original_tick(self, event)
        actual_sidecars.append(deepcopy(tick.get("_source_event_surface_handoff_p4")))
        return tick

    try:
        old_snapshot._frozen_data = lambda: deepcopy(substituted)
        # The cognitive path receives only the synthetic fake provider installed by
        # _build_snapshot. A stray real client construction fails immediately.
        openai.OpenAI = lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("real_provider_client_forbidden")
        )
        os.environ["URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM"] = "off"
        _IsolatedContractBrain.cognitive_tick = capture_tick
        first, first_hashes = old_snapshot._build_snapshot()
        second, second_hashes = old_snapshot._build_snapshot()
    finally:
        old_snapshot._frozen_data = original_frozen_data
        openai.OpenAI = original_openai_client
        _IsolatedContractBrain.cognitive_tick = original_tick
        if prior_surface_arm is None:
            os.environ.pop("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", None)
        else:
            os.environ["URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM"] = prior_surface_arm
    if len(actual_sidecars) != 2 or any(
        old_snapshot._canonical(sidecar) != old_snapshot._canonical(first["initial"]["handoff"])
        for sidecar in actual_sidecars
    ):
        raise RuntimeError(
            "actual_transient_handoff_not_frozen_initial_handoff:"
            f"count={len(actual_sidecars)}:"
            f"actual_sha={[ _sha_value(value) for value in actual_sidecars ]}:"
            f"expected_sha={_sha_value(first['initial']['handoff'])}:"
            f"actual_types={[type(value).__name__ for value in actual_sidecars]}:"
            f"actual_statuses={[value.get('status') if isinstance(value, dict) else None for value in actual_sidecars]}:"
            f"actual_keys={[sorted(value) if isinstance(value, dict) else [] for value in actual_sidecars]}"
        )
    if first_hashes["initial_sha256"] != second_hashes["initial_sha256"]:
        raise RuntimeError("initial_state_not_equal")
    if first_hashes["normalized_post_m21_sha256"] != second_hashes["normalized_post_m21_sha256"]:
        raise RuntimeError("normalized_post_m21_not_repeatable")
    off, on, raw_sha = old_snapshot._two_surface_copies(first["raw_post_m21"])
    if (
        old_snapshot._canonical(off) != old_snapshot._canonical(on)
        or raw_sha != first_hashes["raw_post_m21_sha256"]
    ):
        raise RuntimeError("surface_copy_not_equal")
    temporary_parent = Path(tempfile.gettempdir()).resolve(strict=True)
    for forbidden in (ROOT.parent.resolve(strict=True), Path("/Users/jerrychang/Desktop/uruharemake2").resolve(strict=True)):
        if temporary_parent == forbidden or temporary_parent.is_relative_to(forbidden):
            raise RuntimeError("private_snapshot_temp_parent_inside_checkout")
    root = Path(tempfile.mkdtemp(prefix="uruha-p4-exact-input-before-", dir=temporary_parent))
    os.chmod(root, 0o700)
    if root.is_relative_to(ROOT.parent) or root.is_relative_to(Path("/Users/jerrychang/Desktop/uruharemake2")):
        raise RuntimeError("private_snapshot_inside_checkout")
    target = root / "raw-before.json"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(old_snapshot._canonical({
                "schema": "p4_source_event_surface_exact_input_before_v1",
                "first": first,
                "second": second,
                "first_hashes": first_hashes,
                "second_hashes": second_hashes,
                "actual_transient_handoffs": actual_sidecars,
            }))
            stream.flush()
            os.fsync(stream.fileno())
        if stat.S_IMODE(target.stat().st_mode) != 0o600:
            raise RuntimeError("private_snapshot_file_not_0600")
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        # Keep the private artifact for forensic inspection; never overwrite it.
        raise
    return {
        "schema": "p4_source_event_surface_exact_input_before_receipt_v1",
        "evidence_class": "source_only_fake_provider_no_web",
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "private_raw_path": str(target),
        "private_raw_file_sha256": _sha(target),
        "private_root_mode": oct(stat.S_IMODE(root.stat().st_mode)),
        "private_file_mode": oct(stat.S_IMODE(target.stat().st_mode)),
        "initial_sha256": first_hashes["initial_sha256"],
        "first_raw_post_m21_sha256": first_hashes["raw_post_m21_sha256"],
        "second_raw_post_m21_sha256": second_hashes["raw_post_m21_sha256"],
        "normalized_post_m21_sha256": first_hashes["normalized_post_m21_sha256"],
        "off_on_same_raw_boundary_sha256": raw_sha,
        "actual_transient_handoff_sha256": _sha_value(actual_sidecars[0]),
        "m21_route": first["raw_post_m21"]["logic"]["bounded_slow_path_m21"].get("route"),
        "m21_status": first["raw_post_m21"]["logic"]["bounded_slow_path_m21"].get("status"),
        "source_utility_status": first["raw_post_m21"]["logic"]["source_event_core_utility_p4"].get("status"),
        "real_provider_calls": 0,
        "web_sends": 0,
        "formal_db_writes": 0,
    }


def _sha_value(value: object) -> str:
    return hashlib.sha256(old_snapshot._canonical(value)).hexdigest()


if __name__ == "__main__":
    print(json.dumps(_capture(), ensure_ascii=False, sort_keys=True))
