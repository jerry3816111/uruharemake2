"""Read-only extraction of isolated Safari results; never changes old scores.

Visible observations are separately collected through Safari accessibility/UI.
This script checks the logged backend copies; it cannot prove UI observation.
"""
import argparse
import hashlib
import json
from pathlib import Path

from uruha_actionable_help_delivery_m45 import LABEL, OUTCOME_LABEL, digest
from uruha_memory_observatory import collect_cognitive_graph


def audit(log_path):
    rows = []
    user_sources = {}
    for line in Path(log_path).read_text().splitlines():
        row = json.loads(line)
        cognition = row.get("cognition_trace") or {}
        runtime = cognition.get("runtime_trace") or {}
        state = cognition.get("runtime_state") or {}
        logic = row.get("logic") or {}
        delivery = logic.get(LABEL) or {}
        cycle = runtime.get("cycle_index")
        user_sources[f"current:{cycle}"] = row["user_text"]
        user_sources[f"prior:{cycle}"] = row["user_text"]
        origins = (delivery.get("task_evidence_authorization_m45_1") or {}).get("allowed_origins") or []
        origin_checks = []
        for origin in origins:
            original = user_sources.get(origin["source_id"], "")
            span = original[origin["span_start"]:origin["span_start"] + origin["span_length"]]
            origin_checks.append(bool(original) and digest(original) == origin["source_digest"]
                                 and digest(span) == origin["span_digest"])
        history = state.get("recent_turn_traces") or []
        mirror = history[-1] if history else {}
        graph = collect_cognitive_graph({"logic": logic, **cognition})
        nodes = [n for n in graph["nodes"] if n.get("label") == LABEL]
        utterances = [n for n in runtime.get("blackboard") or [] if n.get("label") == "utterance"]
        final_utterance = (utterances[-1].get("payload") or {}).get("reply") if utterances else None
        decision = logic.get("desired_response_decision_m18") or {}
        feedback = state.get("last_adaptive_person_feedback") or runtime.get("adaptive_person_feedback_m18") or {}
        rows.append({"turn": row["turn_index"], "user": row["user_text"],
            "reply": row["assistant_reply"], "delivery": delivery,
            "outcome": logic.get(OUTCOME_LABEL),
            "task_source_origin_checks_m45_1": origin_checks,
            "policy": decision.get("selected", {}).get("policy_id"),
            "feedback": {k: feedback.get(k) for k in ("status", "reason", "previous_prediction_id",
                "previous_policy_id", "explicit_target_policy", "feedback_linked_to_previous_prediction",
                "policy_reliability_before", "policy_reliability_after", "atom_changes")},
            "m44": logic.get("executed_action_receipt_m44"),
            "latency": runtime.get("runtime_latency_m19"),
            "trace_checks": {"logic_runtime_equal": delivery == runtime.get(LABEL),
                "same_cycle_history_equal": runtime.get("cycle_index") == mirror.get("cycle_index") and delivery == mirror.get(LABEL),
                "one_delivery_node": len(nodes) == 1,
                "delivery_node_connected": len(nodes) == 1 and any(e["source"] == nodes[0]["id"] or e["target"] == nodes[0]["id"] for e in graph["edges"]),
                "final_digest_matches_reply": delivery.get("final_reply_digest") == digest(row["assistant_reply"]),
                "utterance_matches_reply": final_utterance == row["assistant_reply"]}})
    return {"schema": "m45_web_log_audit_v1", "rows": rows,
            "evidence_boundary": "Actual isolated Web log; UI observation and unblinded content verdicts are separate. Not human preference or holdout."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.log)
    if args.output:
        with open(args.output, "x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps([{k: r[k] for k in ("turn", "user", "reply", "trace_checks")}
                      | {"delivery_status": r["delivery"].get("status"), "outcome": r["outcome"]}
                      for r in result["rows"]], ensure_ascii=False, indent=2))
