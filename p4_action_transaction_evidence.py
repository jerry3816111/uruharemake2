"""Read-only, fail-closed provenance check for the prospective P4 raw artifact.

This module does not call a model, trust acceptance flags in the artifact, or
make a component PASS claim.  It binds frozen inputs, committed raw bytes, the
actual saved HTTP envelopes, and all 36 reconstructed observations.  Semantic
adjudication has a later, separately committed gate.
"""

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

import p4_action_transaction_annotation as annotation
import p4_action_transaction_a_observation as a_raw
import p4_action_transaction_b_observation as b_raw
import p4_action_transaction_scoring as tx
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


FREEZE_SHA = "6525810d87ea44bb891a3c5f6c65cfa98f43b8eb"
CONTRACT_PATH = "configs/p4_action_transaction_v1.json"
RAW_PATH = "analysis/p4_action_transaction_v1_amend1_raw_2026-10-01.json"
RUNNER_PATH = "run_p4_action_transaction.py"
ENDPOINT = "http://127.0.0.1:11434/api/chat"
WALL_ROUNDING_TOLERANCE_SECONDS = 0.000001
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_RAW_KEYS = {
    "schema", "status", "freeze_sha", "contract_sha256", "sources_sha256",
    "runner_sha256", "model", "model_digest", "endpoint", "retry_count",
    "maximum_scored_calls", "scored_calls_started", "prewarm", "cases",
    "output_digests", "semantic_quality", "gold_labels_present",
    "production_database_access", "product_runtime_changed",
    "product_eligible", "claim_boundary",
}
_STAGE_KEYS = {
    "stage", "call_index", "attempted", "completed", "request_body",
    "options", "model_digest", "raw_http_response", "ollama_response",
    "raw_content", "prompt_tokens", "completion_tokens", "usage",
    "http_identity", "transport_metadata", "json_parse_success",
    "wall_seconds",
}


class EvidenceError(ValueError):
    """The artifact cannot be used as formal raw evidence."""


def _require(condition: object, reason: str) -> None:
    if not condition:
        raise EvidenceError(reason)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative(path: str) -> str:
    parsed = PurePosixPath(path)
    _require(type(path) is str and not parsed.is_absolute()
             and ".." not in parsed.parts and str(parsed) == path,
             "artifact path must be a fixed repository-relative path")
    return path


