"""Zero-call fake wire/commit tests for the formal P4 raw evidence boundary."""

import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

import p4_action_transaction_a_observation as a_raw
import p4_action_transaction_annotation as annotation
import p4_action_transaction_b_observation as b_raw
import p4_action_transaction_evidence as evidence
import p4_action_transaction_scoring as tx


ROOT = Path(__file__).resolve().parent
FAKE_RUNNER_SHA = "f" * 64
FAKE_RAW_COMMIT = "a" * 40


@pytest.fixture(scope="module")
def frozen():
    # Read the real immutable freeze; no gold reaches either fake request.
    return evidence.frozen_material(ROOT)


def _stage(case, request_arm, kind, contract, content, index):
    body = evidence._request(case, request_arm, contract)
    response = {
        "model": contract["model"], "done": True,
        "message": {"role": "assistant", "content": content},
        "prompt_eval_count": 101, "eval_count": 55,
        "load_duration": 0, "total_duration": 1_000_000_000,
    }
    wire_bytes = json.dumps(response, ensure_ascii=False).encode("utf-8")
    return {
        "stage": kind, "call_index": index,
        "request_body": body, "options": deepcopy(body["options"]),
        "raw_http_response": {
            "status": 200, "headers": {"content-type": "application/json"},
            "body_base64": base64.b64encode(wire_bytes).decode("ascii"),
        },
        "ollama_response": response,
        "raw_content": content, "prompt_tokens": 101,
        "completion_tokens": 55, "wall_seconds": 1.5,
        "usage": {"prompt_eval_count": 101, "eval_count": 55,
                  "load_duration": 0, "total_duration": 1_000_000_000},
        "model_digest": contract["model_digest"],
        "http_identity": {"endpoint": evidence.ENDPOINT,
                          "peer_host": "127.0.0.1", "peer_port": 11434,
                          "model": contract["model"],
                          "response_model": contract["model"]},
        "transport_metadata": {"http_status": 200, "method": "POST",
                               "endpoint": evidence.ENDPOINT},
        "attempted": True, "completed": True,
        "json_parse_success": tx.parse_transaction_json(content) is not None,
    }


def _abstain(case):
    source = case["sources"][0]
    value = {field: "" for field in tx.ACTION_FIELDS}
    value.update({
        "status": "abstain", "task_source_id": source["id"],
        "task_source_span": source["text"],
        "task_target_quote": source["text"][:20].strip(),
        "forbidden_source_id": None, "forbidden_quote": None,
        "actor": "unknown", "receipt": None,
        "prerequisite_status": "unknown",
        "reason_code": "ambiguous_or_unsupported",
    })
    return json.dumps(value, ensure_ascii=False)


def _raw_document(frozen):
    contract = frozen["contract"]
    rows = []
    digests = {}
    index = 0
    for position, case_id in enumerate(frozen["case_order"]):
        case = frozen["prepared_cases"][case_id]
        order = ["A", "B"] if position % 2 == 0 else ["B", "A"]
        arms = {}
        for arm in order:
            index += 1
            if arm == "A":
                # A transport completed, but deliberately truncated JSON is
                # an attributable quality failure, not a missing raw stage.
                gen = _stage(case, "A_M51", "M51", contract, "{", index)
                observed = a_raw.build_a_observation(
                    case, gen, full_turn_seconds=2.0, retries=0)
                arms["A_two_stage"] = {
                    "generator_stage": gen, "reviewer_stage": None,
                    "full_turn_seconds": 2.0, "retries": 0,
                    "observation": observed,
                }
            else:
                stage = _stage(case, "B", "B_transaction", contract,
                               _abstain(case), index)
                observed = b_raw.build_b_observation_from_stage(
                    case, stage, full_turn_seconds=2.0, retries=0)
                arms["B_transaction"] = {
                    "stage": stage, "full_turn_seconds": 2.0,
                    "retries": 0, "observation": observed,
                }
        rows.append({"case_id": case_id, "prepared_case": case,
                     "arm_order": order, "arms": arms})
        digests[case_id] = {
            arm: tx.output_evidence_digest(case_id, arm, arms[arm]["observation"])
            for arm in tx.ARMS
        }
    prewarm_response = {"model": contract["model"], "done": True,
                        "response": "", "prompt_eval_count": 1,
                        "load_duration": 0, "total_duration": 500_000_000}
    prewarm = {
        "attempted": True, "completed": True,
        "model": contract["model"],
        "model_digest": contract["model_digest"],
        "endpoint": "http://127.0.0.1:11434/api/generate",
        "request_body": {"model": contract["model"], "prompt": "",
                         "stream": False, "keep_alive": "30m"},
        "raw_http_response": {
            "status": 200, "headers": {"content-type": "application/json"},
            "body_base64": base64.b64encode(
                json.dumps(prewarm_response).encode("utf-8")).decode("ascii"),
        },
        "http_identity": {"endpoint": "http://127.0.0.1:11434/api/generate",
                          "peer_host": "127.0.0.1", "peer_port": 11434,
                          "response_model": contract["model"]},
        "ollama_response": prewarm_response,
        "transport_metadata": {
            "http_status": 200, "method": "POST",
            "endpoint": "http://127.0.0.1:11434/api/generate",
        },
        "wall_seconds": 1.0,
    }
    return {
        "schema": "uruha_p4_action_transaction_raw_v1",
        "status": "complete_unannotated",
        "freeze_sha": evidence.FREEZE_SHA,
        "contract_sha256": frozen["contract_sha256"],
        "sources_sha256": frozen["sources_sha256"],
        "runner_sha256": FAKE_RUNNER_SHA,
        "model": contract["model"],
        "model_digest": contract["model_digest"],
        "endpoint": evidence.ENDPOINT,
        "retry_count": 0, "maximum_scored_calls": 54,
        "scored_calls_started": index, "prewarm": prewarm,
        "semantic_quality": "unverified", "gold_labels_present": False,
        "production_database_access": False, "product_runtime_changed": False,
        "product_eligible": False,
        "claim_boundary": contract["claim_boundary"],
        "cases": rows, "output_digests": digests,
    }


