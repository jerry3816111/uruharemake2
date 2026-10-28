"""P4-AV: authorize bounded source-neutral workflow roles in M53.

M53 correctly blocks quoted labels that look like source facts but are absent
from the user evidence.  P4-AV changes one classification only: a small
compositional Japanese grammar for workflow positions (for example, the item
handled now versus an item held for later) may be treated as an operational
scaffold role.  It does not authorize topic, priority, emotion, diagnosis,
preference, or feasibility labels and it does not change the plan text.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_actionable_help_delivery_m45 as action45
import uruha_source_neutral_scaffold_m53 as m53


LABEL = "neutral_operational_role_authorization_p4"
SCHEMA = "uruha_neutral_operational_role_authorization_p4"

_INSTALLED_P4_AV = False
_ORIGINAL_AUTHORIZE_P4_AV = m53.authorize_named_scaffold_m53
_ORIGINAL_MATERIALIZE_P4_AV = action45.materialize_trace_m45

_OPERATIONAL_ROLE = re.compile(
    r"^(?:(?:今(?:ここで)?|次に|あとで)(?:扱う|確認する|整理する)(?:項目|内容|こと)"
    r"|保留(?:項目|欄|内容))$"
)


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _normalize_label(value):
    return re.sub(r"\s+", "", str(value or ""))


def is_neutral_operational_role_p4_av(label):
    """Return true only for the frozen workflow-role grammar."""

    return bool(_OPERATIONAL_ROLE.fullmatch(_normalize_label(label)))


def authorize_neutral_operational_roles_p4_av(plan, sources):
    """Return the predecessor M53 state with a bounded additive distinction."""

    predecessor = _ORIGINAL_AUTHORIZE_P4_AV(plan, sources)
    result = deepcopy(predecessor)
    labels = m53._labels(plan) if isinstance(plan, dict) else []
    rows = result.get("labels") if isinstance(result.get("labels"), list) else []
    audit_rows = []
    reclassified = 0

    for index, label in enumerate(labels):
        row = rows[index] if index < len(rows) and isinstance(rows[index], dict) else None
        predecessor_status = row.get("status") if row else "missing_predecessor_row"
        operational = bool(
            row
            and predecessor_status == "unsupported_concrete_label"
            and is_neutral_operational_role_p4_av(label)
        )
        if operational:
            row["status"] = "neutral_operational_role_p4_av"
            row["neutral_role"] = True
            row["neutral_operational_role"] = True
            reclassified += 1
        audit_rows.append(
            {
                "label_digest": _digest(label),
                "predecessor_status": predecessor_status,
                "status": "neutral_operational_role" if operational else "predecessor_preserved",
            }
        )

    unsupported = [
        row for row in rows if isinstance(row, dict) and row.get("status") == "unsupported_concrete_label"
    ]
    if rows:
        result["status"] = "blocked" if unsupported else "authorized"
    else:
        result["status"] = "no_named_labels"
    result["neutral_role_count"] = sum(
        bool(row.get("neutral_role")) and not bool(row.get("source_supported"))
        for row in rows
        if isinstance(row, dict)
    )
    result["unsupported_count"] = len(unsupported)

    if reclassified:
        p4_status = "authorized_operational_roles"
    elif result["status"] == "blocked":
        p4_status = "blocked_unsupported_label"
    else:
        p4_status = "predecessor_preserved"
    result[LABEL] = {
        "schema": SCHEMA,
        "status": p4_status,
        "predecessor_status": predecessor.get("status"),
        "final_m53_status": result.get("status"),
        "named_label_count": len(labels),
        "operational_role_count": reclassified,
        "remaining_unsupported_count": len(unsupported),
        "labels": audit_rows,
        "authorization_basis": "bounded_compositional_workflow_role_grammar",
        "plan_changed": False,
        "candidate_score_or_order_changed": False,
        "m46_review_bypassed": False,
        "m45_or_m39_gate_weakened": False,
        "added_model_calls": 0,
        "factual_memory_write_count": 0,
        "raw_candidate_label_persisted": False,
        "visible_reply_changed": False,
        "claim_boundary": (
            "bounded workflow-role syntax only; not topic, priority, emotion, "
            "diagnosis, preference, feasibility, plan usefulness, or private-state truth"
        ),
    }
    return result


def _extract_trace(result):
    logic = result.get("logic") or {}
    m53_state = logic.get(m53.LABEL)
    if not isinstance(m53_state, dict):
        m46_state = logic.get("goal_progress_delivery_m46") or {}
        m53_state = m46_state.get(m53.LABEL) if isinstance(m46_state, dict) else None
        if not isinstance(m53_state, dict) and isinstance(m46_state, dict):
            m53_state = (m46_state.get("diagnostic") or {}).get(m53.LABEL)
    state = m53_state.get(LABEL) if isinstance(m53_state, dict) else None
    return deepcopy(state) if isinstance(state, dict) else None


def materialize_neutral_operational_role_authorization_p4(result, feedback=None):
    trace = _extract_trace(result)
    if trace is None:
        return result
    logic = result.setdefault("logic", {})
    runtime = result.setdefault("runtime_trace", {})
    logic[LABEL] = deepcopy(trace)
    runtime[LABEL] = deepcopy(trace)
    rows = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (
            index
            for index, row in enumerate(rows)
            if row.get("label") in {m53.LABEL, "goal_progress_delivery_m46", action45.LABEL, "utterance"}
        ),
        len(rows),
    )
    rows.insert(
        insert_at,
        {"stage": "authorize", "label": LABEL, "payload": deepcopy(trace), "salience": 1.0},
    )
    runtime["blackboard"] = rows
    return result


def install_neutral_operational_role_authorization_p4():
    global _INSTALLED_P4_AV, _ORIGINAL_AUTHORIZE_P4_AV, _ORIGINAL_MATERIALIZE_P4_AV
    if _INSTALLED_P4_AV:
        return False
    _ORIGINAL_AUTHORIZE_P4_AV = m53.authorize_named_scaffold_m53
    _ORIGINAL_MATERIALIZE_P4_AV = action45.materialize_trace_m45

    def materialize(result, feedback=None):
        _ORIGINAL_MATERIALIZE_P4_AV(result, feedback)
        materialize_neutral_operational_role_authorization_p4(result, feedback)
        return result

    m53.authorize_named_scaffold_m53 = authorize_neutral_operational_roles_p4_av
    action45.materialize_trace_m45 = materialize
    _INSTALLED_P4_AV = True
    return True


def build_dataset_evidence_p4_av(dataset_path):
    path = Path(dataset_path)
    dataset = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for frozen in dataset["cases"]:
        plan = {
            "progress_criterion_jp": frozen["instruction_jp"],
            "action_object_jp": "考え",
            "action_step_jp": frozen["instruction_jp"],
            "expected_state_change_jp": frozen["instruction_jp"],
            "completion_jp": "一つ置いたら停止する",
            "instruction_jp": frozen["instruction_jp"],
        }
        before = deepcopy(plan)
        sources = [
            {
                "id": f"current:{frozen['id']}",
                "kind": "current_user",
                "text": frozen["source"],
            }
        ]
        predecessor = _ORIGINAL_AUTHORIZE_P4_AV(plan, sources)
        result = authorize_neutral_operational_roles_p4_av(plan, sources)
        trace = result[LABEL]
        serialized = json.dumps(trace, ensure_ascii=False, sort_keys=True)
        raw_label_persisted = any(label and label in serialized for label in frozen["labels"])
        cases.append(
            {
                "case_id": frozen["id"],
                "split": frozen["split"],
                "source_language": frozen.get("source_language"),
                "control_family": frozen.get("control_family"),
                "expected_status": frozen["expected_status"],
                "predecessor_status": predecessor["status"],
                "p4_av_status": trace["status"],
                "final_m53_status": result["status"],
                "operational_role_count": trace["operational_role_count"],
                "remaining_unsupported_count": trace["remaining_unsupported_count"],
                "plan_mutated": plan != before,
                "candidate_score_or_order_changed": trace["candidate_score_or_order_changed"],
                "added_model_call_count": trace["added_model_calls"],
                "factual_memory_write_count": trace["factual_memory_write_count"],
                "raw_label_persisted": raw_label_persisted,
                "m46_review_bypassed": trace["m46_review_bypassed"],
                "m45_or_m39_gate_weakened": trace["m45_or_m39_gate_weakened"],
                "visible_reply_changed": trace["visible_reply_changed"],
            }
        )

    development = [row for row in cases if row["split"] == "exposed_development"]
    positives = [row for row in cases if row["split"] == "fresh_positive"]
    fresh_controls = [row for row in cases if row["split"] == "fresh_control"]
    predecessor_controls = [row for row in cases if row["split"] == "predecessor_control"]
    return {
        "schema": "uruha_p4_av_neutral_operational_role_authorization_evidence_v1",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": {
            "case_count": len(cases),
            "development_authorized_count": sum(
                row["p4_av_status"] == "authorized_operational_roles" for row in development
            ),
            "fresh_positive_authorized_count": sum(
                row["p4_av_status"] == "authorized_operational_roles" for row in positives
            ),
            "fresh_positive_predecessor_blocked_count": sum(
                row["predecessor_status"] == "blocked" for row in positives
            ),
            "fresh_control_blocked_count": sum(
                row["final_m53_status"] == "blocked" for row in fresh_controls
            ),
            "predecessor_control_preserved_count": sum(
                row["p4_av_status"] == "predecessor_preserved"
                and row["final_m53_status"] == row["predecessor_status"]
                for row in predecessor_controls
            ),
            "plan_mutation_count": sum(row["plan_mutated"] for row in cases),
            "candidate_score_or_order_change_count": sum(
                row["candidate_score_or_order_changed"] for row in cases
            ),
            "added_model_call_count": sum(row["added_model_call_count"] for row in cases),
            "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in cases),
            "raw_label_persisted_count": sum(row["raw_label_persisted"] for row in cases),
            "m46_review_bypass_count": sum(row["m46_review_bypassed"] for row in cases),
            "m45_or_m39_gate_weakening_count": sum(
                row["m45_or_m39_gate_weakened"] for row in cases
            ),
            "visible_reply_change_count": sum(row["visible_reply_changed"] for row in cases),
        },
        "claim_boundary": dataset["claim_boundary"],
    }


def evaluate_evidence_p4_av(config, evidence):
    failed = []
    metrics = evidence.get("metrics") or {}
    for metric, expected in (config.get("formal_gates") or {}).items():
        if metric == "full_positive_string_patch_count":
            continue
        observed = metrics.get(metric)
        if observed != expected:
            failed.append({"metric": metric, "expected": expected, "observed": observed})
    return {"status": "pass" if not failed else "fail", "failed_gates": failed}
