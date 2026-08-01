#!/usr/bin/env python3
"""Freeze and serve the bounded 18-slot human codebook pilot."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import secrets
import urllib.parse
import webbrowser
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from public_persona_contrast_coding_tool_v6 import (
    DEFAULT_CODEBOOK,
    DEFAULT_PRIVATE_ROOT,
    DEFAULT_SOURCE_MANIFEST,
    _atomic_write_json,
    _form_payload,
    _write_text,
    build_reliability_report,
    initialize_ledger,
    load_json,
    load_ledger,
    render_coding_page,
    resolve_private_path,
    save_entry,
    sha256_file,
    validate_coder_pseudonym,
    validate_ledger,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_contrast_coding_pilot_v7_preregistration.json"
)
DEFAULT_CODER_MANUAL = ROOT / "configs/public_persona_contrast_coding_manual_v7.json"
DEFAULT_V6_RESULT = (
    ROOT / "configs/public_persona_contrast_coding_tool_v6_result_lock.json"
)
DEFAULT_FULL_FRAME = (
    ROOT / "datasets/public_persona_contrast_event_sampling_frame_v5.json"
)
DEFAULT_PILOT_FRAME = (
    ROOT / "datasets/public_persona_contrast_coding_pilot_frame_v7.json"
)
DEFAULT_GITIGNORE = ROOT / ".gitignore"
DEFAULT_OUTPUT_JSON = (
    ROOT / "reports/public_persona_contrast_coding_pilot_v7_construction.json"
)
DEFAULT_OUTPUT_MD = (
    ROOT / "reports/public_persona_contrast_coding_pilot_v7_construction.md"
)

EXPERIMENT_ID = "public_persona_contrast_coding_pilot_v7"
PASS_DECISION = "authorize_two_human_18_slot_codebook_pilot_only"
FAIL_DECISION = "repair_pilot_protocol_before_any_human_behavior_review"
V6_REQUIRED_DECISION = (
    "authorize_local_two_coder_tool_use_for_v5_bounded_manual_coding_only"
)
PRIVATE_ROOT_RELATIVE = "analysis/local_public_persona_contrast_coding_v5/"
EXPECTED_DEPENDENCIES = {
    "v6_result_lock": "configs/public_persona_contrast_coding_tool_v6_result_lock.json",
    "v5_sampling_frame": "datasets/public_persona_contrast_event_sampling_frame_v5.json",
    "v6_codebook": "configs/public_persona_contrast_coding_codebook_v6.json",
    "v6_tool": "public_persona_contrast_coding_tool_v6.py",
    "coder_manual": "configs/public_persona_contrast_coding_manual_v7.json",
}


def _binding(path):
    path = Path(path).resolve()
    try:
        display = str(path.relative_to(ROOT))
    except ValueError:
        display = str(path)
    return {"path": display, "sha256": sha256_file(path)}


def _binding_valid(binding):
    if not isinstance(binding, dict):
        return False
    path = Path(str(binding.get("path") or ""))
    if not path.is_absolute():
        path = ROOT / path
    expected = str(binding.get("sha256") or "")
    return path.is_file() and len(expected) == 64 and sha256_file(path) == expected


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_pilot_frame(full_frame):
    grouped = defaultdict(list)
    for slot in full_frame.get("sampling_slots") or []:
        grouped[slot["source_id"]].append(slot)
    selected = []
    for source_id in sorted(grouped):
        slots = grouped[source_id]
        for half, indices in (("early", set(range(1, 6))), ("late", set(range(6, 11)))):
            candidates = [slot for slot in slots if slot["slot_index"] in indices]
            ranked = []
            for slot in candidates:
                selection_hash = _digest(
                    f"{EXPERIMENT_ID}|{slot['sampling_slot_id']}|{half}_pilot"
                )
                ranked.append((selection_hash, slot))
            selection_hash, original = min(ranked, key=lambda row: row[0])
            row = json.loads(json.dumps(original))
            row["pilot_half"] = half
            row["pilot_selection_sha256"] = selection_hash
            row["pilot_review_order_sha256"] = _digest(
                f"{EXPERIMENT_ID}|{row['sampling_slot_id']}|pilot_review_order"
            )
            row["pilot_review_order"] = None
            selected.append(row)
    selected.sort(key=lambda row: row["pilot_review_order_sha256"])
    for order, row in enumerate(selected, start=1):
        row["pilot_review_order"] = order
        row["global_review_order"] = order
    return {
        "schema": "uruha_public_persona_contrast_coding_pilot_frame_v7",
        "experiment_id": EXPERIMENT_ID,
        "status": "frozen_empty_18_slot_pilot_before_behavior_review",
        "generated_at": "2026-08-01",
        "preregistration_binding": _binding(DEFAULT_PREREGISTRATION),
        "full_frame_binding": _binding(DEFAULT_FULL_FRAME),
        "codebook_binding": _binding(DEFAULT_CODEBOOK),
        "selection_algorithm": {
            "source_count": 9,
            "pilot_slots_per_source": 2,
            "early_candidate_slot_indices": [1, 2, 3, 4, 5],
            "late_candidate_slot_indices": [6, 7, 8, 9, 10],
            "within_half_rule": "minimum sha256(experiment_id|sampling_slot_id|early_or_late_pilot)",
            "review_order_rule": "ascending sha256(experiment_id|sampling_slot_id|pilot_review_order)",
            "behavior_content_used": False,
            "post_review_replacement_allowed": False,
        },
        "sampling_slots": selected,
        "current_counts": {
            "pilot_sampling_slot_count": len(selected),
            "private_ledger_count": 0,
            "content_reviewed_source_count": 0,
            "selected_event_count": 0,
            "coded_event_count": 0,
            "human_coder_count": 0,
            "model_output_count": 0,
            "persona_score_count": 0,
            "holdout_content_review_count": 0,
            "model_call_count": 0,
        },
    }


def validate_pilot_frame(frame, full_frame):
    errors = []
    expected = build_pilot_frame(full_frame)
    if frame != expected:
        errors.append("pilot_frame_does_not_match_rebuild")
    slots = frame.get("sampling_slots") or []
    if len(slots) != 18:
        errors.append("pilot_slot_count")
    source_counts = Counter(slot.get("source_id") for slot in slots)
    if len(source_counts) != 9 or set(source_counts.values()) != {2}:
        errors.append("pilot_source_balance")
    half_counts = Counter((slot.get("source_id"), slot.get("pilot_half")) for slot in slots)
    if len(half_counts) != 18 or set(half_counts.values()) != {1}:
        errors.append("pilot_half_balance")
    orders = [slot.get("pilot_review_order") for slot in slots]
    if sorted(orders) != list(range(1, 19)):
        errors.append("pilot_review_order")
    expected_counts = {
        "pilot_sampling_slot_count": 18,
        "private_ledger_count": 0,
        "content_reviewed_source_count": 0,
        "selected_event_count": 0,
        "coded_event_count": 0,
        "human_coder_count": 0,
        "model_output_count": 0,
        "persona_score_count": 0,
        "holdout_content_review_count": 0,
        "model_call_count": 0,
    }
    if frame.get("current_counts") != expected_counts:
        errors.append("pilot_counts_nonzero")
    return errors


def validate_coder_manual(manual, codebook):
    errors = []
    if manual.get("schema") != "uruha_public_persona_contrast_coding_manual_v7":
        errors.append("schema")
    if manual.get("experiment_id") != EXPERIMENT_ID:
        errors.append("experiment_id")
    if manual.get("status") != "frozen_before_human_behavior_review":
        errors.append("status")
    expected_flags = {
        "categories_define_target_answers": False,
        "target_specific_examples_present": False,
        "real_source_quotes_present": False,
        "private_motive_inference_allowed": False,
    }
    for field, expected in expected_flags.items():
        if manual.get(field) is not expected:
            errors.append(field)
    definition_contracts = {
        "slot_status_definitions": codebook.get("terminal_slot_statuses") or [],
        "context_family_definitions": codebook.get("context_families") or [],
        "dimension_definitions": codebook.get("dimensions") or [],
        "dialogue_act_or_action_definitions": codebook.get(
            "dialogue_act_or_action_labels"
        )
        or [],
        "audience_relation_definitions": codebook.get("audience_relations") or [],
        "evidence_strength_definitions": codebook.get("evidence_strengths") or [],
    }
    for field, expected_keys in definition_contracts.items():
        definitions = manual.get(field)
        if not isinstance(definitions, dict) or set(definitions) != set(expected_keys):
            errors.append(f"{field}:coverage")
            continue
        if any(
            not isinstance(value, str) or not value.strip()
            for value in definitions.values()
        ):
            errors.append(f"{field}:empty")
    event_rules = manual.get("event_boundary_rules")
    expected_event_rules = {
        "eligible_event",
        "event_start",
        "event_end",
        "same_reaction",
        "unclear_actor",
        "technical_or_waiting",
        "scripted_reading",
        "private_or_sensitive",
    }
    if not isinstance(event_rules, dict) or set(event_rules) != expected_event_rules:
        errors.append("event_boundary_rules:coverage")
    elif any(
        not isinstance(value, str) or not value.strip()
        for value in event_rules.values()
    ):
        errors.append("event_boundary_rules:empty")
    for field, minimum in (("quick_rules", 7), ("decision_order", 7)):
        values = manual.get(field)
        if not isinstance(values, list) or len(values) < minimum:
            errors.append(f"{field}:coverage")
        elif any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"{field}:empty")
    return errors


def build_construction_audit(
    preregistration,
    v6_result,
    full_frame,
    pilot_frame,
    codebook,
    coder_manual,
    gitignore_text,
):
    violations = []
    if preregistration.get("schema") != (
        "uruha_public_persona_contrast_coding_pilot_preregistration_v7"
    ):
        violations.append("preregistration_schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations.append("experiment_id")
    for name, expected_path in EXPECTED_DEPENDENCIES.items():
        binding = (preregistration.get("depends_on") or {}).get(name)
        if not _binding_valid(binding):
            violations.append(f"dependency:{name}:hash")
        if (binding or {}).get("path") != expected_path:
            violations.append(f"dependency:{name}:path")
    if v6_result.get("decision") != V6_REQUIRED_DECISION:
        violations.append("v6_decision")
    sampling = preregistration.get("pilot_sampling_contract") or {}
    expected_sampling = {
        "source_count_exact": 9,
        "pilot_slot_count_per_source_exact": 2,
        "pilot_slot_count_exact": 18,
        "early_candidate_slot_indices": [1, 2, 3, 4, 5],
        "late_candidate_slot_indices": [6, 7, 8, 9, 10],
        "one_early_and_one_late_slot_per_source": True,
        "within_half_selection_algorithm": "minimum sha256(experiment_id|sampling_slot_id|early_or_late_pilot)",
        "pilot_review_order_algorithm": "ascending sha256(experiment_id|sampling_slot_id|pilot_review_order)",
        "behavior_content_used_for_slot_selection": False,
        "slot_replacement_after_behavior_review": False,
        "all_original_v5_search_starts_preserved": True,
    }
    if sampling != expected_sampling:
        violations.append("sampling_contract")
    human = preregistration.get("human_contract") or {}
    expected_human = {
        "distinct_consenting_human_coder_count_exact": 2,
        "each_coder_completes_all_pilot_slots": True,
        "coders_work_from_separate_private_ledgers": True,
        "coders_cannot_see_each_other_records_before_completion": True,
        "actor_identity_blinding_feasible": False,
        "model_outputs_or_persona_scores_visible": False,
        "original_independent_records_preserved_after_adjudication": True,
    }
    if human != expected_human:
        violations.append("human_contract")
    manual_contract = preregistration.get("coding_manual_contract") or {}
    expected_manual_contract = {
        "manual_hash_bound_before_behavior_review": True,
        "same_manual_for_both_coders": True,
        "all_frozen_codebook_categories_operationally_defined": True,
        "target_specific_examples_present": False,
        "real_source_quotes_present": False,
        "private_motive_inference_allowed": False,
        "manual_change_after_first_coder_starts": False,
    }
    if manual_contract != expected_manual_contract:
        violations.append("coding_manual_contract")
    policy = preregistration.get("pilot_decision_policy") or {}
    expected_policy = {
        "reliability_pass": "authorize_full_v5_contrast_coding_with_unchanged_v6_codebook_only",
        "reliability_fail": "revise_codebook_preserve_original_pilot_ledgers_and_run_new_preregistered_pilot",
        "both_ledgers_complete_required": True,
        "coder_pseudonyms_distinct_required": True,
        "temporal_iou_mean_min": 0.5,
        "all_primary_nominal_alpha_min": 0.667,
        "slot_status_agreement_reported": True,
        "secondary_dimension_alpha_reported_but_not_used_as_single_gate": True,
        "aggregate_behavior_profile_authorized_by_pilot": False,
        "persona_similarity_comparison_authorized": False,
        "model_execution": False,
        "target_calibration_behavior_coding": False,
        "sealed_holdout_unsealing": False,
        "model_training": False,
        "public_persona_fidelity_claim": False,
    }
    if policy != expected_policy:
        violations.append("decision_policy")
    expected_counts = {
        "pilot_sampling_slot_count": 18,
        "private_ledger_count": 0,
        "content_reviewed_source_count": 0,
        "selected_event_count": 0,
        "coded_event_count": 0,
        "human_coder_count": 0,
        "model_output_count": 0,
        "persona_score_count": 0,
        "holdout_content_review_count": 0,
        "model_call_count": 0,
    }
    if preregistration.get("expected_counts_before_human_pilot") != expected_counts:
        violations.append("expected_counts")
    violations.extend(validate_pilot_frame(pilot_frame, full_frame))
    if codebook.get("status") != "frozen_before_contrast_behavior_review":
        violations.append("codebook_status")
    violations.extend(
        f"coder_manual:{error}"
        for error in validate_coder_manual(coder_manual, codebook)
    )
    if PRIVATE_ROOT_RELATIVE not in gitignore_text.splitlines():
        violations.append("private_root_not_gitignored")
    checks = {
        "v6_tool_authorization_and_dependencies_are_hash_bound": not any(
            item.startswith(("dependency:", "v6_")) for item in violations
        ),
        "nine_sources_have_one_early_and_one_late_pilot_slot": not any(
            item in {"pilot_slot_count", "pilot_source_balance", "pilot_half_balance"}
            for item in violations
        ),
        "pilot_slots_and_review_order_rebuild_exactly": not any(
            item in {"pilot_frame_does_not_match_rebuild", "pilot_review_order"}
            for item in violations
        ),
        "slot_selection_is_content_free_and_nonreplaceable": (
            "sampling_contract" not in violations
        ),
        "two_distinct_consenting_humans_and_separate_ledgers_are_required": (
            "human_contract" not in violations
        ),
        "coder_manual_defines_every_category_without_target_answers": not any(
            item == "coding_manual_contract" or item.startswith("coder_manual:")
            for item in violations
        ),
        "pilot_reliability_gate_does_not_authorize_persona_comparison": (
            "decision_policy" not in violations
        ),
        "private_storage_and_frozen_codebook_are_preserved": not any(
            item in {"private_root_not_gitignored", "codebook_status"}
            for item in violations
        ),
        "all_human_content_model_score_and_holdout_counts_are_zero": not any(
            item in {"expected_counts", "pilot_counts_nonzero"} for item in violations
        ),
    }
    passed = all(checks.values()) and not violations
    counts = pilot_frame.get("current_counts") or {}
    return {
        "schema": "uruha_public_persona_contrast_coding_pilot_construction_v7",
        "experiment_id": EXPERIMENT_ID,
        "construction_passed": passed,
        "human_pilot_completed": False,
        "reliability_computed": False,
        "persona_score_computed": False,
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "summary": {
            "check_count": len(checks),
            "check_pass_count": sum(checks.values()),
            "source_count": len({slot.get("source_id") for slot in pilot_frame.get("sampling_slots") or []}),
            **counts,
        },
        "checks": checks,
        "violations": violations,
        "authorizations": {
            "two_human_18_slot_codebook_pilot": passed,
            "maximum_human_coder_count": 2 if passed else 0,
            "maximum_slot_count_per_coder": 18 if passed else 0,
            "full_90_slot_coding": False,
            "aggregate_behavior_profile": False,
            "persona_similarity_comparison": False,
            "model_execution": False,
            "target_calibration_behavior_coding": False,
            "sealed_holdout_unsealing": False,
            "model_training": False,
            "public_persona_fidelity_claim": False,
        },
        "next_required_evidence": "兩位不同且知情同意的真人，必須在彼此看不到答案的情況下，各自完成同一組 18 格 pilot；只有兩份帳本都完整後才能計算聚合可靠度。",
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_audit_from_paths():
    preregistration = load_json(DEFAULT_PREREGISTRATION)
    v6_result = load_json(DEFAULT_V6_RESULT)
    full_frame = load_json(DEFAULT_FULL_FRAME)
    pilot_frame = load_json(DEFAULT_PILOT_FRAME)
    codebook = load_json(DEFAULT_CODEBOOK)
    coder_manual = load_json(DEFAULT_CODER_MANUAL)
    report = build_construction_audit(
        preregistration,
        v6_result,
        full_frame,
        pilot_frame,
        codebook,
        coder_manual,
        DEFAULT_GITIGNORE.read_text(encoding="utf-8"),
    )
    report["inputs"] = {
        "preregistration": _binding(DEFAULT_PREREGISTRATION),
        "v6_result_lock": _binding(DEFAULT_V6_RESULT),
        "full_sampling_frame": _binding(DEFAULT_FULL_FRAME),
        "pilot_sampling_frame": _binding(DEFAULT_PILOT_FRAME),
        "codebook": _binding(DEFAULT_CODEBOOK),
        "coder_manual": _binding(DEFAULT_CODER_MANUAL),
    }
    return report


def build_markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# 公開人格對照事件編碼 V7：18 格雙人 Pilot",
            "",
            f"- 建構通過：`{report['construction_passed']}` ({summary['check_pass_count']}/{summary['check_count']})",
            f"- 真人 pilot 完成：`{report['human_pilot_completed']}`",
            f"- 決策：`{report['decision']}`",
            "",
            "## 為什麼不是直接做 90 格",
            "",
            "`9 個來源 x（早段 1 格 + 晚段 1 格）= 每位 18 格`",
            "",
            "先用 18 格確認兩人是否能一致理解 codebook；若分類不清，保留原始帳本、修訂規則並重新預註冊，不浪費完整 180 次人工判斷。",
            "兩位編碼者使用同一份雜湊凍結的中文操作手冊；手冊只定義通用觀察規則，不含人物答案、真實原句或來源案例。",
            "",
            "## 目前資料",
            "",
            "| Pilot 槽 | 真人編碼者 | 私有帳本 | 已選事件 | 可靠度 | 人格分數 |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {summary['pilot_sampling_slot_count']} | {summary['human_coder_count']} | {summary['private_ledger_count']} | {summary['selected_event_count']} | 0 | {summary['persona_score_count']} |",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
            "",
        ]
    )


def _definition_rows(definitions, labels):
    return "".join(
        f"<dt>{html.escape(labels.get(key, key))}</dt><dd>{html.escape(value)}</dd>"
        for key, value in definitions.items()
    )


def render_coder_manual(coder_manual, codebook):
    labels = codebook.get("display_labels_zh_hant") or {}
    quick_rules = "".join(
        f"<li>{html.escape(value)}</li>" for value in coder_manual["quick_rules"]
    )
    decision_order = "".join(
        f"<li>{html.escape(value)}</li>" for value in coder_manual["decision_order"]
    )
    event_rules = "".join(
        f"<dt>{html.escape(key)}</dt><dd>{html.escape(value)}</dd>"
        for key, value in coder_manual["event_boundary_rules"].items()
    )
    groups = (
        ("槽位結果", "slot_status_definitions"),
        ("情境類別", "context_family_definitions"),
        ("主要與次要面向", "dimension_definitions"),
        ("對話行為／行動", "dialogue_act_or_action_definitions"),
        ("可觀察對象關係", "audience_relation_definitions"),
        ("證據強度", "evidence_strength_definitions"),
    )
    definitions = "".join(
        "<details><summary>"
        + html.escape(title)
        + "</summary><dl>"
        + _definition_rows(coder_manual[field], labels)
        + "</dl></details>"
        for title, field in groups
    )
    return (
        '<section class="card manual"><h2>V7 編碼手冊</h2>'
        "<p><strong>這是通用觀察分類，不是官方人格標籤，也不是任何人物的標準答案。</strong></p>"
        f"<details open><summary>先讀這 7 條</summary><ol>{quick_rules}</ol></details>"
        f"<details><summary>事件起點與終點</summary><dl>{event_rules}</dl></details>"
        f"{definitions}"
        f"<details><summary>填寫順序</summary><ol>{decision_order}</ol></details>"
        "</section>"
    )


def render_pilot_page(
    ledger,
    pilot_frame,
    source_manifest,
    codebook,
    coder_manual,
    token,
    slot_order,
    error="",
):
    slot_order = min(max(int(slot_order), 1), 18)
    pilot_ids = {slot["sampling_slot_id"] for slot in pilot_frame["sampling_slots"]}
    completed = len(set(ledger.get("entries") or {}) & pilot_ids)
    page = render_coding_page(
        ledger,
        pilot_frame,
        source_manifest,
        codebook,
        token,
        slot_order,
        error=error,
    )
    page = page.replace(
        "<title>Contrast Coding V6</title>",
        "<title>Contrast Coding Pilot V7</title>",
    )
    page = page.replace(
        f"Progress: {len(ledger.get('entries') or {})}/90",
        f"Pilot progress: {completed}/18",
    )
    page = page.replace(f"Slot: {slot_order}/90", f"Pilot slot: {slot_order}/18")
    page = page.replace(
        f"&slot={min(90, slot_order + 1)}\">下一格",
        f"&slot={min(18, slot_order + 1)}\">下一格",
    )
    page = page.replace(
        "</style></head>",
        ".manual details{margin:12px 0;border-top:1px solid var(--line);padding-top:10px}"
        ".manual summary{font-weight:700;cursor:pointer}.manual dt{font-weight:700;margin-top:10px}"
        ".manual dd{margin:3px 0 8px 0;color:#47534f}</style></head>",
    )
    page = page.replace(
        '<section class="card"><div class="slot">',
        render_coder_manual(coder_manual, codebook)
        + '<section class="card"><div class="slot">',
        1,
    )
    return page


def make_pilot_handler(
    ledger_path,
    private_root,
    token,
    full_frame,
    pilot_frame,
    source_manifest,
    codebook,
    coder_manual,
):
    class PilotHandler(BaseHTTPRequestHandler):
        def _send_html(self, body, status=200):
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'self'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(encoded)

        def _redirect(self, location):
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            if parsed.path == "/health":
                self._send_html("ok")
                return
            if query.get("token", [""])[0] != token:
                self._send_html("invalid session token", status=403)
                return
            try:
                slot_order = int(query.get("slot", ["1"])[0])
            except ValueError:
                slot_order = 1
            _, ledger = load_ledger(ledger_path, private_root)
            self._send_html(
                render_pilot_page(
                    ledger,
                    pilot_frame,
                    source_manifest,
                    codebook,
                    coder_manual,
                    token,
                    slot_order,
                )
            )

        def do_POST(self):
            if self.path != "/save":
                self._send_html("not found", status=404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > 65536:
                self._send_html("invalid form size", status=400)
                return
            form = urllib.parse.parse_qs(
                self.rfile.read(length).decode("utf-8"), keep_blank_values=True
            )
            if form.get("token", [""])[0] != token:
                self._send_html("invalid session token", status=403)
                return
            try:
                slot_order = int(form.get("slot_order", ["1"])[0])
            except ValueError:
                slot_order = 1
            try:
                save_entry(
                    ledger_path,
                    _form_payload(form),
                    frame=pilot_frame,
                    codebook=codebook,
                    private_root=private_root,
                )
            except ValueError as error:
                _, ledger = load_ledger(ledger_path, private_root)
                self._send_html(
                    render_pilot_page(
                        ledger,
                        pilot_frame,
                        source_manifest,
                        codebook,
                        coder_manual,
                        token,
                        slot_order,
                        error=str(error),
                    ),
                    status=400,
                )
                return
            self._redirect(
                f"/?token={urllib.parse.quote(token)}&slot={min(18, slot_order + 1)}"
            )

        def log_message(self, format_string, *args):
            return

    return PilotHandler


def serve_pilot(ledger_path, coder_pseudonym, port, open_browser, private_root):
    full_frame = load_json(DEFAULT_FULL_FRAME)
    pilot_frame = load_json(DEFAULT_PILOT_FRAME)
    source_manifest = load_json(DEFAULT_SOURCE_MANIFEST)
    codebook = load_json(DEFAULT_CODEBOOK)
    coder_manual = load_json(DEFAULT_CODER_MANUAL)
    ledger_path = resolve_private_path(ledger_path, private_root)
    if not ledger_path.exists():
        initialize_ledger(coder_pseudonym, ledger_path, private_root=private_root)
    _, ledger = load_ledger(ledger_path, private_root)
    errors = validate_ledger(
        ledger,
        pilot_frame,
        codebook,
        expected_coder=validate_coder_pseudonym(coder_pseudonym),
    )
    if errors:
        raise ValueError("invalid pilot ledger: " + "; ".join(errors))
    token = secrets.token_urlsafe(24)
    handler = make_pilot_handler(
        ledger_path,
        private_root,
        token,
        full_frame,
        pilot_frame,
        source_manifest,
        codebook,
        coder_manual,
    )
    server = ThreadingHTTPServer(("127.0.0.1", int(port)), handler)
    url = f"http://127.0.0.1:{server.server_port}/?token={urllib.parse.quote(token)}&slot=1"
    print(json.dumps({"url": url, "coder": coder_pseudonym, "pilot_slots": 18}, ensure_ascii=False), flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_pilot_reliability(ledger_a, ledger_b):
    pilot_frame = load_json(DEFAULT_PILOT_FRAME)
    codebook = load_json(DEFAULT_CODEBOOK)
    report = build_reliability_report(ledger_a, ledger_b, pilot_frame, codebook)
    reliability_passed = report["gates"]["reliability_passed"]
    report["schema"] = "uruha_public_persona_contrast_coding_pilot_reliability_v7"
    report["experiment_id"] = EXPERIMENT_ID
    report["gates"]["codebook_pilot_reliability_passed"] = reliability_passed
    report["gates"]["full_v5_coding_authorized"] = reliability_passed
    report["gates"]["aggregate_behavior_profile_authorized"] = False
    report["gates"]["persona_similarity_comparison_authorized"] = False
    report["decision"] = (
        "authorize_full_v5_contrast_coding_with_unchanged_v6_codebook_only"
        if reliability_passed
        else "revise_codebook_preserve_original_pilot_ledgers_and_run_new_preregistered_pilot"
    )
    report["evidence_boundary"] = (
        "Pilot reliability pass would show only that two humans can apply the V6 codebook "
        "consistently enough to proceed to the full frozen contrast coding task. It is not "
        "a behavior profile, persona-similarity score, model result, or public-persona claim."
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--overwrite", action="store_true")
    build_parser.add_argument("--require-pass", action="store_true")

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--coder", required=True)
    serve_parser.add_argument("--ledger", required=True)
    serve_parser.add_argument("--port", type=int, default=7866)
    serve_parser.add_argument("--open-browser", action="store_true")

    reliability_parser = subparsers.add_parser("reliability")
    reliability_parser.add_argument("--ledger-a", required=True)
    reliability_parser.add_argument("--ledger-b", required=True)
    reliability_parser.add_argument("--output", required=True)
    reliability_parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()
    if args.command == "build":
        frame = build_pilot_frame(load_json(DEFAULT_FULL_FRAME))
        _write_text(
            DEFAULT_PILOT_FRAME,
            json.dumps(frame, ensure_ascii=False, indent=2) + "\n",
            args.overwrite,
        )
        report = build_audit_from_paths()
        _write_text(
            DEFAULT_OUTPUT_JSON,
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            args.overwrite,
        )
        _write_text(DEFAULT_OUTPUT_MD, build_markdown(report), args.overwrite)
        print(
            json.dumps(
                {
                    "construction_passed": report["construction_passed"],
                    "checks": f"{report['summary']['check_pass_count']}/{report['summary']['check_count']}",
                    "pilot_slots": report["summary"]["pilot_sampling_slot_count"],
                    "decision": report["decision"],
                },
                ensure_ascii=False,
            )
        )
        if args.require_pass and not report["construction_passed"]:
            raise SystemExit(1)
        return
    if args.command == "serve":
        serve_pilot(
            args.ledger,
            args.coder,
            args.port,
            args.open_browser,
            DEFAULT_PRIVATE_ROOT,
        )
        return
    if args.command == "reliability":
        _, ledger_a = load_ledger(args.ledger_a)
        _, ledger_b = load_ledger(args.ledger_b)
        report = build_pilot_reliability(ledger_a, ledger_b)
        output = resolve_private_path(args.output)
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"refusing to overwrite {output}")
        _atomic_write_json(output, report)
        print(
            json.dumps(
                {
                    "output": str(output),
                    "pilot_reliability_passed": report["gates"][
                        "codebook_pilot_reliability_passed"
                    ],
                    "persona_score_computed": False,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
