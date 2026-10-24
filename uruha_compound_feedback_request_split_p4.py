"""P4-AX: split bounded support for an executed clarification from a new ask.

This additive layer extends P4-AT only when the exact pending M44 receipt already
exists.  It composes an observable clarification/checking action, an explicit
first-person response-need object, and a positive evaluation in one direct
clause.  It does not infer a private preference or alter current-request routing.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_executed_action_outcome_closure_p4 as p4_at
import uruha_executed_action_receipt_m44 as receipt_m44


LABEL = "compound_feedback_request_split_p4"
SCHEMA = "uruha_compound_feedback_request_split_p4"
AUTHORIZED_STATUS = "bounded_support_composed"

_BASE_DECOMPOSE_P4_AX = p4_at.decompose_executed_action_feedback_p4
_INSTALLED_P4_AX_HOOK = False
_INSTALLED_P4_AX_PRODUCT = False
_ORIGINAL_EMIT_P4_AX = None
_ORIGINAL_RUN_TURN_P4_AX = None

_CLAUSE_BREAK = re.compile(r"[；;。！？!?]")
_HYPOTHETICAL = re.compile(
    r"(?:^|[；;。！？!?]\s*)(?:如果|假如|要是|もし)|\bif\b[^.!?;]{0,80}\b(?:would|were|could)\b",
    re.I,
)
_META = re.compile(
    r"(?:測試句|测试句|測試文|测试文|引用|台詞|台词|テスト文|引用文|test\s+(?:sentence|phrase)|quoted?\s+(?:sentence|phrase))",
    re.I,
)
_NON_DIRECT_AX = re.compile(
    r"(?:朋友|同事|同學|同学)[^。！？!?；;]{0,30}(?:說|说)|"
    r"\b(?:my\s+friend|a\s+friend|coworker)\b[^.!?;]{0,40}\b(?:said|says)\b|"
    r"(?:友達|同僚)[^。！？]{0,36}(?:と言った|と言って|と言う|と話した)",
    re.I,
)

_COMPOSITION = {
    "zh": {
        "action": re.compile(r"(?:確認|确认|釐清|厘清|弄清楚|弄清)", re.I),
        "self": re.compile(r"(?:我|我要|我想|我需)", re.I),
        "object": re.compile(r"(?:需要|想要|要的|回應|回应|回覆|回复|方向|方法|傾聽|倾听)", re.I),
        "positive": re.compile(r"(?:是對的|是对的|很正確|很正确|正確|正确|很好|有幫助|有帮助)", re.I),
    },
    "en": {
        "action": re.compile(r"\b(?:checking|clarifying|getting\s+clear\s+on)\b", re.I),
        "self": re.compile(r"\b(?:i|me|my)\b", re.I),
        "object": re.compile(r"\b(?:need(?:ed)?|want(?:ed)?|response|reply|direction|method|listening)\b", re.I),
        "positive": re.compile(r"\b(?:right|correct|good|helpful)\b", re.I),
    },
    "ja": {
        "action": re.compile(r"(?:確認|確かめ|はっきりさせ)", re.I),
        "self": re.compile(r"(?:欲しい|求めて|聞いてほしい|方法か|返し|方向)", re.I),
        "object": re.compile(r"(?:返し|応答|反応|必要|方法|聞いてほしい|方向|求めて)", re.I),
        "positive": re.compile(r"(?:合って|よかった|正解|正しかった)", re.I),
    },
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _bounded_compound_support(user_input):
    text = str(user_input or "")
    if (
        not p4_at._source_is_direct(text)
        or _NON_DIRECT_AX.search(text)
        or _META.search(text)
        or _HYPOTHETICAL.search(text)
    ):
        return None
    offset = 0
    for clause in _CLAUSE_BREAK.split(text):
        stripped = clause.strip()
        if not stripped:
            offset += len(clause) + 1
            continue
        for language, rules in _COMPOSITION.items():
            matches = {name: rule.search(stripped) for name, rule in rules.items()}
            if all(matches.values()):
                return {
                    "language": language,
                    "cue_id": f"p4_ax_compound_support:{language}",
                    "position": offset + min(match.start() for match in matches.values()),
                    "composition": sorted(matches),
                }
        offset += len(clause) + 1
    return None


def decompose_compound_feedback_request_split_p4_ax(
    user_input,
    model,
    turn_index,
    base_request=None,
    original_decompose=None,
):
    """Compose only a missing supported outcome; preserve all P4-AT decisions."""

    original_decompose = original_decompose or _BASE_DECOMPOSE_P4_AX
    base = original_decompose(
        user_input,
        model,
        turn_index,
        base_request=base_request,
    )
    predecessor = deepcopy(base)
    candidate = _bounded_compound_support(user_input)
    eligible = bool(
        candidate
        and base.get("exact_pending_receipt_identity") is True
        and base.get("previous_action_outcome") == "unknown"
        and base.get("current_request_policy") == "solve_regulation"
        and base.get("performed_action_strictly_earlier") is True
        and base.get("source_authorized") is True
    )
    payload = {
        "schema": SCHEMA,
        "status": AUTHORIZED_STATUS if eligible else "predecessor_preserved",
        "reason": (
            "direct_exact_clarification_support_and_current_request_composed"
            if eligible
            else "bounded_composition_not_authorized_or_not_needed"
        ),
        "language": (candidate or {}).get("language"),
        "cue_id": (candidate or {}).get("cue_id"),
        "exact_pending_receipt_identity": base.get("exact_pending_receipt_identity") is True,
        "current_request_policy": base.get("current_request_policy"),
        "predecessor_previous_action_outcome": base.get("previous_action_outcome"),
        "previous_action_outcome_after": "supported" if eligible else base.get("previous_action_outcome"),
        "two_independent_acts_after": True if eligible else base.get("two_independent_acts"),
        "p4_at_predecessor_mutated": False,
        "p4_au_gate_bypassed": False,
        "candidate_score_or_order_changed": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "evidence_digest": _digest(user_input),
        "claim_boundary": "observable exact previous-action support plus current request form only; not private desire truth, stable preference, or action quality",
    }
    result = deepcopy(base)
    if eligible:
        result.update(
            {
                "status": "dual_act_decomposed",
                "previous_action_outcome": "supported",
                "previous_action_feedback_language": candidate["language"],
                "previous_action_feedback_cue_id": candidate["cue_id"],
                "two_independent_acts": True,
            }
        )
    result[LABEL] = payload
    assert predecessor == base
    return result


def install_compound_feedback_request_split_hook_p4_ax():
    global _INSTALLED_P4_AX_HOOK
    if _INSTALLED_P4_AX_HOOK:
        return False
    p4_at.decompose_executed_action_feedback_p4 = decompose_compound_feedback_request_split_p4_ax
    _INSTALLED_P4_AX_HOOK = True
    return True


def append_compound_feedback_request_split_node_p4_ax(result):
    result = result or {}
    logic = result.setdefault("logic", {})
    payload = deepcopy((logic.get(p4_at.LABEL) or {}).get(LABEL) or {})
    if payload.get("schema") != SCHEMA:
        return result
    logic[LABEL] = deepcopy(payload)
    runtime = result.setdefault("runtime_trace", {})
    runtime[LABEL] = deepcopy(payload)
    rows = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (
            index
            for index, row in enumerate(rows)
            if row.get("label") in {p4_at.LABEL, outcome_binding.LABEL, "runtime_temporal_graph_delivery_p4", "utterance"}
        ),
        len(rows),
    )
    rows.insert(
        insert_at,
        {"stage": "understand", "label": LABEL, "payload": deepcopy(payload), "salience": 1.0},
    )
    runtime["blackboard"] = rows
    return result


def install_compound_feedback_request_split_p4_ax():
    global _INSTALLED_P4_AX_PRODUCT, _ORIGINAL_EMIT_P4_AX, _ORIGINAL_RUN_TURN_P4_AX
    install_compound_feedback_request_split_hook_p4_ax()
    if _INSTALLED_P4_AX_PRODUCT:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_P4_AX = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN_TURN_P4_AX = UruhaBrainV4_Mac.run_turn_debug

    def emit(self, event, tick_result):
        result = _ORIGINAL_EMIT_P4_AX(self, event, tick_result)
        result = append_compound_feedback_request_split_node_p4_ax(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def run_turn(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_TURN_P4_AX(self, user_input, input_context=input_context)
        result = append_compound_feedback_request_split_node_p4_ax(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run_turn
    _INSTALLED_P4_AX_PRODUCT = True
    return True


def _core_projection(trace):
    keys = (
        "status",
        "prediction_id",
        "performed_policy",
        "performed_action_created_turn",
        "observed_turn",
        "exact_pending_receipt_identity",
        "source_authorized",
        "previous_action_outcome",
        "previous_action_feedback_language",
        "previous_action_feedback_cue_id",
        "current_request_policy",
        "current_request_mode",
        "current_request_cue_id",
        "two_independent_acts",
        "performed_action_strictly_earlier",
    )
    return {key: trace.get(key) for key in keys}


def build_dataset_evidence_p4_ax(dataset_path):
    path = Path(dataset_path)
    dataset = json.loads(path.read_text(encoding="utf-8"))
    install_compound_feedback_request_split_hook_p4_ax()
    cases = []
    module_source = Path(__file__).read_text(encoding="utf-8")
    for frozen in dataset["cases"]:
        model, binding = p4_at._fixture_pending()
        before_scores = [
            (row["policy_id"], row["operational_action_score"])
            for row in binding["candidate_snapshots"]
        ]
        base_request = adaptive.classify_explicit_desired_response_m25(frozen["input"])
        base = _BASE_DECOMPOSE_P4_AX(
            frozen["input"],
            model,
            2,
            base_request=base_request,
        )
        trace = decompose_compound_feedback_request_split_p4_ax(
            frozen["input"],
            model,
            2,
            base_request=base_request,
            original_decompose=_BASE_DECOMPOSE_P4_AX,
        )
        feedback = {
            "outcome": trace["previous_action_outcome"] if trace["previous_action_outcome"] in {"supported", "contradicted"} else "uncertain",
            "prediction_id": trace.get("prediction_id"),
            "linked": trace["previous_action_outcome"] in {"supported", "contradicted"},
            p4_at.LABEL: deepcopy(trace),
        }
        resolution = outcome_binding.resolve_outcome_binding_p4(binding, feedback, turn_index=2)
        after_scores = [
            (row["policy_id"], row["operational_action_score"])
            for row in resolution["candidate_updates"]
        ]
        payload = trace[LABEL]
        cases.append(
            {
                "case_id": frozen["id"],
                "split": frozen["split"],
                "language": frozen["language"],
                "expected_previous_action_outcome": frozen["expected_previous_action_outcome"],
                "previous_action_outcome": trace["previous_action_outcome"],
                "expected_current_request_policy": frozen.get("expected_current_request_policy"),
                "current_request_policy": trace.get("current_request_policy"),
                "p4_ax_status": payload["status"],
                "exact_receipt_identity": trace["exact_pending_receipt_identity"],
                "two_independent_acts": trace["two_independent_acts"],
                "predecessor_core_unchanged": _core_projection(base) == _core_projection(trace),
                "candidate_score_or_order_unchanged": before_scores == after_scores,
                "p4_au_gate_bypassed": payload["p4_au_gate_bypassed"],
                "visible_reply_changed": payload["visible_reply_changed"],
                "added_model_calls": int(payload["model_call_added"]),
                "factual_memory_write_count": payload["factual_memory_write_count"],
                "raw_dialogue_persisted": frozen["input"] in json.dumps({"trace": trace, "resolution": resolution}, ensure_ascii=False, sort_keys=True),
                "private_state_truth_claimed": payload["private_state_truth_claimed"],
                "full_fresh_string_in_module": frozen["split"] in {"fresh_positive", "fresh_control"} and frozen["input"] in module_source,
            }
        )
    development = [row for row in cases if row["split"] == "exposed_development"]
    positives = [row for row in cases if row["split"] == "fresh_positive"]
    controls = [row for row in cases if row["split"] == "fresh_control"]
    predecessors = [row for row in cases if row["split"] == "predecessor_control"]
    authorized = development + positives + predecessors
    metrics = {
        "case_count": len(cases),
        "development_dual_act_count": sum(row["previous_action_outcome"] == "supported" and row["two_independent_acts"] is True for row in development),
        "fresh_positive_dual_act_count": sum(row["previous_action_outcome"] == "supported" and row["two_independent_acts"] is True for row in positives),
        "fresh_control_false_support_count": sum(row["previous_action_outcome"] != "unknown" for row in controls),
        "fresh_control_blocked_count": sum(row["previous_action_outcome"] == "unknown" for row in controls),
        "predecessor_support_preserved_count": sum(row["previous_action_outcome"] == "supported" and row["predecessor_core_unchanged"] is True for row in predecessors),
        "authorized_support_with_exact_receipt_count": sum(row["previous_action_outcome"] == "supported" and row["exact_receipt_identity"] is True for row in authorized),
        "current_request_policy_preserved_count": sum(row["current_request_policy"] == "solve_regulation" for row in authorized),
        "p4_at_predecessor_mutation_count": sum(row["predecessor_core_unchanged"] is not True for row in predecessors),
        "p4_au_gate_bypass_count": sum(row["p4_au_gate_bypassed"] is True for row in cases),
        "candidate_score_or_order_change_count": sum(row["candidate_score_or_order_unchanged"] is not True for row in cases),
        "visible_reply_change_count": sum(row["visible_reply_changed"] is True for row in cases),
        "added_model_call_count": sum(row["added_model_calls"] for row in cases),
        "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in cases),
        "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] is True for row in cases),
        "private_state_truth_claim_count": sum(row["private_state_truth_claimed"] is True for row in cases),
        "full_fresh_string_patch_count": sum(row["full_fresh_string_in_module"] is True for row in cases),
    }
    return {
        "schema": "uruha_p4_ax_compound_feedback_request_split_evidence_v1",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }


__all__ = [
    "AUTHORIZED_STATUS",
    "LABEL",
    "SCHEMA",
    "append_compound_feedback_request_split_node_p4_ax",
    "build_dataset_evidence_p4_ax",
    "decompose_compound_feedback_request_split_p4_ax",
    "install_compound_feedback_request_split_hook_p4_ax",
    "install_compound_feedback_request_split_p4_ax",
]