@pytest.fixture(scope="module")
def raw(frozen):
    return _raw_document(frozen)


def _verify(raw, frozen):
    return evidence.verify_raw_document(raw, frozen,
                                        runner_sha256=FAKE_RUNNER_SHA,
                                        raw_commit=FAKE_RAW_COMMIT)


def test_all_36_raw_observations_recomputed_from_frozen_identity(raw, frozen):
    result = _verify(raw, frozen)
    assert result["case_order"] == frozen["case_order"]
    assert result["scored_calls"] == 36
    assert len(result["output_digests"]) == 18
    assert all(set(pair) == set(tx.ARMS)
               for pair in result["output_digests"].values())
    assert result["raw_lock"]["commit_sha"] == FAKE_RAW_COMMIT
    assert result["verified_raw_evidence"] is True
    assert result["formal_score_eligible"] is False
    assert result["semantic_quality"] == "unverified"
    assert not result["execution_budget_violations"]


@pytest.mark.parametrize("mutation", [
    "wrong_case_order", "wrong_prepared_case", "missing_b", "forged_observation",
    "wrong_output_digest", "wrong_source_hash", "wrong_runner_hash",
    "wrong_call_index", "extra_retry", "missing_usage", "wrong_wire_content",
    "wrong_request_system", "wrong_request_payload", "wrong_request_schema",
    "wrong_request_option", "wrong_local_peer", "wrong_model_digest",
    "wrong_stage_wall", "missing_b_stage", "false_parse_claim",
    "partial_status", "gold_present", "product_eligible", "wrong_method",
    "wrong_endpoint", "wrong_prewarm_model", "wrong_prewarm_body",
    "wrong_prewarm_digest", "wrong_prewarm_transport", "wrong_prewarm_wire",
    "extra_gold_field", "extra_stage_gold", "false_retry_as_zero",
])
def test_raw_evidence_mutations_fail_closed(raw, frozen, mutation):
    changed = deepcopy(raw)
    first = changed["cases"][0]
    a = first["arms"]["A_two_stage"]
    b = first["arms"]["B_transaction"]
    gen = a["generator_stage"]
    if mutation == "wrong_case_order":
        changed["cases"][0], changed["cases"][1] = changed["cases"][1], changed["cases"][0]
    elif mutation == "wrong_prepared_case":
        first["prepared_case"]["raw_user_input"] += "wrong"
    elif mutation == "missing_b":
        del first["arms"]["B_transaction"]
    elif mutation == "forged_observation":
        a["observation"]["decision"] = "action"
    elif mutation == "wrong_output_digest":
        changed["output_digests"][first["case_id"]]["A_two_stage"] = "0" * 64
    elif mutation == "wrong_source_hash":
        changed["sources_sha256"] = "0" * 64
    elif mutation == "wrong_runner_hash":
        changed["runner_sha256"] = "0" * 64
    elif mutation == "wrong_call_index":
        gen["call_index"] = 2
    elif mutation == "extra_retry":
        b["retries"] = 1
    elif mutation == "missing_usage":
        del gen["usage"]["eval_count"]
    elif mutation == "wrong_wire_content":
        gen["raw_content"] = "{}"
    elif mutation == "wrong_request_system":
        gen["request_body"]["messages"][0]["content"] = "new system"
    elif mutation == "wrong_request_payload":
        gen["request_body"]["messages"][1]["content"] = '{}'
    elif mutation == "wrong_request_schema":
        gen["request_body"]["format"] = {"type": "object"}
    elif mutation == "wrong_request_option":
        gen["request_body"]["options"]["num_predict"] = 999
    elif mutation == "wrong_local_peer":
        gen["http_identity"]["peer_host"] = "example.com"
    elif mutation == "wrong_model_digest":
        gen["model_digest"] = "0" * 64
    elif mutation == "wrong_stage_wall":
        gen["wall_seconds"] = 3.0
    elif mutation == "missing_b_stage":
        b["stage"] = None
    elif mutation == "false_parse_claim":
        gen["json_parse_success"] = True
    elif mutation == "partial_status":
        changed["status"] = "running_not_reusable"
    elif mutation == "gold_present":
        changed["gold_labels_present"] = True
    elif mutation == "product_eligible":
        changed["product_eligible"] = True
    elif mutation == "wrong_method":
        gen["transport_metadata"]["method"] = "GET"
    elif mutation == "wrong_endpoint":
        gen["transport_metadata"]["endpoint"] = "http://example.com/api/chat"
    elif mutation == "wrong_prewarm_model":
        changed["prewarm"]["http_identity"]["response_model"] = "other-model"
    elif mutation == "wrong_prewarm_body":
        changed["prewarm"]["request_body"]["keep_alive"] = "1m"
    elif mutation == "wrong_prewarm_digest":
        changed["prewarm"]["model_digest"] = "0" * 64
    elif mutation == "wrong_prewarm_transport":
        changed["prewarm"]["transport_metadata"]["method"] = "GET"
    elif mutation == "wrong_prewarm_wire":
        changed["prewarm"]["ollama_response"]["model"] = "other-model"
    elif mutation == "extra_gold_field":
        changed["gold_by_case_id"] = {"forged": "pass"}
    elif mutation == "extra_stage_gold":
        gen["gold_label"] = "action"
    elif mutation == "false_retry_as_zero":
        changed["retry_count"] = False
    with pytest.raises(evidence.EvidenceError):
        _verify(changed, frozen)


