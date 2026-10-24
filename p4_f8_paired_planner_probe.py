#!/usr/bin/env python3
"""One-shot, private M21 off/on probe for the frozen P4 f8 source-event arm.

This is a developer-authored planner-boundary diagnostic.  It does not run a
Web turn, write memories, score the visible Japanese reply, or establish a
general advantage over an LLM.  No model call occurs without ``--execute``.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import urllib.request


HERE = Path(__file__).resolve().parent
DATA = HERE / "datasets/p4_source_event_candidate_formation_f8_probe_2026-10-24.json"
FREEZE = HERE / "research/p4_source_event_candidate_formation_f8_source_freeze_2026-10-24.sha256"
MODEL = "qwen2.5:7b"
MODEL_DIGEST = "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
TAGS_URL = "http://127.0.0.1:11434/api/tags"
OPENAI_URL = "http://127.0.0.1:11434/v1"
MAX_TOKENS_PER_ARM = 2000
MAX_PLANNER_SECONDS = 20.0
ARM_ENV = "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _request_bytes(value: dict) -> bytes:
    # Preserve argument/key order as passed to the OpenAI-compatible client.
    # This is a Python request-argument comparison, not captured HTTP wire bytes.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _verify_frozen_sources() -> str:
    expected = {}
    for line in FREEZE.read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        if separator:
            expected[relative] = digest
    for relative in (
        "research/p4_source_event_candidate_formation_f8_plan_2026-10-24.md",
        "datasets/p4_source_event_candidate_formation_f8_probe_2026-10-24.json",
    ):
        if expected.get(relative) != _sha_bytes((HERE / relative).read_bytes()):
            raise RuntimeError("f8_source_only_freeze_mismatch")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if data.get("schema") != "p4_source_event_candidate_formation_f8_developer_probe_v1":
        raise RuntimeError("f8_probe_schema_mismatch")
    if data.get("resource_cap", {}).get("completed_generations_per_arm_max") != 1:
        raise RuntimeError("f8_generation_cap_mismatch")
    if data["resource_cap"].get("provider_tokens_per_arm_max") != MAX_TOKENS_PER_ARM:
        raise RuntimeError("f8_token_cap_mismatch")
    if data["resource_cap"].get("planner_wall_seconds_max") != MAX_PLANNER_SECONDS:
        raise RuntimeError("f8_time_cap_mismatch")
    return data["planner_comparison_source"]


def _model_digest() -> str:
    with urllib.request.urlopen(TAGS_URL, timeout=5) as response:
        tags = json.load(response)
    rows = [row for row in tags.get("models", []) if row.get("name") == MODEL]
    if len(rows) != 1 or rows[0].get("digest") != MODEL_DIGEST:
        raise RuntimeError("f8_model_digest_mismatch_or_missing")
    return rows[0]["digest"]


def _private_root(parent: Path | None) -> Path:
    if parent is not None:
        parent = parent.resolve(strict=True)
        if not parent.is_dir():
            raise ValueError("private_parent_not_directory")
        if parent.is_relative_to(HERE.parent.resolve()):
            raise ValueError("private_parent_inside_worktree_collection_prohibited")
    root = Path(tempfile.mkdtemp(prefix="uruha-f8-paired-", dir=parent))
    root.chmod(0o700)
    if root.stat().st_mode & 0o077:
        raise RuntimeError("private_root_permissions_not_restricted")
    return root


def _write_private(path: Path, payload: object) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _handoff(source: str) -> dict:
    from uruha_direct_reply_act_m29_priority_p4 import LABEL, classify_direct_reply_act_p4
    from uruha_direct_reply_act_planner_handoff_p4 import validate_handoff_p4

    admitted = classify_direct_reply_act_p4(source)
    if admitted.get("status") != "direct" or admitted.get("requested_act") != "brief_encouragement":
        raise RuntimeError("f8_source_not_admitted_by_m29")
    projection = {
        "status": "direct_reply_act_precedes_literal_projection_p4",
        "projection_required": False,
        "surface_authority": False,
        "input_digest": admitted["input_sha256"][:16],
        LABEL: {
            **admitted,
            "status": "admitted_direct_reply_act",
            "original_projection_required": True,
            "original_m33_status": "source_pattern_unavailable",
            "m29_projection_after": False,
        },
    }
    atoms = {"status": "not_applicable", "reason": "m29_projection_not_required"}
    result = validate_handoff_p4(source, projection, atoms)
    if not isinstance(result, dict):
        raise RuntimeError("f8_same_turn_handoff_not_validated")
    return result


def _initial_state() -> tuple[dict, dict]:
    # The same serialized blank planner state is used by dry-run and both live
    # arms; there is no MemoryManager, episode store, or background scheduler.
    return (
        {"episodes": [], "wisdom": [], "profile": "無穩定使用者資料",
         "recent_dialogue": "無近期對話", "working_memory_items": []},
        # Match the product Psyche's numeric neutral initialization, not the
        # unrelated 0..1 profile-confidence scale used by other components.
        {"mood": 0, "trust": 50},
    )


def _zero_provider_dry_run(source: str, handoff: dict, segment: str) -> dict:
    """Exercise the exact initial M21 route twice with fake model candidates."""
    from types import SimpleNamespace
    import uruha_brain_mac as runtime
    import uruha_compact_planner_p2 as compact

    memory, psyche = _initial_state()
    runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = MAX_PLANNER_SECONDS
    compact.install_compact_planner_p2()
    plans = [
        {"scene": "support", "core_message_jp": "うん、よくやった。", "response_mode": "direct_answer"},
        {"scene": "support", "core_message_jp": "夜の星を撮ったんだね、いいね。", "response_mode": "direct_answer"},
        {"scene": "casual", "core_message_jp": "それはやるじゃん。", "response_mode": "direct_answer"},
    ]
    requests: list[dict] = []
    for arm in ("off", "on"):
        def create(**kwargs):
            requests.append(deepcopy(kwargs))
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                finish_reason="stop",
            )])

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        left = runtime.LeftBrain(client)
        flags = {
            "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
            "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
            "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
            ARM_ENV: "1" if arm == "on" else "0",
        }
        prior = {key: os.environ.get(key) for key in flags}
        os.environ.update(flags)
        try:
            if left._rule_based_plan(source, deepcopy(psyche), deepcopy(memory)) is not None:
                raise RuntimeError("f8_not_full_planner_source")
            with redirect_stdout(io.StringIO()):
                result = left.think(
                    source, deepcopy(memory), deepcopy(psyche),
                    force_general_planner=False,
                    direct_reply_act_handoff_p4=None,
                    source_event_core_handoff_p4=deepcopy(handoff),
                )
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        audit = (result.get("bounded_slow_path_m21") or {}).get("compact_general_plan_p2") or {}
        if (
            len(requests) != (1 if arm == "off" else 2)
            or (result.get("bounded_slow_path_m21") or {}).get("route") != "full_planner"
            or (result.get("bounded_slow_path_m21") or {}).get("status") != "completed_within_budget"
            or (result.get("bounded_slow_path_m21") or {}).get("fallback_used") is not False
            or audit.get("completed") is not True
            or audit.get("candidate_count") != 3
        ):
            raise RuntimeError("f8_zero_provider_route_invalid")
        if arm == "on" and (audit.get("source_event_candidate_prompt_p4") or {}).get("prompt_injected") is not True:
            raise RuntimeError("f8_zero_provider_prompt_not_injected")
    _paired_request_check(requests[0], None, segment)
    _paired_request_check(requests[1], requests[0], segment)
    return {
        "status": "full_m21_compact_route_with_fake_candidates",
        "fake_model_call_count": len(requests),
        "request_argument_parity_except_f8_suffix": True,
        "state_sha256": _sha_bytes(_canonical({"source": source, "memory": memory, "psyche": psyche, "handoff": handoff})),
    }


def _paired_request_check(request: dict, off: dict | None, segment: str | None) -> dict:
    """Fail before the on generation unless every other request byte is equal."""
    if request.get("model") != MODEL or request.get("temperature") != 0.1:
        raise RuntimeError("f8_model_or_temperature_drift")
    if request.get("max_tokens") != 256 or request.get("timeout") != MAX_PLANNER_SECONDS:
        raise RuntimeError("f8_budget_or_output_drift")
    if (request.get("response_format") or {}).get("type") != "json_schema":
        raise RuntimeError("f8_compact_schema_drift")
    if off is None:
        if segment and segment in request["messages"][0]["content"]:
            raise RuntimeError("f8_off_arm_was_injected")
        return deepcopy(request)
    if not segment or not request["messages"][0]["content"].endswith(segment):
        raise RuntimeError("f8_on_arm_not_injected")
    comparison = deepcopy(request)
    comparison["messages"][0]["content"] = comparison["messages"][0]["content"][:-len(segment)]
    if _request_bytes(comparison) != _request_bytes(off):
        raise RuntimeError("f8_non_treatment_request_drift")
    return comparison


def _one_arm(
    *, arm: str, source: str, memory: dict, psyche: dict, handoff: dict,
    expected_state_hash: str, segment: str, off_request: dict | None,
    private_root: Path,
) -> tuple[dict, dict | None]:
    from openai import OpenAI
    import uruha_brain_mac as runtime
    from uruha_compute_ledger import ComputeLedger, instrument_openai_client
    from uruha_source_event_core_utility_p4 import assess_candidate_coverage_p4

    state = {"source": source, "memory": memory, "psyche": psyche, "handoff": handoff}
    if _sha_bytes(_canonical(state)) != expected_state_hash:
        raise RuntimeError("f8_initial_state_drift")
    _model_digest()
    ledger = ComputeLedger()
    raw_client = OpenAI(base_url=OPENAI_URL, api_key="ollama", max_retries=0)
    metered_client = instrument_openai_client(raw_client, ledger)
    captured_requests: list[dict] = []
    captured_raw: list[str] = []
    compared_request: dict | None = None

    def create(**kwargs):
        nonlocal compared_request
        if captured_requests:
            raise RuntimeError("f8_second_model_attempt_prohibited")
        captured_requests.append(deepcopy(kwargs))
        compared_request = _paired_request_check(kwargs, off_request, segment)
        response = metered_client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content
        captured_raw.append(raw)
        _write_private(private_root / f"{arm}_raw_response.json", {
            "arm": arm,
            "model": MODEL,
            "model_digest": MODEL_DIGEST,
            "request": kwargs,
            "response_content": raw,
            "finish_reason": response.choices[0].finish_reason,
            "usage": response.usage.model_dump() if response.usage is not None else None,
        })
        return response

    from types import SimpleNamespace
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    left = runtime.LeftBrain(client, compute_ledger=ledger)
    flags = {
        "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
        "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        ARM_ENV: "1" if arm == "on" else "0",
    }
    prior = {key: os.environ.get(key) for key in flags}
    os.environ.update(flags)
    quiet_log = io.StringIO()
    started = time.perf_counter()
    try:
        if left._rule_based_plan(source, deepcopy(psyche), deepcopy(memory)) is not None:
            raise RuntimeError("f8_not_full_planner_source")
        with ledger.item_scope("f8_pair", arm), redirect_stdout(quiet_log):
            result = left.think(
                source, deepcopy(memory), deepcopy(psyche),
                force_general_planner=False,
                direct_reply_act_handoff_p4=None,
                source_event_core_handoff_p4=deepcopy(handoff),
            )
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    elapsed = time.perf_counter() - started
    _model_digest()
    ledger_view = ledger.snapshot()
    summary = ledger_view["summary"]
    compact_audit = (result.get("bounded_slow_path_m21") or {}).get("compact_general_plan_p2") or {}
    prompt_receipt = compact_audit.get("source_event_candidate_prompt_p4")
    if len(captured_requests) != 1 or summary["generative_call_count"] != 1:
        raise RuntimeError("f8_generation_count_invalid")
    if not summary["generative_token_accounting_complete"] or summary["total_tokens"] > MAX_TOKENS_PER_ARM:
        raise RuntimeError("f8_provider_token_cap_or_accounting_failed")
    if elapsed > MAX_PLANNER_SECONDS:
        raise RuntimeError("f8_planner_wall_cap_exceeded")
    if arm == "off" and prompt_receipt is not None:
        raise RuntimeError("f8_off_arm_prompt_receipt_present")
    if arm == "on" and not (
        compact_audit.get("completed") is True
        and isinstance(prompt_receipt, dict)
        and prompt_receipt.get("status") == "prompt_injected"
        and prompt_receipt.get("prompt_injected") is True
    ):
        raise RuntimeError("f8_on_prompt_or_compact_contract_failed")

    plans = []
    if captured_raw:
        try:
            actual = json.loads(captured_raw[0])
            plans = actual["plans"] if isinstance(actual, dict) else []
        except (ValueError, KeyError, TypeError):
            plans = []
    original = [
        {"candidate_label": ("default", "softer", "sharper")[index], **plan}
        for index, plan in enumerate(plans[:3]) if isinstance(plan, dict)
    ]
    coverage = assess_candidate_coverage_p4(source, handoff, original)
    final_core = str(result.get("core_message_jp") or "")
    final_hash = _sha_text(final_core)
    selected_original_indexes = [
        index for index, plan in enumerate(original)
        if _sha_text(str(plan.get("core_message_jp") or "")) == final_hash
    ]
    utility = result.get("source_event_core_utility_p4") or {}
    selected_index = selected_original_indexes[0] if len(selected_original_indexes) == 1 else None
    selected_coverage = next(
        (row for row in coverage["candidate_coverage"] if row["original_index"] == selected_index),
        None,
    )
    arm_report = {
        "arm": arm,
        "state_sha256": expected_state_hash,
        "model": MODEL,
        "model_digest": MODEL_DIGEST,
        "request_argument_sha256": _sha_bytes(_request_bytes(captured_requests[0])),
        "request_argument_without_treatment_sha256": _sha_bytes(_request_bytes(compared_request)),
        "raw_response_sha256": _sha_text(captured_raw[0]) if captured_raw else None,
        "raw_response_private_file": f"{arm}_raw_response.json" if captured_raw else None,
        "actual_candidate_count": len(original),
        "candidate_coverage": coverage,
        "selected_original_index": selected_index,
        "selected_original_core_sha256": selected_coverage["core_sha256"] if selected_coverage else None,
        "selected_original_grounded": selected_coverage["grounded"] if selected_coverage else False,
        "final_core_sha256": final_hash,
        "selected_original_equals_final": bool(selected_coverage and selected_coverage["core_sha256"] == final_hash),
        "f7_winner_matches_selected_original": bool(
            selected_coverage and utility.get("new_index") == selected_index
            and utility.get("winner_core_sha256") == selected_coverage["core_sha256"]
        ),
        "m21_route": (result.get("bounded_slow_path_m21") or {}).get("route"),
        "m21_status": (result.get("bounded_slow_path_m21") or {}).get("status"),
        "m21_fallback_used": (result.get("bounded_slow_path_m21") or {}).get("fallback_used"),
        "planner_repair_applied": result.get("planner_repair_applied"),
        "compact_completed": compact_audit.get("completed"),
        "compact_candidate_count": compact_audit.get("candidate_count"),
        "source_prompt_receipt": prompt_receipt,
        "f7_utility": utility,
        "mechanism_gate_pass_possible": bool(
            (result.get("bounded_slow_path_m21") or {}).get("route") == "full_planner"
            and (result.get("bounded_slow_path_m21") or {}).get("status") == "completed_within_budget"
            and (result.get("bounded_slow_path_m21") or {}).get("fallback_used") is False
            and result.get("planner_repair_applied") is False
            and compact_audit.get("completed") is True
            and compact_audit.get("candidate_count") == 3
            and selected_coverage and selected_coverage["grounded"] is True
            and selected_coverage["core_sha256"] == final_hash
            and utility.get("new_index") == selected_index
        ),
        "provider_prompt_tokens": summary["prompt_tokens"],
        "provider_completion_tokens": summary["completion_tokens"],
        "provider_total_tokens": summary["total_tokens"],
        "planner_wall_seconds": round(elapsed, 6),
        "gold_judgement": "pending_human_review_of_private_original_core",
        "evidence_level": "one_fresh_planner_boundary_generation_not_full_product",
    }
    _write_private(private_root / f"{arm}_selected_private.json", {
        "selected_core": final_core,
        "original_plans": original,
        "logic_status": arm_report["m21_status"],
    })
    return arm_report, captured_requests[0] if arm == "off" else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="authorize the frozen two-call local probe")
    parser.add_argument("--preflight-only", action="store_true", help="verify freeze/model/handoff without generation")
    parser.add_argument("--private-parent", type=Path, help="existing parent for a new unique 0700 evidence root")
    args = parser.parse_args(argv)
    if args.preflight_only and args.execute:
        parser.error("choose either --preflight-only or --execute")
    if args.preflight_only:
        source = _verify_frozen_sources()
        digest = _model_digest()
        handoff = _handoff(source)
        from uruha_source_event_candidate_formation_p4 import build_source_event_constraint_p4
        segment, receipt = build_source_event_constraint_p4(source, handoff)
        if not segment or receipt.get("status") != "authorized":
            raise RuntimeError("f8_source_event_prompt_not_authorized")
        dry_run = _zero_provider_dry_run(source, handoff, segment)
        print(json.dumps({
            "status": "preflight_only_no_generation",
            "source_sha256": _sha_text(source),
            "handoff_input_sha256": handoff.get("input_sha256"),
            "model_digest": digest,
            "constraint_available": receipt["constraint_available"],
            "zero_provider_route": dry_run,
        }, ensure_ascii=False))
        return 0
    if not args.execute:
        parser.error("--execute is required; importing or inspecting this script does not run a model")
    source = _verify_frozen_sources()
    _model_digest()
    handoff = _handoff(source)
    from uruha_source_event_candidate_formation_p4 import build_source_event_constraint_p4
    segment, receipt = build_source_event_constraint_p4(source, handoff)
    if not segment or receipt.get("status") != "authorized":
        raise RuntimeError("f8_source_event_prompt_not_authorized")
    memory, psyche = _initial_state()
    state_hash = _sha_bytes(_canonical({"source": source, "memory": memory, "psyche": psyche, "handoff": handoff}))

    import uruha_brain_mac as runtime
    import uruha_compact_planner_p2 as compact
    runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = MAX_PLANNER_SECONDS
    compact.install_compact_planner_p2()
    _zero_provider_dry_run(source, handoff, segment)
    root = _private_root(args.private_parent)
    report = {
        "schema": "p4_f8_paired_planner_boundary_probe_v1",
        "evidence_class": "developer_authored_one_shot_diagnostic_not_holdout_or_web",
        "source_sha256": _sha_text(source),
        "initial_state_sha256": state_hash,
        "source_freeze_plan_sha256": _sha_bytes((HERE / "research/p4_source_event_candidate_formation_f8_plan_2026-10-24.md").read_bytes()),
        "source_freeze_data_sha256": _sha_bytes(DATA.read_bytes()),
        "arms": [],
        "comparison_status": "incomplete",
        "visible_gold": "pending_human_review",
        "private_root": str(root),
    }
    try:
        off, off_request = _one_arm(
            arm="off", source=source, memory=deepcopy(memory), psyche=deepcopy(psyche),
            handoff=deepcopy(handoff), expected_state_hash=state_hash,
            segment=segment, off_request=None, private_root=root,
        )
        report["arms"].append(off)
        on, _ = _one_arm(
            arm="on", source=source, memory=deepcopy(memory), psyche=deepcopy(psyche),
            handoff=deepcopy(handoff), expected_state_hash=state_hash,
            segment=segment, off_request=off_request, private_root=root,
        )
        report["arms"].append(on)
        if off["request_argument_without_treatment_sha256"] != on["request_argument_without_treatment_sha256"]:
            raise RuntimeError("f8_final_request_parity_failed")
        report["comparison_status"] = "paired_requests_verified_quality_pending"
    except Exception as exc:
        report["comparison_status"] = "strict_fail_stop_no_retry"
        report["failure_type"] = type(exc).__name__
        known_failures = {
            "f8_initial_state_drift", "f8_second_model_attempt_prohibited",
            "f8_model_or_temperature_drift", "f8_budget_or_output_drift",
            "f8_compact_schema_drift", "f8_off_arm_was_injected",
            "f8_on_arm_not_injected", "f8_non_treatment_request_drift",
            "f8_not_full_planner_source", "f8_generation_count_invalid",
            "f8_provider_token_cap_or_accounting_failed", "f8_planner_wall_cap_exceeded",
            "f8_off_arm_prompt_receipt_present", "f8_on_prompt_or_compact_contract_failed",
            "f8_final_request_parity_failed", "f8_model_digest_mismatch_or_missing",
        }
        report["failure_code"] = str(exc) if str(exc) in known_failures else "unexpected_exception"
        report["private_evidence_files"] = sorted(
            path.name for path in root.iterdir() if path.is_file()
        )
        _write_private(root / "failure_private.json", {"exception": repr(exc)})
        _write_private(root / "report.json", report)
        print(json.dumps({"status": report["comparison_status"], "failure_code": report["failure_code"], "private_root": str(root)}, ensure_ascii=False))
        return 1
    _write_private(root / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
