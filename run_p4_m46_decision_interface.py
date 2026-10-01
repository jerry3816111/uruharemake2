#!/usr/bin/env python3
"""One-shot, paired, offline M46 decision-interface study.

The frozen, developer-authored packets are selected once through common
deterministic guards.  A uses the hash-bound legacy transport helper; B changes
only the single review prompt/schema contract.  Neither arm delivers a product
action.  An existing result, including a partial one, is never resumed.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import time

import p4_m46_decision_interface_scoring as scoring
import run_p4_m46_reviewer_necessity as old_runner
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46


ROOT = Path(__file__).resolve().parent
FREEZE_SHA = "7abf74579e7793c22d3111b149037d9d7bdc5393"
CONTRACT_PATH = ROOT / "configs/p4_m46_decision_interface_v1.json"
RESULT_PATH = ROOT / "analysis/p4_m46_decision_interface_result_2026-09-30.json"
RUNNER_PATHS = ("run_p4_m46_decision_interface.py",
                "test_p4_m46_decision_interface_runner.py")
# Preregistered implementation order, fixed before model execution.  Alternating
# within pairs avoids always giving B the second, potentially warmer call.
ARM_ORDER = (("A", "B"), ("B", "A"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _tracked_clean(relative: str) -> None:
    _git("ls-files", "--error-unmatch", relative)
    _git("diff", "--exit-code", "HEAD", "--", relative)
    _git("diff", "--cached", "--exit-code", "HEAD", "--", relative)


def _require_frozen_git() -> None:
    if _git("rev-parse", FREEZE_SHA) != FREEZE_SHA:
        raise RuntimeError("Freeze commit does not resolve exactly")
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_SHA, "HEAD"],
                   cwd=ROOT, check=True)
    for relative in RUNNER_PATHS:
        _tracked_clean(relative)
    frozen_paths = (
        "research/p4_m46_decision_interface_plan_2026-09-30.md",
        "configs/p4_m46_decision_interface_v1.json",
        "datasets/p4_m46_decision_interface_v1.json",
        "p4_m46_decision_interface_scoring.py",
        "test_p4_m46_decision_interface_freeze.py",
        "test_p4_m46_decision_interface_scoring.py",
    )
    _git("diff", "--exit-code", FREEZE_SHA, "--", *frozen_paths)
    _git("diff", "--cached", "--exit-code", FREEZE_SHA, "--", *frozen_paths)


def _validate_hash_bindings(contract: dict) -> None:
    for label, record in (("plan", contract["plan"]),
                          ("dataset", contract["dataset"]),
                          *contract["hash_bound_dependencies"].items()):
        relative = record["path"]
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or _hash(path) != record["sha256"]:
            raise RuntimeError(f"Frozen hash mismatch: {label}")
    previous = contract["hash_bound_dependencies"]["prior_exposed_fixed_failure"]
    result = json.loads((ROOT / previous["path"]).read_text(encoding="utf-8"))
    if result.get("status") != "fixed_discrimination_fail":
        raise RuntimeError("Prior fixed-discrimination failure state changed")


def _validate_contract(contract: dict) -> None:
    constants, execution, gates = (contract["controlled_constants"],
                                   contract["execution"], contract["preregistered_gates"])
    if (contract.get("status") != "prospectively_frozen_before_model_execution"
            or contract.get("single_variable") !=
            "M46_single_review_decision_interface_prompt_plus_schema_as_one_contract"
            or contract.get("model") != "qwen3.5:9b"
            or contract.get("model_digest") !=
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
            or contract.get("hardware") != "Apple M2 Pro 12-core 32GB"
            or {key: constants.get(key) for key in (
                "temperature", "seed", "num_ctx", "num_predict", "stream", "think",
                "keep_alive", "retry_count", "prewarm_once_before_scoring",
                "prewarm_counted_as_case_latency",
            )} != {"temperature": 0, "seed": 20260829, "num_ctx": 4096,
                   "num_predict": 320, "stream": False, "think": False,
                   "keep_alive": "30m", "retry_count": 0,
                   "prewarm_once_before_scoring": True,
                   "prewarm_counted_as_case_latency": False}
            or execution.get("generation_scored_calls") != 0
            or execution.get("scored_packet_count") != 10
            or execution.get("guard_control_count") != 1
            or execution.get("maximum_review_scored_calls") != 20
            or execution.get("reviewer_timeout_seconds") != 30
            or execution.get("result_path") != str(RESULT_PATH.relative_to(ROOT))
            or execution.get("same_source_selected_plan_and_guards_both_arms") is not True
            or execution.get("review_plan_mechanism_hidden") is not True
            or execution.get("review_payload_excludes_gold_and_category") is not True
            or execution.get("localhost_only") is not True
            or execution.get("production_database_access") is not False
            or execution.get("product_runtime_changed") is not False
            or gates.get("B_product_eligible_from_component_only") is not False):
        raise RuntimeError("Frozen decision-interface contract mismatch")


def _prepare_packets(contract: dict, dataset: dict) -> list[dict]:
    """Validate the complete frozen set before prewarm, without model calls."""

    packets = dataset.get("challenge_packets")
    order = contract["dataset"]["packet_order"]
    if (dataset.get("status") != "sealed_before_model_execution"
            or dataset.get("scored_packet_count") != 10
            or dataset.get("guard_control_count") != 1
            or dataset.get("maximum_paired_review_calls") != 20
            or not isinstance(packets, list) or len(packets) != 11
            or not isinstance(order, list) or len(order) != 11):
        raise RuntimeError("Frozen packet count or state mismatch")
    by_id = {packet["packet_id"]: packet for packet in packets}
    if len(by_id) != 11 or len(set(order)) != 11 or set(by_id) != set(order):
        raise RuntimeError("Frozen packet order or identity mismatch")
    planned = []
    for packet_id in order:
        packet = by_id[packet_id]
        source, batch, gold = packet["source"], packet["batch"], packet["gold"]
        expected = packet["expected_deterministic_guard"]
        label, axis = gold["label"], gold["expected_failed_axis"]
        if (label not in {"valid", "invalid"}
                or (label == "valid") != (gold["content_valid"]
                    and gold["japanese_surface_valid"] and gold["actor_valid"])
                or (axis is None) != (label == "valid")
                or (axis is not None and axis not in scoring.AXES)
                or not isinstance(gold.get("rationale_zh"), str)
                or not gold["rationale_zh"].strip()):
            raise RuntimeError(f"Frozen gold mismatch: {packet_id}")
        prior = scoring.score_packet(source, batch, None, None, label, axis)
        guard = not prior["deterministic_eligible"]
        if (prior["selected_index"] != expected["selected_index"]
                or prior["selection_guard_parity"] is not True
                or prior["selected_plan"]["goal_source_id"] != source["id"]
                or prior["selected_plan"]["goal_source_span"] != source["text"]
                or prior["selected_plan_digest"] != m45.digest(prior["selected_plan"])
                or prior["deterministic_eligible"] is not expected["review_eligible"]
                or (not prior["guard_violations"]) is not expected["selected_structural_pass"]
                or guard != (packet["category"] == "guard_control")
                or (guard and prior["guard_violations"] !=
                    ["nonprogress_or_unknown_mechanism"])):
            raise RuntimeError(f"Frozen packet guard/source mismatch: {packet_id}")
        legacy = old_runner.scoring.score_packet(source, batch, None, label)
        if (legacy["selected_plan_digest"] != prior["selected_plan_digest"]
                or legacy["selected_fingerprint"] != prior["selected_fingerprint"]
                or legacy["m39_final_byte_identical"] is not expected["m39_exact_accept"]
                or legacy["m39_surface_trace"].get("action") != "accept"
                or not m45._japanese(prior["selected_plan"].get("instruction_jp"))
                or (guard and (prior["arms"]["old_contract"]["would_deliver"] is not False
                               or prior["arms"]["new_contract"]["would_deliver"] is not False))):
            raise RuntimeError(f"Frozen packet M39/plan mismatch: {packet_id}")
        planned.append({"packet_id": packet_id, "category": packet["category"],
                        "source": source, "batch": batch, "gold_label": label,
                        "expected_failed_axis": axis, "prior_score": prior})
    eligible = [item for item in planned if item["prior_score"]["deterministic_eligible"]]
    valid = [item for item in eligible if item["gold_label"] == "valid"]
    invalid = [item for item in eligible if item["gold_label"] == "invalid"]
    blocked = [item for item in planned if not item["prior_score"]["deterministic_eligible"]]
    gates = contract["preregistered_gates"]
    if (len(eligible) != gates["deterministic_eligible_packet_count"]
            or gates["deterministic_eligible_packet_count"] != 10
            or len(valid) != gates["valid_packet_count"]
            or gates["valid_packet_count"] != 3
            or len(invalid) != gates["invalid_packet_count"]
            or gates["invalid_packet_count"] != 7
            or len(blocked) != gates["guard_control_both_arms_blocked_count"]
            or gates["guard_control_both_arms_blocked_count"] != 1
            or not blocked or blocked[0]["category"] != "guard_control"
            or any(item["category"] == "guard_control" for item in eligible)
            or any(item["prior_score"]["guard_violations"] for item in eligible)):
        raise RuntimeError("Frozen decision-interface preflight gate mismatch")
    return planned


def _legacy_review_contract(contract: dict) -> dict:
    adapter = deepcopy(contract)
    constants = adapter["controlled_constants"]
    constants["m46_seed"] = constants["seed"]
    constants["m46_num_predict"] = constants["num_predict"]
    return adapter


def preflight(contract_path: Path = CONTRACT_PATH,
              output_path: Path = RESULT_PATH) -> tuple[dict, dict, list[dict]]:
    contract_path, output_path = contract_path.resolve(), output_path.resolve()
    if contract_path != CONTRACT_PATH or output_path != RESULT_PATH:
        raise RuntimeError("Formal study requires fixed contract and result paths")
    if output_path.exists():
        raise RuntimeError("Existing result cannot be overwritten or resumed")
    _require_frozen_git()
    scoring.legacy._require_isolated_modules()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    _validate_contract(contract)
    _validate_hash_bindings(contract)
    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    planned = _prepare_packets(contract, dataset)
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Formal host must be Apple arm64")
    cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    if cpu != "Apple M2 Pro" or memory != 34359738368:
        raise RuntimeError("Formal hardware must be M2 Pro 32GB")
    if not old_runner._get_json("http://127.0.0.1:11434/api/version").get("version"):
        raise RuntimeError("Local Ollama unavailable")
    tags = old_runner._get_json("http://127.0.0.1:11434/api/tags")
    digests = {row["name"]: row["digest"] for row in tags["models"]}
    if digests.get(contract["model"]) != contract["model_digest"]:
        raise RuntimeError("Frozen model digest mismatch")
    return contract, dataset, planned


def model_json_call_b(*, case_id: str, source: dict, plan: dict,
                      contract: dict) -> dict:
    """B transport mirrors A's options and payload, changing prompt/schema."""

    constants = contract["controlled_constants"]
    payload = scoring.decision_review_payload(source, plan)
    expected_payload = {
        "sources": [source],
        "plan": {key: value for key, value in plan.items() if key != "progress_mechanism"},
        "planned_payload_digest": m45.digest({"sources": [source], "plan": plan}),
    }
    if payload != expected_payload:
        raise RuntimeError("B review payload differs from frozen A payload")
    schema = scoring.decision_review_schema(source, plan)
    system = scoring.DECISION_REVIEW_SYSTEM
    body = {
        "model": contract["model"],
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        "format": schema, "stream": constants["stream"], "think": constants["think"],
        "keep_alive": constants["keep_alive"],
        "options": {"temperature": constants["temperature"], "seed": constants["seed"],
                    "num_ctx": constants["num_ctx"], "num_predict": constants["num_predict"]},
    }
    started = time.monotonic()
    record = {
        "call_id": f"review_b:{case_id}", "stage": "review", "arm": "B",
        "model": contract["model"], "attempted": True, "completed": False,
        "json_parse_success": False,
        "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(
            json.dumps(schema, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "payload_digest": m45.digest(payload), "options": deepcopy(body["options"]),
    }
    try:
        data = old_runner._post_json(old_runner.OLLAMA_CHAT, body,
                                     contract["execution"]["reviewer_timeout_seconds"])
        record.update(completed=True,
                      prompt_tokens=int(data.get("prompt_eval_count") or 0),
                      completion_tokens=int(data.get("eval_count") or 0),
                      load_duration_ns=int(data.get("load_duration") or 0),
                      total_duration_ns=int(data.get("total_duration") or 0))
        content = (data.get("message") or {}).get("content", "")
        record["content_digest"] = m45.digest(content)
        try:
            record["parsed"] = json.loads(content)
            record["json_parse_success"] = True
        except (ValueError, TypeError) as exc:
            record.update(error_type=type(exc).__name__, error=str(exc)[:300],
                          raw_content=content)
    except Exception as exc:  # one attempt; preserve the failure
        record.update(error_type=type(exc).__name__, error=str(exc)[:300])
    record["wall_seconds"] = round(time.monotonic() - started, 5)
    return record


def _arm_order(eligible_index: int) -> tuple[str, str]:
    return ARM_ORDER[eligible_index % len(ARM_ORDER)]


def _count(rows: list[dict], arm: str, field: str) -> int:
    arm_key = "old_contract" if arm == "A" else "new_contract"
    return sum(row.get("score", {}).get("arms", {}).get(arm_key, {}).get(field) is True
               for row in rows)


def summarize(rows: list[dict], contract: dict) -> dict:
    """Report each arm's absolute gates, cost, and paired regressions."""

    eligible = [row for row in rows if row["deterministic_eligible"]]
    valid = [row for row in eligible if row["gold_label"] == "valid"]
    invalid = [row for row in eligible if row["gold_label"] == "invalid"]
    guards = [row for row in rows if not row["deterministic_eligible"]]
    gates = contract["preregistered_gates"]
    metrics = {
        "packet_count": len(rows), "deterministic_eligible_packet_count": len(eligible),
        "valid_packet_count": len(valid), "invalid_packet_count": len(invalid),
        "guard_control_both_arms_blocked_count": sum(
            row.get("score", {}).get("arms", {}).get("old_contract", {}).get("would_deliver") is False
            and row.get("score", {}).get("arms", {}).get("new_contract", {}).get("would_deliver") is False
            and row["calls"] == {"A": None, "B": None} for row in guards),
        "selector_parity_all_packets": all(
            row.get("score", {}).get("selection_guard_parity") is True for row in rows),
        "source_and_selected_plan_identity_both_arms": all(
            row.get("score", {}).get("source_digest") == m45.digest(row["source"]["text"])
            and row.get("score", {}).get("selected_plan_digest") == row["selected_plan_digest_before_review"]
            and row.get("score", {}).get("selected_fingerprint") == row["selected_fingerprint_before_review"]
            and row.get("score", {}).get("selected_plan", {}).get("goal_source_id") == row["source"]["id"]
            and row.get("score", {}).get("selected_plan", {}).get("goal_source_span") == row["source"]["text"]
            for row in rows),
        "review_scored_call_count": sum(row["call_started"][arm]
                                        for row in rows for arm in ("A", "B")),
    }
    per_arm = {}
    for arm in ("A", "B"):
        calls = [row["calls"][arm] for row in eligible if isinstance(row["calls"][arm], dict)]
        times = [call["wall_seconds"] for call in calls if isinstance(call.get("wall_seconds"), (int, float))]
        completed = sum(call.get("completed") is True and call.get("json_parse_success") is True
                        and old_runner._tokens_complete(call) for call in calls)
        source_exact = sum(isinstance(row["reviews"][arm], dict)
                           and row["reviews"][arm].get("source_id") == row["source"]["id"]
                           and row["reviews"][arm].get("source_span") == row["source"]["text"]
                           for row in eligible)
        reason_key = "old_category_reason_hit" if arm == "A" else "new_category_reason_hit"
        reason_metric = ("mapped_expected_axis_false_check_count" if arm == "A"
                         else "explicit_expected_axis_fail_count")
        arm_metrics = {
            "completed_parseable_token_count": completed,
            "source_exact_count": source_exact,
            "valid_retained_count": _count(valid, arm, "valid_retained"),
            "invalid_false_action_count": _count(invalid, arm, "false_action"),
            reason_metric: sum(row.get("score", {}).get(reason_key) is True
                               for row in invalid),
            "reviewer_only_max_wall_seconds": max(times) if times else None,
            "reviewer_only_median_wall_seconds": statistics.median(times) if times else None,
            "prompt_tokens": sum(call.get("prompt_tokens") or 0 for call in calls),
            "completion_tokens": sum(call.get("completion_tokens") or 0 for call in calls),
        }
        comparisons = {
            "completed_parseable_token_count": gates["per_arm_completed_parseable_token_count"],
            "source_exact_count": gates["per_arm_source_exact_count"],
            "valid_retained_count": gates["per_arm_valid_retained_count"],
            "invalid_false_action_count": gates["per_arm_invalid_false_action_count"],
            reason_metric: gates["per_arm_explicit_expected_axis_fail_count"],
        }
        failed = [key for key, expected in comparisons.items() if arm_metrics[key] != expected]
        if (arm_metrics["reviewer_only_max_wall_seconds"] is None
                or arm_metrics["reviewer_only_max_wall_seconds"] >
                gates["per_arm_reviewer_only_max_wall_seconds"]):
            failed.append("reviewer_only_max_wall_seconds")
        per_arm[arm] = {"metrics": arm_metrics, "failed_gates": failed,
                        "reason_diagnostic_kind": (
                            "legacy_many_to_one_false_check_proxy" if arm == "A"
                            else "explicit_expected_axis_fail_and_primary_proxy"),
                        "component_gate_pass": not failed}
    common_expected = {
        "deterministic_eligible_packet_count": gates["deterministic_eligible_packet_count"],
        "valid_packet_count": gates["valid_packet_count"],
        "invalid_packet_count": gates["invalid_packet_count"],
        "guard_control_both_arms_blocked_count": gates["guard_control_both_arms_blocked_count"],
        "review_scored_call_count": contract["execution"]["maximum_review_scored_calls"],
        "selector_parity_all_packets": True,
        "source_and_selected_plan_identity_both_arms": True,
    }
    common_failed = [key for key, expected in common_expected.items() if metrics[key] != expected]
    # Only delivery decisions are paired here.  A's many-to-one mapped false
    # check and B's explicit primary-axis fail are not symmetric reason quality.
    paired = {"B_only_decision_correct_count": 0, "A_only_decision_correct_count": 0,
              "B_only_decision_correct_packet_ids": [],
              "A_only_decision_correct_packet_ids": [],
              "valid_retention_B_only_count": 0, "valid_retention_A_only_count": 0,
              "invalid_block_B_only_count": 0, "invalid_block_A_only_count": 0,
              "reason_metrics_not_semantically_symmetric": True}
    for row in eligible:
        if "arms" not in row.get("score", {}):
            continue
        def decision_correct(arm: str) -> bool:
            decision = row["score"]["arms"]["old_contract" if arm == "A" else "new_contract"]
            if row["gold_label"] == "valid":
                return decision["valid_retained"] is True
            return decision["would_deliver"] is False
        a, b = decision_correct("A"), decision_correct("B")
        if b and not a:
            paired["B_only_decision_correct_packet_ids"].append(row["packet_id"])
            key = ("valid_retention_B_only_count" if row["gold_label"] == "valid"
                   else "invalid_block_B_only_count")
            paired[key] += 1
        if a and not b:
            paired["A_only_decision_correct_packet_ids"].append(row["packet_id"])
            key = ("valid_retention_A_only_count" if row["gold_label"] == "valid"
                   else "invalid_block_A_only_count")
            paired[key] += 1
    paired["B_only_decision_correct_count"] = len(paired["B_only_decision_correct_packet_ids"])
    paired["A_only_decision_correct_count"] = len(paired["A_only_decision_correct_packet_ids"])
    b_pass = not common_failed and per_arm["B"]["component_gate_pass"]
    status = ("bounded_component_pass_not_product_eligible" if b_pass
              else "review_required_component_fail")
    return {"metrics": metrics, "common_failed_gates": common_failed,
            "arms": per_arm, "paired": paired, "B_component_gate_pass": b_pass,
            "A_component_gate_pass": not common_failed and per_arm["A"]["component_gate_pass"],
            "product_eligible": False, "status": status,
            "reason_quality_human_validated": False,
            "claim_boundary": contract["claim_boundary"]}


def run(contract_path: Path = CONTRACT_PATH, output_path: Path = RESULT_PATH) -> dict:
    contract_path, output_path = contract_path.resolve(), output_path.resolve()
    contract, dataset, planned = preflight(contract_path, output_path)
    evidence = {
        "schema": "uruha_p4_m46_decision_interface_result_v1",
        "status": "running_not_reusable", "freeze_sha": FREEZE_SHA,
        "contract_sha256": _hash(contract_path), "dataset_sha256": contract["dataset"]["sha256"],
        "runner_sha256": _hash(Path(__file__)), "retry_count": 0,
        "arm_order_rule": "eligible case index even A-B, odd B-A",
        "maximum_review_scored_calls": contract["execution"]["maximum_review_scored_calls"],
        "generation_scored_calls": 0, "prewarm": None, "rows": [], "summary": None,
        "production_database_access": False, "product_runtime_changed": False,
        "product_eligible": False, "claim_boundary": contract["claim_boundary"],
    }
    old_runner._checkpoint(output_path, evidence, first=True)
    evidence["prewarm"] = old_runner.prewarm_model(
        contract["model"], contract["controlled_constants"]["keep_alive"])
    old_runner._checkpoint(output_path, evidence)
    if evidence["prewarm"].get("completed") is not True:
        evidence["status"] = "prewarm_failed_no_scored_calls"
        old_runner._checkpoint(output_path, evidence)
        return evidence
    legacy_contract = _legacy_review_contract(contract)
    eligible_index = 0
    for item in planned:
        prior = item["prior_score"]
        row = {
            "packet_id": item["packet_id"], "category": item["category"],
            "source": deepcopy(item["source"]), "batch_digest": m45.digest(item["batch"]),
            "gold_label": item["gold_label"],
            "expected_failed_axis": item["expected_failed_axis"],
            "selected_plan_digest_before_review": prior["selected_plan_digest"],
            "selected_fingerprint_before_review": prior["selected_fingerprint"],
            "deterministic_eligible": prior["deterministic_eligible"],
            "arm_order": list(_arm_order(eligible_index)) if prior["deterministic_eligible"] else [],
            "call_started": {"A": False, "B": False},
            "calls": {"A": None, "B": None}, "reviews": {"A": None, "B": None},
            "score": prior,
        }
        evidence["rows"].append(row)
        old_runner._checkpoint(output_path, evidence)
        if not prior["deterministic_eligible"]:
            continue  # one common guard control, zero review calls
        eligible_index += 1
        for arm in row["arm_order"]:
            started = sum(saved["call_started"][key] for saved in evidence["rows"]
                          for key in ("A", "B"))
            if started >= contract["execution"]["maximum_review_scored_calls"]:
                evidence["status"] = "review_call_budget_exceeded_partial_no_resume"
                old_runner._checkpoint(output_path, evidence)
                return evidence
            row["call_started"][arm] = True
            old_runner._checkpoint(output_path, evidence)
            try:
                if arm == "A":
                    call = old_runner.model_json_call(
                        stage="review", case_id=item["packet_id"], source=item["source"],
                        plan=prior["selected_plan"], contract=legacy_contract)
                else:
                    call = model_json_call_b(
                        case_id=item["packet_id"], source=item["source"],
                        plan=prior["selected_plan"], contract=contract)
            except Exception as exc:
                call = {"attempted": True, "completed": False,
                        "error_type": type(exc).__name__, "error": str(exc)[:300]}
            parsed = call.pop("parsed", None)
            row["calls"][arm] = call
            row["reviews"][arm] = parsed if isinstance(parsed, dict) else None
            old_runner._checkpoint(output_path, evidence)
            if (call.get("completed") is not True
                    or call.get("json_parse_success") is not True
                    or not old_runner._tokens_complete(call)
                    or not isinstance(parsed, dict)):
                evidence["status"] = "review_call_failed_partial_no_resume"
                old_runner._checkpoint(output_path, evidence)
                return evidence
        a_call, b_call = row["calls"]["A"], row["calls"]["B"]
        if (a_call.get("payload_digest") != b_call.get("payload_digest")
                or a_call.get("options") != b_call.get("options")
                or a_call.get("model") != b_call.get("model")
                or a_call.get("system_sha256") !=
                hashlib.sha256(m46.REVIEW_SYSTEM.encode("utf-8")).hexdigest()
                or b_call.get("system_sha256") !=
                hashlib.sha256(scoring.DECISION_REVIEW_SYSTEM.encode("utf-8")).hexdigest()):
            evidence["status"] = "paired_transport_changed_partial_no_resume"
            old_runner._checkpoint(output_path, evidence)
            return evidence
        try:
            row["score"] = scoring.score_packet(
                item["source"], item["batch"], row["reviews"]["A"], row["reviews"]["B"],
                item["gold_label"], item["expected_failed_axis"])
        except Exception as exc:
            row.update(packet_error_type=type(exc).__name__, packet_error=str(exc)[:300])
            evidence["status"] = "review_packet_failed_partial_no_resume"
            old_runner._checkpoint(output_path, evidence)
            return evidence
        if (row["score"]["selected_plan_digest"] != prior["selected_plan_digest"]
                or row["score"]["selected_fingerprint"] != prior["selected_fingerprint"]
                or row["score"]["source_digest"] != prior["source_digest"]
                or row["score"]["selected_plan"] != prior["selected_plan"]):
            evidence["status"] = "paired_packet_changed_partial_no_resume"
            old_runner._checkpoint(output_path, evidence)
            return evidence
        old_runner._checkpoint(output_path, evidence)
    evidence["summary"] = summarize(evidence["rows"], contract)
    evidence["status"] = evidence["summary"]["status"]
    old_runner._checkpoint(output_path, evidence)
    return evidence


def main() -> int:
    result = run()
    print(json.dumps({"status": result["status"], "rows": len(result["rows"]),
                      "summary": result.get("summary")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
