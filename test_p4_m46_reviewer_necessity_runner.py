"""Fake-transport tests for the one-shot M46 runner; no Ollama or Web calls."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

import run_p4_m46_reviewer_necessity as runner
import uruha_goal_progress_delivery_m46 as m46


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "configs/p4_m46_reviewer_necessity_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONTRACT["dataset"]["path"]).read_text(encoding="utf-8"))


def _fake_batch(source):
    return {
        "sid": source["id"], "span": source["text"],
        "goal": "資料を一つ整理する", "unknown": "詳しい内容は不明",
        "items": [
            {"mechanism": "structure_scaffold", "object": "見出し二つ", "verb": "書く",
             "effect": "見出しが二つできた状態", "stop": "二つ書いたら止める",
             "instruction": "まず見出し二つだけ書いて、そこで止めよ。"},
            {"mechanism": "unknown", "object": "全体", "verb": "眺める",
             "effect": "全体を見ただけの状態", "stop": "一度見たら止める",
             "instruction": "まず全体を一度眺めて、そこで止めよ。"},
        ],
    }


def _fake_review(source, plan, reject=False):
    content = {key: True for key in m46.CONTENT_CHECKS}
    surface = {key: True for key in m46.SURFACE_CHECKS}
    if reject:
        content["goal_matches_source"] = False
    return {"source_id": source["id"], "source_span": source["text"],
            "counterfactual_before_jp": "まだ整理されていない",
            "counterfactual_after_jp": "見出しが二つある",
            "observed_progress_mechanism": plan["progress_mechanism"],
            "content_checks": content, "surface_checks": surface}


def _call(stage, case_id, parsed, *, completed=True, tokens=True):
    row = {"call_id": f"{stage}:{case_id}", "stage": stage,
           "attempted": True, "completed": completed,
           "json_parse_success": completed, "wall_seconds": 2.0}
    if completed:
        row.update(prompt_tokens=100 if tokens else 0,
                   completion_tokens=40 if tokens else 0, parsed=parsed)
    else:
        row.update(error_type="TimeoutError", error="fake timeout")
    return row


def _prewarm(model, keep_alive):
    assert model == CONTRACT["model"]
    assert keep_alive == CONTRACT["controlled_constants"]["keep_alive"]
    return {"model": model, "attempted": True, "completed": True, "wall_seconds": 1.0}


def _run_fake_generation(tmp_path, monkeypatch, *, fail_at=None):
    calls = []
    monkeypatch.setattr(runner, "preflight_generate", lambda *_: (CONTRACT, DATASET))
    monkeypatch.setattr(runner, "prewarm_model", _prewarm)

    def send(*, stage, case_id, source, plan, contract):
        calls.append((stage, case_id))
        assert stage == "generate" and plan is None and contract is CONTRACT
        return _call(stage, case_id, _fake_batch(source), completed=case_id != fail_at)

    monkeypatch.setattr(runner, "model_json_call", send)
    output = tmp_path / "generated.json"
    return runner.run_generate(output_path=output), output, calls


def _gold_for(generated, tmp_path):
    labels = []
    for index, row in enumerate(generated["rows"]):
        labels.append({"case_id": row["case_id"],
                       "selected_plan_digest": row["selected_plan_digest"],
                       "label": "valid" if index < 3 else "invalid",
                       "reason": "Independent fake rubric label, not an observed reviewer decision."})
    return {"schema": "uruha_p4_m46_generated_gold_v1", "generation_sha256": "fake",
            "labels": labels}, {row["case_id"]: row for row in labels}


def test_generation_six_once_no_gold_no_review_and_never_overwrites(tmp_path, monkeypatch):
    evidence, output, calls = _run_fake_generation(tmp_path, monkeypatch)
    assert evidence["status"] == "complete_unannotated"
    assert len(calls) == 6 and len(set(calls)) == 6
    assert all(stage == "generate" for stage, _ in calls)
    assert evidence["review_calls"] == 0 and evidence["gold_labels_present"] is False
    assert all("gold_label" not in row for row in evidence["rows"])
    assert all(isinstance(row["batch"], dict) and row["selected_plan_digest"] for row in evidence["rows"])
    assert evidence["production_database_access"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "complete_unannotated"
    with pytest.raises(FileExistsError):
        runner.run_generate(output_path=output)


def test_generation_failure_checkpoints_partial_and_does_not_retry(tmp_path, monkeypatch):
    failure_id = DATASET["generation_cases"][1]["case_id"]
    evidence, output, calls = _run_fake_generation(tmp_path, monkeypatch, fail_at=failure_id)
    assert evidence["status"] == "generation_call_failed_partial_no_resume"
    assert len(calls) == 2 and len(evidence["rows"]) == 2
    assert evidence["rows"][-1]["call"]["error_type"] == "TimeoutError"
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == evidence["status"]
    with pytest.raises(FileExistsError):
        runner.run_generate(output_path=output)


def test_failed_prewarm_sends_zero_scored_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "preflight_generate", lambda *_: (CONTRACT, DATASET))
    monkeypatch.setattr(runner, "prewarm_model", lambda *_: {"attempted": True, "completed": False})
    monkeypatch.setattr(runner, "model_json_call", lambda **_: pytest.fail("model call after failed prewarm"))
    evidence = runner.run_generate(output_path=tmp_path / "prewarm.json")
    assert evidence["status"] == "prewarm_failed_no_scored_calls"
    assert evidence["rows"] == []


def test_review_uses_same_generated_packet_and_only_one_call_per_eligible_case(tmp_path, monkeypatch):
    generated, generated_path, _ = _run_fake_generation(tmp_path, monkeypatch)
    gold, labels = _gold_for(generated, tmp_path)
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    calls = []
    monkeypatch.setattr(runner, "preflight_review", lambda *_: (CONTRACT, DATASET, generated, gold, labels))
    monkeypatch.setattr(runner, "prewarm_model", _prewarm)
    def review_send(*, stage, case_id, source, plan, contract):
        assert stage == "review" and contract is CONTRACT
        calls.append((case_id, deepcopy(plan)))
        invalid = case_id in {row["case_id"] for row in generated["rows"][3:]} or case_id in {
            packet["packet_id"] for packet in DATASET["challenge_packets"] if packet["gold"]["accept"] is False
        }
        return _call(stage, case_id, _fake_review(source, plan, reject=invalid))
    monkeypatch.setattr(runner, "model_json_call", review_send)
    output = tmp_path / "review.json"
    evidence = runner.run_review(generated_path=generated_path, gold_path=gold_path,
                                 output_path=output)
    assert len(evidence["rows"]) == 15
    assert len(calls) <= 14 and len({case_id for case_id, _ in calls}) == len(calls)
    assert "p4_m46_fixture_guard_block_001" not in {case_id for case_id, _ in calls}
    for row in evidence["rows"]:
        if row["stratum"] == "generated_m51":
            original = next(item for item in generated["rows"] if item["case_id"] == row["case_id"])
            assert row["score"]["selected_plan_digest"] == original["selected_plan_digest"]
        assert row["score"]["arms"]["A_model_review"]["would_deliver"] in {True, False}
        assert row["score"]["arms"]["B_deterministic_only"]["would_deliver"] in {True, False}
    assert evidence["summary"]["metrics"]["review_scored_call_count"] == len(calls)
    assert evidence["production_database_access"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == evidence["status"]
    with pytest.raises(FileExistsError):
        runner.run_review(generated_path=generated_path, gold_path=gold_path, output_path=output)


def test_review_failure_is_partial_no_retry(tmp_path, monkeypatch):
    generated, generated_path, _ = _run_fake_generation(tmp_path, monkeypatch)
    gold, labels = _gold_for(generated, tmp_path)
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    monkeypatch.setattr(runner, "preflight_review", lambda *_: (CONTRACT, DATASET, generated, gold, labels))
    monkeypatch.setattr(runner, "prewarm_model", _prewarm)
    calls = []
    def timeout(*, stage, case_id, source, plan, contract):
        calls.append(case_id)
        return _call(stage, case_id, None, completed=False)
    monkeypatch.setattr(runner, "model_json_call", timeout)
    evidence = runner.run_review(generated_path=generated_path, gold_path=gold_path,
                                 output_path=tmp_path / "review_fail.json")
    assert evidence["status"] == "review_call_failed_partial_no_resume"
    assert len(calls) == 1 and len(evidence["rows"]) == 1


def test_review_scoring_error_preserves_completed_call_without_retry(tmp_path, monkeypatch):
    generated, generated_path, _ = _run_fake_generation(tmp_path, monkeypatch)
    gold, labels = _gold_for(generated, tmp_path)
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    monkeypatch.setattr(runner, "preflight_review", lambda *_: (CONTRACT, DATASET, generated, gold, labels))
    monkeypatch.setattr(runner, "prewarm_model", _prewarm)
    real_score = runner.scoring.score_packet
    calls = []

    def score(source, batch, review, label):
        if review is not None:
            raise RuntimeError("fake evaluator failure")
        return real_score(source, batch, review, label)

    def review_send(*, stage, case_id, source, plan, contract):
        calls.append(case_id)
        return _call(stage, case_id, _fake_review(source, plan))

    monkeypatch.setattr(runner.scoring, "score_packet", score)
    monkeypatch.setattr(runner, "model_json_call", review_send)
    output = tmp_path / "review_scoring_fail.json"
    evidence = runner.run_review(generated_path=generated_path, gold_path=gold_path,
                                 output_path=output)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["status"] == saved["status"] == "review_packet_failed_partial_no_resume"
    assert len(calls) == 1 and len(saved["rows"]) == 1
    assert saved["rows"][0]["review_call"]["completed"] is True
    assert saved["rows"][0]["packet_error_type"] == "RuntimeError"


def test_gold_requires_all_six_digest_bound_labels_before_review(tmp_path, monkeypatch):
    generated, path, _ = _run_fake_generation(tmp_path, monkeypatch)
    gold, _ = _gold_for(generated, tmp_path)
    monkeypatch.setattr(runner, "GENERATED_PATH", path)
    gold["generation_sha256"] = runner._hash(path)
    assert len(runner._validate_gold(gold, generated)) == 6
    missing = deepcopy(gold)
    missing["labels"].pop()
    with pytest.raises(RuntimeError, match="all six"):
        runner._validate_gold(missing, generated)
    wrong_hash = deepcopy(gold)
    wrong_hash["generation_sha256"] = "not-the-generated-artifact"
    with pytest.raises(RuntimeError, match="bind"):
        runner._validate_gold(wrong_hash, generated)
    wrong_plan = deepcopy(gold)
    wrong_plan["labels"][0]["selected_plan_digest"] = "other-plan"
    with pytest.raises(RuntimeError, match="another selected plan"):
        runner._validate_gold(wrong_plan, generated)


def test_preflight_rejects_nonfixed_paths_before_network(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_get_json", lambda *_: pytest.fail("network before path guard"))
    with pytest.raises(RuntimeError, match="fixed contract and output"):
        runner.preflight_generate(output_path=tmp_path / "other.json")
    with pytest.raises(RuntimeError, match="fixed generated and gold"):
        runner.preflight_review(generated_path=tmp_path / "other.json")
    with pytest.raises(RuntimeError, match="artifacts are required"):
        runner.preflight_review()


def test_review_payload_hides_plan_mechanism_and_uses_frozen_options(monkeypatch):
    source = DATASET["challenge_packets"][0]["source"]
    plan = runner.scoring.score_packet(
        source, DATASET["challenge_packets"][0]["batch"], None, "valid",
    )["selected_plan"]
    captured = {}
    def fake_post(url, body, timeout):
        captured.update(url=url, body=body, timeout=timeout)
        review = _fake_review(source, plan)
        return {"message": {"content": json.dumps(review, ensure_ascii=False)},
                "prompt_eval_count": 100, "eval_count": 50}
    monkeypatch.setattr(runner, "_post_json", fake_post)
    call = runner.model_json_call(stage="review", case_id="fixture", source=source,
                                  plan=plan, contract=CONTRACT)
    payload = json.loads(captured["body"]["messages"][1]["content"])
    assert "progress_mechanism" not in payload["plan"]
    assert captured["body"]["options"]["seed"] == CONTRACT["controlled_constants"]["m46_seed"]
    assert captured["body"]["options"]["num_predict"] == CONTRACT["controlled_constants"]["m46_num_predict"]
    assert captured["url"] == runner.OLLAMA_CHAT
    assert call["completed"] is True and call["json_parse_success"] is True
