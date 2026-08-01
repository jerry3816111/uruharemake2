#!/usr/bin/env python3
"""Build synthetic evidence for the structured persona surface boundary."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import torch

import public_persona_runtime_manifest_v1 as runtime_manifest
import uruha_compute_ledger as ledger_module
import uruha_persona_policy as persona_policy
from uruha_brain_mac import RightBrain, StructuredSurfaceUnavailableError


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "persona_surface_provider_migration_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/persona_surface_provider_migration_v1_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports/persona_surface_provider_migration_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/persona_surface_provider_migration_v1_construction.md"
PASS_DECISION = "authorize_fresh_local_model_target_vs_neutral_surface_pilot_only"
FAIL_DECISION = "repair_structured_surface_boundary_before_any_persona_pilot"


BASE_LOGIC = {
    "public_persona_context": "fatigue_update_with_near_term_plan",
    "scene": "support",
    "intent": "state_update",
    "jp_summary": "少し疲れていて、次の行動について話している。",
    "core_message_jp": "疲れている状態を伝え、次の行動を一つ示す",
    "required_marker_groups": [["疲れ"], ["次"]],
    "memory_anchor": {},
    "memory_speakability": "no_memory",
    "memory_use_expected": False,
    "constraints": {"max_chars": 64, "sentence_count": 2},
    "human_speech_plan": {
        "dialogue_act": "state_update_then_action_plan",
        "content_units": ["疲れている状態", "次の行動"],
        "speech_moves": [],
        "style_operators": ["short"],
        "target_length": "2_short_sentences",
        "turn_opening_potential": False,
        "prosody_hint": {},
        "forbidden_repetition": {"recent_openings": [], "avoid_generic_frames": []},
        "grounding_terms": ["疲れ", "次"],
    },
}
MEMORY = {
    "wisdom": "",
    "episodes": "",
    "profile": "",
    "recent_dialogue": "",
    "working_memory_summary": "",
    "working_memory_items": [],
    "recent_turns": [],
    "profile_structured": {},
}
PSYCHE = {"mood": -12, "trust": 58}
SUCCESS_OUTPUTS = {
    persona_policy.TARGET_PROVIDER: "疲れてるなら少し休め。次はあとでやればいい。<|im_end|>",
    persona_policy.NEUTRAL_PROVIDER: "疲れているなら少し休む。次はあとで進めればいい。<|im_end|>",
}
REJECTED_OUTPUT = "今は分からない。<|im_end|>"


class FakeTokenizer:
    eos_token_id = 0

    def __init__(self, output):
        self.output = output

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "synthetic prompt"

    def __call__(self, prompt, return_tensors="pt"):
        return {"input_ids": torch.tensor([[1, 2, 3]])}

    def decode(self, token_ids, skip_special_tokens=False):
        return self.output


class FakeModel:
    def generate(self, **kwargs):
        return torch.tensor([[1, 2, 3, 4, 5]])


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_text(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binding(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def build_structured_rightbrain(provider_id, output=None, compute_ledger=None):
    provider = persona_policy.build_persona_policy_provider(provider_id)
    rightbrain = RightBrain(
        load_model=False,
        persona_policy_provider=provider,
        compute_ledger=compute_ledger,
    )
    rightbrain.model_candidate_count = 1
    rightbrain.model_repair_enabled = False
    if output is not None:
        rightbrain.model = FakeModel()
        rightbrain.tokenizer = FakeTokenizer(output)
        rightbrain.device = "cpu"
    return rightbrain


def run_success_case(provider_id, compute_ledger):
    rightbrain = build_structured_rightbrain(
        provider_id,
        SUCCESS_OUTPUTS[provider_id],
        compute_ledger,
    )
    logic = copy.deepcopy(BASE_LOGIC)
    with compute_ledger.item_scope("surface_success_01", provider_id):
        reply = rightbrain.speak("今日は少し疲れた。", logic, copy.deepcopy(MEMORY), dict(PSYCHE))
    trace = logic["persona_surface_runtime_trace"]
    selection = logic["model_surface_selection"]
    return {
        "provider_id": provider_id,
        "status": trace["status"],
        "selected_source": selection["selected_source"],
        "reply_sha256": sha256_text(reply),
        "legacy_fixed_surface_access_count": rightbrain.legacy_fixed_surface_access_count,
        "legacy_family_entry_count": len(rightbrain.scene_fallbacks) + len(rightbrain.intent_reply_families),
        "legacy_fixed_surface_used": trace["legacy_fixed_surface_used"],
        "contains_raw_reply": False,
    }


def run_failed_closed_case(provider_id, failure_mode, compute_ledger=None):
    expected_reasons = {
        "model_not_loaded": "model_not_loaded",
        "hard_boundary": "hard_boundary_scene",
        "all_candidates_rejected": "all_model_candidates_rejected",
    }
    output = None
    logic = copy.deepcopy(BASE_LOGIC)
    if failure_mode == "hard_boundary":
        output = SUCCESS_OUTPUTS[provider_id]
        logic["scene"] = "boundary"
    elif failure_mode == "all_candidates_rejected":
        output = REJECTED_OUTPUT
    elif failure_mode != "model_not_loaded":
        raise ValueError(f"unknown failure mode: {failure_mode}")

    rightbrain = build_structured_rightbrain(provider_id, output, compute_ledger)
    caught = None
    try:
        scope = (
            compute_ledger.item_scope(f"surface_failure_{failure_mode}", provider_id)
            if compute_ledger is not None
            else None
        )
        if scope is None:
            rightbrain.speak("今日は少し疲れた。", logic, copy.deepcopy(MEMORY), dict(PSYCHE))
        else:
            with scope:
                rightbrain.speak("今日は少し疲れた。", logic, copy.deepcopy(MEMORY), dict(PSYCHE))
    except StructuredSurfaceUnavailableError as exc:
        caught = exc

    trace = logic.get("persona_surface_runtime_trace") or {}
    return {
        "provider_id": provider_id,
        "failure_mode": failure_mode,
        "typed_error_raised": caught is not None,
        "error_reason": caught.reason if caught is not None else None,
        "expected_error_reason": expected_reasons[failure_mode],
        "status": trace.get("status"),
        "legacy_fixed_surface_access_count": rightbrain.legacy_fixed_surface_access_count,
        "legacy_fixed_surface_used": trace.get("legacy_fixed_surface_used"),
        "reply_returned": caught is None,
    }


def legacy_logic_cases():
    return [
        copy.deepcopy(BASE_LOGIC),
        {
            "scene": "casual",
            "intent": "greeting",
            "jp_summary": "挨拶している。",
            "core_message_jp": "短く挨拶を返す",
            "constraints": {"max_chars": 32, "sentence_count": 1},
        },
        {
            "scene": "casual",
            "intent": "memory_uncertain",
            "jp_summary": "記憶が曖昧か確認している。",
            "core_message_jp": "曖昧な記憶を断定しない",
            "constraints": {"max_chars": 40, "sentence_count": 1},
        },
    ]


def run_legacy_pairs():
    provider = persona_policy.build_persona_policy_provider(persona_policy.LEGACY_PROVIDER)
    rows = []
    for index, logic in enumerate(legacy_logic_cases(), start=1):
        default = RightBrain(load_model=False)
        explicit = RightBrain(load_model=False, persona_policy_provider=provider)
        default_logic = copy.deepcopy(logic)
        explicit_logic = copy.deepcopy(logic)
        default_reply = default.speak(
            "今日は少し話そう。",
            default_logic,
            copy.deepcopy(MEMORY),
            dict(PSYCHE),
        )
        explicit_reply = explicit.speak(
            "今日は少し話そう。",
            explicit_logic,
            copy.deepcopy(MEMORY),
            dict(PSYCHE),
        )
        rows.append(
            {
                "case_id": f"legacy_runtime_pair_{index:02d}",
                "reply_equal": default_reply == explicit_reply,
                "default_reply_sha256": sha256_text(default_reply),
                "explicit_reply_sha256": sha256_text(explicit_reply),
            }
        )
    return rows


def direct_guard_check():
    rightbrain = build_structured_rightbrain(persona_policy.TARGET_PROVIDER)
    caught = None
    try:
        rightbrain._template_reply(copy.deepcopy(BASE_LOGIC))
    except StructuredSurfaceUnavailableError as exc:
        caught = exc
    return {
        "typed_error_raised": caught is not None,
        "error_reason": caught.reason if caught is not None else None,
        "guard_access_count": rightbrain.legacy_fixed_surface_access_count,
    }


def build_report(preregistration):
    target_ledger = ledger_module.ComputeLedger()
    neutral_ledger = ledger_module.ComputeLedger()
    ledgers = {
        persona_policy.TARGET_PROVIDER: target_ledger,
        persona_policy.NEUTRAL_PROVIDER: neutral_ledger,
    }
    success_rows = [
        run_success_case(provider_id, ledgers[provider_id])
        for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER)
    ]
    failed_rows = []
    for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER):
        failed_rows.append(run_failed_closed_case(provider_id, "model_not_loaded"))
        failed_rows.append(run_failed_closed_case(provider_id, "hard_boundary"))
        failed_rows.append(
            run_failed_closed_case(
                provider_id,
                "all_candidates_rejected",
                ledgers[provider_id],
            )
        )

    target_snapshot = target_ledger.snapshot()
    neutral_snapshot = neutral_ledger.snapshot()
    compute_parity = ledger_module.compare_compute_envelopes(target_snapshot, neutral_snapshot)
    legacy_rows = run_legacy_pairs()
    guard = direct_guard_check()
    fixed_literal_count = runtime_manifest.source_audit()["persona_crosscut_evidence"][
        "rightbrain_fixed_reply_literal_count"
    ]
    structured_access_count = sum(
        row["legacy_fixed_surface_access_count"] for row in [*success_rows, *failed_rows]
    )
    reachable_entries = sum(row["legacy_family_entry_count"] for row in success_rows)
    generation_call_count = target_snapshot["call_count"] + neutral_snapshot["call_count"]

    counts = {
        "structured_success_case_count": len(success_rows),
        "structured_failed_closed_case_count": len(failed_rows),
        "structured_legacy_fixed_surface_access_count": structured_access_count,
        "structured_reachable_fixed_family_entry_count": reachable_entries,
        "legacy_runtime_pair_count": len(legacy_rows),
        "legacy_runtime_mismatch_count": sum(not row["reply_equal"] for row in legacy_rows),
        "actual_local_generation_call_count": generation_call_count,
        "source_legacy_fixed_reply_literal_count": fixed_literal_count,
        "holdout_content_review_count": 0,
        "production_memory_write_count": 0,
        "persona_score_count": 0,
    }
    required = preregistration["construction_success_requires"]
    checks = {
        "structured_success_cases_selected_model": all(
            row["status"] == "model_reply_selected"
            and row["selected_source"] == "structured_model"
            and not row["legacy_fixed_surface_used"]
            for row in success_rows
        ),
        "structured_failures_are_typed_and_closed": all(
            row["typed_error_raised"]
            and not row["reply_returned"]
            and row["status"] == "failed_closed"
            and row["error_reason"] == row["expected_error_reason"]
            and not row["legacy_fixed_surface_used"]
            for row in failed_rows
        ),
        "legacy_direct_access_guarded": (
            guard["typed_error_raised"]
            and guard["error_reason"] == "legacy_fixed_surface_access:template_reply"
            and guard["guard_access_count"] == 1
        ),
        "compute_parity": compute_parity["parity_pass"],
        "compute_ledgers_contain_no_raw_text": (
            not target_snapshot["contains_raw_prompt_or_reply"]
            and not neutral_snapshot["contains_raw_prompt_or_reply"]
        ),
        "success_output_hashes_differ": success_rows[0]["reply_sha256"] != success_rows[1]["reply_sha256"],
        "source_legacy_literals_remain_visible": fixed_literal_count > 0,
    }
    count_requirements_pass = (
        counts["structured_success_case_count"] == required["structured_success_case_count_exact"]
        and counts["structured_failed_closed_case_count"] == required["structured_failed_closed_case_count_exact"]
        and counts["structured_legacy_fixed_surface_access_count"] == required["structured_legacy_fixed_surface_access_count_exact"]
        and counts["structured_reachable_fixed_family_entry_count"] == required["structured_reachable_fixed_family_entry_count_exact"]
        and counts["legacy_runtime_pair_count"] == required["legacy_runtime_pair_count_exact"]
        and counts["legacy_runtime_mismatch_count"] == required["legacy_runtime_mismatch_count_exact"]
        and counts["actual_local_generation_call_count"] == required["actual_local_generation_call_count_exact"]
        and counts["holdout_content_review_count"] == required["holdout_content_review_count_exact"]
        and counts["production_memory_write_count"] == required["production_memory_write_count_exact"]
        and counts["persona_score_count"] == required["persona_score_count_exact"]
        and compute_parity["parity_pass"] is required["compute_parity_pass"]
    )
    checks["all_preregistered_counts_match"] = count_requirements_pass
    passed = all(checks.values())

    return {
        "schema": "uruha_persona_surface_provider_migration_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "construction_passed" if passed else "construction_failed",
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "persona_policy_source": binding(ROOT / "uruha_persona_policy.py"),
            "brain_source": binding(ROOT / "uruha_brain_mac.py"),
        },
        "success_cases": success_rows,
        "failed_closed_cases": failed_rows,
        "legacy_runtime_pairs": legacy_rows,
        "direct_guard_check": guard,
        "compute_parity": compute_parity,
        "counts": counts,
        "checks": checks,
        "remaining_blockers": {
            "source_legacy_fixed_reply_literal_count": fixed_literal_count,
            "legacy_source_removed": False,
            "full_persona_disabled_control_ready": False,
            "fresh_actual_local_model_persona_evidence": False,
            "reason": (
                "The structured runtime no longer reaches legacy final-reply families, but shared speech planning, "
                "surface gates, and legacy source still contain target-shaped rules that must be audited before C2."
            ),
        },
        "authorizations": {
            "fresh_local_model_target_vs_neutral_surface_pilot": passed,
            "formal_persona_similarity_evaluation": False,
            "sealed_holdout_unsealing": False,
            "human_blind_rating": False,
            "model_training": False,
            "production_default_enablement": False,
            "public_persona_fidelity_claim": False,
            "private_person_copy_claim": False,
        },
    }


def render_markdown(report):
    counts = report["counts"]
    parity = report["compute_parity"]
    lines = [
        "# 人格表面生成 provider 遷移建構報告",
        "",
        "## 結果",
        "",
        f"**{report['status']}**",
        "",
        "目標人格與中性對照現在都必須走同一條本機模型生成路徑；固定台詞不能作為後備答案。",
        "",
        "| 檢查 | 結果 |",
        "|---|---:|",
        f"| structured 正常案例 | {counts['structured_success_case_count']}/2 |",
        f"| structured 失敗關閉案例 | {counts['structured_failed_closed_case_count']}/6 |",
        f"| structured 固定回覆存取 | {counts['structured_legacy_fixed_surface_access_count']} |",
        f"| structured 可達固定家族項目 | {counts['structured_reachable_fixed_family_entry_count']} |",
        f"| legacy 預設／明示輸出不一致 | {counts['legacy_runtime_mismatch_count']}/{counts['legacy_runtime_pair_count']} |",
        f"| 目標／中性運算排程一致 | {'通過' if parity['parity_pass'] else '失敗'} |",
        f"| 合成本機生成呼叫 | {counts['actual_local_generation_call_count']} |",
        "",
        "## 失敗關閉",
        "",
        "無模型、硬邊界情境、所有候選被閘門拒絕時，都回傳型別化錯誤；沒有固定人格句接手。",
        "",
        "## 證據邊界",
        "",
        f"原始碼仍保留 {counts['source_legacy_fixed_reply_literal_count']} 個 legacy 固定回覆字串，供目前預設聊天相容使用；本輪證明的是 structured 路徑可達數為 0，不是已刪除原始碼。",
        "",
        "這是合成 provider 邊界測試，沒有讀取 holdout、沒有使用目標人物原句、沒有計算人格分數，也不授權正式人格結論或 production 啟用。",
        "",
        f"下一個獲授權步驟：`{report['decision']}`。",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args()
    preregistration = load_json(args.preregistration)
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit("wrong preregistration experiment_id")
    report = build_report(preregistration)
    Path(args.report_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.report_md).write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "decision": report["decision"], "counts": report["counts"]}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "construction_passed" else 1)


if __name__ == "__main__":
    main()
