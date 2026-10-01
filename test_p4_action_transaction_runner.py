"""Zero-model-call fake HTTP tests for the one-shot transaction raw runner."""

from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path

import pytest

import p4_action_transaction_scoring as tx
import run_p4_action_transaction as runner
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "configs/p4_action_transaction_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONTRACT["dataset"]["sources"]["path"])
                     .read_text(encoding="utf-8"))


def _wire(data: dict, path: str, *, status: int = 200,
          peer_host: str = "127.0.0.1") -> dict:
    return {"status": status, "headers": {"Content-Type": "application/json"},
            "body_base64": base64.b64encode(
                json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii"),
            "endpoint": runner.OLLAMA_ORIGIN + path,
            "method": "POST", "peer_host": peer_host, "peer_port": 11434}


def _abstain_from_body(body: dict) -> str:
    source = json.loads(body["messages"][1]["content"])["user_sources"][0]
    transaction = {
        "status": "abstain", "task_source_id": source["id"],
        "task_source_span": source["text"], "task_target_quote": "",
        "forbidden_source_id": None, "forbidden_quote": None,
        "actor": "user", "receipt": None, "prerequisite_status": "unknown",
        "reason_code": "ambiguous_or_unsupported",
    }
    transaction.update({field: "" for field in tx.ACTION_FIELDS})
    return json.dumps(transaction, ensure_ascii=False)


def _fake_http(calls: list, *, fail_at: int | None = None,
               failure: str | None = None, b_parse_failure: bool = False):
    def exchange(method, path, body, timeout):
        assert method == "POST"
        assert path in {"/api/generate", "/api/chat"}
        if path == "/api/generate":
            return _wire({"model": CONTRACT["model"], "done": True,
                          "load_duration": 10, "total_duration": 20}, path)
        calls.append((deepcopy(body), timeout))
        index = len(calls)
        if fail_at == index and failure == "transport":
            raise TimeoutError("fake one-shot timeout")
        system = body["messages"][0]["content"]
        if system == m51.CANDIDATE_SYSTEM:
            content = '{"sid":'  # complete transport, attributable quality failure
        elif system == tx.TRANSACTION_SYSTEM:
            content = '{"status":' if b_parse_failure else _abstain_from_body(body)
        elif system == m46.REVIEW_SYSTEM:
            content = "{}"
        else:
            pytest.fail("unfrozen model prompt")
        data = {"model": CONTRACT["model"], "done": True,
                "message": {"role": "assistant", "content": content},
                "prompt_eval_count": 120, "eval_count": 100,
                "load_duration": 10, "total_duration": 20}
        if fail_at == index and failure == "usage":
            data["prompt_eval_count"] = data["eval_count"] = 0
        if fail_at == index and failure == "model":
            data["model"] = "another-model"
        if fail_at == index and failure == "cap":
            data["eval_count"] = body["options"]["num_predict"] + 1
        if fail_at == index and failure == "duration":
            data["total_duration"] = 25_000_000_000
        return _wire(data, path, status=500 if fail_at == index and failure == "status"
                     else 200,
                     peer_host="192.0.2.7" if fail_at == index and failure == "peer"
                     else "127.0.0.1")
    return exchange


def _fake_run(tmp_path, monkeypatch, *, fail_at=None, failure=None,
              b_parse_failure=False, prewarm_ok=True, all_a_review=False):
    prepared = runner._prepare_cases(CONTRACT, DATASET)
    monkeypatch.setattr(runner, "preflight", lambda *_: (CONTRACT, DATASET, prepared))
    calls = []
    monkeypatch.setattr(runner, "_http_exchange", _fake_http(
        calls, fail_at=fail_at, failure=failure, b_parse_failure=b_parse_failure))
    if not prewarm_ok:
        monkeypatch.setattr(runner, "_prewarm", lambda *_: {
            "attempted": True, "completed": False, "wall_seconds": 1.0,
            "error_type": "TimeoutError"})
    if all_a_review:
        def observe_a(case, generator_stage_record, *, full_turn_seconds,
                      reviewer_stage_record=None, retries=0):
            if reviewer_stage_record is None:
                source = case["sources"][0]
                return {"failure_stage": "review_missing",
                        "selected_plan": {"goal_source_id": source["id"],
                                          "goal_source_span": source["text"],
                                          "progress_mechanism": "structure_scaffold"}}
            return {"arm": "A_two_stage", "failure_stage": "review_contract",
                    "decision": "abstain", "semantic_gold_checked": False,
                    "full_turn_seconds": full_turn_seconds}
        monkeypatch.setattr(runner.a_raw, "build_a_observation", observe_a)
    path = tmp_path / "raw.json"
    artifact = runner.run(output_path=path)
    return artifact, path, calls


def test_frozen_sources_hash_contract_and_no_gold_in_prepared_cases():
    runner._validate_contract(CONTRACT)
    runner._validate_hash_bindings(CONTRACT)
    cases = runner._prepare_cases(CONTRACT, DATASET)
    assert len(cases) == 18
    assert [case["case_id"] for case in cases] == CONTRACT["dataset"]["case_order"]
    assert all(case["logic"] == tx.FIXED_COMPONENT_LOGIC
               and case["source_gate"]["excluded"] == [] for case in cases)
    assert all("gold" not in case and "expected" not in case for case in cases)
    altered = deepcopy(CONTRACT)
    altered["hash_bound_dependencies"]["A_raw_observation_builder"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="Frozen hash mismatch"):
        runner._validate_hash_bindings(altered)
    changed_order = deepcopy(DATASET)
    changed_order["cases"][0], changed_order["cases"][1] = (
        changed_order["cases"][1], changed_order["cases"][0])
    with pytest.raises(RuntimeError, match="source case count or order"):
        runner._prepare_cases(CONTRACT, changed_order)
    injected = deepcopy(DATASET)
    injected["cases"][0]["gold"] = {"decision": "action"}
    with pytest.raises(RuntimeError, match="non-source case metadata"):
        runner._prepare_cases(CONTRACT, injected)


def test_exact_frozen_a_and_b_requests_exclude_gold_and_keep_equal_total_cap():
    case = runner._prepare_cases(CONTRACT, DATASET)[0]
    source = case["sources"][0]
    plan = {"goal_source_id": source["id"], "goal_source_span": source["text"],
            "progress_mechanism": "structure_scaffold", "instruction_jp": "一つ書いてみよ。"}
    a_gen = runner._expected_body("M51", case, CONTRACT)
    a_rev = runner._expected_body("M46", case, CONTRACT, plan)
    b = runner._expected_body("B_transaction", case, CONTRACT)
    assert [body["options"]["num_predict"] for body in (a_gen, a_rev, b)] == [360, 320, 680]
    assert [body["options"]["seed"] for body in (a_gen, a_rev, b)] == [20260830, 20260829, 20260830]
    assert all(body["model"] == CONTRACT["model"] and body["stream"] is False
               and body["think"] is False and body["keep_alive"] == "30m"
               and body["options"]["num_ctx"] == 4096
               and body["options"]["temperature"] == 0
               for body in (a_gen, a_rev, b))
    assert a_gen["messages"][0]["content"] == m51.CANDIDATE_SYSTEM
    assert a_rev["messages"][0]["content"] == m46.REVIEW_SYSTEM
    assert b["messages"][0]["content"] == tx.TRANSACTION_SYSTEM
    assert a_gen["format"] == m51._candidate_schema(case["sources"])
    assert a_rev["format"] == m46.review_schema(case["sources"], plan)
    assert b["format"] == tx.transaction_schema(case["sources"])
    assert json.loads(a_gen["messages"][1]["content"]) == {"user_sources": case["sources"]}
    assert json.loads(b["messages"][1]["content"]) == tx.transaction_payload(case["sources"])
    assert json.loads(a_rev["messages"][1]["content"]) == {
        "sources": case["sources"],
        "plan": {key: value for key, value in plan.items() if key != "progress_mechanism"},
        "planned_payload_digest": runner.m45.digest({"sources": case["sources"], "plan": plan})}
    assert all("gold" not in json.dumps(body, ensure_ascii=False).lower()
               for body in (a_gen, a_rev, b))


def test_complete_transport_parse_failures_continue_all_cases_in_alternating_order(
        tmp_path, monkeypatch):
    artifact, path, calls = _fake_run(tmp_path, monkeypatch, b_parse_failure=True)
    assert artifact["status"] == "complete_unannotated"
    assert artifact["scored_calls_started"] == len(calls) == 36
    assert len(artifact["cases"]) == 18
    assert artifact["prewarm"]["completed"] is True
    assert artifact["retry_count"] == 0 and artifact["gold_labels_present"] is False
    assert artifact["semantic_quality"] == "unverified"
    actual = []
    for case in artifact["cases"]:
        assert case["arms"]["A_two_stage"]["reviewer_stage"] is None
        assert case["arms"]["A_two_stage"]["observation"]["failure_stage"] == "generator_parse"
        assert case["arms"]["B_transaction"]["observation"]["failure_stage"] == "transaction_parse"
        assert case["arms"]["B_transaction"]["observation"]["decision"] == "abstain"
        assert case["arms"]["B_transaction"]["observation"]["raw_stage_complete"] is True
        assert case["arms"]["A_two_stage"]["full_turn_seconds"] >= 0
        assert case["arms"]["B_transaction"]["full_turn_seconds"] >= 0
        for arm in case["arm_order"]:
            stage = (case["arms"]["A_two_stage"]["generator_stage"] if arm == "A"
                     else case["arms"]["B_transaction"]["stage"])
            actual.append((case["case_id"], arm, stage["call_index"]))
            assert stage["request_body"]["model"] == CONTRACT["model"]
            assert stage["raw_http_response"]["status"] == 200
            assert stage["ollama_response"]["message"]["content"] == stage["raw_content"]
            assert stage["http_identity"]["peer_host"] == "127.0.0.1"
            assert stage["model_digest"] == CONTRACT["model_digest"]
            assert stage["usage"]["eval_count"] == stage["completion_tokens"]
    expected = [(case_id, arm, i + 1)
                for i, (case_id, arm) in enumerate(
                    (case_id, arm) for index, case_id in enumerate(CONTRACT["dataset"]["case_order"])
                    for arm in runner.ARM_ORDER[index % 2])]
    assert actual == expected
    assert len(artifact["output_digests"]) == 18
    for case in artifact["cases"]:
        assert set(artifact["output_digests"][case["case_id"]]) == set(tx.ARMS)
        for arm in tx.ARMS:
            observed = case["arms"][arm]["observation"]
            assert artifact["output_digests"][case["case_id"]][arm] == (
                tx.output_evidence_digest(case["case_id"], arm, observed))
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["status"] == artifact["status"]
    assert all("gold_label" not in row and "score" not in row
               for row in saved["cases"])
    assert "expected_reason_code" not in path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        runner.run(output_path=path)


def test_eligible_a_uses_m51_then_m46_and_never_exceeds_54_calls(tmp_path, monkeypatch):
    artifact, _, calls = _fake_run(tmp_path, monkeypatch, all_a_review=True)
    assert artifact["status"] == "complete_unannotated"
    assert artifact["scored_calls_started"] == len(calls) == 54
    indices = []
    for index, case in enumerate(artifact["cases"]):
        assert case["arm_order"] == list(runner.ARM_ORDER[index % 2])
        a = case["arms"]["A_two_stage"]
        assert a["generator_stage"]["request_body"]["options"]["num_predict"] == 360
        assert a["reviewer_stage"]["request_body"]["options"]["num_predict"] == 320
        indices.extend([a["generator_stage"]["call_index"],
                        a["reviewer_stage"]["call_index"],
                        case["arms"]["B_transaction"]["stage"]["call_index"]])
    assert sorted(indices) == list(range(1, 55))


@pytest.mark.parametrize("failure", ["transport", "usage", "model", "cap", "status", "peer",
                                     "duration"])
def test_fatal_exchange_or_usage_stops_partial_no_retry(tmp_path, monkeypatch, failure):
    artifact, path, calls = _fake_run(tmp_path, monkeypatch, fail_at=2, failure=failure)
    assert len(calls) == artifact["scored_calls_started"] == 2
    assert len(artifact["cases"]) == 1
    assert artifact["status"].endswith("_partial_no_resume")
    assert artifact["cases"][0]["arms"]["A_two_stage"]["observation"] is not None
    assert artifact["cases"][0]["arms"]["B_transaction"]["observation"] is None
    assert artifact["retry_count"] == 0
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == artifact["status"]
    with pytest.raises(FileExistsError):
        runner.run(output_path=path)


def test_every_stage_rechecks_a_seed_model_request_and_b_source_prompt_schema(monkeypatch):
    case = runner._prepare_cases(CONTRACT, DATASET)[0]
    monkeypatch.setattr(runner, "_http_exchange", _fake_http([]))
    a = runner._model_stage("M51", case, CONTRACT, timeout=5, call_index=1)
    assert runner._verify_stage(a, stage="M51", case=case, contract=CONTRACT) is None
    for mutate in (
        lambda row: row["request_body"]["options"].__setitem__("seed", 1),
        lambda row: row["request_body"].__setitem__("model", "other"),
        lambda row: row["request_body"]["messages"][1].__setitem__("content", "{}"),
    ):
        bad = deepcopy(a)
        mutate(bad)
        assert runner._verify_stage(bad, stage="M51", case=case, contract=CONTRACT) == (
            "frozen_request_or_model_identity_mismatch")
    b = runner._model_stage("B_transaction", case, CONTRACT, timeout=5, call_index=2)
    assert runner._verify_stage(b, stage="B_transaction", case=case, contract=CONTRACT) is None
    for mutate in (
        lambda row: row["request_body"]["messages"][1].__setitem__("content", "{}"),
        lambda row: row["request_body"]["messages"][0].__setitem__("content", "forged"),
        lambda row: row["request_body"].__setitem__("format", {"type": "object"}),
        lambda row: row.__setitem__("model_digest", "0" * 64),
    ):
        bad = deepcopy(b)
        mutate(bad)
        assert runner._verify_stage(bad, stage="B_transaction", case=case, contract=CONTRACT) == (
            "frozen_request_or_model_identity_mismatch")
    bad = deepcopy(b)
    bad["completion_tokens"] = 0
    assert runner._verify_stage(bad, stage="B_transaction", case=case, contract=CONTRACT) == (
        "token_usage_incomplete")
    bad = deepcopy(b)
    bad["wall_seconds"] = 35
    assert runner._verify_stage(bad, stage="B_transaction", case=case, contract=CONTRACT) == (
        "stage_wall_invalid_or_deadline_exceeded")
    bad = deepcopy(b)
    bad["raw_http_response"]["body_base64"] = "e30="
    assert runner._verify_stage(bad, stage="B_transaction", case=case, contract=CONTRACT) == (
        "ollama_response_identity_mismatch")


@pytest.mark.parametrize("load,total", [
    (0, 25_000_000_000),  # claimed 25 s for a subsecond client wall
    (-1, 20), (21, 20), (1.5, 20), (True, 20), (10, -1), (10, None),
])
def test_stage_server_durations_must_be_integral_nonnegative_and_fit_client_wall(
        monkeypatch, load, total):
    case = runner._prepare_cases(CONTRACT, DATASET)[0]
    monkeypatch.setattr(runner, "_http_exchange", _fake_http([]))
    stage = runner._model_stage("B_transaction", case, CONTRACT, timeout=5, call_index=1)
    assert runner._verify_stage(stage, stage="B_transaction", case=case,
                                contract=CONTRACT) is None
    modified = deepcopy(stage)
    envelope = modified["ollama_response"]
    envelope["load_duration"] = load
    envelope["total_duration"] = total
    modified["usage"]["load_duration"] = load
    modified["usage"]["total_duration"] = total
    modified["raw_http_response"]["body_base64"] = base64.b64encode(
        json.dumps(envelope, ensure_ascii=False).encode("utf-8")).decode("ascii")
    assert runner._verify_stage(modified, stage="B_transaction", case=case,
                                contract=CONTRACT) == (
        "server_duration_invalid_or_exceeds_stage_wall")


def test_stage_duration_allows_only_microsecond_wall_rounding(monkeypatch):
    case = runner._prepare_cases(CONTRACT, DATASET)[0]
    monkeypatch.setattr(runner, "_http_exchange", _fake_http([]))
    stage = runner._model_stage("B_transaction", case, CONTRACT, timeout=5, call_index=1)
    stage["wall_seconds"] = 1.5
    for nanoseconds, valid in ((1_500_000_500, True), (1_500_001_000, True),
                               (1_500_001_001, False)):
        modified = deepcopy(stage)
        modified["ollama_response"]["load_duration"] = 0
        modified["ollama_response"]["total_duration"] = nanoseconds
        modified["usage"]["load_duration"] = 0
        modified["usage"]["total_duration"] = nanoseconds
        modified["raw_http_response"]["body_base64"] = base64.b64encode(
            json.dumps(modified["ollama_response"], ensure_ascii=False)
            .encode("utf-8")).decode("ascii")
        result = runner._verify_stage(modified, stage="B_transaction", case=case,
                                      contract=CONTRACT)
        assert (result is None) is valid


@pytest.mark.parametrize("load,total", [(0, 25_000_000_000), (-1, 20),
                                         (21, 20), (1.5, 20), (10, None)])
def test_prewarm_invalid_server_duration_stops_before_scoring(
        tmp_path, monkeypatch, load, total):
    prepared = runner._prepare_cases(CONTRACT, DATASET)
    monkeypatch.setattr(runner, "preflight", lambda *_: (CONTRACT, DATASET, prepared))
    calls = []
    fake = _fake_http(calls)

    def exchange(method, path, body, timeout):
        if path == "/api/generate":
            return _wire({"model": CONTRACT["model"], "done": True,
                          "load_duration": load, "total_duration": total}, path)
        return fake(method, path, body, timeout)

    monkeypatch.setattr(runner, "_http_exchange", exchange)
    artifact = runner.run(output_path=tmp_path / "raw.json")
    assert artifact["status"] == "prewarm_failed_no_scored_calls"
    assert artifact["scored_calls_started"] == 0
    assert artifact["prewarm"]["error_type"] == "ServerDurationMismatch"
    assert calls == []


def test_load_only_prewarm_without_duration_pair_is_accepted_but_not_scored(
        monkeypatch):
    def load_only(method, path, body, timeout):
        assert method == "POST" and path == "/api/generate"
        return _wire({"model": CONTRACT["model"], "done": True,
                      "done_reason": "load", "response": ""}, path)

    monkeypatch.setattr(runner, "_http_exchange", load_only)
    record = runner._prewarm(CONTRACT)
    assert record["completed"] is True
    assert record["ollama_response"]["done_reason"] == "load"
    assert "total_duration" not in record["ollama_response"]
    assert record["wall_seconds"] >= 0
    assert runner._prewarm_timing_valid(record["ollama_response"],
                                        record["wall_seconds"])
    for bad in ({"done_reason": "load", "load_duration": 1},
                {"done_reason": "stop"},
                {"done_reason": "load", "load_duration": 1,
                 "total_duration": 25_000_000_000}):
        assert not runner._prewarm_timing_valid(
            {"model": CONTRACT["model"], "done": True, **bad}, 1.0)


def test_prewarm_failure_starts_no_scored_call(tmp_path, monkeypatch):
    artifact, path, calls = _fake_run(tmp_path, monkeypatch, prewarm_ok=False)
    assert calls == []
    assert artifact["scored_calls_started"] == 0
    assert artifact["cases"] == []
    assert artifact["status"] == "prewarm_failed_no_scored_calls"
    assert json.loads(path.read_text(encoding="utf-8"))["prewarm"]["completed"] is False


def test_formal_preflight_refuses_wrong_or_existing_output_before_network(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_get_json", lambda *_: pytest.fail("network must not run"))
    with pytest.raises(RuntimeError, match="fixed contract and raw output paths"):
        runner.preflight(output_path=tmp_path / "other.json")
    existing = tmp_path / "raw.json"
    existing.write_text("prior raw evidence", encoding="utf-8")
    monkeypatch.setattr(runner, "RAW_PATH", existing)
    with pytest.raises(RuntimeError, match="cannot be overwritten or resumed"):
        runner.preflight(output_path=existing)
    assert existing.read_text(encoding="utf-8") == "prior raw evidence"


def test_full_turn_over_20_seconds_is_recorded_as_cost_failure_not_transport_retry(
        tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_seconds_since", lambda *_: 21.0)
    artifact, _, calls = _fake_run(tmp_path, monkeypatch)
    assert len(calls) == 36 and artifact["status"] == "complete_unannotated"
    assert all(case["arms"]["B_transaction"]["observation"]["full_turn_budget_ok"] is False
               for case in artifact["cases"])
    assert artifact["semantic_quality"] == "unverified"
