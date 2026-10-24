"""Read-only handoff integrity check. No model, DB, network or artifact writes.

This only authorizes offline P3-A implementation, never a comparison run.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = "research/p3_gpt5_handoff_lock_v1.json"


def design_errors(design):
    errors = []

    def require(ok, reason):
        if not ok:
            errors.append(reason)

    require(design.get("schema") == "uruha_p3_product_comparison_design_v1", "schema")
    require(design.get("conditions") == [
        "full_history_direct", "full_history_deliberate", "product_system"
    ], "strong_baselines")
    release = design.get("implementation_release", {})
    require(release.get("stage") == "P3-A", "offline_stage")
    require(release.get("real_generation_authorized") is False, "no_generation_release")
    require(release.get("review_before_first_real_run") is True, "review_gate")
    history = design.get("common_history", {})
    require(history.get("include_all_prior_sessions") is True, "full_history")
    require(history.get("truncate_or_summarize") is False, "no_hidden_truncation")
    require(history.get("current_system_reply_visible_to_baselines") is False, "no_current_reply_leak")
    require(history.get("cross_case_state_shared") is False, "case_isolation")
    model = design.get("model", {})
    require(model.get("generation_model") == "qwen2.5:7b", "same_generation_model")
    require(model.get("all_generation_routes_same_model") is True, "all_model_routes")
    require(model.get("transport_retries") == 0, "no_retries")
    require(model.get("remote_paid_calls_allowed") is False, "no_paid_calls")
    limits = design.get("budget", {}).get("per_condition_turn", {})
    require(limits == {
        "aggregate_prompt_tokens_max": 32768,
        "aggregate_completion_tokens_max": 768,
        "wall_seconds_max": 60,
    }, "shared_budget")
    require(design.get("gates", {}).get("quality_proxy", {}).get(
        "must_pass_against_both_baselines") is True, "no_baseline_cherry_pick")
    require(design.get("grading", {}).get("human_preference_claim_allowed") is False,
            "proxy_is_not_human_evidence")
    require(design.get("data", {}).get("source_manifest_present") is False,
            "data_not_yet_released")
    return errors


def verify(root=ROOT):
    errors = []
    checked = 0
    try:
        lock = json.loads((root / LOCK).read_text(encoding="utf-8"))
        for name, expected in lock["files_sha256"].items():
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()):
                errors.append(f"outside_root:{name}")
                continue
            if not path.is_file():
                errors.append(f"missing:{name}")
                continue
            checked += 1
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append(f"digest_mismatch:{name}")
        design = json.loads((root / "configs/p3_product_comparison_v1.json").read_text(encoding="utf-8"))
        errors.extend(design_errors(design))
        accounting = json.loads((root / design["accounting_freeze"]).read_text(encoding="utf-8"))
        for name, expected in accounting["source_sha256"].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
                errors.append(f"accounting_source_changed:{name}")
        require_product = lock["product_commit"]
        if design["product_commit"] != require_product:
            errors.append("product_commit_binding")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"invalid_handoff:{type(exc).__name__}")
    return {
        "status": "ready_for_offline_implementation" if not errors else "not_ready",
        "checked_files": checked,
        "errors": errors,
        "real_generation_authorized": False,
        "data_freeze_complete": False,
        "human_or_safari_acceptance": False,
        "app_model_or_goal_changed": False,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not result["errors"] else 1)
