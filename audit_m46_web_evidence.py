"""Read-only M46 Web-log consistency audit.

This verifies stored copies and graph topology.  Safari visibility and whether
an action is genuinely useful remain separate observations.
"""
import argparse
import json
from pathlib import Path

import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
from uruha_memory_observatory import collect_cognitive_graph


def audit(log_path, session_id=None):
    rows, user_sources = [], {}
    for line in Path(log_path).read_text().splitlines():
        row = json.loads(line)
        if session_id and row.get("session_id") != session_id:
            continue
        cognition = row.get("cognition_trace") or {}
        runtime = cognition.get("runtime_trace") or {}
        state = cognition.get("runtime_state") or {}
        logic = row.get("logic") or {}
        delivery = logic.get(m45.LABEL) or {}
        progress = logic.get(m46.LABEL) or delivery.get(m46.LABEL)
        cycle = runtime.get("cycle_index")
        user_sources[f"current:{cycle}"] = row.get("user_text", "")
        user_sources[f"prior:{cycle}"] = row.get("user_text", "")
        origin_checks = []
        for origin in (delivery.get("task_evidence_authorization_m45_1") or {}).get("allowed_origins") or []:
            original = user_sources.get(origin.get("source_id"), "")
            span = original[origin.get("span_start", 0):origin.get("span_start", 0) + origin.get("span_length", 0)]
            origin_checks.append(bool(original) and m45.digest(original) == origin.get("source_digest")
                                 and m45.digest(span) == origin.get("span_digest"))
        history = state.get("recent_turn_traces") or []
        mirror = history[-1] if history else {}
        graph = collect_cognitive_graph({"logic": logic, **cognition})
        delivery_nodes = [node for node in graph["nodes"] if node.get("label") == m45.LABEL]
        progress_nodes = [node for node in graph["nodes"] if node.get("label") == m46.LABEL]
        utterances = [item for item in runtime.get("blackboard") or [] if item.get("label") == "utterance"]
        final_utterance = (utterances[-1].get("payload") or {}).get("reply") if utterances else None

        def connected(nodes):
            return len(nodes) == 1 and any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"]
                                           for edge in graph["edges"])

        progress_expected = isinstance(progress, dict)
        rows.append({
            "turn": row.get("turn_index"), "user": row.get("user_text"), "reply": row.get("assistant_reply"),
            "delivery_status": delivery.get("status"), "delivered": delivery.get("delivered"),
            "model_calls_completed": delivery.get("model_calls_completed", 0),
            "prompt_tokens": delivery.get("prompt_tokens", 0),
            "completion_tokens": delivery.get("completion_tokens", 0),
            "added_seconds": delivery.get("added_seconds", 0),
            "progress": progress, "outcome": logic.get(m45.OUTCOME_LABEL),
            "policy": (logic.get("desired_response_decision_m18") or {}).get("selected_policy")
                      or logic.get("desired_response_policy_m18"),
            "task_source_origin_checks_m45_1": origin_checks,
            "visible_reply_japanese": m45._japanese(row.get("assistant_reply", "")),
            "trace_checks": {
                "delivery_logic_runtime_equal": delivery == runtime.get(m45.LABEL),
                "delivery_same_cycle_history_equal": runtime.get("cycle_index") == mirror.get("cycle_index")
                                                       and delivery == mirror.get(m45.LABEL),
                "one_connected_delivery_node": connected(delivery_nodes),
                "progress_logic_runtime_equal": (not progress_expected) or progress == runtime.get(m46.LABEL),
                "progress_same_cycle_history_equal": (not progress_expected) or (
                    runtime.get("cycle_index") == mirror.get("cycle_index") and progress == mirror.get(m46.LABEL)),
                "progress_node_presence_matches": len(progress_nodes) == (1 if progress_expected else 0),
                "progress_node_connected_if_present": (not progress_expected) or connected(progress_nodes),
                "final_digest_matches_reply": delivery.get("final_reply_digest") == m45.digest(row.get("assistant_reply", "")),
                "utterance_matches_reply": final_utterance == row.get("assistant_reply"),
            },
        })
    calls = sum(int(row.get("model_calls_completed", 0) or 0) for row in rows)
    return {"schema": "m46_web_log_audit_v1", "session_id": session_id, "rows": rows,
            "summary": {"turn_count": len(rows), "delivered_count": sum(row["delivered"] is True for row in rows),
                        "all_trace_checks": all(all(item["trace_checks"].values()) for item in rows),
                        "all_origin_checks": all(all(item["task_source_origin_checks_m45_1"]) for item in rows),
                        "all_visible_replies_japanese": all(item["visible_reply_japanese"] for item in rows),
                        "model_calls_completed": calls,
                        "prompt_tokens": sum(int(row.get("prompt_tokens", 0) or 0) for row in rows),
                        "completion_tokens": sum(int(row.get("completion_tokens", 0) or 0) for row in rows),
                        "added_seconds": round(sum(float(row.get("added_seconds", 0) or 0) for row in rows), 5)},
            "evidence_boundary": "Backend consistency for an actual isolated Web session. Safari observation, usefulness judgment and independent human preference are separate."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--session")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.log, args.session)
    if args.output:
        with open(args.output, "x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
