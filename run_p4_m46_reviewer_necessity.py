#!/usr/bin/env python3
"""One-shot, two-phase offline M46 reviewer-necessity ablation.

``generate`` saves six fresh M51 packets without reviewing or labeling them.
The packet artifact and a separate blind-to-review gold artifact must then be
committed in that order. ``review`` replays those exact packets plus the nine
frozen challenge packets. B is scored counterfactually; no product bypass,
database write, or Web delivery occurs here.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time
import urllib.request

import p4_m46_reviewer_necessity_scoring as scoring
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


ROOT = Path(__file__).resolve().parent
FREEZE_SHA = "2d522885b939cdb9a3dfd6d8bf4a2786527b6f31"
CONTRACT_PATH = ROOT / "configs/p4_m46_reviewer_necessity_v1.json"
GENERATED_PATH = ROOT / "analysis/p4_m46_reviewer_necessity_generation_2026-09-30.json"
GOLD_PATH = ROOT / "analysis/p4_m46_reviewer_necessity_generated_gold_2026-09-30.json"
REVIEW_PATH = ROOT / "analysis/p4_m46_reviewer_necessity_review_2026-09-30.json"
RUNNER_PATHS = ("run_p4_m46_reviewer_necessity.py", "test_p4_m46_reviewer_necessity_runner.py")
OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"
OLLAMA_GENERATE = "http://127.0.0.1:11434/api/generate"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: object) -> str:
    return m45.digest(value)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.load(response)


def _post_json(url: str, body: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _tracked_clean(relative: str) -> None:
    _git("ls-files", "--error-unmatch", relative)
    _git("diff", "--exit-code", "HEAD", "--", relative)
    _git("diff", "--cached", "--exit-code", "HEAD", "--", relative)


def _committed_artifact(path: Path) -> str:
    relative = str(path.relative_to(ROOT))
    _tracked_clean(relative)
    committed = subprocess.check_output(
        ["git", "show", f"HEAD:{relative}"], cwd=ROOT,
    )
    if committed != path.read_bytes():
        raise RuntimeError(f"Uncommitted artifact bytes: {relative}")
    return _git("log", "-1", "--format=%H", "--", relative)


def _preflight_common(contract_path: Path, output_path: Path, expected_output: Path) -> tuple[dict, dict]:
    if output_path != expected_output or contract_path != CONTRACT_PATH:
        raise RuntimeError("Formal M46 ablation requires fixed contract and output paths")
    if output_path.exists():
        raise RuntimeError("Existing result cannot be overwritten or resumed")
    if _git("rev-parse", FREEZE_SHA) != FREEZE_SHA:
        raise RuntimeError("Freeze commit does not resolve exactly")
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_SHA, "HEAD"], cwd=ROOT, check=True)
    for relative in RUNNER_PATHS:
        _tracked_clean(relative)
    scoring._require_isolated_modules()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("status") != "prospectively_frozen_before_model_execution":
        raise RuntimeError("M46 ablation contract is not frozen")
    frozen_paths = ["configs/p4_m46_reviewer_necessity_v1.json", contract["dataset"]["path"],
                    "p4_m46_reviewer_necessity_scoring.py", "test_p4_m46_reviewer_necessity_freeze.py",
                    "test_p4_m46_reviewer_necessity_scoring.py",
                    "research/p4_m46_reviewer_necessity_plan_2026-09-30.md"]
    _git("diff", "--exit-code", FREEZE_SHA, "--", *frozen_paths)
    if _hash(ROOT / contract["dataset"]["path"]) != contract["dataset"]["sha256"]:
        raise RuntimeError("Frozen dataset hash mismatch")
    for label, record in contract["hash_bound_implementation"].items():
        if _hash(ROOT / record["path"]) != record["sha256"]:
            raise RuntimeError(f"Frozen implementation hash mismatch: {label}")
    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    if (dataset.get("status") != "sealed_before_model_execution"
            or len(dataset.get("generation_cases", [])) != 6
            or len(dataset.get("challenge_packets", [])) != 9):
        raise RuntimeError("Frozen case count or state mismatch")
    if contract["model"] != "qwen3.5:9b" or contract["controlled_constants"]["retry_count"] != 0:
        raise RuntimeError("Model or retry contract mismatch")
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
    # An incorrect challenge packet must fail before even a prewarm call.
    for packet in dataset["challenge_packets"]:
        gold = "valid" if packet["gold"]["accept"] is True else "invalid"
        score = scoring.score_packet(packet["source"], packet["batch"], None, gold)
        expected = packet["expected_deterministic_guard"]
        if (score["selected_index"] != expected["selected_index"]
                or score["selection_guard_parity"] is not True
                or score["deterministic_eligible"] is not expected["arm_b_would_allow"]):
            raise RuntimeError(f"Frozen challenge guard mismatch: {packet['packet_id']}")
    return contract, dataset


def preflight_generate(contract_path: Path = CONTRACT_PATH,
                       output_path: Path = GENERATED_PATH) -> tuple[dict, dict]:
    if GOLD_PATH.exists() or REVIEW_PATH.exists():
        raise RuntimeError("Later-phase artifacts exist; generation cannot be restarted")
    return _preflight_common(contract_path.resolve(), output_path.resolve(), GENERATED_PATH)


def _validate_generated_artifact(artifact: dict, dataset: dict) -> None:
    cases = dataset["generation_cases"]
    rows = artifact.get("rows") if isinstance(artifact, dict) else None
    if artifact.get("status") != "complete_unannotated" or not isinstance(rows, list) or len(rows) != len(cases):
        raise RuntimeError("Generated packet artifact is incomplete")
    if artifact.get("gold_labels_present") is not False or artifact.get("review_calls") != 0:
        raise RuntimeError("Generation phase leaked labels or review calls")
    if [row.get("case_id") for row in rows] != [case["case_id"] for case in cases]:
        raise RuntimeError("Generated packet order differs from freeze")
    for row, case in zip(rows, cases):
        if row.get("source") != case["source"] or not isinstance(row.get("batch"), dict):
            raise RuntimeError("Generated packet source or batch missing")
        call = row.get("call") or {}
        if not call.get("completed") or not call.get("json_parse_success") or not _tokens_complete(call):
            raise RuntimeError("Generated packet call incomplete")
        score = scoring.score_packet(case["source"], row["batch"], None, "uncertain")
        if (row.get("selected_plan_digest") != score["selected_plan_digest"]
                or row.get("selected_fingerprint") != score["selected_fingerprint"]
                or row.get("guard_violations") != score["guard_violations"]):
            raise RuntimeError("Generated packet selection or guard changed")


def _validate_gold(gold: dict, generated: dict) -> dict[str, dict]:
    if (gold.get("schema") != "uruha_p4_m46_generated_gold_v1"
            or gold.get("generation_sha256") != _hash(GENERATED_PATH)):
        raise RuntimeError("Gold artifact does not bind the generated packet bytes")
    labels = gold.get("labels")
    if not isinstance(labels, list) or len(labels) != len(generated["rows"]):
        raise RuntimeError("Gold must label all six generated cases before review")
    by_id = {}
    for item in labels:
        if not isinstance(item, dict) or item.get("label") not in {"valid", "invalid", "uncertain"}:
            raise RuntimeError("Gold label invalid")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise RuntimeError("Gold requires a nonempty independent reason")
        case_id = item.get("case_id")
        if case_id in by_id:
            raise RuntimeError("Duplicate gold case")
        by_id[case_id] = item
    for row in generated["rows"]:
        item = by_id.get(row["case_id"])
        if not item or item.get("selected_plan_digest") != row["selected_plan_digest"]:
            raise RuntimeError("Gold missing or bound to another selected plan")
    return by_id


def preflight_review(contract_path: Path = CONTRACT_PATH,
                     generated_path: Path = GENERATED_PATH,
                     gold_path: Path = GOLD_PATH,
                     output_path: Path = REVIEW_PATH) -> tuple[dict, dict, dict, dict, dict]:
    contract_path, generated_path, gold_path, output_path = (
        path.resolve() for path in (contract_path, generated_path, gold_path, output_path)
    )
    if generated_path != GENERATED_PATH or gold_path != GOLD_PATH:
        raise RuntimeError("Formal review requires the fixed generated and gold paths")
    if not generated_path.exists() or not gold_path.exists():
        raise RuntimeError("Committed generated packet and blind gold artifacts are required before review")
    contract, dataset = _preflight_common(contract_path, output_path, REVIEW_PATH)
    generated_commit = _committed_artifact(generated_path)
    gold_commit = _committed_artifact(gold_path)
    if not generated_commit or not gold_commit or generated_commit == gold_commit:
        raise RuntimeError("Generated packet and blind gold require separate commits")
    subprocess.run(["git", "merge-base", "--is-ancestor", generated_commit, gold_commit], cwd=ROOT, check=True)
    generated = json.loads(generated_path.read_text(encoding="utf-8"))
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    if generated.get("freeze_sha") != FREEZE_SHA or generated.get("contract_sha256") != _hash(contract_path):
        raise RuntimeError("Generated artifact does not bind the current frozen contract")
    _validate_generated_artifact(generated, dataset)
    labels = _validate_gold(gold, generated)
    return contract, dataset, generated, gold, labels


def prewarm_model(model: str, keep_alive: str) -> dict:
    started = time.monotonic()
    row = {"model": model, "attempted": True, "completed": False}
    try:
        data = _post_json(
            OLLAMA_GENERATE,
            {"model": model, "prompt": "", "stream": False, "keep_alive": keep_alive},
            120,
        )
        row.update(completed=True, load_duration_ns=int(data.get("load_duration") or 0),
                   total_duration_ns=int(data.get("total_duration") or 0))
    except Exception as exc:  # no retry
        row.update(error_type=type(exc).__name__, error=str(exc)[:300])
    row["wall_seconds"] = round(time.monotonic() - started, 5)
    return row


def model_json_call(*, stage: str, case_id: str, source: dict, plan: dict | None,
                    contract: dict) -> dict:
    constants = contract["controlled_constants"]
    if stage == "generate":
        system = m51.CANDIDATE_SYSTEM
        payload = {"user_sources": [source]}
        schema = m51._candidate_schema([source])
        seed, num_predict = constants["m51_seed"], constants["m51_num_predict"]
        timeout = contract["execution"]["generator_timeout_seconds"]
    elif stage == "review" and isinstance(plan, dict):
        system = m46.REVIEW_SYSTEM
        audited = {key: value for key, value in plan.items() if key != "progress_mechanism"}
        payload = {"sources": [source], "plan": audited,
                   "planned_payload_digest": m45.digest({"sources": [source], "plan": plan})}
        schema = m46.review_schema([source], plan)
        seed, num_predict = constants["m46_seed"], constants["m46_num_predict"]
        timeout = contract["execution"]["reviewer_timeout_seconds"]
    else:
        raise ValueError("Invalid model call stage or review plan")
    body = {
        "model": contract["model"],
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        "format": schema, "stream": False, "think": False,
        "keep_alive": constants["keep_alive"],
        "options": {"temperature": constants["temperature"], "seed": seed,
                    "num_ctx": constants["num_ctx"], "num_predict": num_predict},
    }
    started = time.monotonic()
    record = {"call_id": f"{stage}:{case_id}", "stage": stage, "model": contract["model"],
              "attempted": True, "completed": False, "json_parse_success": False,
              "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
              "schema_sha256": hashlib.sha256(
                  json.dumps(schema, ensure_ascii=False, sort_keys=True).encode("utf-8")
              ).hexdigest(),
              "payload_digest": _digest(payload), "options": deepcopy(body["options"])}
    try:
        data = _post_json(OLLAMA_CHAT, body, timeout)
        record.update(completed=True,
                      prompt_tokens=int(data.get("prompt_eval_count") or 0),
                      completion_tokens=int(data.get("eval_count") or 0),
                      load_duration_ns=int(data.get("load_duration") or 0),
                      total_duration_ns=int(data.get("total_duration") or 0))
        content = (data.get("message") or {}).get("content", "")
        record["content_digest"] = _digest(content)
        try:
            record["parsed"] = json.loads(content)
            record["json_parse_success"] = True
        except (ValueError, TypeError) as exc:
            record.update(error_type=type(exc).__name__, error=str(exc)[:300],
                          raw_content=content)
    except Exception as exc:  # preserve one-shot failure; never retry
        record.update(error_type=type(exc).__name__, error=str(exc)[:300])
    record["wall_seconds"] = round(time.monotonic() - started, 5)
    return record


def _tokens_complete(call: dict) -> bool:
    return bool(isinstance(call.get("prompt_tokens"), int) and call["prompt_tokens"] > 0
                and isinstance(call.get("completion_tokens"), int) and call["completion_tokens"] > 0)


def _checkpoint(path: Path, evidence: dict, *, first: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    if first:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".p4_m46_", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _unannotated_component(score: dict) -> dict:
    return {key: deepcopy(score[key]) for key in (
        "selected_plan", "selected_plan_digest", "selected_fingerprint", "selected_index",
        "selection_guard_parity", "guard_violations", "deterministic_eligible",
        "m39_surface_trace", "m39_final_byte_identical", "label_authorization",
    )}


def run_generate(contract_path: Path = CONTRACT_PATH,
                 output_path: Path = GENERATED_PATH) -> dict:
    contract_path, output_path = contract_path.resolve(), output_path.resolve()
    contract, dataset = preflight_generate(contract_path, output_path)
    evidence = {
        "schema": "uruha_p4_m46_reviewer_necessity_generation_v1",
        "status": "running_not_reusable", "freeze_sha": FREEZE_SHA,
        "contract_sha256": _hash(contract_path), "dataset_sha256": contract["dataset"]["sha256"],
        "runner_sha256": _hash(Path(__file__)), "gold_labels_present": False,
        "review_calls": 0, "retry_count": 0, "prewarm": None, "rows": [],
        "max_scored_calls": contract["execution"]["maximum_generation_scored_calls"],
        "production_database_access": False, "product_runtime_changed": False,
        "claim_boundary": contract["claim_boundary"],
    }
    _checkpoint(output_path, evidence, first=True)
    evidence["prewarm"] = prewarm_model(contract["model"], contract["controlled_constants"]["keep_alive"])
    _checkpoint(output_path, evidence)
    if evidence["prewarm"].get("completed") is not True:
        evidence["status"] = "prewarm_failed_no_scored_calls"
        _checkpoint(output_path, evidence)
        return evidence
    for case in dataset["generation_cases"]:
        source = deepcopy(case["source"])
        call = model_json_call(stage="generate", case_id=case["case_id"], source=source,
                               plan=None, contract=contract)
        batch = call.pop("parsed", None)
        row = {"case_id": case["case_id"], "source": source, "call": call,
               "batch": batch if isinstance(batch, dict) else None}
        evidence["rows"].append(row)
        if call.get("completed") is not True or call.get("json_parse_success") is not True or not _tokens_complete(call):
            evidence["status"] = "generation_call_failed_partial_no_resume"
            _checkpoint(output_path, evidence)
            return evidence
        try:
            score = scoring.score_packet(source, batch, None, "uncertain")
            row.update(_unannotated_component(score))
        except Exception as exc:
            row.update(packet_error_type=type(exc).__name__, packet_error=str(exc)[:300])
            evidence["status"] = "generation_packet_failed_partial_no_resume"
            _checkpoint(output_path, evidence)
            return evidence
        _checkpoint(output_path, evidence)
    evidence["status"] = "complete_unannotated"
    evidence["generation_scored_calls"] = len(evidence["rows"])
    evidence["generated_guard_eligible_count"] = sum(row["deterministic_eligible"] for row in evidence["rows"])
    evidence["prompt_tokens"] = sum(row["call"]["prompt_tokens"] for row in evidence["rows"])
    evidence["completion_tokens"] = sum(row["call"]["completion_tokens"] for row in evidence["rows"])
    _checkpoint(output_path, evidence)
    return evidence


def _review_inputs(dataset: dict, generated: dict, labels: dict) -> list[dict]:
    rows = []
    for row in generated["rows"]:
        rows.append({"case_id": row["case_id"], "stratum": "generated_m51",
                     "source": row["source"], "batch": row["batch"],
                     "gold_label": labels[row["case_id"]]["label"],
                     "generation_call": row["call"],
                     "expected_plan_digest": row["selected_plan_digest"]})
    for packet in dataset["challenge_packets"]:
        rows.append({"case_id": packet["packet_id"], "stratum": "hand_authored_challenge",
                     "category": packet["category"], "source": packet["source"],
                     "batch": packet["batch"],
                     "gold_label": "valid" if packet["gold"]["accept"] is True else "invalid",
                     "generation_call": None, "expected_plan_digest": None})
    return rows


def summarize_review(rows: list[dict], contract: dict) -> dict:
    generated = [row for row in rows if row["stratum"] == "generated_m51"]
    challenge = [row for row in rows if row["stratum"] == "hand_authored_challenge"]
    reviewed = [row for row in rows if isinstance(row.get("review_call"), dict)]
    def count(items, arm, field):
        return sum(row["score"]["arms"][arm][field] is True for row in items)
    def eligible(items):
        return [row for row in items if row["score"]["deterministic_eligible"]]
    challenge_valid = [row for row in challenge if row["gold_label"] == "valid"]
    challenge_invalid = [row for row in challenge if row["gold_label"] == "invalid"
                         and row.get("category") != "guard_block"]
    guard_controls = [row for row in challenge if row.get("category") == "guard_block"]
    generated_eligible = eligible(generated)
    calls = [row["review_call"] for row in reviewed]
    expected_review_calls = sum(row["score"]["deterministic_eligible"] for row in rows)
    all_calls_complete = bool(
        len(calls) == expected_review_calls
        and all(call.get("completed") and call.get("json_parse_success") for call in calls)
    )
    all_tokens_complete = bool(
        len(generated) == contract["execution"]["generation_case_count"]
        and all(_tokens_complete(row["generation_call"]) for row in generated)
        and all(_tokens_complete(call) for call in calls)
    )
    combined = [row["generation_call"]["wall_seconds"] + row["review_call"]["wall_seconds"]
                for row in generated if isinstance(row.get("review_call"), dict)]
    generation_times = [row["generation_call"]["wall_seconds"] for row in generated]
    metrics = {
        "challenge_valid_count": len(challenge_valid),
        "challenge_semantic_or_surface_invalid_count": len(challenge_invalid),
        "challenge_guard_control_count": len(guard_controls),
        "challenge_A_valid_retained_count": count(challenge_valid, "A_model_review", "valid_retained"),
        "challenge_A_false_action_count": count(challenge, "A_model_review", "false_action"),
        "challenge_B_false_action_count": count(challenge, "B_deterministic_only", "false_action"),
        "challenge_guard_control_A_and_B_blocked_count": sum(
            not row["score"]["arms"]["A_model_review"]["would_deliver"]
            and not row["score"]["arms"]["B_deterministic_only"]["would_deliver"]
            for row in guard_controls),
        "generated_valid_adjudicated_eligible_count": sum(row["gold_label"] == "valid" for row in generated_eligible),
        "generated_invalid_adjudicated_eligible_count": sum(row["gold_label"] == "invalid" for row in generated_eligible),
        "generated_uncertain_eligible_count": sum(row["gold_label"] == "uncertain" for row in generated_eligible),
        "generated_A_valid_retained_count": count(generated_eligible, "A_model_review", "valid_retained"),
        "generated_B_valid_retained_count": count(generated_eligible, "B_deterministic_only", "valid_retained"),
        "generated_A_invalid_or_uncertain_false_action_count": count(generated, "A_model_review", "false_action"),
        "generated_B_invalid_or_uncertain_false_action_count": count(generated, "B_deterministic_only", "false_action"),
        "review_scored_call_count": len(calls),
        "model_calls_json_complete": all_calls_complete,
        "token_accounting_complete": all_tokens_complete,
        "maximum_generated_A_total_wall_seconds": max(combined) if combined else None,
        "maximum_generated_B_total_wall_seconds": max(generation_times) if generation_times else None,
        "median_review_wall_seconds": statistics.median(call["wall_seconds"] for call in calls) if calls else None,
        "review_prompt_tokens": sum(call.get("prompt_tokens") or 0 for call in calls),
        "review_completion_tokens": sum(call.get("completion_tokens") or 0 for call in calls),
        "generation_prompt_tokens": sum(row["generation_call"].get("prompt_tokens") or 0 for row in generated),
        "generation_completion_tokens": sum(row["generation_call"].get("completion_tokens") or 0 for row in generated),
        "source_identity_exact": all(
            row["score"]["selected_plan"].get("goal_source_id") == row["source"]["id"]
            and row["score"]["selected_plan"].get("goal_source_span") == row["source"]["text"]
            and isinstance(row.get("review"), dict)
            and row["review"].get("source_id") == row["source"]["id"]
            and row["review"].get("source_span") == row["source"]["text"]
            for row in rows if row["score"]["deterministic_eligible"]),
        "natural_japanese_surface": all(
            m45._japanese(row["score"]["selected_plan"].get("instruction_jp"))
            and row["score"]["m39_surface_trace"].get("action") == "accept"
            for row in rows if row["score"]["deterministic_eligible"]),
    }
    gates = contract["preregistered_gates"]
    common_fail = []
    for key in ("challenge_valid_count", "challenge_semantic_or_surface_invalid_count",
                "challenge_guard_control_count", "challenge_guard_control_A_and_B_blocked_count",
                "model_calls_json_complete", "token_accounting_complete", "source_identity_exact",
                "natural_japanese_surface"):
        if metrics[key] != gates[key]:
            common_fail.append(key)
    if metrics["review_scored_call_count"] > contract["execution"]["maximum_review_scored_calls"]:
        common_fail.append("review_call_budget")
    a_fail = list(common_fail)
    for key in ("challenge_A_valid_retained_count", "challenge_A_false_action_count",
                "generated_A_invalid_or_uncertain_false_action_count"):
        if metrics[key] != gates[key]:
            a_fail.append(key)
    if metrics["generated_A_valid_retained_count"] != metrics["generated_valid_adjudicated_eligible_count"]:
        a_fail.append("generated_A_valid_retention")
    if metrics["maximum_generated_A_total_wall_seconds"] is None or metrics["maximum_generated_A_total_wall_seconds"] > gates["maximum_product_case_total_wall_seconds"]:
        a_fail.append("maximum_product_case_total_wall_seconds")
    b_fail = list(common_fail)
    if metrics["challenge_B_false_action_count"] != gates["challenge_B_false_action_count_for_bypass_eligibility"]:
        b_fail.append("challenge_B_false_action_count_for_bypass_eligibility")
    if metrics["generated_B_invalid_or_uncertain_false_action_count"] != gates["generated_B_invalid_or_uncertain_false_action_count_for_bypass_eligibility"]:
        b_fail.append("generated_B_invalid_or_uncertain_false_action_count_for_bypass_eligibility")
    if metrics["generated_B_valid_retained_count"] < metrics["generated_A_valid_retained_count"]:
        b_fail.append("generated_B_valid_retention_below_A")
    if metrics["maximum_generated_B_total_wall_seconds"] is None or metrics["maximum_generated_B_total_wall_seconds"] > gates["maximum_product_case_total_wall_seconds"]:
        b_fail.append("maximum_product_case_total_wall_seconds")
    sufficient_generated = bool(
        metrics["generated_valid_adjudicated_eligible_count"] >= gates["minimum_generated_valid_adjudicated_for_reviewer_necessity_claim"]
        and metrics["generated_invalid_adjudicated_eligible_count"] >= gates["minimum_generated_invalid_adjudicated_for_reviewer_necessity_claim"]
    )
    if not sufficient_generated:
        a_fail.append("generated_adjudicated_mix_insufficient")
        b_fail.append("generated_adjudicated_mix_insufficient")
    return {"metrics": metrics, "common_failed_gates": common_fail,
            "A_failed_gates": a_fail, "B_failed_gates": b_fail,
            "A_offline_eligible": not a_fail, "B_offline_bypass_eligible": not b_fail,
            "generated_reviewer_necessity_informative": sufficient_generated,
            "claim_boundary": contract["claim_boundary"]}


def run_review(contract_path: Path = CONTRACT_PATH, generated_path: Path = GENERATED_PATH,
               gold_path: Path = GOLD_PATH, output_path: Path = REVIEW_PATH) -> dict:
    contract_path, generated_path, gold_path, output_path = (
        path.resolve() for path in (contract_path, generated_path, gold_path, output_path)
    )
    contract, dataset, generated, gold, labels = preflight_review(
        contract_path, generated_path, gold_path, output_path,
    )
    inputs = _review_inputs(dataset, generated, labels)
    planned = []
    for item in inputs:
        score = scoring.score_packet(item["source"], item["batch"], None, item["gold_label"])
        if item["expected_plan_digest"] and score["selected_plan_digest"] != item["expected_plan_digest"]:
            raise RuntimeError("Pre-review selected plan changed")
        planned.append((item, score))
    if sum(score["deterministic_eligible"] for _, score in planned) > contract["execution"]["maximum_review_scored_calls"]:
        raise RuntimeError("Frozen review call budget exceeded")
    evidence = {
        "schema": "uruha_p4_m46_reviewer_necessity_review_v1",
        "status": "running_not_reusable", "freeze_sha": FREEZE_SHA,
        "contract_sha256": _hash(contract_path), "generation_sha256": _hash(generated_path),
        "gold_sha256": _hash(gold_path), "runner_sha256": _hash(Path(__file__)),
        "gold_authority": contract["generated_plan_label_protocol"]["gold_authority"],
        "retry_count": 0, "prewarm": None, "rows": [], "summary": None,
        "max_review_scored_calls": contract["execution"]["maximum_review_scored_calls"],
        "production_database_access": False, "product_runtime_changed": False,
        "claim_boundary": contract["claim_boundary"],
    }
    _checkpoint(output_path, evidence, first=True)
    evidence["prewarm"] = prewarm_model(contract["model"], contract["controlled_constants"]["keep_alive"])
    _checkpoint(output_path, evidence)
    if evidence["prewarm"].get("completed") is not True:
        evidence["status"] = "prewarm_failed_no_review_calls"
        _checkpoint(output_path, evidence)
        return evidence
    for item, prior in planned:
        row = {"case_id": item["case_id"], "stratum": item["stratum"],
               "category": item.get("category"), "source": deepcopy(item["source"]),
               "batch_digest": _digest(item["batch"]), "gold_label": item["gold_label"],
               "generation_call": item["generation_call"], "review_call": None,
               "score": prior}
        evidence["rows"].append(row)
        if prior["deterministic_eligible"]:
            call = model_json_call(stage="review", case_id=item["case_id"],
                                   source=item["source"], plan=prior["selected_plan"], contract=contract)
            parsed = call.pop("parsed", None)
            row["review_call"] = call
            if call.get("completed") is not True or call.get("json_parse_success") is not True or not _tokens_complete(call) or not isinstance(parsed, dict):
                evidence["status"] = "review_call_failed_partial_no_resume"
                _checkpoint(output_path, evidence)
                return evidence
            row["review"] = parsed
            try:
                row["score"] = scoring.score_packet(
                    item["source"], item["batch"], parsed, item["gold_label"],
                )
            except Exception as exc:
                # A scored call already happened. Preserve it even if the
                # offline evaluator cannot consume the parsed review.
                row.update(packet_error_type=type(exc).__name__,
                           packet_error=str(exc)[:300])
                evidence["status"] = "review_packet_failed_partial_no_resume"
                _checkpoint(output_path, evidence)
                return evidence
            if row["score"]["selected_plan_digest"] != prior["selected_plan_digest"]:
                evidence["status"] = "paired_packet_changed_partial_no_resume"
                _checkpoint(output_path, evidence)
                return evidence
        _checkpoint(output_path, evidence)
    evidence["summary"] = summarize_review(evidence["rows"], contract)
    evidence["status"] = (
        "bounded_offline_A_pass_B_fail" if evidence["summary"]["A_offline_eligible"] and not evidence["summary"]["B_offline_bypass_eligible"]
        else "bounded_offline_B_pass" if evidence["summary"]["B_offline_bypass_eligible"]
        else "fail_or_inconclusive"
    )
    _checkpoint(output_path, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("generate", "review"))
    args = parser.parse_args()
    evidence = run_generate() if args.phase == "generate" else run_review()
    print(json.dumps({"status": evidence["status"], "rows": len(evidence["rows"]),
                      "summary": evidence.get("summary")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