def _git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(["git", *args], cwd=repo, check=False,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode:
        raise EvidenceError(f"Git verification failed: {' '.join(args[:2])}")
    return completed.stdout


def _commit(repo: Path, sha: str) -> str:
    _require(type(sha) is str and _SHA.fullmatch(sha), "full commit SHA required")
    resolved = _git(repo, "rev-parse", "--verify", f"{sha}^{{commit}}").decode().strip()
    _require(resolved == sha, "commit SHA does not resolve exactly")
    return sha


def _strict_ancestor(repo: Path, earlier: str, later: str) -> None:
    _require(earlier != later, "commit sequence must be strictly ordered")
    _git(repo, "merge-base", "--is-ancestor", earlier, later)


def _blob(repo: Path, commit: str, path: str) -> bytes:
    return _git(repo, "show", f"{commit}:{_relative(path)}")


def _same_working_bytes(repo: Path, path: str, committed: bytes) -> None:
    location = repo / _relative(path)
    _require(location.is_file() and location.read_bytes() == committed,
             f"working file differs from committed artifact: {path}")


def _json_object(data: bytes, label: str) -> dict:
    try:
        value = tx.parse_transaction_json(data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"{label} is not UTF-8 JSON") from exc
    _require(isinstance(value, dict), f"{label} is not one strict JSON object")
    return value


def _server_durations_fit_wall(response: object, wall_seconds: object) -> bool:
    """Reject server timing that contradicts the saved monotonic wall clock."""

    if not isinstance(response, dict) or not tx._valid_seconds(wall_seconds):
        return False
    load = response.get("load_duration")
    total = response.get("total_duration")
    return bool(type(load) is int and type(total) is int
                and 0 <= load <= total
                and total / 1_000_000_000 <=
                wall_seconds + WALL_ROUNDING_TOLERANCE_SECONDS)


def _prewarm_timing_valid(response: object, wall_seconds: object) -> bool:
    if not isinstance(response, dict) or not tx._valid_seconds(wall_seconds):
        return False
    if (response.get("done_reason") == "load"
            and "load_duration" not in response
            and "total_duration" not in response):
        return True
    return _server_durations_fit_wall(response, wall_seconds)


def frozen_material(repo: Path) -> dict:
    """Derive order and source/gold digests from the fixed freeze commit only."""

    repo = Path(repo).resolve()
    _commit(repo, FREEZE_SHA)
    contract_bytes = _blob(repo, FREEZE_SHA, CONTRACT_PATH)
    _same_working_bytes(repo, CONTRACT_PATH, contract_bytes)
    contract = _json_object(contract_bytes, "frozen contract")
    _require(contract.get("schema") == "uruha_p4_action_transaction_topology_contract_v1"
             and contract.get("version") == "1.0.1"
             and contract.get("status") ==
             "prospectively_amended_after_prewarm_only_zero_scored_calls"
             and contract.get("model") == "qwen3.5:9b"
             and contract.get("execution", {}).get("source_case_count") == 18
             and contract.get("execution", {}).get("maximum_scored_calls") == 54
             and contract.get("controlled_constants", {}).get("retry_count") == 0,
             "frozen topology contract is not the expected P4 study")
    for binding in [contract["plan"], contract["dataset"]["sources"],
                    contract["dataset"]["gold"],
                    *contract["hash_bound_dependencies"].values()]:
        path = binding["path"]
        frozen = _blob(repo, FREEZE_SHA, path)
        _require(_sha256(frozen) == binding["sha256"],
                 f"freeze hash binding differs: {path}")
        _same_working_bytes(repo, path, frozen)
    sources_bytes = _blob(repo, FREEZE_SHA, contract["dataset"]["sources"]["path"])
    gold_bytes = _blob(repo, FREEZE_SHA, contract["dataset"]["gold"]["path"])
    source_doc = _json_object(sources_bytes, "frozen sources")
    gold_doc = _json_object(gold_bytes, "frozen gold")
    order = contract["dataset"]["case_order"]
    cases = source_doc.get("cases")
    gold_by_id = gold_doc.get("gold_by_case_id")
    _require(isinstance(order, list) and len(order) == 18
             and all(type(item) is str for item in order)
             and len(set(order)) == 18
             and isinstance(cases, list) and len(cases) == 18
             and [case.get("case_id") for case in cases] == order
             and isinstance(gold_by_id, dict) and set(gold_by_id) == set(order)
             and sum(gold_by_id[item].get("decision") == "action" for item in order) == 9
             and sum(gold_by_id[item].get("decision") == "abstain" for item in order) == 9,
             "frozen 18-case source/gold identity mismatch")
    prepared = {case["case_id"]: tx.prepare_source_case(case) for case in cases}
    return {
        "contract": contract,
        "contract_sha256": _sha256(contract_bytes),
        "sources_sha256": _sha256(sources_bytes),
        "case_order": list(order),
        "prepared_cases": prepared,
        "gold_by_case_id": gold_by_id,
        "expected_source_digests": {
            case_id: tx._sha256_json({"raw_user_input": prepared[case_id]["raw_user_input"],
                                      "sources": prepared[case_id]["sources"]})
            for case_id in order
        },
        "expected_gold_digests": {
            case_id: tx._sha256_json(gold_by_id[case_id]) for case_id in order
        },
    }


def _request(case: dict, arm: str, contract: dict, plan: dict | None = None) -> dict:
    constants = contract["controlled_constants"]
    if arm == "A_M51":
        system = m51.CANDIDATE_SYSTEM
        payload = {"user_sources": case["sources"]}
        schema = m51._candidate_schema(case["sources"])
        setting = contract["arms"]["A"]["generator"]
    elif arm == "A_M46":
        _require(isinstance(plan, dict), "M46 request has no raw-derived selected plan")
        system = m46.REVIEW_SYSTEM
        audited = {key: value for key, value in plan.items()
                   if key != "progress_mechanism"}
        payload = {"sources": case["sources"], "plan": audited,
                   "planned_payload_digest": m45.digest({"sources": case["sources"],
                                                          "plan": plan})}
        schema = m46.review_schema(case["sources"], plan)
        setting = contract["arms"]["A"]["reviewer"]
    elif arm == "B":
        system = tx.TRANSACTION_SYSTEM
        payload = tx.transaction_payload(case["sources"])
        schema = tx.transaction_schema(case["sources"])
        setting = contract["arms"]["B"]["transaction"]
    else:
        raise EvidenceError("unknown request arm")
    return {
        "model": contract["model"],
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        "format": schema,
        "stream": constants["stream"],
        "think": constants["think"],
        "keep_alive": constants["keep_alive"],
        "options": {"temperature": constants["temperature"],
                    "seed": setting["seed"], "num_ctx": constants["num_ctx"],
                    "num_predict": setting["num_predict"]},
    }


def _verify_prewarm(value: object, contract: dict) -> None:
    expected = {"model": contract["model"], "prompt": "", "stream": False,
                "keep_alive": contract["controlled_constants"]["keep_alive"]}
    endpoint = "http://127.0.0.1:11434/api/generate"
    _require(isinstance(value, dict)
             and set(value) == {
                 "attempted", "completed", "model", "endpoint", "request_body",
                 "raw_http_response", "ollama_response", "http_identity",
                 "transport_metadata", "model_digest", "wall_seconds"}
             and value.get("attempted") is True
             and value.get("completed") is True
             and value.get("model") == contract["model"]
             and value.get("model_digest") == contract["model_digest"]
             and value.get("endpoint") == endpoint
             and value.get("request_body") == expected
             and value.get("transport_metadata") == {
                 "http_status": 200, "method": "POST", "endpoint": endpoint}
             and tx._valid_seconds(value.get("wall_seconds")),
             "prewarm request or completion is not bound")
    identity = value.get("http_identity")
    _require(identity == {"endpoint": endpoint,
                          "peer_host": "127.0.0.1", "peer_port": 11434,
                          "response_model": contract["model"]},
             "prewarm did not record frozen local model identity")
    wire = value.get("raw_http_response")
    _require(isinstance(wire, dict) and wire.get("status") == 200
             and isinstance(wire.get("headers"), dict)
             and type(wire.get("body_base64")) is str,
             "prewarm raw HTTP response incomplete")
    try:
        decoded = base64.b64decode(wire["body_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise EvidenceError("prewarm HTTP body is not base64") from exc
    response = _json_object(decoded, "prewarm HTTP body")
    _require(response == value.get("ollama_response")
             and response.get("model") == contract["model"]
             and response.get("done") is True
             and _prewarm_timing_valid(response, value["wall_seconds"]),
             "prewarm response model/completion mismatch")


def verify_stage(stage: object, *, expected_stage: str, expected_body: dict,
                 model_digest: str) -> dict:
    """Cross-check one saved exchange against the frozen request and wire body."""

    _require(isinstance(stage, dict) and set(stage) == _STAGE_KEYS
             and stage.get("stage") == expected_stage,
             f"missing or wrong {expected_stage} raw stage")
    _require(stage.get("request_body") == expected_body
             and stage.get("options") == expected_body["options"],
             f"{expected_stage} request differs from frozen body")
    _require(stage.get("model_digest") == model_digest,
             f"{expected_stage} model digest differs")
    identity = stage.get("http_identity")
    _require(isinstance(identity, dict)
             and identity.get("endpoint") == ENDPOINT
             and identity.get("peer_host") == "127.0.0.1"
             and identity.get("peer_port") == 11434
             and identity.get("model") == expected_body["model"]
             and identity.get("response_model") == expected_body["model"],
             f"{expected_stage} local HTTP/model identity mismatch")
    wire = stage.get("raw_http_response")
    _require(isinstance(wire, dict) and type(wire.get("status")) is int
             and wire["status"] == 200 and isinstance(wire.get("headers"), dict)
             and type(wire.get("body_base64")) is str,
             f"{expected_stage} raw HTTP response incomplete")
    try:
        wire_bytes = base64.b64decode(wire["body_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise EvidenceError(f"{expected_stage} response body is not base64") from exc
    envelope = _json_object(wire_bytes, f"{expected_stage} HTTP body")
    _require(envelope == stage.get("ollama_response")
             and envelope.get("model") == expected_body["model"]
             and envelope.get("done") is True
             and isinstance(envelope.get("message"), dict)
             and envelope["message"].get("role") == "assistant"
             and type(envelope["message"].get("content")) is str
             and envelope["message"]["content"] == stage.get("raw_content"),
             f"{expected_stage} envelope/content mismatch")
    prompt = envelope.get("prompt_eval_count")
    completion = envelope.get("eval_count")
    usage = stage.get("usage")
    _require(tx._valid_usage(prompt, completion)
             and type(stage.get("prompt_tokens")) is int
             and type(stage.get("completion_tokens")) is int
             and stage.get("prompt_tokens") == prompt
             and stage.get("completion_tokens") == completion
             and isinstance(usage, dict)
             and set(usage) == {"prompt_eval_count", "eval_count",
                                    "load_duration", "total_duration"}
             and type(usage.get("prompt_eval_count")) is int
             and type(usage.get("eval_count")) is int
             and usage.get("prompt_eval_count") == prompt
             and usage.get("eval_count") == completion
             and type(usage.get("load_duration")) is int
             and usage["load_duration"] >= 0
             and type(usage.get("total_duration")) is int
             and usage["total_duration"] >= 0
             and _server_durations_fit_wall(envelope, stage.get("wall_seconds")),
             f"{expected_stage} usage is missing or inconsistent")
    transport = stage.get("transport_metadata")
    _require(transport == {"http_status": 200, "method": "POST",
                           "endpoint": ENDPOINT}
             and stage.get("attempted") is True
             and stage.get("completed") is True
             and not stage.get("transport_error_type")
             and stage.get("json_parse_success") is
             (tx.parse_transaction_json(stage["raw_content"]) is not None)
             and tx._valid_seconds(stage.get("wall_seconds")),
             f"{expected_stage} transport or wall evidence is inconsistent")
    index = stage.get("call_index")
    _require(type(index) is int and index > 0,
             f"{expected_stage} lacks a positive call index")
    return {"call_index": index, "completion_tokens": completion,
            "wall_seconds": stage["wall_seconds"]}


def verify_raw_document(raw: dict, frozen: dict, *, runner_sha256: str,
                        raw_commit: str) -> dict:
    """Pure content check; all inputs must already come from verified Git blobs."""

    contract = frozen["contract"]
    order = frozen["case_order"]
    _require(isinstance(raw, dict)
             and set(raw) == _RAW_KEYS
             and raw.get("schema") == "uruha_p4_action_transaction_raw_v1"
             and raw.get("status") == "complete_unannotated"
             and raw.get("freeze_sha") == FREEZE_SHA
             and raw.get("contract_sha256") == frozen["contract_sha256"]
             and raw.get("sources_sha256") == frozen["sources_sha256"]
             and raw.get("runner_sha256") == runner_sha256
             and raw.get("model") == contract["model"]
             and raw.get("model_digest") == contract["model_digest"]
             and raw.get("endpoint") == ENDPOINT
             and type(raw.get("retry_count")) is int
             and raw.get("retry_count") == 0
             and raw.get("maximum_scored_calls") == 54
             and raw.get("gold_labels_present") is False
             and raw.get("production_database_access") is False
             and raw.get("product_runtime_changed") is False
             and raw.get("product_eligible") is False
             and raw.get("claim_boundary") == contract["claim_boundary"]
             and raw.get("semantic_quality") == "unverified",
             "raw artifact study identity mismatch")
    _verify_prewarm(raw.get("prewarm"), contract)
    rows = raw.get("cases")
    _require(isinstance(rows, list) and len(rows) == 18
             and [row.get("case_id") for row in rows] == order,
             "raw artifact lacks the frozen 18-case order")
    _require(isinstance(raw.get("output_digests"), dict)
             and set(raw["output_digests"]) == set(order),
             "raw artifact lacks 18 output digest pairs")
    observations: dict[str, dict] = {}
    output_digests: dict[str, dict] = {}
    call_indices: list[int] = []
    budget_violations: list[str] = []
    for position, row in enumerate(rows):
        case_id = order[position]
        case = frozen["prepared_cases"][case_id]
        expected_order = ["A", "B"] if position % 2 == 0 else ["B", "A"]
        _require(set(row) == {"case_id", "prepared_case", "arm_order", "arms"}
                 and row.get("prepared_case") == case
                 and row.get("arm_order") == expected_order
                 and isinstance(row.get("arms"), dict)
                 and set(row["arms"]) == set(tx.ARMS),
                 f"{case_id} prepared case or arm order mismatch")
        a = row["arms"]["A_two_stage"]
        b = row["arms"]["B_transaction"]
        _require(isinstance(a, dict) and isinstance(b, dict)
                 and set(a) == {"generator_stage", "reviewer_stage",
                                "full_turn_seconds", "retries", "observation"}
                 and set(b) == {"stage", "full_turn_seconds", "retries",
                                "observation"}
                 and type(a.get("retries")) is int and a["retries"] == 0
                 and type(b.get("retries")) is int and b["retries"] == 0
                 and tx._valid_seconds(a.get("full_turn_seconds"))
                 and tx._valid_seconds(b.get("full_turn_seconds")),
                 f"{case_id} retry or full-turn wall record invalid")
        gen = a.get("generator_stage")
        gen_check = verify_stage(gen, expected_stage="M51",
                                 expected_body=_request(case, "A_M51", contract),
                                 model_digest=contract["model_digest"])
        _require(gen_check["completion_tokens"] <= 360,
                 f"{case_id} M51 completion cap exceeded")
        rev = a.get("reviewer_stage")
        a_observed = a_raw.build_a_observation(
            case, gen, reviewer_stage_record=rev,
            full_turn_seconds=a["full_turn_seconds"], retries=0)
        _require(a.get("observation") == a_observed
                 and a_observed["failure_stage"] != "review_missing",
                 f"{case_id} A observation not raw-derived or review missing")
        a_calls = [gen_check]
        if rev is not None:
            _require(isinstance(a_observed.get("selected_plan"), dict)
                     and "unexpected_reviewer_after_upstream_failure"
                     not in a_observed["guard_violations"],
                     f"{case_id} M46 called after ineligible generator")
            rev_check = verify_stage(
                rev, expected_stage="M46",
                expected_body=_request(case, "A_M46", contract,
                                       a_observed["selected_plan"]),
                model_digest=contract["model_digest"])
            _require(rev_check["completion_tokens"] <= 320,
                     f"{case_id} M46 completion cap exceeded")
            a_calls.append(rev_check)
        b_stage = b.get("stage")
        b_check = verify_stage(b_stage, expected_stage="B_transaction",
                               expected_body=_request(case, "B", contract),
                               model_digest=contract["model_digest"])
        _require(b_check["completion_tokens"] <= 680,
                 f"{case_id} B completion cap exceeded")
        b_observed = b_raw.build_b_observation_from_stage(
            case, b_stage, full_turn_seconds=b["full_turn_seconds"], retries=0,
            fallback_kind="unavailable")
        _require(b.get("observation") == b_observed,
                 f"{case_id} B observation not raw-derived")
        for arm, calls, full in (("A", a_calls, a["full_turn_seconds"]),
                                 ("B", [b_check], b["full_turn_seconds"])):
            _require(full <= contract["execution"]["per_arm_deadline_seconds"]
                     and all(item["wall_seconds"] <=
                             contract["execution"]["per_arm_deadline_seconds"]
                             for item in calls)
                     and all(item["wall_seconds"] <= full for item in calls)
                     and sum(item["wall_seconds"] for item in calls) <= full + 0.01,
                     f"{case_id} {arm} stage wall exceeds full-turn wall")
            if full > tx.MAX_FULL_TURN_SECONDS:
                budget_violations.append(f"{case_id}:{arm}:full_turn_over_20s")
        for arm in expected_order:
            call_indices.extend(item["call_index"] for item in
                                (a_calls if arm == "A" else [b_check]))
        observations[case_id] = {"A_two_stage": a_observed,
                                 "B_transaction": b_observed}
        output_digests[case_id] = {
            arm: tx.output_evidence_digest(case_id, arm, observations[case_id][arm])
            for arm in tx.ARMS
        }
        _require(raw["output_digests"].get(case_id) == output_digests[case_id],
                 f"{case_id} whole-observation digest mismatch")
    _require(36 <= len(call_indices) <= 54
             and call_indices == list(range(1, len(call_indices) + 1))
             and type(raw.get("scored_calls_started")) is int
             and raw["scored_calls_started"] == len(call_indices),
             "scored call count or interleaved order mismatch")
    return {
        "case_order": list(order),
        "prepared_cases": frozen["prepared_cases"],
        "gold_by_case_id": frozen["gold_by_case_id"],
        "observations": observations,
        "output_digests": output_digests,
        "expected_source_digests": frozen["expected_source_digests"],
        "expected_gold_digests": frozen["expected_gold_digests"],
        "raw_lock": {"commit_sha": raw_commit, "output_digests": output_digests},
        "raw_commit": raw_commit,
        "verified_raw_evidence": True,
        "scored_calls": len(call_indices),
        "execution_budget_violations": budget_violations,
        "semantic_quality": "unverified",
        "formal_score_eligible": False,
    }


def verify_raw_evidence(repo: Path, *, runner_commit: str,
                        raw_commit: str) -> dict:
    """Verify the fixed committed raw file and return only reconstructed evidence.

    A raw lock alone cannot establish blind annotation or semantic quality;
    callers must not promote ``formal_score_eligible`` until a separately
    committed annotation and reveal sequence has been checked.
    """

    repo = Path(repo).resolve()
    _commit(repo, FREEZE_SHA)
    _commit(repo, runner_commit)
    _commit(repo, raw_commit)
    _strict_ancestor(repo, FREEZE_SHA, runner_commit)
    _strict_ancestor(repo, runner_commit, raw_commit)
    _require(not _blob_exists(repo, runner_commit, RAW_PATH)
             and not _path_exposed_in_ancestors(repo, runner_commit, RAW_PATH),
             "raw artifact existed before the scored run")
    frozen = frozen_material(repo)
    runner_bytes = _blob(repo, runner_commit, RUNNER_PATH)
    _same_working_bytes(repo, RUNNER_PATH, runner_bytes)
    _require(_blob(repo, raw_commit, RUNNER_PATH) == runner_bytes,
             "runner changed before raw lock")
    raw_bytes = _blob(repo, raw_commit, RAW_PATH)
    _same_working_bytes(repo, RAW_PATH, raw_bytes)
    raw = _json_object(raw_bytes, "committed raw artifact")
    return verify_raw_document(raw, frozen, runner_sha256=_sha256(runner_bytes),
                               raw_commit=raw_commit)


def require_annotation_after_raw(repo: Path, evidence: dict, *,
                                 annotation_commit: str) -> None:
    """Check chronology only; this does not certify masking or annotation."""

    repo = Path(repo).resolve()
    _commit(repo, annotation_commit)
    _strict_ancestor(repo, evidence["raw_commit"], annotation_commit)
    _require(evidence.get("formal_score_eligible") is False,
             "raw evidence must never self-authorize a formal PASS")


def _blob_exists(repo: Path, commit: str, path: str) -> bool:
    result = subprocess.run(["git", "cat-file", "-e",
                             f"{commit}:{_relative(path)}"],
                            cwd=repo, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


def _path_changed_between(repo: Path, earlier: str, later: str,
                          path: str) -> bool:
    return bool(_git(repo, "log", "--format=%H", f"{earlier}..{later}",
                     "--", _relative(path)).strip())


def _path_exposed_in_ancestors(repo: Path, before_commit: str,
                               path: str) -> bool:
    """Detect even an add-then-delete on any ancestor before legal reveal."""

    return bool(_git(repo, "log", "--full-history", "--format=%H",
                     before_commit, "--", _relative(path)).strip())


def verify_annotation_lock(repo: Path, *, runner_commit: str, raw_commit: str,
                           packet_commit: str, submission_commit: str,
                           reveal_commit: str) -> dict:
    """Verify the arm-masked commit sequence, then score the locked evidence.

    The reveal mapping must first enter Git *after* the anonymous 36-label
    submission.  This proves repository ordering and digest binding, not that
    the annotator was a different person or had no out-of-band arm knowledge.
    """

    repo = Path(repo).resolve()
    verified = verify_raw_evidence(repo, runner_commit=runner_commit,
                                   raw_commit=raw_commit)
    for sha in (packet_commit, submission_commit, reveal_commit):
        _commit(repo, sha)
    _strict_ancestor(repo, raw_commit, packet_commit)
    _strict_ancestor(repo, packet_commit, submission_commit)
    _strict_ancestor(repo, submission_commit, reveal_commit)
    _require(not _blob_exists(repo, raw_commit, annotation.PACKET_PATH)
             and not _blob_exists(repo, raw_commit, annotation.SUBMISSION_PATH)
             and not _blob_exists(repo, raw_commit, annotation.MAPPING_PATH)
             and not _blob_exists(repo, packet_commit, annotation.SUBMISSION_PATH)
             and not _blob_exists(repo, submission_commit, annotation.MAPPING_PATH)
             and not _path_exposed_in_ancestors(repo, raw_commit,
                                                annotation.PACKET_PATH)
             and not _path_exposed_in_ancestors(repo, packet_commit,
                                                annotation.SUBMISSION_PATH)
             and not _path_exposed_in_ancestors(repo, submission_commit,
                                                annotation.MAPPING_PATH)
             and not _path_changed_between(repo, raw_commit, submission_commit,
                                           annotation.MAPPING_PATH),
             "anonymous packet/submission or reveal mapping was exposed too early")
    raw_bytes = _blob(repo, raw_commit, RAW_PATH)
    _require(_blob(repo, reveal_commit, RAW_PATH) == raw_bytes
             and not _path_changed_between(repo, raw_commit, reveal_commit,
                                           RAW_PATH),
             "raw artifact changed after lock")
    packet_bytes = _blob(repo, packet_commit, annotation.PACKET_PATH)
    _same_working_bytes(repo, annotation.PACKET_PATH, packet_bytes)
    _require(_blob(repo, submission_commit, annotation.PACKET_PATH) == packet_bytes
             and _blob(repo, reveal_commit, annotation.PACKET_PATH) == packet_bytes,
             "masked packet changed after annotation began")
    submission_bytes = _blob(repo, submission_commit, annotation.SUBMISSION_PATH)
    _same_working_bytes(repo, annotation.SUBMISSION_PATH, submission_bytes)
    _require(_blob(repo, reveal_commit, annotation.SUBMISSION_PATH) == submission_bytes,
             "anonymous submission changed after mapping reveal")
    mapping_bytes = _blob(repo, reveal_commit, annotation.MAPPING_PATH)
    _same_working_bytes(repo, annotation.MAPPING_PATH, mapping_bytes)
    packet = _json_object(packet_bytes, "committed masked packet")
    submission = _json_object(submission_bytes, "committed anonymous submission")
    mapping = _json_object(mapping_bytes, "committed reveal mapping")
    try:
        bound = annotation.unblind_annotations(packet, mapping, submission, verified)
    except (TypeError, ValueError, KeyError) as exc:
        raise EvidenceError("committed annotation or reveal binding invalid") from exc
    adjudications = deepcopy(bound["adjudications"])
    for case_id in verified["case_order"]:
        for arm in tx.ARMS:
            adjudications[case_id][arm]["output_locked_before_annotation"] = True
    rows = [tx.score_case(verified["prepared_cases"][case_id],
                          verified["gold_by_case_id"][case_id],
                          verified["observations"][case_id],
                          adjudications[case_id], verified["raw_lock"])
            for case_id in verified["case_order"]]
    summary = tx.summarize_scores(
        rows, expected_case_order=verified["case_order"],
        expected_source_digests=verified["expected_source_digests"],
        expected_gold_digests=verified["expected_gold_digests"])
    _require(summary["frozen_case_identity_match"] is True
             and summary["all_raw_observations_locked"] is True,
             "score table lost frozen/raw-lock identity")
    result = {**verified,
              "annotation_authority": annotation.AUTHORITY,
              "packet_commit": packet_commit,
              "submission_commit": submission_commit,
              "reveal_commit": reveal_commit,
              "annotation_submission_digest": bound["submission_digest"],
              "adjudications": adjudications,
              "score_rows": rows,
              "score_summary": summary,
              "formal_score_eligible": True,
              "semantic_quality": "arm_masked_developer_proxy_not_independent_human",
              "component_status": (
                  "COMPONENT_GATE_PASS_NEXT_LAYER_REQUIRED"
                  if summary["overall_b_qualified"]
                  else "REVIEW_REQUIRED_COMPONENT_FAIL"),
              }
    return result