def test_timeout_is_preserved_as_negative_evidence_not_erased(raw, frozen):
    changed = deepcopy(raw)
    first = changed["cases"][0]
    b = first["arms"]["B_transaction"]
    b["full_turn_seconds"] = 21.0
    b["observation"] = b_raw.build_b_observation_from_stage(
        first["prepared_case"], b["stage"], full_turn_seconds=21.0, retries=0)
    changed["output_digests"][first["case_id"]]["B_transaction"] = (
        tx.output_evidence_digest(first["case_id"], "B_transaction", b["observation"]))
    result = _verify(changed, frozen)
    assert result["execution_budget_violations"] == [
        first["case_id"] + ":B:full_turn_over_20s"]
    assert result["formal_score_eligible"] is False


@pytest.mark.parametrize("load,total", [
    (0, 25_000_000_000), (-1, 1_000_000_000),
    (2_000_000_000, 1_000_000_000), (0, 1.5),
])
def test_server_duration_cannot_contradict_stage_wall(raw, frozen, load, total):
    stage = deepcopy(raw["cases"][0]["arms"]["B_transaction"]["stage"])
    response = deepcopy(stage["ollama_response"])
    response["load_duration"] = load
    response["total_duration"] = total
    stage["ollama_response"] = response
    stage["usage"]["load_duration"] = load
    stage["usage"]["total_duration"] = total
    stage["raw_http_response"]["body_base64"] = base64.b64encode(
        json.dumps(response, ensure_ascii=False).encode("utf-8")).decode("ascii")
    case = raw["cases"][0]["prepared_case"]
    expected_body = evidence._request(case, "B", frozen["contract"])
    with pytest.raises(evidence.EvidenceError):
        evidence.verify_stage(stage, expected_stage="B_transaction",
                              expected_body=expected_body,
                              model_digest=frozen["contract"]["model_digest"])


