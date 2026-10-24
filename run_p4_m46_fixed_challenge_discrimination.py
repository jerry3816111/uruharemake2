#!/usr/bin/env python3
"""One-shot fixed-packet M46 discrimination study; B is offline-only.

The existing M51 generation failure is never resumed.  Only the nine frozen
hand-authored challenge packets are replayed, with at most eight M46 calls.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import urllib.request

import p4_m46_reviewer_necessity_scoring as scoring
import run_p4_m46_reviewer_necessity as old_runner
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46


ROOT = Path(__file__).resolve().parent
FREEZE_SHA = "41bb4f02edf1bab392a001e0043eda4368d57144"
CONTRACT_PATH = ROOT / "configs/p4_m46_fixed_challenge_discrimination_v1.json"
RESULT_PATH = ROOT / "analysis/p4_m46_fixed_challenge_discrimination_2026-09-30.json"
RUNNER_PATHS = ("run_p4_m46_fixed_challenge_discrimination.py",
                "test_p4_m46_fixed_challenge_discrimination_runner.py")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _tracked_clean(relative: str) -> None:
    _git("ls-files", "--error-unmatch", relative)
    _git("diff", "--exit-code", "HEAD", "--", relative)
    _git("diff", "--cached", "--exit-code", "HEAD", "--", relative)


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.load(response)


def _relevant_false(review: dict, paths: list[str]) -> bool:
    for path in paths:
        group, field = path.split(".")
        checks = review.get(group)
        if isinstance(checks, dict) and checks.get(field) is False:
            return True
    return False


def _prepare_packets(contract: dict, dataset: dict) -> list[dict]:
    """Check all nine packets offline before prewarm or a scored call."""

    if dataset.get("status") != "sealed_before_model_execution":
        raise RuntimeError("Frozen packet dataset status mismatch")
    packets = dataset.get("challenge_packets")
    if not isinstance(packets, list) or len(packets) != 9:
        raise RuntimeError("Frozen challenge packet count mismatch")
    by_id = {packet["packet_id"]: packet for packet in packets}
    order = contract["dataset"]["packet_order"]
    if len(by_id) != 9 or len(order) != 9 or set(by_id) != set(order) or len(set(order)) != 9:
        raise RuntimeError("Frozen challenge packet order or identity mismatch")
    reasons = contract["invalid_category_relevant_false_checks"]
    gates = contract["preregistered_gates"]
    planned = []
    for packet_id in order:
        packet = by_id[packet_id]
        category = packet["category"]
        gold = "valid" if packet["gold"]["accept"] is True else "invalid"
        source, batch = packet["source"], packet["batch"]
        score = scoring.score_packet(source, batch, None, gold)
        expected = packet["expected_deterministic_guard"]
        if (score["selected_index"] != expected["selected_index"]
                or score["selection_guard_parity"] is not True
                or score["deterministic_eligible"] is not expected["arm_b_would_allow"]
                or score["selected_plan"].get("goal_source_id") != source["id"]
                or score["selected_plan"].get("goal_source_span") != source["text"]):
            raise RuntimeError(f"Frozen challenge guard/source mismatch: {packet_id}")
        if category == "guard_block" and score["deterministic_eligible"]:
            raise RuntimeError("Guard control unexpectedly eligible")
        if category != "guard_block" and not score["deterministic_eligible"]:
            raise RuntimeError(f"Reviewer challenge unexpectedly blocked: {packet_id}")
        if category in reasons:
            for path in reasons[category]:
                group, field = path.split(".")
                allowed = m46.CONTENT_CHECKS if group == "content_checks" else m46.SURFACE_CHECKS
                if field not in allowed:
                    raise RuntimeError(f"Unknown category-relevant check: {path}")
        planned.append({"packet_id": packet_id, "category": category,
                        "source": source, "batch": batch, "gold_label": gold,
                        "prior_score": score})

    eligible = [item for item in planned if item["prior_score"]["deterministic_eligible"]]
    valid = [item for item in eligible if item["gold_label"] == "valid"]
    invalid = [item for item in eligible if item["gold_label"] == "invalid"]
    blocked = [item for item in planned if not item["prior_score"]["deterministic_eligible"]]
    b_valid = sum(item["prior_score"]["arms"]["B_deterministic_only"]["valid_retained"]
                  for item in planned)
    b_false = sum(item["prior_score"]["arms"]["B_deterministic_only"]["false_action"]
                  for item in planned)
    m39_exact = sum(bool(item["prior_score"]["m39_final_byte_identical"]
                         and item["prior_score"]["m39_surface_trace"].get("action") == "accept"
                         and m45._japanese(item["prior_score"]["selected_plan"].get("instruction_jp")))
                    for item in eligible)
    if (len(eligible) != gates["deterministic_eligible_packet_count"]
            or len(valid) != gates["valid_packet_count"]
            or len(invalid) != gates["semantic_or_surface_invalid_packet_count"]
            or len(blocked) != gates["guard_control_count"]
            or blocked[0]["category"] != "guard_block"
            or b_valid != gates["B_valid_retained_count_preflight"]
            or b_false != gates["B_invalid_false_action_count_preflight"]
            or m39_exact != gates["natural_japanese_and_m39_exact_count"]):
        raise RuntimeError("Frozen challenge preflight gate mismatch")
    return planned


def _legacy_review_contract(contract: dict) -> dict:
    """Map only the new seed/cap names expected by the hash-bound old helper."""

    adapter = deepcopy(contract)
    constants = adapter["controlled_constants"]
    constants["m46_seed"] = constants["seed"]
    constants["m46_num_predict"] = constants["num_predict"]
    return adapter


def preflight(contract_path: Path = CONTRACT_PATH,
              output_path: Path = RESULT_PATH) -> tuple[dict, dict, list[dict]]:
    contract_path, output_path = contract_path.resolve(), output_path.resolve()
    if contract_path != CONTRACT_PATH or output_path != RESULT_PATH:
        raise RuntimeError("Formal fixed challenge study requires fixed contract and output paths")
    if output_path.exists():
        raise RuntimeError("Existing fixed challenge result cannot be overwritten or resumed")
    if _git("rev-parse", FREEZE_SHA) != FREEZE_SHA:
        raise RuntimeError("Freeze commit does not resolve exactly")
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_SHA, "HEAD"], cwd=ROOT, check=True)
    for relative in RUNNER_PATHS:
        _tracked_clean(relative)
    frozen_paths = (
        "research/p4_m46_fixed_challenge_discrimination_plan_2026-09-30.md",
        "configs/p4_m46_fixed_challenge_discrimination_v1.json",
        "test_p4_m46_fixed_challenge_discrimination_freeze.py",
    )
    _git("diff", "--exit-code", FREEZE_SHA, "--", *frozen_paths)
    scoring._require_isolated_modules()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if (contract.get("status") != "prospectively_frozen_before_model_execution"
            or contract.get("model") != "qwen3.5:9b"
            or contract["controlled_constants"]["retry_count"] != 0
            or contract["execution"]["generation_scored_call_count"] != 0
            or contract["execution"]["maximum_review_scored_calls"] != 8
            or contract["execution"]["result_path"] != str(RESULT_PATH.relative_to(ROOT))):
        raise RuntimeError("Frozen fixed-challenge contract mismatch")
    dataset_record = contract["dataset"]
    if _hash(ROOT / dataset_record["path"]) != dataset_record["sha256"]:
        raise RuntimeError("Frozen challenge dataset hash mismatch")
    for label, record in contract["hash_bound_dependencies"].items():
        if _hash(ROOT / record["path"]) != record["sha256"]:
            raise RuntimeError(f"Frozen dependency hash mismatch: {label}")
    prior = contract["prior_inconclusive_result"]
    if _hash(ROOT / prior["path"]) != prior["sha256"]:
        raise RuntimeError("Original partial failure artifact changed")
    original = json.loads((ROOT / prior["path"]).read_text(encoding="utf-8"))
    if original.get("status") != prior["status"] or original.get("review_calls") != 0:
        raise RuntimeError("Original A/B failure state changed")
    dataset = json.loads((ROOT / dataset_record["path"]).read_text(encoding="utf-8"))
    planned = _prepare_packets(contract, dataset)
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Formal host must be Apple arm64")
    cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    if cpu != "Apple M2 Pro" or memory != 34359738368:
        raise RuntimeError("Formal hardware must be M2 Pro 32GB")
    if not _get_json("http://127.0.0.1:11434/api/version").get("version"):
        raise RuntimeError("Local Ollama unavailable")
    tags = _get_json("http://127.0.0.1:11434/api/tags")
    digests = {row["name"]: row["digest"] for row in tags["models"]}
    if digests.get(contract["model"]) != contract["model_digest"]:
        raise RuntimeError("Frozen model digest mismatch")
    return contract, dataset, planned


def summarize(rows: list[dict], contract: dict) -> dict:
    gates = contract["preregistered_gates"]
    eligible = [row for row in rows if row["deterministic_eligible"]]
    valid = [row for row in eligible if row["gold_label"] == "valid"]
    invalid = [row for row in eligible if row["gold_label"] == "invalid"]
    calls = [row["review_call"] for row in eligible if isinstance(row["review_call"], dict)]
    source_exact = sum(row.get("review", {}).get("source_id") == row["source"]["id"]
                       and row.get("review", {}).get("source_span") == row["source"]["text"]
                       for row in eligible)
    times = [call["wall_seconds"] for call in calls]
    metrics = {
        "packet_count": len(rows),
        "selector_parity_all_packets": all(row["score"]["selection_guard_parity"] is True
                                           for row in rows),
        "source_and_selected_plan_identity_both_arms": all(
            row["score"]["source_digest"] == m45.digest(row["source"]["text"])
            and row["score"]["selected_plan"].get("goal_source_id") == row["source"]["id"]
            and row["score"]["selected_plan"].get("goal_source_span") == row["source"]["text"]
            and row["score"]["selected_plan_digest"] == row["selected_plan_digest_before_review"]
            and row["score"]["selected_fingerprint"] == row["selected_fingerprint_before_review"]
            for row in rows),
        "review_scored_call_count": len(calls),
        "review_completed_json_and_tokens_count": sum(
            call.get("completed") is True and call.get("json_parse_success") is True
            and old_runner._tokens_complete(call) for call in calls),
        "review_source_identity_exact_count": source_exact,
        "A_valid_retained_count": sum(row["score"]["arms"]["A_model_review"]["valid_retained"] for row in valid),
        "A_invalid_false_action_count": sum(row["score"]["arms"]["A_model_review"]["false_action"] for row in invalid),
        "A_category_relevant_false_check_count": sum(row.get("category_relevant_false_check") is True for row in invalid),
        "B_valid_retained_count": sum(row["score"]["arms"]["B_deterministic_only"]["valid_retained"] for row in valid),
        "B_invalid_false_action_count": sum(row["score"]["arms"]["B_deterministic_only"]["false_action"] for row in invalid),
        "guard_control_both_arms_blocked_count": sum(
            not row["score"]["arms"]["A_model_review"]["would_deliver"]
            and not row["score"]["arms"]["B_deterministic_only"]["would_deliver"]
            for row in rows if row["category"] == "guard_block"),
        "natural_japanese_and_m39_exact_count": sum(
            row["score"]["m39_final_byte_identical"]
            and row["score"]["m39_surface_trace"].get("action") == "accept"
            and m45._japanese(row["score"]["selected_plan"].get("instruction_jp"))
            for row in eligible),
        "reviewer_only_max_wall_seconds": max(times) if times else None,
        "reviewer_only_median_wall_seconds": statistics.median(times) if times else None,
        "review_prompt_tokens": sum(call.get("prompt_tokens") or 0 for call in calls),
        "review_completion_tokens": sum(call.get("completion_tokens") or 0 for call in calls),
    }
    failed = []
    comparisons = {
        "selector_parity_all_packets": gates["selector_parity_all_packets"],
        "source_and_selected_plan_identity_both_arms": gates["source_and_selected_plan_identity_both_arms"],
        "review_scored_call_count": gates["deterministic_eligible_packet_count"],
        "review_completed_json_and_tokens_count": gates["A_review_completed_json_and_tokens_count"],
        "review_source_identity_exact_count": gates["A_review_source_identity_exact_count"],
        "A_valid_retained_count": gates["A_valid_retained_count"],
        "A_invalid_false_action_count": gates["A_invalid_false_action_count"],
        "A_category_relevant_false_check_count": gates["A_category_relevant_false_check_count"],
        "B_valid_retained_count": gates["B_valid_retained_count_preflight"],
        "B_invalid_false_action_count": gates["B_invalid_false_action_count_preflight"],
        "guard_control_both_arms_blocked_count": gates["guard_control_both_arms_blocked_count"],
        "natural_japanese_and_m39_exact_count": gates["natural_japanese_and_m39_exact_count"],
    }
    for key, expected in comparisons.items():
        if metrics[key] != expected:
            failed.append(key)
    quality_pass = not failed
    max_wall = metrics["reviewer_only_max_wall_seconds"]
    reviewer_only_within_20 = bool(max_wall is not None and max_wall <=
                                   contract["latency_interpretation"]["product_two_stage_budget_seconds"])
    status = (
        "fixed_discrimination_fail" if not quality_pass
        else "bounded_quality_value_cost_ineligible" if not reviewer_only_within_20
        else "bounded_fixed_discrimination_pass_not_product_eligible"
    )
    return {"metrics": metrics, "failed_quality_gates": failed,
            "A_fixed_quality_pass": quality_pass,
            "A_reviewer_only_within_20_seconds": reviewer_only_within_20,
            "B_product_bypass_authorized": False, "product_qualified": False,
            "status": status, "claim_boundary": contract["claim_boundary"]}


def run(contract_path: Path = CONTRACT_PATH, output_path: Path = RESULT_PATH) -> dict:
    contract_path, output_path = contract_path.resolve(), output_path.resolve()
    contract, dataset, planned = preflight(contract_path, output_path)
    if len(planned) != contract["execution"]["challenge_packet_count"]:
        raise RuntimeError("Packet count changed after preflight")
    evidence = {
        "schema": "uruha_p4_m46_fixed_challenge_discrimination_result_v1",
        "status": "running_not_reusable", "freeze_sha": FREEZE_SHA,
        "contract_sha256": _hash(contract_path),
        "dataset_sha256": contract["dataset"]["sha256"],
        "runner_sha256": _hash(Path(__file__)),
        "prior_failure_sha256": contract["prior_inconclusive_result"]["sha256"],
        "retry_count": 0, "prewarm": None, "rows": [], "summary": None,
        "maximum_review_scored_calls": contract["execution"]["maximum_review_scored_calls"],
        "generation_scored_calls": 0, "production_database_access": False,
        "product_runtime_changed": False, "claim_boundary": contract["claim_boundary"],
    }
    old_runner._checkpoint(output_path, evidence, first=True)
    evidence["prewarm"] = old_runner.prewarm_model(
        contract["model"], contract["controlled_constants"]["keep_alive"])
    old_runner._checkpoint(output_path, evidence)
    if evidence["prewarm"].get("completed") is not True:
        evidence["status"] = "prewarm_failed_no_scored_calls"
        old_runner._checkpoint(output_path, evidence)
        return evidence
    adapter = _legacy_review_contract(contract)
    for item in planned:
        prior = item["prior_score"]
        row = {"packet_id": item["packet_id"], "category": item["category"],
               "source": deepcopy(item["source"]), "batch_digest": m45.digest(item["batch"]),
               "gold_label": item["gold_label"],
               "selected_plan_digest_before_review": prior["selected_plan_digest"],
               "selected_fingerprint_before_review": prior["selected_fingerprint"],
               "deterministic_eligible": prior["deterministic_eligible"],
               "review_call_started": False, "review_call": None, "score": prior}
        evidence["rows"].append(row)
        old_runner._checkpoint(output_path, evidence)
        if prior["deterministic_eligible"]:
            if sum(saved["review_call_started"] for saved in evidence["rows"]) >= contract["execution"]["maximum_review_scored_calls"]:
                evidence["status"] = "review_call_budget_exceeded_partial_no_resume"
                old_runner._checkpoint(output_path, evidence)
                return evidence
            row["review_call_started"] = True
            old_runner._checkpoint(output_path, evidence)
            try:
                call = old_runner.model_json_call(
                    stage="review", case_id=item["packet_id"], source=item["source"],
                    plan=prior["selected_plan"], contract=adapter)
            except Exception as exc:
                row["review_call"] = {"attempted": True, "completed": False,
                                      "error_type": type(exc).__name__, "error": str(exc)[:300]}
                evidence["status"] = "review_call_failed_partial_no_resume"
                old_runner._checkpoint(output_path, evidence)
                return evidence
            parsed = call.pop("parsed", None)
            row["review_call"] = call
            if (call.get("completed") is not True or call.get("json_parse_success") is not True
                    or not old_runner._tokens_complete(call) or not isinstance(parsed, dict)):
                evidence["status"] = "review_call_failed_partial_no_resume"
                old_runner._checkpoint(output_path, evidence)
                return evidence
            row["review"] = parsed
            try:
                row["score"] = scoring.score_packet(
                    item["source"], item["batch"], parsed, item["gold_label"])
            except Exception as exc:
                row.update(packet_error_type=type(exc).__name__, packet_error=str(exc)[:300])
                evidence["status"] = "review_packet_failed_partial_no_resume"
                old_runner._checkpoint(output_path, evidence)
                return evidence
            if (row["score"]["selected_plan_digest"] != prior["selected_plan_digest"]
                    or row["score"]["selected_fingerprint"] != prior["selected_fingerprint"]
                    or row["score"]["source_digest"] != prior["source_digest"]):
                evidence["status"] = "paired_packet_changed_partial_no_resume"
                old_runner._checkpoint(output_path, evidence)
                return evidence
            checks = contract["invalid_category_relevant_false_checks"].get(item["category"])
            row["category_relevant_false_check"] = (
                _relevant_false(parsed, checks) if checks is not None else None)
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
