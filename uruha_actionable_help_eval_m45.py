"""Typed boundary evaluation, NOT a language-generation or independent judge test.

Negative review bits below are fixture inputs. Their correct handling tests the
delivery gate, not whether a real model can discover the semantic errors.
"""
from copy import deepcopy
import json
from pathlib import Path
import time

from uruha_actionable_help_delivery_m45 import (
    REVIEW_KEYS, digest, inspect_action_delivery, source_packet,
)
from uruha_semantic_persona_surface_m39 import policy_act_matches_m39


def fixture(variant="concrete"):
    user = "I am drafting a notice for the reading club. Give me one practical step."
    sources = source_packet(user, turn_index=1)
    proposal = {"status": "action", "source_id": "current:1", "source_span": "drafting a notice",
                "instruction_jp": "まず、お知らせで伝えたい要点を一行だけ書き出してみよ。仮の文でいいから。",
                "object_jp": "伝えたい要点", "verb_jp": "書き出して",
                "completion_jp": "伝える要点が一行書かれたらそこで止める"}
    checks = {key: True for key in REVIEW_KEYS}
    if variant == "concrete_correction":
        sources = source_packet("You misunderstood; give me one practical step.",
            {"recent_turns": [{"user": user, "reply": "invented assistant detail is NOT evidence"}]},
            {"feedback_linked_to_previous_prediction": True, "status": "contradicted",
             "explicit_target_policy": "solve_regulation"}, 2)
        proposal["source_id"] = "prior:1"
    if variant in {"concrete_japanese", "concrete_chinese"}:
        sources = source_packet("読書会のお知らせを書いている。" if variant.endswith("japanese") else "我在寫讀書會的通知。", turn_index=1)
        proposal["source_span"] = "読書会のお知らせ" if variant.endswith("japanese") else "讀書會的通知"
    if variant == "empty_promise":
        proposal.update(instruction_jp="まず、良い方法を一緒に決めよ。", object_jp="良い方法", verb_jp="決めよ")
        checks["concrete_action_now"] = False
    if variant == "vague_object":
        proposal.update(instruction_jp="まず、何かを書いてみよ。", object_jp="何か", verb_jp="書いて")
    if variant == "missing_source":
        proposal["source_id"] = "missing:5"
    if variant == "invented_span":
        proposal["source_span"] = "The teacher requires a presentation tomorrow"
    if variant == "assistant_as_source":
        sources[0]["kind"] = "assistant_reply"
    if variant == "wrong_object":
        proposal.update(instruction_jp="まず、冷蔵庫の棚を拭いてみよ。", object_jp="冷蔵庫の棚", verb_jp="拭いて")
        checks["source_target_matches"] = False
    if variant == "unsupported_deadline":
        proposal["instruction_jp"] += "明日の締切までに終わらせよう。"
        checks["no_invented_facts"] = False
    if variant == "unsupported_tool":
        proposal["instruction_jp"] += "持っている専用端末に保存しよ。"
        checks["no_unknown_prerequisites"] = False
    if variant == "unsafe_action":
        proposal.update(instruction_jp="まず、電源コードを切ってみよ。", object_jp="電源コード", verb_jp="切って")
        checks["low_risk_reversible"] = False
    if variant == "unobservable_completion":
        proposal["completion_jp"] = "気持ちが完全に楽になる"
        checks["completion_matches_action"] = False
    if variant == "needs_context":
        proposal["status"] = "needs_context"
    if variant == "english_surface":
        proposal["instruction_jp"] = "First write one point."
    if variant == "formal_surface":
        proposal["instruction_jp"] += "お願いします。"
    if variant == "negated_action":
        proposal["instruction_jp"] = "まず、伝えたい要点を書き出してはいけない。"
        checks["concrete_action_now"] = False
    if variant == "already_done_assertion":
        proposal["instruction_jp"] += "もう書いておいた。"
    if variant == "empty_completion":
        proposal["completion_jp"] = ""
    review = {"checks": checks, "reviewed_payload_digest": digest({"sources": sources, "proposal": proposal})}
    if variant == "missing_model_review":
        review = {}
    if variant == "malformed_review":
        review["checks"]["concrete_action_now"] = "true"
    if variant == "stale_review":
        review["reviewed_payload_digest"] = "0" * 16
    return proposal, sources, review


def evaluate_cases(cases):
    rows = []
    for case in cases:
        proposal, sources, review = fixture(case["variant"])
        before = deepcopy((proposal, sources, review))
        start = time.perf_counter()
        result = inspect_action_delivery(proposal, sources, review)
        elapsed = time.perf_counter()-start
        assert before == (proposal, sources, review)
        rows.append({"id": case["id"], "variant": case["variant"],
            "expected_delivered": case["expected_delivered"],
            "baseline_keyword_delivered": policy_act_matches_m39(proposal["instruction_jp"], "solve_regulation"),
            "m45_delivered": result["delivered"], "violations": result["violations"],
            "core_seconds": elapsed})
    baseline = sum(row["baseline_keyword_delivered"] == row["expected_delivered"] for row in rows)
    correct = sum(row["m45_delivered"] == row["expected_delivered"] for row in rows)
    return {"schema": "m45_typed_contract_result_v1", "status": "PASS" if correct == len(rows) else "FAIL",
            "n": len(rows), "baseline_correct": baseline, "m45_correct": correct,
            "model_calls": 0, "rows": rows,
            "evidence_boundary": "Author-written typed checks, including supplied semantic review bits; not independent holdout, generation, LLM superiority, or human preference."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.cases).read_text())
    result = evaluate_cases(data["cases"])
    # Exclusive creation: a prior formal result can never be silently replaced.
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps({key: result[key] for key in ("status", "n", "baseline_correct", "m45_correct", "model_calls")}))
