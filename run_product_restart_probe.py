"""Isolated product-stack restart probe, never a formal human/holdout test.

--backend contract uses the existing fake memory/left/right fixture with the real
runtime and product overlays. --backend local uses the real local runtime with
an empty temporary Chroma store and its current model settings. Neither is Safari.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


def probe(backend, report_path, scenario="restart"):
    with tempfile.TemporaryDirectory(prefix="uruha-product-restart-") as temp:
        root = Path(temp)
        os.environ["URUHA_MEMORY_DB_PATH"] = str(root / "memory")
        os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"] = str(root / "adaptive.json")
        os.environ["URUHA_WEB_PREWARM_BRAIN"] = "0"
        os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"] = "false"
        os.environ["GRADIO_ANALYTICS_ENABLED"] = "false"
        # Redirect the Web module's existing log constants before import.
        import project_paths
        project_paths.WEB_LOG_DIR = str(root / "web_logs")
        project_paths.WEB_CONVERSATION_LOG_JSONL_PATH = str(root / "web_logs/turns.jsonl")
        project_paths.WEB_CONVERSATION_LOG_TXT_PATH = str(root / "web_logs/turns.txt")
        import uruha_web_ui_product as product
        import uruha_adaptive_person_model as adaptive
        from uruha_brain_mac import UruhaBrainV4_Mac
        from uruha_compute_ledger import ComputeLedger
        from uruha_memory_observatory import collect_cognitive_graph
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        result = {"schema": "uruha_product_restart_probe_v2", "backend": backend, "scenario": scenario,
                  "evidence_kind": "developer_authored_isolated_runtime_probe",
                  "mock_memory_and_models": backend == "contract", "safari_verified": False,
                  "human_rating_count": 0, "formal_holdout_used": False,
                  "formal_database_used": False, "rightbrain_transformer_loaded": False,
                  "p1_added_model_calls": 0, "turns": [], "status": "started"}
        result["planner_budget_seconds"] = product._brain.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if report_path.exists() or report_path.with_suffix(".html").exists():
            raise FileExistsError("Use a new output path; prior runs are retained")

        def save():
            report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        ledger = ComputeLedger()
        graphs = []
        snapshots = []

        def new_brain():
            if backend == "local":
                return UruhaBrainV4_Mac(load_right_brain_model=False, compute_ledger=ledger)
            brain = _IsolatedContractBrain()
            brain.adaptive_person_model_path = str(root / "adaptive.json")
            model, load_trace = adaptive.load_model(brain.adaptive_person_model_path)
            brain.runtime.set_adaptive_person_model(model, load_trace)
            return brain

        # Same text and reset cycle 1 are intentional: they reproduce the ID
        # collision. Additional language turns are exploratory, not a holdout.
        sessions = [
            ["方法はいらない。ただ聞いてほしい。", "そう、それでいい。"],
            ["方法はいらない。ただ聞いてほしい。", "不是要方法，今天也只是想讓你聽我說。",
             "No advice right now. Just listen.", "うん、聞いてくれてありがとう。"],
        ]
        if scenario == "controls":
            # New development controls, authored after the P2 gate implementation.
            # Each session resets the brain, but shares the isolated adaptive
            # store. Never presented as independent blind holdout evidence.
            sessions = [
                ["考えとく。", "また今度にしようかな。"],
                ["今日はただ聞いてほしい。", "謝謝。不過現在請幫我想一個做法。"],
                ["今日はただ聞いてほしい。", "違う。今日は一人にしてほしい。"],
                ["今日はただ聞いてほしい。", "「ありがとう」は誰の言葉だった？"],
                ["那個。"],
            ]
        elif scenario == "planner_diagnostic":
            sessions = sessions[:1]
        started = time.perf_counter()
        try:
            for session_index, turns in enumerate(sessions, 1):
                brain = new_brain()
                for user_text in turns:
                    turn_started = time.perf_counter()
                    turn = brain.run_turn_debug(user_text)
                    trace = turn.get("runtime_trace") or {}
                    model = deepcopy(brain.runtime.adaptive_person_model)
                    graph = collect_cognitive_graph(turn)
                    decision = trace.get("desired_response_decision_m18") or {}
                    entry = {"session": session_index, "cycle": brain.runtime.cycle_index,
                             "input": user_text, "reply": turn.get("reply"),
                             "prediction_id": decision.get("prediction_id"),
                             "policy": (decision.get("selected") or {}).get("policy_id"),
                             "sequence": model.get("prediction_event_sequence_p1"),
                             "pending_id": (model.get("pending_prediction") or {}).get("prediction_id"),
                             "feedback_status": (trace.get("adaptive_person_feedback_m18") or {}).get("status"),
                             "active_validation_strategy": (turn.get("logic") or {}).get("active_validation_strategy_v2_13"),
                             "planner_trace": (turn.get("logic") or {}).get("bounded_slow_path_m21"),
                             "ledger": model.get("outcome_calibration_ledger_m27"),
                             "persistence": brain.runtime.last_adaptive_person_persistence.get("status"),
                             "graph_labels": [node["label"] for node in graph["nodes"]],
                             "graph_contains_current_prediction": decision.get("prediction_id", "__missing__") in json.dumps(graph),
                             "latency_seconds": round(time.perf_counter() - turn_started, 6)}
                    result["turns"].append(entry)
                    print(json.dumps({key: entry[key] for key in ("session", "cycle", "reply", "prediction_id", "sequence", "feedback_status")}, ensure_ascii=False), flush=True)
                    graphs.append(product._base.render_memory_observatory(turn))
                    snapshots.append(model)
                    save()
            result["checks"] = {
                "persistence_all_saved": all(row["persistence"] == "saved" for row in result["turns"]),
                "graph_current_id_all_present": all(row["graph_contains_current_prediction"] for row in result["turns"] if row["prediction_id"]),
                "no_prediction_turns_leave_no_pending": all(row["pending_id"] is None for row in result["turns"] if not row["prediction_id"]),
                "all_graphs_include_calibration": all("causal_outcome_calibration_ledger_m27" in row["graph_labels"] for row in result["turns"]),
            }
            if scenario == "restart":
                old_row = snapshots[1]["outcome_calibration_ledger_m27"][0]
                restarted_rows = snapshots[2]["outcome_calibration_ledger_m27"]
                result["checks"].update({
                    "restart_cycle_reset": result["turns"][0]["cycle"] == result["turns"][2]["cycle"],
                    "same_input_different_prediction": result["turns"][0]["prediction_id"] != result["turns"][2]["prediction_id"],
                    "old_completed_row_preserved_at_restart": old_row in restarted_rows,
                    "old_completed_row_preserved_at_end": old_row in snapshots[-1]["outcome_calibration_ledger_m27"],
                })
            result["prediction_graph_turn_count"] = sum(bool(row["prediction_id"]) for row in result["turns"])
            result["no_prediction_turn_count"] = len(result["turns"]) - result["prediction_graph_turn_count"]
            result["status"] = (("bounded_identity_pass" if scenario == "restart" else "bounded_trace_pass")
                                if all(result["checks"].values()) else "structural_check_failed")
            # This is the existing product graph from actual probe turns. It is
            # an offline artifact, never represented as a browser screenshot.
            from html import escape
            body = "".join(f"<section><h2>Session {row['session']} · Turn {row['cycle']}</h2><p>{escape(row['input'])}</p><p>{escape(str(row['reply']))}</p>{html}</section>" for row, html in zip(result["turns"], graphs))
            html = '<!doctype html><meta charset="utf-8"><title>Product runtime probe</title><p>Developer-authored runtime evidence. Browser visual acceptance pending.</p>' + body
            report_path.with_suffix(".html").write_text(html, encoding="utf-8")
            result["graph_html_sha256"] = hashlib.sha256(html.encode()).hexdigest()
        except BaseException as exc:
            result["status"] = "runtime_error"
            result["error"] = {"type": type(exc).__name__, "message": str(exc)[:600]}
            raise
        finally:
            result["elapsed_seconds"] = round(time.perf_counter() - started, 6)
            result["openai_compatible_call_ledger"] = ledger.snapshot()
            result["call_accounting_scope"] = "OpenAI-compatible calls only; native urllib calls, embeddings and uninstrumented inference may be absent"
            save()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("contract", "local"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scenario", choices=("restart", "controls", "planner_diagnostic"), default="restart")
    args = parser.parse_args()
    value = probe(args.backend, args.output, args.scenario)
    print(json.dumps({"status": value["status"], "checks": value.get("checks")}, ensure_ascii=False))
    raise SystemExit(0 if value["status"] in {"bounded_identity_pass", "bounded_trace_pass"} else 1)
