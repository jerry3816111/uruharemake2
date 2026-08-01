#!/usr/bin/env python3
"""Revalidate the V89 observe-only shadow against the current merged main."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

from build_rightbrain_forbidden_projection_live_evidence import (
    _contains_raw_bearing_key,
    build_report,
)
from project_paths import WEB_CONVERSATION_LOG_JSONL_PATH
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = (
    ROOT / "configs/rightbrain_forbidden_projection_shadow_v90_preregistration.json"
)
V89_PREREGISTRATION = (
    ROOT / "configs/rightbrain_forbidden_projection_shadow_v89_preregistration.json"
)
V88_RESULT = ROOT / "reports/rightbrain_forbidden_projection_v88.json"
WEB_UI = ROOT / "uruha_web_ui.py"
DEFAULT_REPORT_JSON = (
    ROOT / "reports/rightbrain_forbidden_projection_shadow_v90_revalidation.json"
)
DEFAULT_REPORT_MD = (
    ROOT / "reports/rightbrain_forbidden_projection_shadow_v90_revalidation.md"
)
EXPERIMENT_ID = "rightbrain_forbidden_projection_shadow_v90_current_main_revalidation"
PASS_DECISION = "authorize_current_main_observe_only_live_shadow_collection_only"
FAIL_DECISION = "repair_or_retire_shadow_before_collecting_new_live_evidence"

EMPTY_MEMORY = {
    "wisdom": "",
    "episodes": "",
    "profile": "",
    "recent_dialogue": "",
    "working_memory_summary": "",
    "working_memory_items": [],
    "recent_turns": [],
    "profile_structured": {},
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def conflict_logic():
    return {
        "jp_summary": "以前の食べ物の話に答える。",
        "core_message_jp": "ポテトなら普通にあり。少しもらう。",
        "memory_use_expected": True,
        "memory_speakability": "explicit_ok",
        "memory_anchor": {
            "kind": "context",
            "jp_anchor": "ポテトの話",
            "terms": ["ポテト"],
        },
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["ポテトなら普通にあり", "少しもらう"],
            "grounding_terms": ["ポテト"],
            "forbidden_repetition": {"recent_openings": ["ポテトなら"]},
        },
        "must_avoid": ["ポテトなら", "危険な指示"],
        "model_surface_candidate_trace": {
            "accepted": [],
            "initial_rejected": [
                {
                    "candidate_index": 0,
                    "raw_candidate": "ポテトなら普通にあり。少しもらう。",
                    "candidate": "ポテトなら普通にあり。少しもらう。",
                    "rejection_reasons": ["must_avoid_violation"],
                }
            ],
            "repairs": [],
        },
    }


def speak_probe_logic():
    return {
        "scene": "support",
        "intent": "friend_no_reply",
        "surface_act": "validate_then_hold",
        "dialogue_act": "emotional_containment",
        "jp_summary": "既読のまま返事がないことを心配している。",
        "core_message_jp": (
            "既読のまま返事がなくて不安でも、自分のせいと決めつけず少し待つ"
        ),
        "grounding": {
            "reply_self_blame": True,
            "reply_context": "direct_reply",
            "reply_signal": "read_receipt",
        },
        "constraints": {"max_chars": 80, "sentence_count": 2},
        "human_speech_plan": {
            "dialogue_act": "emotional_containment",
            "content_units": [
                "既読の文脈を拾う",
                "理由は未確定",
                "自責を止める",
                "少し待つ",
            ],
            "speech_moves": [
                {"role": "context_acknowledgement", "signal": "read_receipt"},
                {"role": "uncertainty_tolerance", "target": "reason_for_silence"},
                {"role": "self_blame_boundary", "target": "premature_self_blame"},
                {"role": "next_action", "action": "wait_before_followup"},
            ],
            "grounding_terms": [],
            "style_operators": ["warm"],
            "forbidden_repetition": {"recent_openings": ["既読のまま"]},
        },
        "must_avoid": ["既読のまま"],
    }


def run_visible_reply_noninterference_probe():
    rightbrain_on = RightBrain(load_model=False)
    rightbrain_off = RightBrain(load_model=False)
    rightbrain_off.forbidden_projection_shadow_enabled = False

    def install_synthetic_candidate_trace(rightbrain):
        def generate_candidates(
            *, user_input, logic_data, memory_data, current_psyche, max_chars
        ):
            del memory_data, current_psyche
            candidate = "既読のままでも理由はまだ分からない。自分のせいにせず少し待て。"
            logic_data["model_surface_candidate_trace"] = {
                "accepted": [],
                "initial_rejected": [
                    {
                        "candidate_index": 0,
                        "raw_candidate": candidate,
                        "candidate": candidate,
                        "rejection_reasons": ["must_avoid_violation"],
                    }
                ],
                "repairs": [],
            }
            rightbrain._record_forbidden_projection_shadow(
                logic_data, user_input, max_chars
            )
            return []

        rightbrain._generate_model_surface_candidates = generate_candidates

    install_synthetic_candidate_trace(rightbrain_on)
    install_synthetic_candidate_trace(rightbrain_off)
    logic_on = speak_probe_logic()
    logic_off = copy.deepcopy(logic_on)
    user_input = "他已讀但沒回，是不是我講錯話？"
    psyche = {"mood": 0, "trust": 50}
    reply_on = rightbrain_on.speak(
        user_input, logic_on, copy.deepcopy(EMPTY_MEMORY), psyche
    )
    reply_off = rightbrain_off.speak(
        user_input, logic_off, copy.deepcopy(EMPTY_MEMORY), psyche
    )
    reply_sha256 = hashlib.sha256(reply_on.encode("utf-8")).hexdigest()
    shadow_on = logic_on.get("model_surface_forbidden_projection_shadow") or {}
    shadow_off = logic_off.get("model_surface_forbidden_projection_shadow") or {}
    return {
        "visible_replies_equal": reply_on == reply_off,
        "enabled_trace_is_active": shadow_on.get("status") == "active",
        "disabled_trace_is_explicit": shadow_off.get("status") == "disabled",
        "enabled_trace_hash_matches_reply": shadow_on.get("visible_reply_sha256")
        == reply_sha256,
        "disabled_trace_hash_matches_reply": shadow_off.get("visible_reply_sha256")
        == hashlib.sha256(reply_off.encode("utf-8")).hexdigest(),
        "real_model_load_count": 0,
        "real_model_call_count": 0,
    }


def web_logger_contract(path=WEB_UI):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_append_conversation_log"
        ),
        None,
    )
    if function is None:
        return {
            "append_function_found": False,
            "record_keeps_logic": False,
            "jsonl_write_found": False,
        }
    record_keeps_logic = False
    jsonl_write_found = False
    for node in ast.walk(function):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if not isinstance(key, ast.Constant) or key.value != "logic":
                    continue
                if not isinstance(value, ast.Call):
                    continue
                function_node = value.func
                record_keeps_logic = (
                    isinstance(function_node, ast.Attribute)
                    and function_node.attr == "get"
                    and isinstance(function_node.value, ast.Name)
                    and function_node.value.id == "result"
                    and bool(value.args)
                    and isinstance(value.args[0], ast.Constant)
                    and value.args[0].value == "logic"
                )
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "write" or not node.args:
            continue
        argument = node.args[0]
        if isinstance(argument, ast.BinOp) and isinstance(argument.left, ast.Call):
            dump_call = argument.left
            jsonl_write_found = (
                isinstance(dump_call.func, ast.Attribute)
                and isinstance(dump_call.func.value, ast.Name)
                and dump_call.func.value.id == "json"
                and dump_call.func.attr == "dumps"
            )
    return {
        "append_function_found": True,
        "record_keeps_logic": record_keeps_logic,
        "jsonl_write_found": jsonl_write_found,
    }


def build_revalidation_report():
    preregistration = load_json(PREREGISTRATION)
    v89_preregistration = load_json(V89_PREREGISTRATION)
    v88_result = load_json(V88_RESULT)
    rightbrain = RightBrain(load_model=False)
    before = {
        "history": copy.deepcopy(rightbrain.history),
        "reply_variant_counts": copy.deepcopy(rightbrain.reply_variant_counts),
        "intent_variant_counts": copy.deepcopy(rightbrain.intent_variant_counts),
        "normalized_reply_counts": copy.deepcopy(rightbrain.normalized_reply_counts),
        "intent_normalized_counts": copy.deepcopy(
            rightbrain.intent_normalized_counts
        ),
        "projection": rightbrain.forbidden_conflict_projection_enabled,
    }
    logic = conflict_logic()
    shadow = rightbrain._record_forbidden_projection_shadow(
        logic, "ポテトはどう？", 40
    )
    after = {
        "history": rightbrain.history,
        "reply_variant_counts": rightbrain.reply_variant_counts,
        "intent_variant_counts": rightbrain.intent_variant_counts,
        "normalized_reply_counts": rightbrain.normalized_reply_counts,
        "intent_normalized_counts": rightbrain.intent_normalized_counts,
        "projection": rightbrain.forbidden_conflict_projection_enabled,
    }
    legacy_report = build_report(
        [{"session_id": "legacy", "turn_index": 1, "logic": {}}],
        source_meta={"invalid_line_count": 0},
    )
    logger = web_logger_contract()
    noninterference = run_visible_reply_noninterference_probe()
    expected_revalidation_contract = {
        "model_load_allowed": False,
        "model_call_count_exact": 0,
        "runtime_file_change_allowed": False,
        "shadow_enabled_by_default": True,
        "production_projection_enabled_by_default": False,
        "visible_reply_change_count_exact": 0,
        "extra_model_call_count_exact": 0,
        "raw_candidate_or_marker_text_in_shadow_allowed": False,
        "web_logger_must_persist_logic_shadow": True,
        "legacy_rows_count_as_v89_shadow": False,
        "old_web_log_reuse_as_current_live_result": False,
    }
    expected_decision_policy = {
        "pass": PASS_DECISION,
        "fail": FAIL_DECISION,
        "limited_activation_review": False,
        "projection_runtime_enable": False,
        "production_default_enable": False,
        "training_data": False,
        "persona_fidelity_claim": False,
    }
    dependency_checks = {
        "v88_result_hash_matches": sha256_file(V88_RESULT)
        == preregistration["dependencies"]["v88_result"]["sha256"],
        "v88_shadow_authorization_matches": v88_result.get("decision")
        == preregistration["dependencies"]["v88_result"]["required_decision"],
        "v89_preregistration_hash_matches": sha256_file(V89_PREREGISTRATION)
        == preregistration["dependencies"]["v89_preregistration"]["sha256"],
        "v89_evidence_boundary_preserved": v89_preregistration.get(
            "evidence_boundary"
        )
        == (
            "V89 measures live prevalence and counterfactual gate outcomes using "
            "already-generated candidates. It does not generate treatment replies, "
            "change user-visible output, enable production projection, or measure "
            "public-persona fidelity."
        ),
    }
    runtime_checks = {
        "shadow_enabled_by_default": rightbrain.forbidden_projection_shadow_enabled
        is True,
        "production_projection_disabled_by_default": before["projection"] is False,
        "synthetic_conflict_is_active": shadow.get("status") == "active",
        "synthetic_conflict_recovers_candidate": shadow.get(
            "recovered_candidate_count"
        )
        == 1,
        "shadow_does_not_change_visible_reply": shadow.get(
            "changes_user_visible_reply"
        )
        is False,
        "speak_visible_reply_is_identical_with_shadow_on_or_off": all(
            value is True
            for key, value in noninterference.items()
            if key not in {"real_model_load_count", "real_model_call_count"}
        ),
        "shadow_adds_zero_model_calls": shadow.get("extra_model_call_count") == 0,
        "shadow_contains_no_raw_bearing_key": not _contains_raw_bearing_key(shadow),
        "shadow_restores_runtime_state": before == after,
        "legacy_row_is_not_v89_evidence": legacy_report["summary"][
            "shadow_trace_count"
        ]
        == 0,
        "web_logger_persists_logic": all(logger.values()),
    }
    scope_checks = {
        "preregistration_schema_matches": preregistration.get("schema")
        == "uruha_rightbrain_forbidden_projection_shadow_revalidation_preregistration_v90",
        "experiment_id_matches": preregistration.get("experiment_id")
        == EXPERIMENT_ID,
        "revalidation_contract_matches": preregistration.get(
            "revalidation_contract"
        )
        == expected_revalidation_contract,
        "decision_policy_matches": preregistration.get("decision_policy")
        == expected_decision_policy,
        "no_existing_current_clone_web_log_reused": not Path(
            WEB_CONVERSATION_LOG_JSONL_PATH
        ).exists(),
        "model_call_count_is_zero": shadow.get("extra_model_call_count") == 0,
    }
    checks = {**dependency_checks, **runtime_checks, **scope_checks}
    passed = all(checks.values())
    return {
        "schema": "uruha_rightbrain_forbidden_projection_shadow_revalidation_v90",
        "experiment_id": EXPERIMENT_ID,
        "construction_passed": passed,
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "summary": {
            "check_count": len(checks),
            "check_pass_count": sum(checks.values()),
            "model_load_count": 0,
            "model_call_count": 0,
            "visible_reply_change_count": 0,
            "new_live_shadow_trace_count": 0,
            "legacy_log_record_count_used_as_v89_evidence": 0,
            "persona_score_count": 0,
        },
        "checks": checks,
        "web_logger_contract": logger,
        "visible_reply_noninterference_probe": noninterference,
        "current_source_bindings": {
            "production_brain": {
                "path": "uruha_brain_mac.py",
                "sha256": sha256_file(ROOT / "uruha_brain_mac.py"),
            },
            "path_registry": {
                "path": "project_paths.py",
                "sha256": sha256_file(ROOT / "project_paths.py"),
            },
            "web_log_writer": {
                "path": "uruha_web_ui.py",
                "sha256": sha256_file(WEB_UI),
            },
            "live_evidence_builder": {
                "path": "build_rightbrain_forbidden_projection_live_evidence.py",
                "sha256": sha256_file(
                    ROOT / "build_rightbrain_forbidden_projection_live_evidence.py"
                ),
            },
        },
        "authorizations": {
            "current_main_observe_only_live_shadow_collection": passed,
            "limited_activation_review": False,
            "projection_runtime_enable": False,
            "production_default_enable": False,
            "training_data": False,
            "persona_fidelity_claim": False,
        },
        "next_required_evidence": (
            "Only newly generated web conversations on this hash-bound main may count. "
            "The frozen V89 thresholds still require at least 20 active conflict turns, "
            "5 sessions and 5 recovered turns with every safety gate passing."
        ),
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def build_markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# V90：現行 Main 的 RightBrain Shadow 重驗",
            "",
            f"- 建構通過：`{report['construction_passed']}` ({summary['check_pass_count']}/{summary['check_count']})",
            f"- 決策：`{report['decision']}`",
            "",
            "| 本輪實際做了什麼 | 數量 |",
            "|---|---:|",
            f"| 載入模型 | {summary['model_load_count']} |",
            f"| 模型呼叫 | {summary['model_call_count']} |",
            f"| 改變可見回覆 | {summary['visible_reply_change_count']} |",
            f"| 新 live shadow trace | {summary['new_live_shadow_trace_count']} |",
            f"| 舊日誌冒充新證據 | {summary['legacy_log_record_count_used_as_v89_evidence']} |",
            "",
            "通過只表示現行版本可以安全開始收集新 trace；目前仍沒有 live 效果數據，也沒有啟用修正。",
            "",
            report["evidence_boundary"],
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default=DEFAULT_REPORT_JSON)
    parser.add_argument("--output-md", default=DEFAULT_REPORT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    report = build_revalidation_report()
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(args.output_md).write_text(build_markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "construction_passed": report["construction_passed"],
                "checks": f"{report['summary']['check_pass_count']}/{report['summary']['check_count']}",
                "decision": report["decision"],
            },
            ensure_ascii=False,
        )
    )
    if args.require_pass and not report["construction_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
