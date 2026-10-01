"""Local development generation, separate from frozen typed evaluation/Web QA."""
import argparse
import json
from pathlib import Path
from uruha_actionable_help_delivery_m45 import (
    deliver_action, source_packet, _native_json, PLAN_SCHEMA,
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--linked", action="store_true")
    args = parser.parse_args()
    records = []
    cases = ["I need to organize the notes for my study group. Give me one practical step.",
             "讀書會的通知寫不下去了，給我一個現在可以做的步驟。",
             "Give me one practical step I can take now."]
    if args.linked:
        cases = ["You misunderstood; give me one practical step I can take now."]
    # Reserve variants are never loaded by this development probe.
    for source in cases:
        calls = []
        def observed(system, payload, schema, deadline, metrics):
            response = _native_json(system, payload, schema, deadline, metrics)
            calls.append({"stage": "proposal" if schema is PLAN_SCHEMA else "review", "response": response})
            return response
        sources = source_packet(source, {"recent_turns": [{"user": "The report has stalled again."}]},
            {"status": "contradicted", "explicit_target_policy": "solve_regulation",
             "feedback_linked_to_previous_prediction": True}, 2) if args.linked else source_packet(source, turn_index=1)
        result, trace = deliver_action(source, "じゃあ、まず一個だけ決めよ。",
            {"desired_response_policy_m18": "solve_regulation", "correction_aware_surface_m20": {"authoritative": bool(args.linked)}}, sources, observed)
        records.append({"source": source, "reply": result, "trace": trace, "calls": calls})
        print(json.dumps(records[-1], ensure_ascii=False), flush=True)
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump({"evidence": "nonfresh development generation, not Web or holdout", "records": records},
                  handle, ensure_ascii=False, indent=2)
