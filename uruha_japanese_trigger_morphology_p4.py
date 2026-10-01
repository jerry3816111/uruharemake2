"""P4-AJ additive Japanese predicate-inflection coverage."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_multilingual_observable_trigger_p4 as base_trigger


SCHEMA = "uruha_japanese_trigger_morphology_p4"
_HEAD = r"(?:頭の中|頭|考え|思考|思い|アイデア)"
_PREDICATE = r"(?:止められ(?:なくて|なくなって)|止められず|静まらなくて|落ち着かなくて|休まらなくて|止まんない)"
_META = r"(?:台本|白板|という言葉|単語|引用|書いた)"


def extend_japanese_morphology_p4(user_input, predecessor=None):
    text = str(user_input or "")
    base = deepcopy(predecessor if isinstance(predecessor, dict) else base_trigger.extend_observable_trigger_p4(text))
    result = deepcopy(base)
    existing = "cognitive_overactivity" in set(base.get("predicates") or [])
    matched = bool(not existing and not re.search(_META, text) and re.search(rf"{_HEAD}.{{0,48}}{_PREDICATE}", text))
    if matched:
        result.update({
            "status": "single_observable_trigger",
            "predicates": ["cognitive_overactivity"],
            "matched_languages": sorted({*(base.get("matched_languages") or []), "ja"}),
            "cue_ids": [*(base.get("cue_ids") or []), "cognitive_overactivity:ja:predicate:morphology_p4"],
        })
    result.update({
        "schema": SCHEMA,
        "predecessor_schema": base.get("schema"),
        "morphology_status": "baseline_retained" if existing else "inflection_matched" if matched else "abstained",
        "base_trace_mutated": False,
        "private_state_truth_claimed": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "memory_write_count": 0,
        "raw_dialogue_persisted": False,
    })
    return result


def build_dataset_evidence_p4_aj(path):
    path = Path(path)
    dataset = json.loads(path.read_text(encoding="utf-8"))
    frozen = [
        *(dict(row, partition="development") for row in dataset["development_cases"]),
        *(dict(row, partition="positive") for row in dataset["fresh_positive_cases"]),
        *(dict(row, partition="control") for row in dataset["fresh_control_cases"]),
    ]
    source = Path(__file__).read_text(encoding="utf-8")
    rows = []
    for row in frozen:
        predecessor = base_trigger.extend_observable_trigger_p4(row["input"])
        before = deepcopy(predecessor)
        trace = extend_japanese_morphology_p4(row["input"], predecessor)
        serialized = json.dumps(trace, ensure_ascii=False)
        rows.append({
            "case_id": row["case_id"], "partition": row["partition"],
            "detected": "cognitive_overactivity" in set(trace.get("predicates") or []),
            "private_truth_claimed": trace["private_state_truth_claimed"],
            "predecessor_mutated": predecessor != before,
            "complete_case_string_in_source": row["input"] in source,
            "visible_reply_changed": trace["visible_reply_changed"],
            "model_call_added": trace["model_call_added"],
            "memory_write_count": trace["memory_write_count"],
            "raw_dialogue_persisted": trace["raw_dialogue_persisted"] or row["input"] in serialized,
        })
    dev = rows[:1]; pos = rows[1:7]; controls = rows[7:]
    return {
        "schema": "uruha_p4_aj_evidence_v1",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": rows,
        "metrics": {
            "case_count": len(rows),
            "development_detected_count": sum(r["detected"] for r in dev),
            "fresh_positive_detected_count": sum(r["detected"] for r in pos),
            "fresh_control_abstention_count": sum(not r["detected"] for r in controls),
            "private_truth_claim_count": sum(r["private_truth_claimed"] is not False for r in rows),
            "predecessor_mutation_count": sum(r["predecessor_mutated"] for r in rows),
            "complete_case_string_in_source_count": sum(r["complete_case_string_in_source"] for r in rows),
            "visible_reply_changed_count": sum(r["visible_reply_changed"] for r in rows),
            "model_call_added_count": sum(r["model_call_added"] for r in rows),
            "memory_write_count": sum(r["memory_write_count"] for r in rows),
            "raw_dialogue_persisted_count": sum(r["raw_dialogue_persisted"] for r in rows),
        },
    }