def test_server_duration_cannot_contradict_prewarm_wall(raw, frozen):
    changed = deepcopy(raw)
    prewarm = changed["prewarm"]
    response = deepcopy(prewarm["ollama_response"])
    response["total_duration"] = 25_000_000_000
    prewarm["ollama_response"] = response
    prewarm["raw_http_response"]["body_base64"] = base64.b64encode(
        json.dumps(response).encode("utf-8")).decode("ascii")
    with pytest.raises(evidence.EvidenceError):
        _verify(changed, frozen)


def test_load_only_prewarm_without_duration_pair_is_verifiable(raw, frozen):
    changed = deepcopy(raw)
    prewarm = changed["prewarm"]
    response = {"model": frozen["contract"]["model"], "done": True,
                "done_reason": "load", "response": ""}
    prewarm["ollama_response"] = response
    prewarm["raw_http_response"]["body_base64"] = base64.b64encode(
        json.dumps(response).encode("utf-8")).decode("ascii")
    assert _verify(changed, frozen)["verified_raw_evidence"] is True
    for bad in ({**response, "load_duration": 1},
                {**response, "done_reason": "stop"},
                {**response, "load_duration": 1,
                 "total_duration": 25_000_000_000}):
        invalid = deepcopy(changed)
        invalid["prewarm"]["ollama_response"] = bad
        invalid["prewarm"]["raw_http_response"]["body_base64"] = (
            base64.b64encode(json.dumps(bad).encode("utf-8")).decode("ascii"))
        with pytest.raises(evidence.EvidenceError):
            _verify(invalid, frozen)


def test_working_bytes_and_strict_git_chronology_are_required(tmp_path, monkeypatch):
    relative = evidence.RAW_PATH
    location = tmp_path / relative
    location.parent.mkdir(parents=True)
    location.write_bytes(b"original")
    evidence._same_working_bytes(tmp_path, relative, b"original")
    location.write_bytes(b"changed")
    with pytest.raises(evidence.EvidenceError):
        evidence._same_working_bytes(tmp_path, relative, b"original")
    with pytest.raises(evidence.EvidenceError):
        evidence._strict_ancestor(tmp_path, FAKE_RAW_COMMIT, FAKE_RAW_COMMIT)
    monkeypatch.setattr(evidence, "_git", lambda *_args: (_ for _ in ()).throw(
        evidence.EvidenceError("not ancestor")))
    with pytest.raises(evidence.EvidenceError):
        evidence._strict_ancestor(tmp_path, "a" * 40, "b" * 40)


def test_annotation_chronology_does_not_self_certify_masking(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "_commit", lambda _repo, sha: sha)
    seen = []
    monkeypatch.setattr(evidence, "_strict_ancestor",
                        lambda _repo, earlier, later: seen.append((earlier, later)))
    verified = {"raw_commit": FAKE_RAW_COMMIT, "formal_score_eligible": False}
    evidence.require_annotation_after_raw(tmp_path, verified,
                                          annotation_commit="b" * 40)
    assert seen == [(FAKE_RAW_COMMIT, "b" * 40)]
    verified["formal_score_eligible"] = True
    with pytest.raises(evidence.EvidenceError):
        evidence.require_annotation_after_raw(tmp_path, verified,
                                              annotation_commit="b" * 40)


def _git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo).decode().strip()


def _commit_file(repo, relative, value, label):
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    _git(repo, "add", relative)
    _git(repo, "-c", "user.name=Fake Test",
         "-c", "user.email=fake@example.invalid", "commit", "-qm", label)
    return _git(repo, "rev-parse", "HEAD")


