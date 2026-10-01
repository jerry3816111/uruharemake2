"""M54 machine-checkable candidate human-response equation contract.

This module is a read-only research adapter.  It summarizes existing runtime
state by digest, never changes a reply or decision, and is not evidence that
the named variables are literal human or biological states.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from html import escape
import json
from pathlib import Path

import uruha_actionable_help_delivery_m45 as action45


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m54_human_response_equation_v1.json"
LABEL = "human_response_equation_v1_m54"
SCHEMA = "uruha_human_response_equation_snapshot_m54"
EXPECTED_VARIABLE_IDS = (
    "current_observable_input",
    "observable_history",
    "structured_memory",
    "transient_state",
    "relationship_state",
    "goal_need_state",
    "observable_context",
    "person_parameter",
    "uncertainty_calibration",
)
_INSTALLED = False
_PREVIOUS_MATERIALIZE = action45.materialize_trace_m45


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def load_contract(path=CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_contract_m54(contract):
    errors = []
    if contract.get("schema") != "uruha_human_response_equation_contract_m54":
        errors.append("invalid_schema")
    variables = contract.get("variables") or []
    ids = [str(row.get("id") or "") for row in variables if isinstance(row, dict)]
    if tuple(ids) != EXPECTED_VARIABLE_IDS:
        errors.append("variable_order_or_membership_mismatch")
    if len(ids) != len(set(ids)):
        errors.append("duplicate_variable_id")
    required = {
        "symbol", "epistemic_status", "allowed_evidence", "runtime_paths",
        "measurement", "uncertainty", "persistence", "interventions",
        "forbidden_claims",
    }
    for row in variables:
        variable_id = str(row.get("id") or "missing")
        for key in sorted(required):
            value = row.get(key)
            if value in (None, "", []):
                errors.append(f"{variable_id}:missing_{key}")
        epistemic = str(row.get("epistemic_status") or "")
        persistence = str(row.get("persistence") or "")
        if "inferred" in epistemic and "factual" in persistence and "never_factual" not in persistence:
            errors.append(f"{variable_id}:inferred_promoted_to_factual")
    outputs = contract.get("outputs") or []
    roles = [row.get("role") for row in outputs if isinstance(row, dict)]
    if roles != ["primary", "secondary_interactive", "downstream_realization"]:
        errors.append("output_role_order_mismatch")
    primary = outputs[0] if outputs else {}
    for requirement in ("generated_before_utterance", "normalized", "observable_labels", "cutoff_bound"):
        if requirement not in (primary.get("requirements") or []):
            errors.append(f"primary_output_missing_{requirement}")
    update = contract.get("outcome_update") or {}
    if update.get("allowed_statuses") != ["supported", "contradicted", "unknown"]:
        errors.append("invalid_outcome_statuses")
    if update.get("unknown_counts_as_success") is not False:
        errors.append("unknown_must_not_count_as_success")
    if update.get("raw_inferred_state_factual_write") is not False:
        errors.append("raw_inferred_state_write_must_be_false")
    boundaries = contract.get("claim_boundary") or {}
    if not boundaries.get("may_claim") or not boundaries.get("may_not_claim"):
        errors.append("claim_boundary_missing")
    return {
        "valid": not errors,
        "errors": errors,
        "variable_count": len(variables),
        "output_count": len(outputs),
        "contract_hash": digest(contract),
    }


def _path_value(roots, dotted_path):
    parts = str(dotted_path or "").split(".")
    if not parts or parts[0] not in roots:
        return None
    value = roots[parts[0]]
    for key in parts[1:]:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _available(value):
    return value is not None and value != "" and value != [] and value != {}


def _value_summary(value):
    if isinstance(value, dict):
        size = len(value)
        value_type = "object"
    elif isinstance(value, list):
        size = len(value)
        value_type = "array"
    elif isinstance(value, str):
        size = len(value)
        value_type = "text"
    elif value is None:
        size = 0
        value_type = "unavailable"
    else:
        size = 1
        value_type = type(value).__name__
    return {
        "value_digest": digest(value),
        "value_type": value_type,
        "item_or_character_count": size,
        "raw_value_persisted": False,
    }


def _normalize_distribution(rows):
    normalized_rows = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        label = str(
            row.get("behavior_id")
            or row.get("policy_id")
            or row.get("label")
            or ""
        ).strip()
        raw = row.get("probability")
        if raw is None:
            raw = row.get("outcome_weighted_probability")
        if raw is None:
            raw = row.get("base_softmax_probability")
        try:
            probability = max(0.0, float(raw))
        except (TypeError, ValueError):
            continue
        if label:
            normalized_rows.append({"label": label, "probability": probability})
    total = sum(row["probability"] for row in normalized_rows)
    if total <= 0:
        return []
    result = [
        {"label": row["label"], "probability": round(row["probability"] / total, 6)}
        for row in normalized_rows
    ]
    correction = round(1.0 - sum(row["probability"] for row in result), 6)
    if result and correction:
        result[-1]["probability"] = round(result[-1]["probability"] + correction, 6)
    return result


def _distribution_from_paths(roots, paths):
    for path in paths or []:
        value = _path_value(roots, path)
        distribution = _normalize_distribution(value)
        if distribution:
            return path, distribution
    return None, []


def build_snapshot_m54(result, contract=None):
    result = result or {}
    contract = deepcopy(contract or load_contract())
    validation = validate_contract_m54(contract)
    roots = {
        "logic": result.get("logic") or {},
        "memory_data": result.get("memory_data") or {},
        "runtime_trace": result.get("runtime_trace") or {},
        "runtime_state": result.get("runtime_state") or {},
        "reply": result.get("reply"),
        "contract": {"person_parameter": contract.get("person_parameter") or {}},
    }
    variables = []
    for definition in contract.get("variables") or []:
        source_path = None
        value = None
        for path in definition.get("runtime_paths") or []:
            candidate = _path_value(roots, path)
            if _available(candidate):
                source_path = path
                value = candidate
                break
        variables.append(
            {
                "id": definition["id"],
                "symbol": definition["symbol"],
                "status": "available" if source_path else "unavailable_not_inferred",
                "source_path": source_path,
                "epistemic_status": definition["epistemic_status"],
                "persistence": definition["persistence"],
                "intervention_count": len(definition.get("interventions") or []),
                **_value_summary(value),
            }
        )
    outputs = []
    for definition in contract.get("outputs") or []:
        if definition.get("role") == "downstream_realization":
            value = result.get("reply")
            outputs.append(
                {
                    "id": definition["id"],
                    "role": definition["role"],
                    "status": "available" if _available(value) else "unavailable",
                    "source_path": "reply" if _available(value) else None,
                    "distribution": [],
                    **_value_summary(value),
                }
            )
            continue
        source_path, distribution = _distribution_from_paths(roots, definition.get("runtime_paths"))
        outputs.append(
            {
                "id": definition["id"],
                "role": definition["role"],
                "status": "available_normalized" if distribution else "unavailable_not_fabricated",
                "source_path": source_path,
                "distribution": distribution,
                "probability_sum": round(sum(row["probability"] for row in distribution), 6),
                "raw_value_persisted": False,
            }
        )
    available_count = sum(row["status"] == "available" for row in variables)
    primary = next((row for row in outputs if row["role"] == "primary"), {})
    secondary = next((row for row in outputs if row["role"] == "secondary_interactive"), {})
    snapshot = {
        "schema": SCHEMA,
        "status": "contract_valid" if validation["valid"] else "contract_invalid",
        "equation_version": contract.get("version"),
        "equations": deepcopy(contract.get("equations") or {}),
        "contract_hash": validation["contract_hash"],
        "contract_errors": validation["errors"],
        "variables": variables,
        "outputs": outputs,
        "coverage": {
            "available_variables": available_count,
            "total_variables": len(variables),
            "primary_behavior_distribution_available": primary.get("status") == "available_normalized",
            "secondary_policy_distribution_available": secondary.get("status") == "available_normalized",
        },
        "outcome_update_contract": deepcopy(contract.get("outcome_update") or {}),
        "runtime_effect": {
            "reply_changed": False,
            "decision_changed": False,
            "added_model_calls": 0,
            "long_term_memory_write": False,
        },
        "m55_readiness": {
            "equation_contract_ready": validation["valid"],
            "real_person_temporal_data_ready": False,
            "reason": "M55 timestamped real-person pilot not yet collected",
        },
        "claim_boundary": deepcopy(contract.get("claim_boundary") or {}),
    }
    snapshot["snapshot_hash"] = digest(snapshot)
    return snapshot


def intervene_snapshot_m54(snapshot, variable_id, replacement):
    if variable_id not in EXPECTED_VARIABLE_IDS:
        raise ValueError(f"unknown M54 variable: {variable_id}")
    updated = deepcopy(snapshot)
    variables = updated.get("variables") or []
    target = next((row for row in variables if row.get("id") == variable_id), None)
    if target is None:
        raise ValueError(f"snapshot missing M54 variable: {variable_id}")
    before = {row["id"]: row.get("value_digest") for row in variables}
    replacement_summary = _value_summary(replacement)
    target.update(
        status="intervened",
        source_path="counterfactual_intervention_m54",
        **replacement_summary,
    )
    after = {row["id"]: row.get("value_digest") for row in variables}
    changed = [key for key in EXPECTED_VARIABLE_IDS if before.get(key) != after.get(key)]
    updated["intervention"] = {
        "target_variable": variable_id,
        "changed_variables": changed,
        "single_variable_only": changed == [variable_id],
        "before_digest": before[variable_id],
        "after_digest": after[variable_id],
        "raw_replacement_persisted": False,
        "prediction_recomputed": False,
        "claim_boundary": "interface proof only; causal prediction effect is tested in M59",
    }
    updated["snapshot_hash"] = digest({key: value for key, value in updated.items() if key != "snapshot_hash"})
    return updated


def graph_payload_m54(snapshot):
    nodes = [
        {
            "id": f"m54-{row['id']}",
            "kind": "variable",
            "label": row["symbol"],
            "status": row["status"],
            "detail_digest": row["value_digest"],
        }
        for row in snapshot.get("variables") or []
    ]
    nodes.extend(
        {
            "id": f"m54-output-{row['id']}",
            "kind": "output",
            "label": row["id"],
            "status": row["status"],
        }
        for row in snapshot.get("outputs") or []
    )
    nodes.append({"id": "m54-outcome-update", "kind": "update", "label": "outcome / error update", "status": "contract_defined"})
    variable_ids = [node["id"] for node in nodes if node["kind"] == "variable"]
    primary = "m54-output-observable_behavior_distribution"
    secondary = "m54-output-desired_response_policy_distribution"
    utterance = "m54-output-visible_utterance"
    edges = [{"source": node_id, "target": primary, "class": "equation-input"} for node_id in variable_ids]
    edges.extend(
        [
            {"source": primary, "target": secondary, "class": "interactive-projection"},
            {"source": secondary, "target": utterance, "class": "language-realization"},
            {"source": utterance, "target": "m54-outcome-update", "class": "observable-outcome"},
            {"source": "m54-outcome-update", "target": "m54-structured_memory", "class": "typed-update"},
            {"source": "m54-outcome-update", "target": "m54-uncertainty_calibration", "class": "calibration-update"},
        ]
    )
    return {"schema": "uruha_human_response_equation_graph_m54", "nodes": nodes, "edges": edges}


def materialize_trace_m54(result, feedback=None):
    _PREVIOUS_MATERIALIZE(result, feedback)
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    reply_before = result.get("reply")
    snapshot = build_snapshot_m54(result)
    logic = result.setdefault("logic", {})
    logic[LABEL] = deepcopy(snapshot)
    runtime_trace = result.setdefault("runtime_trace", {})
    runtime_trace[LABEL] = deepcopy(snapshot)
    rows = [row for row in runtime_trace.get("blackboard") or [] if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows))
    rows.insert(index, {"label": LABEL, "stage": "equation", "payload": deepcopy(snapshot), "salience": 0.99})
    runtime_trace["blackboard"] = rows
    sync_current_history_m41_1(result)
    if result.get("reply") != reply_before:
        raise RuntimeError("M54 read-only adapter changed the visible reply")


def render_m54(result):
    from uruha_source_neutral_scaffold_m53 import render_m53

    html = render_m53(result)
    snapshot = (result.get("logic") or {}).get(LABEL)
    if not isinstance(snapshot, dict):
        snapshot = build_snapshot_m54(result)
    coverage = snapshot.get("coverage") or {}
    variables = snapshot.get("variables") or []
    variable_nodes = "".join(
        '<div class="m54-variable"><b>{}</b><span>{}</span></div>'.format(
            escape(str(row.get("symbol") or "?")),
            "有資料" if row.get("status") == "available" else "未知／未提供",
        )
        for row in variables
    )
    primary = "已形成" if coverage.get("primary_behavior_distribution_available") else "尚未形成"
    card = (
        '<section class="m54-equation" aria-label="M54 human response equation">'
        '<style>.m54-equation{grid-column:1/-1;background:linear-gradient(135deg,#092635,#123d4b);border:2px solid #5eead4;border-radius:18px;padding:17px;margin:12px 0;color:#ecfeff}'
        '.m54-equation *{color:#ecfeff!important}.m54-equation h3{font-size:19px;margin:0 0 5px}.m54-equation p{font-size:12px;line-height:1.55;margin:4px 0}.m54-grid{display:grid;grid-template-columns:repeat(9,minmax(92px,1fr));gap:6px;margin-top:12px;overflow-x:auto}.m54-variable{background:#155e75;border-radius:9px;padding:9px;min-width:92px}.m54-variable b,.m54-variable span{display:block}.m54-variable b{font-size:12px}.m54-variable span{font-size:10px;opacity:.8;margin-top:4px}.m54-verdict{margin-top:10px;padding:10px;border-radius:9px;background:#164e63;font-size:12px}</style>'
        '<h3>人類反應方程式候選 V1 · M54</h3>'
        '<p>P(Y下一輪｜當前輸入、歷史、記憶、狀態、關係、需求、情境、人物參數、不確定性)</p>'
        '<p>這張卡顯示目前有哪些變數真的有runtime來源；未知就保持未知，不補成人類心理。</p>'
        f'<div class="m54-grid">{variable_nodes}</div>'
        f'<div class="m54-verdict">本輪變數來源 {coverage.get("available_variables", 0)}/{coverage.get("total_variables", 9)}；主要真人行為分布：{primary}。契約成立不等於已證明人類方程式。</div>'
        '</section>'
    )
    anchor = '<section class="m53-flow" aria-label="M53 source neutral scaffold">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html


def install_m54_human_response_equation():
    global _INSTALLED, _PREVIOUS_MATERIALIZE
    if _INSTALLED:
        return False
    _PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
    action45.materialize_trace_m45 = materialize_trace_m54
    _INSTALLED = True
    return True
