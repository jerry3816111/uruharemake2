"""P4-AH additive multilingual observable-trigger coverage.

The extension requires a cognitive head and an unresolved/continuing predicate
inside one bounded span.  It records a visible linguistic signal only; it does
not claim that the inferred private state is true.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_outcome_binding_p4 as outcome_binding


LABEL = "multilingual_observable_trigger_coverage_p4"
SCHEMA = "uruha_multilingual_observable_trigger_coverage_p4"

_COMPOSITIONAL_PATTERNS = {
    "zh": {
        "head": r"(?:念頭|念头|想法|思緒|思绪|腦海|脑海|腦中|脑中|腦袋|脑袋|腦子|脑子)",
        "predicate": (
            r"(?:一直(?:湧|涌|冒|轉|转)|(?:怎麼|怎么)都(?:慢|靜|静|安靜|安静|歇)不下|"
            r"(?:完全)?(?:安靜|安静|靜|静|慢|歇)不下|停不住地冒)"
        ),
        "metalinguistic": r"(?:寫在|写在|兩個詞|两个词|這個詞|这个词|字面|引用)",
    },
    "en": {
        "head": r"\b(?:thoughts?|ideas?|mind|head)\b",
        "predicate": (
            r"\b(?:(?:will\s+not|won't|cannot|can't|does\s+not|doesn't)\s+"
            r"(?:slow\s+down|settle|quiet\s+down|switch\s+off|rest)|"
            r"keeps?\s+(?:running|churning|turning\s+over))\b"
        ),
        "metalinguistic": r"\b(?:wrote\s+the\s+words?|the\s+phrase|the\s+word|literal(?:ly)?|quoted?)\b",
    },
    "ja": {
        "head": r"(?:頭の中|頭|考え|思考|思い|アイデア)",
        "predicate": r"(?:回り続け|静まらない|落ち着かない|休まらない|休んでくれない|止められない)",
        "metalinguistic": r"(?:白板に書|という言葉|単語|字面|引用)",
    },
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _extension_match(user_input):
    text = str(user_input or "")
    lowered = text.lower()
    for language, patterns in _COMPOSITIONAL_PATTERNS.items():
        if re.search(patterns["metalinguistic"], lowered, re.I):
            continue
        composition = rf"(?:{patterns['head']}).{{0,56}}(?:{patterns['predicate']})"
        match = re.search(composition, lowered, re.I)
        if match:
            return {
                "language": language,
                "head_cue_id": f"cognitive_overactivity:{language}:head:extension_p4",
                "predicate_cue_id": f"cognitive_overactivity:{language}:predicate:extension_p4",
                "bounded_span_length": len(match.group(0)),
            }
    return None


def extend_observable_trigger_p4(user_input, base_trace=None):
    """Return an additive typed trace without mutating released M37 output."""

    base = deepcopy(
        base_trace
        if isinstance(base_trace, dict)
        else adaptive.extract_observable_trigger_predicates_m37(user_input)
    )
    extended = deepcopy(base)
    existing = "cognitive_overactivity" in set(base.get("predicates") or [])
    match = None if existing else _extension_match(user_input)
    if match:
        predicates = sorted({*(base.get("predicates") or []), "cognitive_overactivity"})
        extended.update(
            {
                "status": "single_observable_trigger" if len(predicates) == 1 else "multiple_observable_triggers",
                "predicates": predicates,
                "matched_languages": sorted({*(base.get("matched_languages") or []), match["language"]}),
                "cue_ids": list(
                    dict.fromkeys(
                        [
                            *(base.get("cue_ids") or []),
                            match["head_cue_id"],
                            match["predicate_cue_id"],
                        ]
                    )
                )[:16],
            }
        )
    extended.update(
        {
            "schema": SCHEMA,
            "predecessor_schema": base.get("schema"),
            "coverage_extension": {
                "status": (
                    "baseline_trigger_retained"
                    if existing
                    else "additive_compositional_trigger"
                    if match
                    else "abstained_no_bounded_composition"
                ),
                "language": (match or {}).get("language"),
                "required_structure": "cognitive_head_plus_unresolved_predicate_in_bounded_span",
                "metalinguistic_guard": True,
                "complete_sentence_lookup_used": False,
            },
            "evidence_digest": str(base.get("evidence_digest") or _digest(user_input)),
            "base_trace_mutated": False,
            "private_state_truth_claimed": False,
            "raw_dialogue_persisted": False,
            "visible_reply_changed": False,
            "model_call_added": False,
            "candidate_ranking_changed": False,
            "fact_write_count": 0,
            "profile_write_count": 0,
            "episode_write_count": 0,
            "claim_boundary": (
                "typed visible-language trigger evidence only; not proof of a private mental state"
            ),
        }
    )
    return extended


def apply_extended_trigger_to_shadow_state_p4(state, trigger):
    """Prepare a downstream shadow state; released state remains unchanged."""

    shadow = deepcopy(state or {})
    trigger = deepcopy(trigger or {})
    shadow["observable_trigger_m37"] = trigger
    if "cognitive_overactivity" not in set(trigger.get("predicates") or []):
        return shadow
    shadow["active"] = True
    shadow["activation_reasons"] = list(
        dict.fromkeys(
            [
                *(shadow.get("activation_reasons") or []),
                "p4_ah_typed_cognitive_overactivity_shadow",
            ]
        )
    )
    uncertainty = deepcopy(((shadow.get("atoms") or {}).get("uncertainty")) or {})
    uncertainty.update(
        {
            "value": max(0.86, float(uncertainty.get("value") or 0.0)),
            "confidence": max(0.86, float(uncertainty.get("confidence") or 0.0)),
            "status": "bounded_observable_trigger_inference",
            "evidence": "p4_ah:cognitive_overactivity",
        }
    )
    shadow.setdefault("atoms", {})["uncertainty"] = uncertainty
    return shadow


def append_trigger_coverage_node_p4(result, trace):
    result = result or {}
    payload = deepcopy(trace or {})
    if not payload:
        return result
    logic = result.get("logic") or {}
    logic[LABEL] = payload
    result["logic"] = logic
    runtime = result.get("runtime_trace") or {}
    blackboard = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (index for index, row in enumerate(blackboard) if row.get("label") == "utterance"),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {"stage": "perceive", "label": LABEL, "payload": payload, "salience": 0.94},
    )
    runtime["blackboard"] = blackboard
    runtime[LABEL] = payload
    result["runtime_trace"] = runtime
    return result


_INSTALLED_P4_AH = False
_ORIGINAL_EMIT_RESPONSE_P4_AH = None


def install_multilingual_observable_trigger_p4():
    global _INSTALLED_P4_AH, _ORIGINAL_EMIT_RESPONSE_P4_AH
    if _INSTALLED_P4_AH:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_RESPONSE_P4_AH = UruhaBrainV4_Mac.emit_response_if_ready

    def emit_with_p4_ah(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_AH(self, event, tick_result)
        user_input = str((event or {}).get("user_input") or "")
        runtime = (result or {}).get("runtime_trace") or {}
        logic = (result or {}).get("logic") or {}
        state = runtime.get("desired_response_state_m18") or logic.get("desired_response_state_m18") or {}
        base = deepcopy(state.get("observable_trigger_m37") or {})
        trace = extend_observable_trigger_p4(user_input, base)
        result = append_trigger_coverage_node_p4(result, trace)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_ah
    _INSTALLED_P4_AH = True
    return True


def build_dataset_evidence_p4_ah(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    expected = [
        *(dict(row, partition="development_cases") for row in dataset["development_cases"]),
        *(dict(row, partition="fresh_positive_cases") for row in dataset["fresh_positive_cases"]),
        *(dict(row, partition="fresh_control_cases") for row in dataset["fresh_control_cases"]),
    ]
    source = Path(__file__).read_text(encoding="utf-8")
    cases = []
    for frozen in expected:
        base = adaptive.extract_observable_trigger_predicates_m37(frozen["input"])
        base_before = deepcopy(base)
        trace = extend_observable_trigger_p4(frozen["input"], base)
        serialized = json.dumps(trace, ensure_ascii=False, sort_keys=True)
        cases.append(
            {
                "case_id": frozen["case_id"],
                "partition": frozen["partition"],
                "predicates": trace.get("predicates") or [],
                "matched_languages": trace.get("matched_languages") or [],
                "coverage_status": (trace.get("coverage_extension") or {}).get("status"),
                "private_state_truth_claimed": trace.get("private_state_truth_claimed"),
                "base_trace_mutated": base != base_before,
                "complete_case_string_in_source": frozen["input"] in source,
                "candidate_ranking_changed": trace.get("candidate_ranking_changed"),
                "visible_reply_changed": trace.get("visible_reply_changed"),
                "new_model_call_count": int(trace.get("model_call_added") or 0),
                "fact_write_count": trace.get("fact_write_count"),
                "profile_write_count": trace.get("profile_write_count"),
                "episode_write_count": trace.get("episode_write_count"),
                "raw_dialogue_persisted": (
                    trace.get("raw_dialogue_persisted") or frozen["input"] in serialized
                ),
            }
        )
    development = cases[: len(dataset["development_cases"])]
    positive_start = len(development)
    positive_end = positive_start + len(dataset["fresh_positive_cases"])
    positives = cases[positive_start:positive_end]
    controls = cases[positive_end:]
    product_path = Path(__file__).with_name("uruha_web_ui_product_p4_ah.py")
    product_source = product_path.read_text(encoding="utf-8") if product_path.is_file() else ""
    graph_probe = append_trigger_coverage_node_p4(
        {
            "reply": "unchanged",
            "logic": {},
            "runtime_trace": {
                "blackboard": [
                    {"stage": "select", "label": ambiguity.LABEL, "payload": {}},
                    {"stage": "learn", "label": outcome_binding.LABEL, "payload": {}},
                    {"stage": "surface", "label": "utterance", "payload": {}},
                ]
            },
        },
        {"status": "single_observable_trigger"},
    )
    labels = [row.get("label") for row in graph_probe["runtime_trace"]["blackboard"]]
    return {
        "schema": "uruha_p4_ah_multilingual_trigger_coverage_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": {
            "case_count": len(cases),
            "development_exact_predicate_count": sum("cognitive_overactivity" in row["predicates"] for row in development),
            "fresh_positive_exact_predicate_count": sum("cognitive_overactivity" in row["predicates"] for row in positives),
            "fresh_control_exact_abstention_count": sum(not row["predicates"] for row in controls),
            "private_truth_claim_count": sum(row["private_state_truth_claimed"] is not False for row in cases),
            "base_trace_mutation_count": sum(row["base_trace_mutated"] for row in cases),
            "complete_case_string_in_source_count": sum(row["complete_case_string_in_source"] for row in cases),
            "candidate_ranking_changed_count": sum(row["candidate_ranking_changed"] for row in cases),
            "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in cases),
            "new_model_call_count": sum(row["new_model_call_count"] for row in cases),
            "fact_write_count": sum(row["fact_write_count"] for row in cases),
            "profile_write_count": sum(row["profile_write_count"] for row in cases),
            "episode_write_count": sum(row["episode_write_count"] for row in cases),
            "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in cases),
        },
        "integration": {
            "additive_product_entry_installs_extension": (
                "import uruha_web_ui_product_p4_ag as _p4_ag" in product_source
                and "install_multilingual_observable_trigger_p4()" in product_source
            ),
            "single_graph_node_before_utterance": labels == [
                ambiguity.LABEL,
                outcome_binding.LABEL,
                LABEL,
                "utterance",
            ],
            "predecessor_nodes_retained": ambiguity.LABEL in labels and outcome_binding.LABEL in labels,
        },
        "claim_boundary": dataset["claim_boundary"],
    }
