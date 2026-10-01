"""Fake-transport tests only; no Ollama, scored model, or Web call."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

import run_p4_m46_fixed_challenge_discrimination as runner
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "configs/p4_m46_fixed_challenge_discrimination_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONTRACT["dataset"]["path"]).read_text(encoding="utf-8"))


def _review(source, plan, category, *, relevant=True):
    content = {key: True for key in m46.CONTENT_CHECKS}
    surface = {key: True for key in m46.SURFACE_CHECKS}
    if category in CONTRACT["invalid_category_relevant_false_checks"]:
        path = (CONTRACT["invalid_category_relevant_false_checks"][category][0]
                if relevant else "surface_checks.casual_japanese")
        group, field = path.split(".")
        (content if group == "content_checks" else surface)[field] = False
    return {
        "source_id": source["id"], "source_span": source["text"],
        "counterfactual_before_jp": "作業がまだ終わっていない",
        "counterfactual_after_jp": "一つの作業が終わった",
        "observed_progress_mechanism": plan["progress_mechanism"],
        "content_checks": content, "surface_checks": surface,
    }


def _call(case_id, parsed, *, completed=True, wall=2.0, tokens=True):
    row = {"call_id": f"review:{case_id}", "stage": "review", "attempted": True,
           "completed": completed, "json_parse_success": completed,
           "wall_seconds": wall}
    if completed:
        row.update(prompt_tokens=100 if tokens else 0,
                   completion_tokens=40 if tokens else 0, parsed=parsed)
    else:
        row.update(error_type="TimeoutError", error="fake timeout")
    return row


def _fake_prewarm(model, keep_alive):
    assert model == CONTRACT["model"]
    assert keep_alive == CONTRACT["controlled_constants"]["keep_alive"]
    return {"model": model, "attempted": True, "completed": True, "wall_seconds": 1.0}


def _fake_run(tmp_path, monkeypatch, *, fail_at=None, slow_at=None, relevant=True,
              accept_all=False):
    planned = runner._prepare_packets(CONTRACT, DATASET)
    monkeypatch.setattr(runner, "preflight", lambda *_: (CONTRACT, DATASET, planned))
    monkeypatch.setattr(runner.old_runner, "prewarm_model", _fake_prewarm)
    calls = []

    def send(*, stage, case_id, source, plan, contract):
        assert stage == "review"
        assert contract == runner._legacy_review_contract(CONTRACT)
        item = next(row for row in planned if row["packet_id"] == case_id)
        assert item["source"] == source
        assert item["prior_score"]["selected_plan"] == plan
        calls.append(case_id)
        if case_id == fail_at:
            return _call(case_id, None, completed=False)
        category = "valid" if accept_all else item["category"]
        return _call(case_id, _review(source, plan, category, relevant=relevant),
                     wall=21.0 if case_id == slow_at else 2.0)

    monkeypatch.setattr(runner.old_runner, "model_json_call", send)
    output = tmp_path / "fixed_result.json"
    return runner.run(output_path=output), output, calls


def test_packet_preflight_is_eight_eligible_and_one_no_call_guard():
    planned = runner._prepare_packets(CONTRACT, DATASET)
    assert [row["packet_id"] for row in planned] == CONTRACT["dataset"]["packet_order"]
    assert len(planned) == 9
    assert sum(row["prior_score"]["deterministic_eligible"] for row in planned) == 8
    assert planned[-1]["category"] == "guard_block"
    assert planned[-1]["prior_score"]["deterministic_eligible"] is False
    assert sum(row["prior_score"]["arms"]["B_deterministic_only"]["false_action"]
               for row in planned) == 5
    altered = deepcopy(DATASET)
    altered["challenge_packets"][0]["expected_deterministic_guard"]["arm_b_would_allow"] = False
    with pytest.raises(RuntimeError, match="guard/source mismatch"):
        runner._prepare_packets(CONTRACT, altered)


def test_adapter_changes_only_seed_cap_names_and_outbound_payload(monkeypatch):
    adapter = runner._legacy_review_contract(CONTRACT)
    expected = deepcopy(CONTRACT)
    expected["controlled_constants"]["m46_seed"] = CONTRACT["controlled_constants"]["seed"]
    expected["controlled_constants"]["m46_num_predict"] = CONTRACT["controlled_constants"]["num_predict"]
    assert adapter == expected
    assert CONTRACT["controlled_constants"].get("m46_seed") is None
    assert CONTRACT["controlled_constants"].get("m46_num_predict") is None
    item = runner._prepare_packets(CONTRACT, DATASET)[0]
    source, plan = item["source"], item["prior_score"]["selected_plan"]
    captured = {}

    def fake_post(url, body, timeout):
        captured.update(url=url, body=body, timeout=timeout)
        return {"message": {"content": json.dumps(_review(source, plan, "valid"), ensure_ascii=False)},
                "prompt_eval_count": 100, "eval_count": 40}

    monkeypatch.setattr(runner.old_runner, "_post_json", fake_post)
    call = runner.old_runner.model_json_call(
        stage="review", case_id=item["packet_id"], source=source, plan=plan,
        contract=adapter)
    body = captured["body"]
    payload = json.loads(body["messages"][1]["content"])
    assert captured["url"] == runner.old_runner.OLLAMA_CHAT
    assert captured["timeout"] == CONTRACT["execution"]["reviewer_timeout_seconds"] == 30
    assert body["messages"][0] == {"role": "system", "content": m46.REVIEW_SYSTEM}
    assert body["model"] == CONTRACT["model"]
    assert body["format"] == m46.review_schema([source], plan)
    assert body["options"] == {"temperature": 0, "seed": 20260829,
                               "num_ctx": 4096, "num_predict": 320}
    assert body["stream"] is False and body["think"] is False
    assert body["keep_alive"] == "30m"
    assert set(payload) == {"sources", "plan", "planned_payload_digest"}
    assert payload["sources"] == [source]
    assert payload["plan"] == {key: value for key, value in plan.items()
                               if key != "progress_mechanism"}
    assert payload["planned_payload_digest"] == m45.digest({"sources": [source], "plan": plan})
    assert "gold" not in body["messages"][1]["content"]
    assert "category" not in body["messages"][1]["content"]
    assert call["completed"] is True and call["json_parse_success"] is True
    assert runner.old_runner._tokens_complete(call)


def test_eight_one_shot_reviews_quality_pass_b_not_product_and_no_resume(tmp_path, monkeypatch):
    evidence, output, calls = _fake_run(tmp_path, monkeypatch)
    assert calls == CONTRACT["dataset"]["packet_order"][:-1]
    assert len(calls) == len(set(calls)) == 8
    assert evidence["status"] == "bounded_fixed_discrimination_pass_not_product_eligible"
    assert evidence["generation_scored_calls"] == 0
    assert len(evidence["rows"]) == 9
    assert evidence["rows"][-1]["review_call"] is None
    assert evidence["rows"][-1]["review_call_started"] is False
    metrics = evidence["summary"]["metrics"]
    assert metrics["selector_parity_all_packets"] is True
    assert metrics["source_and_selected_plan_identity_both_arms"] is True
    assert metrics["review_completed_json_and_tokens_count"] == 8
    assert metrics["review_source_identity_exact_count"] == 8
    assert metrics["A_valid_retained_count"] == 3
    assert metrics["A_invalid_false_action_count"] == 0
    assert metrics["A_category_relevant_false_check_count"] == 5
    assert metrics["B_valid_retained_count"] == 3
    assert metrics["B_invalid_false_action_count"] == 5
    assert metrics["reviewer_only_max_wall_seconds"] == 2.0
    assert metrics["reviewer_only_median_wall_seconds"] == 2.0
    assert metrics["review_prompt_tokens"] == 800
    assert metrics["review_completion_tokens"] == 320
    assert evidence["summary"]["product_qualified"] is False
    assert evidence["summary"]["B_product_bypass_authorized"] is False
    assert evidence["production_database_access"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == evidence["status"]
    with pytest.raises(FileExistsError):
        runner.run(output_path=output)


def test_summary_rejects_selection_or_source_identity_drift(tmp_path, monkeypatch):
    evidence, _, _ = _fake_run(tmp_path, monkeypatch)
    rows = deepcopy(evidence["rows"])
    rows[0]["score"]["selection_guard_parity"] = False
    parity = runner.summarize(rows, CONTRACT)
    assert parity["metrics"]["selector_parity_all_packets"] is False
    assert "selector_parity_all_packets" in parity["failed_quality_gates"]
    rows = deepcopy(evidence["rows"])
    rows[0]["score"]["selected_plan_digest"] = "different-plan"
    identity = runner.summarize(rows, CONTRACT)
    assert identity["metrics"]["source_and_selected_plan_identity_both_arms"] is False
    assert "source_and_selected_plan_identity_both_arms" in identity["failed_quality_gates"]


def test_slow_review_is_quality_value_but_not_cost_or_product_pass(tmp_path, monkeypatch):
    slow = CONTRACT["dataset"]["packet_order"][2]
    evidence, _, calls = _fake_run(tmp_path, monkeypatch, slow_at=slow)
    assert len(calls) == 8
    assert evidence["status"] == "bounded_quality_value_cost_ineligible"
    assert evidence["summary"]["A_fixed_quality_pass"] is True
    assert evidence["summary"]["A_reviewer_only_within_20_seconds"] is False
    assert evidence["summary"]["product_qualified"] is False


def test_irrelevant_style_rejection_does_not_count_as_discrimination(tmp_path, monkeypatch):
    evidence, _, calls = _fake_run(tmp_path, monkeypatch, relevant=False)
    assert len(calls) == 8
    assert evidence["summary"]["metrics"]["A_valid_retained_count"] == 3
    assert evidence["summary"]["metrics"]["A_invalid_false_action_count"] == 0
    assert evidence["summary"]["metrics"]["A_category_relevant_false_check_count"] == 0
    assert "A_category_relevant_false_check_count" in evidence["summary"]["failed_quality_gates"]
    assert evidence["status"] == "fixed_discrimination_fail"


def test_wrong_acceptance_fails_even_if_review_is_fast(tmp_path, monkeypatch):
    evidence, _, calls = _fake_run(tmp_path, monkeypatch, accept_all=True)
    assert len(calls) == 8
    assert evidence["summary"]["metrics"]["A_invalid_false_action_count"] == 5
    assert evidence["status"] == "fixed_discrimination_fail"


def test_failed_prewarm_starts_no_scored_call(tmp_path, monkeypatch):
    planned = runner._prepare_packets(CONTRACT, DATASET)
    monkeypatch.setattr(runner, "preflight", lambda *_: (CONTRACT, DATASET, planned))
    monkeypatch.setattr(runner.old_runner, "prewarm_model", lambda *_: {"completed": False})
    monkeypatch.setattr(runner.old_runner, "model_json_call", lambda **_: pytest.fail("scored call"))
    evidence = runner.run(output_path=tmp_path / "prewarm_fail.json")
    assert evidence["status"] == "prewarm_failed_no_scored_calls"
    assert evidence["rows"] == []


def test_failed_review_preserves_partial_and_never_retries(tmp_path, monkeypatch):
    fail_at = CONTRACT["dataset"]["packet_order"][1]
    evidence, output, calls = _fake_run(tmp_path, monkeypatch, fail_at=fail_at)
    assert calls == CONTRACT["dataset"]["packet_order"][:2]
    assert evidence["status"] == "review_call_failed_partial_no_resume"
    assert len(evidence["rows"]) == 2
    assert evidence["rows"][-1]["review_call_started"] is True
    assert evidence["rows"][-1]["review_call"]["error_type"] == "TimeoutError"
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == evidence["status"]
    with pytest.raises(FileExistsError):
        runner.run(output_path=output)


def test_scoring_error_preserves_completed_call(tmp_path, monkeypatch):
    real_score = runner.scoring.score_packet
    planned = runner._prepare_packets(CONTRACT, DATASET)
    monkeypatch.setattr(runner, "preflight", lambda *_: (CONTRACT, DATASET, planned))
    monkeypatch.setattr(runner.old_runner, "prewarm_model", _fake_prewarm)
    first = planned[0]
    calls = []

    def send(*, stage, case_id, source, plan, contract):
        calls.append(case_id)
        return _call(case_id, _review(source, plan, "valid"))

    def broken_score(source, batch, review, gold):
        if review is not None:
            raise RuntimeError("fake scoring failure")
        return real_score(source, batch, review, gold)

    monkeypatch.setattr(runner.old_runner, "model_json_call", send)
    monkeypatch.setattr(runner.scoring, "score_packet", broken_score)
    output = tmp_path / "score_fail.json"
    evidence = runner.run(output_path=output)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert calls == [first["packet_id"]]
    assert evidence["status"] == saved["status"] == "review_packet_failed_partial_no_resume"
    assert saved["rows"][0]["review_call"]["completed"] is True
    assert saved["rows"][0]["packet_error_type"] == "RuntimeError"


def test_formal_preflight_checks_fixed_paths_before_network(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_get_json", lambda *_: pytest.fail("network before path guard"))
    with pytest.raises(RuntimeError, match="fixed contract and output paths"):
        runner.preflight(output_path=tmp_path / "wrong.json")
    with pytest.raises(RuntimeError, match="fixed contract and output paths"):
        runner.preflight(contract_path=tmp_path / "wrong.json")
