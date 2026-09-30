#!/usr/bin/env python3
"""One-shot, source-only A/B action-transaction raw evidence runner.

This file never reads semantic gold, scores a case, invokes a product action, or
runs on import.  It records the complete model exchanges and raw-derived A/B
observations for a later, separately committed adjudication.  A parse or
contract failure is a quality observation; a transport, usage, or identity
failure stops this one-shot artifact without retry or resume.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import http.client
from importlib.metadata import version as package_version
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time

import p4_action_transaction_a_observation as a_raw
import p4_action_transaction_b_observation as b_raw
import p4_action_transaction_scoring as tx
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


ROOT = Path(__file__).resolve().parent
FREEZE_SHA = "8b5e7a8972b27402342596d5fe18064795b7a452"
CONTRACT_PATH = ROOT / "configs/p4_action_transaction_v1.json"
RAW_PATH = ROOT / "analysis/p4_action_transaction_v1_raw_2026-09-30.json"
RUNNER_PATHS = ("run_p4_action_transaction.py", "test_p4_action_transaction_runner.py")
OLLAMA_ORIGIN = "http://127.0.0.1:11434"
OLLAMA_CHAT = OLLAMA_ORIGIN + "/api/chat"
ARM_ORDER = (("A", "B"), ("B", "A"))
ARM_KEYS = {"A": "A_two_stage", "B": "B_transaction"}
# Stage/prewarm walls are saved to six decimal places.  Permit only their
# microsecond rounding difference, never an unexplained server/client gap.
WALL_ROUNDING_TOLERANCE_SECONDS = 0.000001


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _tracked_clean(relative: str) -> None:
    _git("ls-files", "--error-unmatch", relative)
    _git("diff", "--exit-code", "HEAD", "--", relative)
    _git("diff", "--cached", "--exit-code", "HEAD", "--", relative)
    committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
    if committed != (ROOT / relative).read_bytes():
        raise RuntimeError(f"Uncommitted runner bytes: {relative}")


def _require_frozen_git(contract: dict) -> None:
    if _git("rev-parse", FREEZE_SHA) != FREEZE_SHA:
        raise RuntimeError("Freeze commit does not resolve exactly")
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_SHA, "HEAD"],
                   cwd=ROOT, check=True)
    frozen = ["configs/p4_action_transaction_v1.json", contract["plan"]["path"],
              contract["dataset"]["sources"]["path"],
              contract["dataset"]["gold"]["path"]]
    frozen += [item["path"] for item in contract["hash_bound_dependencies"].values()]
    frozen += ["test_p4_action_transaction_freeze.py",
               "test_p4_action_transaction_scoring.py",
               "test_p4_action_transaction_a_observation.py",
               "test_p4_action_transaction_b_observation.py"]
    _git("diff", "--exit-code", FREEZE_SHA, "--", *frozen)
    _git("diff", "--cached", "--exit-code", FREEZE_SHA, "--", *frozen)
    for relative in RUNNER_PATHS:
        _tracked_clean(relative)
    commits = [_git("log", "-1", "--format=%H", "--", relative)
               for relative in RUNNER_PATHS]
    if len(set(commits)) != 1 or commits[0] in {"", FREEZE_SHA}:
        raise RuntimeError("Runner and fake tests require one post-freeze commit")
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_SHA, commits[0]],
                   cwd=ROOT, check=True)


def _validate_hash_bindings(contract: dict) -> None:
    records = {"plan": contract["plan"],
               "sources": contract["dataset"]["sources"],
               "gold": contract["dataset"]["gold"],
               **contract["hash_bound_dependencies"]}
    for label, item in records.items():
        path = (ROOT / item["path"]).resolve()
        if not path.is_relative_to(ROOT) or _hash(path) != item["sha256"]:
            raise RuntimeError(f"Frozen hash mismatch: {label}")


def _validate_contract(contract: dict) -> None:
    constants = contract.get("controlled_constants", {})
    execution = contract.get("execution", {})
    arms = contract.get("arms", {})
    if (contract.get("schema") != "uruha_p4_action_transaction_topology_contract_v1"
            or contract.get("status") != "prospectively_frozen_before_model_execution"
            or contract.get("single_variable") !=
            "decision_topology_two_candidates_two_calls_vs_one_source_bound_transaction"
            or contract.get("model") != "qwen3.5:9b"
            or contract.get("model_digest") !=
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
            or contract.get("hardware") != "Apple M2 Pro 12-core 32GB"
            or {key: constants.get(key) for key in (
                "temperature", "num_ctx", "stream", "think", "keep_alive",
                "retry_count", "prewarm_once_before_scoring",
                "prewarm_counted_as_case_latency", "offline_jsonschema_version")} != {
                    "temperature": 0, "num_ctx": 4096, "stream": False,
                    "think": False, "keep_alive": "30m", "retry_count": 0,
                    "prewarm_once_before_scoring": True,
                    "prewarm_counted_as_case_latency": False,
                    "offline_jsonschema_version": "4.26.0"}
            or arms.get("A", {}).get("generator") != {"seed": 20260830, "num_predict": 360}
            or arms.get("A", {}).get("reviewer") != {"seed": 20260829, "num_predict": 320}
            or arms.get("B", {}).get("transaction") != {"seed": 20260830, "num_predict": 680}
            or arms.get("A", {}).get("maximum_completion_tokens_per_case") != 680
            or arms.get("B", {}).get("maximum_completion_tokens_per_case") != 680
            or execution.get("source_case_count") != 18
            or execution.get("maximum_scored_calls") != 54
            or execution.get("per_arm_deadline_seconds") != 34
            or execution.get("arm_order_rule") != "case_index_even_A_then_B_odd_B_then_A"
            or execution.get("raw_result_path") != str(RAW_PATH.relative_to(ROOT))
            or execution.get("generation_reads_gold") is not False
            or execution.get("localhost_only") is not True
            or execution.get("production_database_access") is not False
            or execution.get("product_runtime_changed") is not False):
        raise RuntimeError("Frozen action-transaction contract mismatch")
    order = contract.get("dataset", {}).get("case_order")
    if not isinstance(order, list) or len(order) != 18 or len(set(order)) != 18:
        raise RuntimeError("Frozen case order mismatch")


def _prepare_cases(contract: dict, dataset: dict) -> list[dict]:
    """Read source-only cases and run the common filter before any model call."""

    if (dataset.get("schema") != "p4_action_transaction_sources_v1"
            or dataset.get("case_count") != 18
            or not isinstance(dataset.get("cases"), list)
            or len(dataset["cases"]) != 18
            or [row.get("case_id") for row in dataset["cases"]] !=
            contract["dataset"]["case_order"]):
        raise RuntimeError("Frozen source case count or order mismatch")
    prepared = []
    for raw_case in dataset["cases"]:
        if set(raw_case) != {"case_id", "language", "sources"}:
            raise RuntimeError("Generation source contains non-source case metadata")
        case = tx.prepare_source_case(raw_case)
        if case["source_gate"].get("excluded") != []:
            raise RuntimeError("Frozen M45.1 source exclusion changed")
        prepared.append(case)
    return prepared


def _http_exchange(method: str, path: str, body: dict | None, timeout: float) -> dict:
    """Direct localhost HTTP, recording actual socket peer and response bytes."""

    if method not in {"GET", "POST"} or path not in {
            "/api/version", "/api/tags", "/api/generate", "/api/chat"}:
        raise ValueError("Unapproved Ollama HTTP request")
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=timeout)
    try:
        connection.connect()
        peer_host, peer_port = connection.sock.getpeername()[:2]
        payload = (json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                   if body is not None else None)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        response_bytes = response.read()
        return {"status": response.status,
                "headers": dict(response.getheaders()),
                "body_base64": base64.b64encode(response_bytes).decode("ascii"),
                "endpoint": OLLAMA_ORIGIN + path, "method": method,
                "peer_host": peer_host, "peer_port": peer_port}
    finally:
        connection.close()


def _decode_wire(wire: dict, *, method: str, path: str) -> dict:
    if (not isinstance(wire, dict) or wire.get("status") != 200
            or wire.get("endpoint") != OLLAMA_ORIGIN + path
            or wire.get("method") != method
            or wire.get("peer_host") != "127.0.0.1"
            or wire.get("peer_port") != 11434
            or not isinstance(wire.get("headers"), dict)):
        raise RuntimeError("Ollama HTTP status, endpoint, or actual peer mismatch")
    encoded = wire.get("body_base64")
    if type(encoded) is not str:
        raise RuntimeError("Ollama raw HTTP body missing")
    try:
        raw = base64.b64decode(encoded, validate=True)
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Ollama HTTP envelope is not UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Ollama HTTP envelope is not an object")
    return data


def _get_json(path: str) -> dict:
    return _decode_wire(_http_exchange("GET", path, None, 3), method="GET", path=path)


def preflight(contract_path: Path = CONTRACT_PATH,
              output_path: Path = RAW_PATH) -> tuple[dict, dict, list[dict]]:
    contract_path, output_path = contract_path.resolve(), output_path.resolve()
    if contract_path != CONTRACT_PATH or output_path != RAW_PATH:
        raise RuntimeError("Formal run requires fixed contract and raw output paths")
    if output_path.exists():
        raise RuntimeError("Existing raw result cannot be overwritten or resumed")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    _validate_contract(contract)
    _require_frozen_git(contract)
    _validate_hash_bindings(contract)
    if package_version("jsonschema") != contract["controlled_constants"]["offline_jsonschema_version"]:
        raise RuntimeError("Frozen jsonschema version mismatch")
    tx.require_isolated_m45_1_source_filter()
    dataset = json.loads((ROOT / contract["dataset"]["sources"]["path"])
                         .read_text(encoding="utf-8"))
    prepared = _prepare_cases(contract, dataset)
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Formal host must be Apple arm64")
    cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"],
                                  text=True).strip()
    memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"],
                                         text=True).strip())
    if cpu != "Apple M2 Pro" or memory != 34359738368:
        raise RuntimeError("Formal hardware must be M2 Pro 32GB")
    if not _get_json("/api/version").get("version"):
        raise RuntimeError("Local Ollama unavailable")
    tags = _get_json("/api/tags")
    models = tags.get("models")
    if not isinstance(models, list):
        raise RuntimeError("Ollama model tags unavailable")
    digests = {row.get("name"): row.get("digest") for row in models
               if isinstance(row, dict)}
    if digests.get(contract["model"]) != contract["model_digest"]:
        raise RuntimeError("Frozen model digest mismatch")
    return contract, dataset, prepared


def _expected_body(stage: str, case: dict, contract: dict,
                   plan: dict | None = None) -> dict:
    sources = case["sources"]
    if stage == "M51":
        system = m51.CANDIDATE_SYSTEM
        payload = {"user_sources": sources}
        schema = m51._candidate_schema(sources)
        options = contract["arms"]["A"]["generator"]
    elif stage == "M46" and isinstance(plan, dict):
        system = m46.REVIEW_SYSTEM
        payload = {"sources": sources,
                   "plan": {key: value for key, value in plan.items()
                            if key != "progress_mechanism"},
                   "planned_payload_digest": m45.digest({"sources": sources, "plan": plan})}
        schema = m46.review_schema(sources, plan)
        options = contract["arms"]["A"]["reviewer"]
    elif stage == "B_transaction":
        system = tx.TRANSACTION_SYSTEM
        payload = tx.transaction_payload(sources)
        schema = tx.transaction_schema(sources)
        options = contract["arms"]["B"]["transaction"]
    else:
        raise ValueError("Invalid frozen stage or M46 plan")
    constants = contract["controlled_constants"]
    return {"model": contract["model"],
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            "format": schema, "stream": constants["stream"],
            "think": constants["think"], "keep_alive": constants["keep_alive"],
            "options": {"temperature": constants["temperature"],
                        "seed": options["seed"], "num_ctx": constants["num_ctx"],
                        "num_predict": options["num_predict"]}}


def _model_stage(stage: str, case: dict, contract: dict, *,
                 plan: dict | None = None, timeout: float,
                 call_index: int) -> dict:
    body = _expected_body(stage, case, contract, plan)
    record = {"stage": stage, "call_index": call_index,
              "attempted": True, "completed": False,
              "request_body": deepcopy(body), "options": deepcopy(body["options"]),
              "model_digest": contract["model_digest"], "raw_http_response": None,
              "ollama_response": None, "raw_content": None,
              "prompt_tokens": None, "completion_tokens": None,
              "usage": None, "http_identity": None, "transport_metadata": None,
              "json_parse_success": False}
    started = time.monotonic()
    try:
        wire = _http_exchange("POST", "/api/chat", body, timeout)
        record["raw_http_response"] = {key: deepcopy(wire.get(key))
                                       for key in ("status", "headers", "body_base64")}
        record["transport_metadata"] = {"http_status": wire.get("status"),
                                        "method": wire.get("method"),
                                        "endpoint": wire.get("endpoint")}
        data = _decode_wire(wire, method="POST", path="/api/chat")
        record["ollama_response"] = deepcopy(data)
        record["http_identity"] = {"endpoint": wire["endpoint"],
                                   "peer_host": wire["peer_host"],
                                   "peer_port": wire["peer_port"],
                                   "model": body["model"],
                                   "response_model": data.get("model")}
        message = data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        record["raw_content"] = content
        record["prompt_tokens"] = data.get("prompt_eval_count")
        record["completion_tokens"] = data.get("eval_count")
        record["usage"] = {key: data.get(key) for key in (
            "prompt_eval_count", "eval_count", "load_duration", "total_duration")}
        record["json_parse_success"] = tx.parse_transaction_json(content) is not None
        record["completed"] = True
    except Exception as exc:  # one attempt only; all evidence collected so far survives
        record["transport_error_type"] = type(exc).__name__
        record["transport_error"] = str(exc)[:300]
    record["wall_seconds"] = round(time.monotonic() - started, 6)
    return record


def _server_durations_fit_wall(response: object, wall_seconds: object) -> bool:
    if not isinstance(response, dict) or not tx._valid_seconds(wall_seconds):
        return False
    load = response.get("load_duration")
    total = response.get("total_duration")
    return bool(type(load) is int and type(total) is int
                and 0 <= load <= total
                and total / 1_000_000_000 <=
                wall_seconds + WALL_ROUNDING_TOLERANCE_SECONDS)


def _verify_stage(record: dict, *, stage: str, case: dict, contract: dict,
                  plan: dict | None = None) -> str | None:
    """Recompute request/response identity, not just builder metadata flags."""

    expected = _expected_body(stage, case, contract, plan)
    if (record.get("stage") != stage or record.get("attempted") is not True
            or record.get("request_body") != expected
            or record.get("options") != expected["options"]
            or record.get("model_digest") != contract["model_digest"]):
        return "frozen_request_or_model_identity_mismatch"
    if record.get("completed") is not True or record.get("transport_error_type"):
        return "transport_incomplete"
    response = record.get("raw_http_response")
    metadata = record.get("transport_metadata")
    identity = record.get("http_identity")
    if (not isinstance(response, dict) or not isinstance(metadata, dict)
            or not isinstance(identity, dict)
            or metadata != {"http_status": 200, "method": "POST", "endpoint": OLLAMA_CHAT}
            or identity != {"endpoint": OLLAMA_CHAT, "peer_host": "127.0.0.1",
                            "peer_port": 11434, "model": contract["model"],
                            "response_model": contract["model"]}):
        return "http_or_peer_identity_mismatch"
    try:
        data = _decode_wire({**response, "endpoint": OLLAMA_CHAT,
                             "method": "POST", "peer_host": identity["peer_host"],
                             "peer_port": identity["peer_port"]},
                            method="POST", path="/api/chat")
    except Exception:
        return "raw_http_response_invalid"
    message = data.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if (data != record.get("ollama_response") or data.get("model") != contract["model"]
            or data.get("done") is not True or not isinstance(message, dict)
            or message.get("role") != "assistant" or type(content) is not str
            or content != record.get("raw_content")
            or record.get("json_parse_success") !=
            (tx.parse_transaction_json(content) is not None)):
        return "ollama_response_identity_mismatch"
    usage = {key: data.get(key) for key in (
        "prompt_eval_count", "eval_count", "load_duration", "total_duration")}
    if (record.get("usage") != usage
            or record.get("prompt_tokens") != usage["prompt_eval_count"]
            or record.get("completion_tokens") != usage["eval_count"]
            or not tx._valid_usage(usage["prompt_eval_count"], usage["eval_count"])):
        return "token_usage_incomplete"
    if usage["eval_count"] > expected["options"]["num_predict"]:
        return "completion_token_cap_exceeded"
    seconds = record.get("wall_seconds")
    if not (tx._valid_seconds(seconds)
            and seconds <= contract["execution"]["per_arm_deadline_seconds"]):
        return "stage_wall_invalid_or_deadline_exceeded"
    if not _server_durations_fit_wall(data, seconds):
        return "server_duration_invalid_or_exceeds_stage_wall"
    return None


def _prewarm(contract: dict) -> dict:
    body = {"model": contract["model"], "prompt": "", "stream": False,
            "keep_alive": contract["controlled_constants"]["keep_alive"]}
    row = {"attempted": True, "completed": False, "model": contract["model"],
           "endpoint": OLLAMA_ORIGIN + "/api/generate",
           "request_body": deepcopy(body),
           "raw_http_response": None, "ollama_response": None,
           "http_identity": None, "transport_metadata": None,
           "model_digest": contract["model_digest"]}
    started = time.monotonic()
    try:
        wire = _http_exchange("POST", "/api/generate", body, 120)
        row["raw_http_response"] = {key: deepcopy(wire.get(key))
                                    for key in ("status", "headers", "body_base64")}
        row["transport_metadata"] = {"http_status": wire.get("status"),
                                     "method": wire.get("method"),
                                     "endpoint": wire.get("endpoint")}
        data = _decode_wire(wire, method="POST", path="/api/generate")
        row["ollama_response"] = deepcopy(data)
        row["http_identity"] = {"endpoint": wire["endpoint"],
                                "peer_host": wire["peer_host"],
                                "peer_port": wire["peer_port"],
                                "response_model": data.get("model")}
        if data.get("model") != contract["model"] or data.get("done") is not True:
            raise RuntimeError("Prewarm model identity or completion mismatch")
        row["completed"] = True
    except Exception as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:300]
    row["wall_seconds"] = round(time.monotonic() - started, 6)
    if row["completed"] and not _server_durations_fit_wall(
            row["ollama_response"], row["wall_seconds"]):
        row["completed"] = False
        row["error_type"] = "ServerDurationMismatch"
        row["error"] = "Prewarm server durations invalid or exceed measured wall"
    return row


def _checkpoint(path: Path, artifact: dict, *, first: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
    if first:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return
    temp = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".p4_tx_raw_", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def _seconds_since(started: float) -> float:
    return round(time.monotonic() - started, 6)


def _remaining(started: float, contract: dict) -> float:
    return contract["execution"]["per_arm_deadline_seconds"] - (time.monotonic() - started)


def _call_and_save(artifact: dict, output_path: Path, arm_row: dict,
                   stage_field: str, stage: str, case: dict, contract: dict,
                   started: float, *, plan: dict | None = None) -> str | None:
    if artifact["scored_calls_started"] >= contract["execution"]["maximum_scored_calls"]:
        return "scored_call_budget_exceeded"
    remaining = _remaining(started, contract)
    if remaining <= 0:
        return "arm_deadline_exhausted_before_call"
    artifact["scored_calls_started"] += 1
    _checkpoint(output_path, artifact)  # a crash still consumes this unique attempt
    record = _model_stage(stage, case, contract, plan=plan, timeout=remaining,
                          call_index=artifact["scored_calls_started"])
    arm_row[stage_field] = record
    _checkpoint(output_path, artifact)
    return _verify_stage(record, stage=stage, case=case, contract=contract, plan=plan)


def _finish_arm(artifact: dict, output_path: Path, row: dict, arm: str,
                observation: dict | None, seconds: float, error: Exception | None = None) -> None:
    key = ARM_KEYS[arm]
    arm_row = row["arms"][key]
    arm_row["full_turn_seconds"] = seconds
    arm_row["observation"] = observation
    if error is not None:
        arm_row["observation_error"] = {"type": type(error).__name__,
                                         "message": str(error)[:300]}
    if observation is not None:
        artifact["output_digests"].setdefault(row["case_id"], {})[key] = (
            tx.output_evidence_digest(row["case_id"], key, observation))
    _checkpoint(output_path, artifact)


def run(contract_path: Path = CONTRACT_PATH, output_path: Path = RAW_PATH) -> dict:
    contract_path, output_path = contract_path.resolve(), output_path.resolve()
    contract, _dataset, cases = preflight(contract_path, output_path)
    artifact = {
        "schema": "uruha_p4_action_transaction_raw_v1",
        "status": "running_not_reusable", "freeze_sha": FREEZE_SHA,
        "contract_sha256": _hash(contract_path),
        "sources_sha256": contract["dataset"]["sources"]["sha256"],
        "runner_sha256": _hash(Path(__file__)),
        "model": contract["model"], "model_digest": contract["model_digest"],
        "endpoint": OLLAMA_CHAT, "retry_count": 0,
        "maximum_scored_calls": contract["execution"]["maximum_scored_calls"],
        "scored_calls_started": 0, "prewarm": None, "cases": [],
        "output_digests": {}, "semantic_quality": "unverified",
        "gold_labels_present": False, "production_database_access": False,
        "product_runtime_changed": False, "product_eligible": False,
        "claim_boundary": contract["claim_boundary"],
    }
    _checkpoint(output_path, artifact, first=True)
    artifact["prewarm"] = _prewarm(contract)
    _checkpoint(output_path, artifact)
    if artifact["prewarm"]["completed"] is not True:
        artifact["status"] = "prewarm_failed_no_scored_calls"
        _checkpoint(output_path, artifact)
        return artifact
    for index, case in enumerate(cases):
        row = {"case_id": case["case_id"], "prepared_case": deepcopy(case),
               "arm_order": list(ARM_ORDER[index % 2]),
               "arms": {
                   "A_two_stage": {"generator_stage": None, "reviewer_stage": None,
                                   "full_turn_seconds": None, "retries": 0,
                                   "observation": None},
                   "B_transaction": {"stage": None, "full_turn_seconds": None,
                                     "retries": 0, "observation": None},
               }}
        artifact["cases"].append(row)
        _checkpoint(output_path, artifact)
        for arm in row["arm_order"]:
            arm_started = time.monotonic()
            arm_row = row["arms"][ARM_KEYS[arm]]
            if arm == "A":
                fatal = _call_and_save(artifact, output_path, arm_row, "generator_stage",
                                       "M51", case, contract, arm_started)
                if fatal is not None:
                    artifact["status"] = f"{fatal}_partial_no_resume"
                    _checkpoint(output_path, artifact)
                    return artifact
                try:
                    interim = a_raw.build_a_observation(
                        case, arm_row["generator_stage"],
                        full_turn_seconds=_seconds_since(arm_started), retries=0)
                    if interim["failure_stage"] == "review_missing":
                        plan = interim["selected_plan"]
                        if not isinstance(plan, dict):
                            raise RuntimeError("A review-eligible plan missing")
                        fatal = _call_and_save(
                            artifact, output_path, arm_row, "reviewer_stage", "M46",
                            case, contract, arm_started, plan=plan)
                        if fatal is not None:
                            artifact["status"] = f"{fatal}_partial_no_resume"
                            _checkpoint(output_path, artifact)
                            return artifact
                    # The first rebuild includes the review, guard, and fallback
                    # work in the decision-to-reply monotonic measurement.
                    a_raw.build_a_observation(
                        case, arm_row["generator_stage"],
                        reviewer_stage_record=arm_row["reviewer_stage"],
                        full_turn_seconds=_seconds_since(arm_started), retries=0)
                    elapsed = _seconds_since(arm_started)
                    observed = a_raw.build_a_observation(
                        case, arm_row["generator_stage"],
                        reviewer_stage_record=arm_row["reviewer_stage"],
                        full_turn_seconds=elapsed, retries=0)
                    _finish_arm(artifact, output_path, row, arm, observed, elapsed)
                except Exception as exc:
                    _finish_arm(artifact, output_path, row, arm, None,
                                _seconds_since(arm_started), exc)
            else:
                fatal = _call_and_save(artifact, output_path, arm_row, "stage",
                                       "B_transaction", case, contract, arm_started)
                if fatal is not None:
                    artifact["status"] = f"{fatal}_partial_no_resume"
                    _checkpoint(output_path, artifact)
                    return artifact
                try:
                    b_raw.build_b_observation_from_stage(
                        case, arm_row["stage"], full_turn_seconds=_seconds_since(arm_started),
                        retries=0, fallback_kind="unavailable")
                    elapsed = _seconds_since(arm_started)
                    observed = b_raw.build_b_observation_from_stage(
                        case, arm_row["stage"], full_turn_seconds=elapsed,
                        retries=0, fallback_kind="unavailable")
                    _finish_arm(artifact, output_path, row, arm, observed, elapsed)
                except Exception as exc:
                    _finish_arm(artifact, output_path, row, arm, None,
                                _seconds_since(arm_started), exc)
    if (len(artifact["cases"]) == 18
            and all(len(artifact["output_digests"].get(row["case_id"], {})) == 2
                    for row in artifact["cases"])):
        artifact["status"] = "complete_unannotated"
    else:
        artifact["status"] = "complete_with_quality_observation_errors_unannotated"
    _checkpoint(output_path, artifact)
    return artifact


def main() -> int:
    result = run()
    print(json.dumps({"status": result["status"],
                      "case_count": len(result["cases"]),
                      "scored_calls_started": result["scored_calls_started"]},
                     ensure_ascii=False, indent=2))
    return 0 if result["status"] == "complete_unannotated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