def _annotation_chain(repo, raw, frozen, *, premature_mapping=False,
                      mutate_packet=False, mutate_raw_after_lock=False,
                      premature_before_raw_path=None):
    _git(repo, "init", "-q")
    if premature_before_raw_path is not None:
        _commit_file(repo, premature_before_raw_path,
                     {"early": "already exposed"}, "premature ancestor exposure")
        _git(repo, "rm", premature_before_raw_path)
        _git(repo, "-c", "user.name=Fake Test",
             "-c", "user.email=fake@example.invalid",
             "commit", "-qm", "delete exposed ancestor artifact")
    raw_commit = _commit_file(repo, evidence.RAW_PATH, raw, "raw")
    verified = evidence.verify_raw_document(raw, frozen,
                                            runner_sha256=FAKE_RUNNER_SHA,
                                            raw_commit=raw_commit)
    packet, mapping = annotation.build_masked_packet(
        verified, seed=bytes(range(32)))
    packet_commit = _commit_file(repo, annotation.PACKET_PATH, packet, "packet")
    if premature_mapping:
        _commit_file(repo, annotation.MAPPING_PATH, mapping, "premature mapping")
        (repo / annotation.MAPPING_PATH).unlink()
        _git(repo, "rm", annotation.MAPPING_PATH)
    labels = [{"item_id": row["item_id"],
               "axes": {axis: "pass" for axis in tx.SEMANTIC_AXES}}
              for row in packet["records"]]
    submission = annotation.build_annotation_submission(packet, labels)
    submission_commit = _commit_file(
        repo, annotation.SUBMISSION_PATH, submission, "submission")
    if mutate_packet:
        altered = deepcopy(packet)
        altered["records"][0]["reply_jp"] = "changed after submission"
        _commit_file(repo, annotation.PACKET_PATH, altered, "alter packet")
    if mutate_raw_after_lock:
        _commit_file(repo, evidence.RAW_PATH, {"changed": True},
                     "alter raw after lock")
        _commit_file(repo, evidence.RAW_PATH, raw, "restore raw after lock")
    reveal_commit = _commit_file(repo, annotation.MAPPING_PATH, mapping, "reveal")
    return verified, (raw_commit, packet_commit, submission_commit, reveal_commit)


def test_git_locked_anonymous_submission_only_promotes_after_reveal(
        tmp_path, monkeypatch, raw, frozen):
    verified, commits = _annotation_chain(tmp_path, raw, frozen)
    monkeypatch.setattr(evidence, "verify_raw_evidence",
                        lambda *_args, **_kwargs: verified)
    result = evidence.verify_annotation_lock(
        tmp_path, runner_commit="f" * 40, raw_commit=commits[0],
        packet_commit=commits[1], submission_commit=commits[2],
        reveal_commit=commits[3])
    assert result["formal_score_eligible"] is True
    assert result["annotation_authority"] == annotation.AUTHORITY
    assert result["score_summary"]["all_raw_observations_locked"] is True
    assert result["score_summary"]["frozen_case_identity_match"] is True
    assert result["component_status"] == "REVIEW_REQUIRED_COMPONENT_FAIL"
    assert all(item["output_locked_before_annotation"] is True
               for pair in result["adjudications"].values()
               for item in pair.values())


@pytest.mark.parametrize("premature_mapping,mutate_packet,mutate_raw_after_lock", [
    (True, False, False), (False, True, False), (False, False, True),
])
def test_git_annotation_lock_rejects_early_reveal_or_packet_rewrite(
        tmp_path, monkeypatch, raw, frozen, premature_mapping, mutate_packet,
        mutate_raw_after_lock):
    verified, commits = _annotation_chain(
        tmp_path, raw, frozen, premature_mapping=premature_mapping,
        mutate_packet=mutate_packet,
        mutate_raw_after_lock=mutate_raw_after_lock)
    monkeypatch.setattr(evidence, "verify_raw_evidence",
                        lambda *_args, **_kwargs: verified)
    with pytest.raises(evidence.EvidenceError):
        evidence.verify_annotation_lock(
            tmp_path, runner_commit="f" * 40, raw_commit=commits[0],
            packet_commit=commits[1], submission_commit=commits[2],
            reveal_commit=commits[3])


@pytest.mark.parametrize("early_path", [
    annotation.PACKET_PATH, annotation.SUBMISSION_PATH,
    annotation.MAPPING_PATH,
])
def test_git_annotation_lock_rejects_ancestor_add_then_delete(
        tmp_path, monkeypatch, raw, frozen, early_path):
    verified, commits = _annotation_chain(
        tmp_path, raw, frozen, premature_before_raw_path=early_path)
    monkeypatch.setattr(evidence, "verify_raw_evidence",
                        lambda *_args, **_kwargs: verified)
    with pytest.raises(evidence.EvidenceError, match="exposed too early"):
        evidence.verify_annotation_lock(
            tmp_path, runner_commit="f" * 40, raw_commit=commits[0],
            packet_commit=commits[1], submission_commit=commits[2],
            reveal_commit=commits[3])
