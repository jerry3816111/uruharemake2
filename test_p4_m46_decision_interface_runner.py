"""Fake-transport checks for the one-shot decision-interface runner; zero model calls."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import p4_m46_decision_interface_scoring as scoring
import run_p4_m46_decision_interface as runner
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "configs/p4_m46_decision_interface_v1.json")
                      .read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONTRACT["dataset"]["path"]).read_text(encoding="utf-8"))
OLD_REASON_FIELD = {
    "task_alignment": "content_checks.goal_matches_source",
    "state_change": "content_checks.action_changes_task_state",
    "source_grounding": "content_checks.no_invented_facts",
    "private_claim": "content_checks.no_invented_facts",
    "prerequisites": "content_checks.no_unknown_prerequisites",
    "actor_capability": "surface_checks.no_identity_or_role_error",
    "natural_japanese": "surface_checks.casual_japanese",
    "stop_visible": "surface_checks.completion_is_visible",
}


def _old_review(source, plan, axis=None):
    review = {
        "source_id": source["id"], "source_span": source["text"],
        "counterfactual_before_jp": "作業はまだ始まっていない。",
        "counterfactual_after_jp": "作業を一つ進めた状態。",
        "observed_progress_mechanism": plan["progress_mechanism"],
        "content_checks": {key: True for key in m46.CONTENT_CHECKS},
        "surface_checks": {key: True for key in m46.SURFACE_CHECKS},
    }
    if axis:
        group, field = OLD_REASON_FIELD[axis].split(".")
        review[group][field] = False
    return review


def _new_review(source, plan, axis=None, *, value="fail"):
    review = {
        "source_id": source["id"], "source_span": source["text"],
        "before_jp": "作業はまだ始まっていない。",
        "after_jp": "作業を一つ進めた状態。",
        "observed_progress_mechanism": plan["progress_mechanism"],
        "checks": {key: "pass" for key in scoring.AXES},
        "primary_failure": axis or "none",
        "evidence_jp": "「まず」の動作を確認した。",
    }
    if axis:
        review["checks"][axis] = value
    return review


def _call(arm, packet_id, source, plan, parsed, *, fail=None, wall=2.0):
    payload = scoring.decision_review_payload(source, plan)
    system = m46.REVIEW_SYSTEM if arm == "A" else scoring.DECISION_REVIEW_SYSTEM
    record = {
        "call_id": f"review_{arm}:{packet_id}", "arm": arm,
        "model": CONTRACT["model"], "attempted": True,
        "completed": True, "json_parse_success": True,
        "prompt_tokens": 100, "completion_tokens": 40,
        "wall_seconds": wall, "parsed": parsed,
        "payload_digest": m45.digest(payload),
        "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
        "options": {"temperature": 0, "seed": 20260829,
                    "num_ctx": 4096, "num_predict": 320},
    }
    if fail == "transport":
        record.update(completed=False, json_parse_success=False,
                      error_type="TimeoutError", error="fake timeout")
        record.pop("parsed")
    elif fail == "parse":
        record.update(json_parse_success=False, error_type="JSONDecodeError")
        record.pop("parsed")
    elif fail == "tokens":
        record["completion_tokens"] = 0
    return record


def _fake_run(tmp_path, monkeypatch, *, fail_at=None, fail_kind=None,
              uncertain_at=None, slow_at=None, wrong_source_at=None,
              transport_drift=False, prewarm_ok=True, accept_all_b=False):
    planned = runner._prepare_packets(CONTRACT, DATASET)
    monkeypatch.setattr(runner, "preflight", lambda *_: (CONTRACT, DATASET, planned))
    monkeypatch.setattr(runner.old_runner, "prewarm_model", lambda *_: {
        "model": CONTRACT["model"], "attempted": True,
        "completed": prewarm_ok, "wall_seconds": 1.0,
    })
    calls = []

    def send(arm, packet_id, source, plan):
        item = next(row for row in planned if row["packet_id"] == packet_id)
        assert item["source"] == source
        assert item["prior_score"]["selected_plan"] == plan
        calls.append((packet_id, arm))
        axis = item["expected_failed_axis"] if item["gold_label"] == "invalid" else None
        parsed = (_old_review(source, plan, axis) if arm == "A" else
                  _new_review(source, plan, None if accept_all_b else axis,
                              value="uncertain" if packet_id == uncertain_at else "fail"))
        if (packet_id, arm) == wrong_source_at:
            parsed["source_span"] = "wrong source"
        result = _call(arm, packet_id, source, plan, parsed,
                       fail=fail_kind if (packet_id, arm) == fail_at else None,
                       wall=21.0 if (packet_id, arm) == slow_at else 2.0)
        if transport_drift and arm == "B":
            result["options"]["seed"] += 1
        return result

    def old_send(*, stage, case_id, source, plan, contract):
        assert stage == "review"
        assert contract == runner._legacy_review_contract(CONTRACT)
        return send("A", case_id, source, plan)

    def new_send(*, case_id, source, plan, contract):
        assert contract == CONTRACT
        return send("B", case_id, source, plan)

    monkeypatch.setattr(runner.old_runner, "model_json_call", old_send)
    monkeypatch.setattr(runner, "model_json_call_b", new_send)
    output = tmp_path / "decision_result.json"
    return runner.run(output_path=output), output, calls


def test_preflight_packets_exact_10_eligible_1_guard_and_fixed_order():
    planned = runner._prepare_packets(CONTRACT, DATASET)
    assert [item["packet_id"] for item in planned] == CONTRACT["dataset"]["packet_order"]
    assert len(planned) == 11
    assert sum(item["prior_score"]["deterministic_eligible"] for item in planned) == 10
    assert sum(item["gold_label"] == "valid" for item in planned[:-1]) == 3
    assert sum(item["gold_label"] == "invalid" for item in planned[:-1]) == 7
    assert planned[-1]["category"] == "guard_control"
    assert planned[-1]["prior_score"]["guard_violations"] == [
        "nonprogress_or_unknown_mechanism"]
    altered = deepcopy(DATASET)
    altered["challenge_packets"][0]["expected_deterministic_guard"]["review_eligible"] = False
    with pytest.raises(RuntimeError, match="guard/source mismatch"):
        runner._prepare_packets(CONTRACT, altered)
    wrong_gates = deepcopy(CONTRACT)
    wrong_gates["preregistered_gates"]["deterministic_eligible_packet_count"] = 9
    with pytest.raises(RuntimeError, match="preflight gate mismatch"):
        runner._prepare_packets(wrong_gates, DATASET)


def test_A_and_B_transport_identical_payload_options_different_interface(monkeypatch):
    item = runner._prepare_packets(CONTRACT, DATASET)[0]
    source, plan = item["source"], item["prior_score"]["selected_plan"]
    bodies = []

    def fake_post(url, body, timeout):
        bodies.append((url, body, timeout))
        review = (_old_review(source, plan) if len(bodies) == 1 else
                  _new_review(source, plan))
        return {"message": {"content": json.dumps(review, ensure_ascii=False)},
                "prompt_eval_count": 100, "eval_count": 40}

    monkeypatch.setattr(runner.old_runner, "_post_json", fake_post)
    old = runner.old_runner.model_json_call(
        stage="review", case_id=item["packet_id"], source=source, plan=plan,
        contract=runner._legacy_review_contract(CONTRACT))
    new = runner.model_json_call_b(
        case_id=item["packet_id"], source=source, plan=plan, contract=CONTRACT)
    assert len(bodies) == 2
    a_url, a_body, a_timeout = bodies[0]
    b_url, b_body, b_timeout = bodies[1]
    assert a_url == b_url == runner.old_runner.OLLAMA_CHAT
    assert a_timeout == b_timeout == 30
    assert a_body["messages"][1] == b_body["messages"][1]
    payload = json.loads(a_body["messages"][1]["content"])
    assert set(payload) == {"sources", "plan", "planned_payload_digest"}
    assert payload["sources"] == [source]
    assert payload["plan"] == {key: value for key, value in plan.items()
                               if key != "progress_mechanism"}
    assert payload["planned_payload_digest"] == m45.digest({"sources": [source], "plan": plan})
    assert all(key not in a_body["messages"][1]["content"]
               for key in ("gold", "category", "expected_failed_axis"))
    assert a_body["options"] == b_body["options"] == {
        "temperature": 0, "seed": 20260829, "num_ctx": 4096, "num_predict": 320}
    assert a_body["model"] == b_body["model"] == CONTRACT["model"]
    assert a_body["stream"] is b_body["stream"] is False
    assert a_body["think"] is b_body["think"] is False
    assert a_body["keep_alive"] == b_body["keep_alive"] == "30m"
    assert a_body["messages"][0]["content"] == m46.REVIEW_SYSTEM
    assert b_body["messages"][0]["content"] == scoring.DECISION_REVIEW_SYSTEM
    assert a_body["format"] == m46.review_schema([source], plan)
    assert b_body["format"] == scoring.decision_review_schema(source, plan)
    assert old["payload_digest"] == new["payload_digest"]
    assert old["options"] == new["options"]


def test_twenty_one_shot_calls_alternate_order_guard_zero_and_absolute_gates(tmp_path, monkeypatch):
    evidence, output, calls = _fake_run(tmp_path, monkeypatch)
    expected = []
    for index, packet_id in enumerate(CONTRACT["dataset"]["packet_order"][:-1]):
        expected.extend((packet_id, arm) for arm in runner.ARM_ORDER[index % 2])
    assert calls == expected
    assert len(calls) == len(set(calls)) == 20
    assert evidence["rows"][-1]["calls"] == {"A": None, "B": None}
    assert evidence["rows"][-1]["call_started"] == {"A": False, "B": False}
    assert evidence["status"] == "bounded_component_pass_not_product_eligible"
    assert evidence["generation_scored_calls"] == evidence["retry_count"] == 0
    assert evidence["product_eligible"] is False
    summary = evidence["summary"]
    assert summary["common_failed_gates"] == []
    assert summary["metrics"]["review_scored_call_count"] == 20
    assert summary["metrics"]["guard_control_both_arms_blocked_count"] == 1
    for arm in ("A", "B"):
        assert summary["arms"][arm]["failed_gates"] == []
        assert summary["arms"][arm]["metrics"]["completed_parseable_token_count"] == 10
        assert summary["arms"][arm]["metrics"]["source_exact_count"] == 10
        assert summary["arms"][arm]["metrics"]["valid_retained_count"] == 3
        assert summary["arms"][arm]["metrics"]["invalid_false_action_count"] == 0
        reason_metric = ("mapped_expected_axis_false_check_count" if arm == "A"
                         else "explicit_expected_axis_fail_count")
        assert summary["arms"][arm]["metrics"][reason_metric] == 7
        assert summary["arms"][arm]["metrics"]["prompt_tokens"] == 1000
        assert summary["arms"][arm]["metrics"]["completion_tokens"] == 400
        assert summary["arms"][arm]["metrics"]["reviewer_only_median_wall_seconds"] == 2.0
    assert summary["paired"]["B_only_decision_correct_count"] == 0
    assert summary["paired"]["A_only_decision_correct_count"] == 0
    assert summary["paired"]["reason_metrics_not_semantically_symmetric"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == evidence["status"]
    with pytest.raises(FileExistsError):
        runner.run(output_path=output)


@pytest.mark.parametrize("kind", ["transport", "parse", "tokens"])
def test_call_failure_preserves_partial_without_retry_or_resume(tmp_path, monkeypatch, kind):
    first = CONTRACT["dataset"]["packet_order"][0]
    evidence, output, calls = _fake_run(
        tmp_path, monkeypatch, fail_at=(first, "B"), fail_kind=kind)
    assert calls == [(first, "A"), (first, "B")]
    assert evidence["status"] == "review_call_failed_partial_no_resume"
    assert len(evidence["rows"]) == 1
    assert evidence["rows"][0]["call_started"] == {"A": True, "B": True}
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["rows"][0]["calls"]["A"]["completed"] is True
    assert saved["status"] == evidence["status"]
    with pytest.raises(FileExistsError):
        runner.run(output_path=output)


def test_prewarm_failure_has_zero_scored_calls(tmp_path, monkeypatch):
    evidence, output, calls = _fake_run(tmp_path, monkeypatch, prewarm_ok=False)
    assert calls == []
    assert evidence["status"] == "prewarm_failed_no_scored_calls"
    assert evidence["rows"] == []
    assert json.loads(output.read_text(encoding="utf-8"))["prewarm"]["completed"] is False


def test_uncertain_and_source_failure_continue_all_calls_but_fail_gates(tmp_path, monkeypatch):
    invalid = CONTRACT["dataset"]["packet_order"][1]
    evidence, _, calls = _fake_run(tmp_path, monkeypatch, uncertain_at=invalid)
    assert len(calls) == 20
    assert evidence["status"] == "review_required_component_fail"
    assert evidence["summary"]["arms"]["B"]["metrics"]["invalid_false_action_count"] == 0
    assert evidence["summary"]["arms"]["B"]["metrics"]["explicit_expected_axis_fail_count"] == 6
    assert "explicit_expected_axis_fail_count" in evidence["summary"]["arms"]["B"]["failed_gates"]
    assert evidence["summary"]["paired"]["A_only_decision_correct_count"] == 0
    source_failure, _, source_calls = _fake_run(
        tmp_path / "other", monkeypatch, wrong_source_at=(invalid, "B"))
    assert len(source_calls) == 20
    assert source_failure["summary"]["arms"]["B"]["metrics"]["source_exact_count"] == 9
    assert "source_exact_count" in source_failure["summary"]["arms"]["B"]["failed_gates"]


def test_false_actions_are_not_hidden_by_reason_or_speed(tmp_path, monkeypatch):
    evidence, _, calls = _fake_run(tmp_path, monkeypatch, accept_all_b=True)
    assert len(calls) == 20
    assert evidence["status"] == "review_required_component_fail"
    b = evidence["summary"]["arms"]["B"]
    assert b["metrics"]["invalid_false_action_count"] == 7
    assert b["metrics"]["explicit_expected_axis_fail_count"] == 0
    assert "invalid_false_action_count" in b["failed_gates"]
    assert evidence["summary"]["paired"]["A_only_decision_correct_count"] == 7


def test_scoring_exception_keeps_both_completed_calls(tmp_path, monkeypatch):
    original = scoring.score_packet

    def broken(source, batch, old, new, gold, axis=None):
        if old is not None and new is not None:
            raise RuntimeError("fake scoring failure")
        return original(source, batch, old, new, gold, axis)

    monkeypatch.setattr(scoring, "score_packet", broken)
    evidence, output, calls = _fake_run(tmp_path, monkeypatch)
    assert len(calls) == 2
    assert evidence["status"] == "review_packet_failed_partial_no_resume"
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["rows"][0]["calls"]["A"]["completed"] is True
    assert saved["rows"][0]["calls"]["B"]["completed"] is True
    assert saved["rows"][0]["packet_error_type"] == "RuntimeError"


def test_cost_and_transport_drift_fail_without_product_eligibility(tmp_path, monkeypatch):
    first = CONTRACT["dataset"]["packet_order"][0]
    slow, _, calls = _fake_run(tmp_path, monkeypatch, slow_at=(first, "B"))
    assert len(calls) == 20
    assert slow["summary"]["arms"]["B"]["metrics"]["reviewer_only_max_wall_seconds"] == 21.0
    assert "reviewer_only_max_wall_seconds" in slow["summary"]["arms"]["B"]["failed_gates"]
    assert slow["summary"]["product_eligible"] is False
    drift, output, drift_calls = _fake_run(
        tmp_path / "other", monkeypatch, transport_drift=True)
    assert drift_calls == [(first, "A"), (first, "B")]
    assert drift["status"] == "paired_transport_changed_partial_no_resume"
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == drift["status"]


def test_stale_hash_and_freeze_rejected_before_network(tmp_path, monkeypatch):
    bad = deepcopy(CONTRACT)
    bad["hash_bound_dependencies"]["prospective_decision_scorer"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="Frozen hash mismatch"):
        runner._validate_hash_bindings(bad)
    real_require = runner._require_frozen_git
    real_hash = runner._hash
    real_exists = Path.exists
    # The formal one-shot result now exists.  Isolate the stale-hash probe from
    # the production no-overwrite gate, which must still reject that result.
    with monkeypatch.context() as stale:
        stale.setattr(runner, "_require_frozen_git", lambda: None)
        stale.setattr(runner, "_hash", lambda path: (
            "0" * 64 if path.name == "p4_m46_decision_interface_scoring.py" else real_hash(path)))
        stale.setattr(Path, "exists", lambda path: (
            False if path == runner.RESULT_PATH else real_exists(path)))
        stale.setattr(runner.old_runner, "_get_json", lambda *_: pytest.fail("network"))
        with pytest.raises(RuntimeError, match="Frozen hash mismatch"):
            runner.preflight()
    monkeypatch.setattr(runner, "_require_frozen_git", real_require)
    monkeypatch.setattr(runner, "_git", lambda *_: "wrong-sha")
    monkeypatch.setattr(runner, "_tracked_clean", lambda *_: pytest.fail("tracked check too early"))
    with pytest.raises(RuntimeError, match="Freeze commit does not resolve exactly"):
        runner._require_frozen_git()
    monkeypatch.setattr(runner.old_runner, "_get_json", lambda *_: pytest.fail("network"))
    with pytest.raises(RuntimeError, match="fixed contract and result paths"):
        runner.preflight(output_path=tmp_path / "wrong.json")
    result = tmp_path / "existing.json"
    result.write_text("already exists", encoding="utf-8")
    monkeypatch.setattr(runner, "RESULT_PATH", result)
    with pytest.raises(RuntimeError, match="cannot be overwritten or resumed"):
        runner.preflight(output_path=result)
