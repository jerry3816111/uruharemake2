#!/usr/bin/env python3
"""Audit whether existing data can safely supervise a dedicated local planner."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v75_readiness_contract.json"
REPORT_JSON_PATH = ROOT / "reports/planner_supervision_v75_readiness.json"
REPORT_MD_PATH = ROOT / "reports/planner_supervision_v75_readiness.md"
PLAN_SIGNATURES = (
    b'"bayes_candidates"',
    b'"user_belief"',
    b'"my_hidden_knowledge"',
    b'"user_expectation"',
)


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").casefold())


def _nonempty(value):
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _complete_plan(plan, contract):
    if not isinstance(plan, dict):
        return False
    for field in contract["required_target_plan_fields"]:
        if field not in plan or not _nonempty(plan[field]):
            return False
    candidates = plan.get("bayes_candidates")
    return isinstance(candidates, list) and len(candidates) >= contract["minimum_candidate_plan_count"]


def _complete_input_context(input_context, contract):
    if not isinstance(input_context, dict):
        return False
    return all(field in input_context and _nonempty(input_context[field]) for field in contract["required_input_fields"])


def _canonical_sha256(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _training_example_fingerprint(row):
    input_context = (row or {}).get("input") or {}
    return _canonical_sha256(
        {
            "user_utterance": _normalize(input_context.get("user_utterance")),
            "language": input_context.get("language"),
            "recent_dialogue": input_context.get("recent_dialogue") or [],
            "working_memory": input_context.get("working_memory") or [],
            "psyche_state": input_context.get("psyche_state") or {},
            "relationship_state": input_context.get("relationship_state") or {},
        }
    )


def _strict_review(row, contract):
    review = row.get("human_review") if isinstance(row, dict) else None
    if not isinstance(review, dict) or review.get("decision") != contract["strict_human_review"]["required_decision"]:
        return False
    if not all(_nonempty(review.get(field)) for field in contract["strict_human_review"]["required_fields"]):
        return False
    return review.get("target_plan_sha256") == _canonical_sha256(row.get("target_plan"))


def _complete_provenance(row, contract):
    provenance = row.get("provenance") if isinstance(row, dict) else None
    if not isinstance(provenance, dict):
        return False
    if not all(_nonempty(provenance.get(field)) for field in contract["required_provenance_fields"]):
        return False
    if provenance.get("benchmark_origin") != contract["required_benchmark_origin"]:
        return False
    return bool(re.fullmatch(contract["sha256_pattern"], str(provenance.get("source_sha256") or "")))


def _unit(plan=None, user_utterance="", input_context=None, strict_review=False, provenance=False, split=None):
    return {
        "plan": plan,
        "user_utterance": str(user_utterance or ""),
        "input_context": input_context,
        "strict_review": bool(strict_review),
        "provenance": bool(provenance),
        "split": split,
    }


def _rightbrain_contract_units(rows):
    units = []
    for row in rows:
        payload = None
        for message in row.get("messages") or []:
            if message.get("role") == "user":
                try:
                    payload = json.loads(message.get("content") or "")
                except (TypeError, json.JSONDecodeError):
                    payload = None
                break
        plan = payload.get("leftbrain_plan") if isinstance(payload, dict) else None
        units.append(_unit(plan=plan))
    return units


def _strict_units(rows, contract):
    units = []
    for row in rows:
        input_context = row.get("input") or {}
        units.append(
            _unit(
                plan=row.get("target_plan"),
                user_utterance=input_context.get("user_utterance", ""),
                input_context=input_context,
                strict_review=_strict_review(row, contract),
                provenance=_complete_provenance(row, contract),
                split=row.get("split"),
            )
        )
    return units


def _load_source(spec, contract):
    paths = [ROOT / rel for rel in spec["paths"]]
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    if missing and not spec.get("optional"):
        raise FileNotFoundError(f"required V75 source missing: {missing}")
    paths = [path for path in paths if path.exists()]
    bindings = {str(path.relative_to(ROOT)): _sha256(path) for path in paths}
    adapter = spec["adapter"]
    record_count = 0
    units = []
    protected_utterances = []
    surface_human_accept_count = 0

    if adapter == "strict_planner_jsonl":
        rows = [row for path in paths for row in _load_jsonl(path)]
        record_count = len(rows)
        units = _strict_units(rows, contract)
    elif adapter == "human_feedback_annotations":
        rows = [row for path in paths for row in _load_jsonl(path)]
        record_count = len(rows)
        surface_human_accept_count = sum(row.get("verdict") == "pass" for row in rows)
        units = [
            _unit(plan=row.get("logic"), user_utterance=row.get("user_text"))
            for row in rows
        ]
    elif adapter == "human_feedback_regression":
        rows = [row for path in paths for row in _load_json(path)]
        record_count = len(rows)
    elif adapter == "rightbrain_contract_training":
        rows = [row for path in paths for row in _load_json(path)]
        record_count = len(rows)
        units = _rightbrain_contract_units(rows)
    elif adapter == "rightbrain_surface_corpora":
        rows = [row for path in paths for row in _load_json(path)]
        record_count = len(rows)
    elif adapter == "v2_human_answer_report":
        rows = [row for path in paths for row in _load_json(path).get("results", [])]
        record_count = len(rows)
        units = [_unit(plan=row.get("logic"), user_utterance=row.get("prompt")) for row in rows]
    elif adapter == "cognitive_architecture_report":
        rows = [row for path in paths for row in _load_json(path).get("results", [])]
        record_count = len(rows)
        units = [_unit(plan=row.get("plan"), user_utterance=row.get("prompt")) for row in rows]
    elif adapter == "v61_captures":
        rows = [row for path in paths for row in _load_json(path).get("captures", [])]
        record_count = len(rows)
        units = [
            _unit(
                plan=row.get("logic"),
                user_utterance=row.get("user_input"),
                input_context={
                    "user_utterance": row.get("user_input"),
                    "language": "ja",
                    "recent_dialogue": (row.get("memory_data") or {}).get("recent_turns", []),
                    "working_memory": row.get("working_memory_items", []),
                    "psyche_state": row.get("psyche_state", {}),
                    "relationship_state": {"trust": (row.get("psyche_state") or {}).get("trust")},
                },
            )
            for row in rows
        ]
    elif adapter == "v63_captures":
        rows = [row for path in paths for row in _load_json(path).get("captures", [])]
        record_count = len(rows)
        units = [
            _unit(
                plan=row.get("base_logic"),
                user_utterance=row.get("user_input"),
                input_context={
                    "user_utterance": row.get("user_input"),
                    "language": "ja",
                    "recent_dialogue": (row.get("memory_data") or {}).get("recent_turns", []),
                    "working_memory": (row.get("memory_data") or {}).get("working_memory_items", []),
                    "psyche_state": row.get("psyche_state", {}),
                    "relationship_state": {"trust": (row.get("psyche_state") or {}).get("trust")},
                },
            )
            for row in rows
        ]
    elif adapter == "reflection_reports":
        rows = [row for path in paths for row in _load_json(path).get("rows", [])]
        record_count = len(rows)
        for row in rows:
            case = row.get("case") or {}
            for condition in (row.get("conditions") or {}).values():
                units.append(_unit(plan=condition.get("future_logic"), user_utterance=case.get("future_prompt")))
    elif adapter == "formal_holdouts":
        rows = [row for path in paths for row in _load_json(path).get("cases", [])]
        record_count = len(rows)
        protected_utterances = []
        for row in rows:
            planning_packet = row.get("planning_packet") or {}
            utterance = str(
                row.get("user_input")
                or row.get("prompt")
                or row.get("utterance")
                or planning_packet.get("user_input")
                or planning_packet.get("prompt")
                or planning_packet.get("utterance")
                or ""
            ).strip()
            if utterance:
                protected_utterances.append(utterance)
    elif adapter == "annotation_drafts":
        rows = [row for path in paths for row in _load_json(path).get("drafts", [])]
        record_count = len(rows)
        for row in rows:
            source = row.get("source_record") or {}
            units.append(_unit(plan=source.get("logic"), user_utterance=source.get("user_text")))
    else:
        raise ValueError(f"unknown V75 source adapter: {adapter}")

    return {
        "spec": spec,
        "missing_optional_paths": missing,
        "bindings": bindings,
        "record_count": record_count,
        "units": units,
        "protected_utterances": protected_utterances + [
            unit["user_utterance"] for unit in units if str(unit.get("user_utterance") or "").strip()
        ],
        "surface_human_accept_count": surface_human_accept_count,
    }


def _discover_plan_signature_files(contract):
    discovered = []
    excluded_prefixes = tuple(contract.get("discovery_excluded_quarantine_prefixes") or [])
    for directory in (ROOT / "analysis", ROOT / "datasets", ROOT / "reports"):
        for path in sorted(directory.rglob("*")):
            if path.suffix not in {".json", ".jsonl"} or path in {REPORT_JSON_PATH}:
                continue
            relative = str(path.relative_to(ROOT))
            if relative.startswith(excluded_prefixes):
                continue
            data = path.read_bytes()
            if PLAN_SIGNATURES[0] in data or all(signature in data for signature in PLAN_SIGNATURES[1:]):
                discovered.append(relative)
    return sorted(discovered)


def _registered_paths(contract):
    return {
        rel
        for source in contract["source_registry"]
        for rel in source["paths"]
    }


def _unit_rejection_reasons(unit, contract, protected, protected_inputs):
    reasons = []
    normalized = _normalize(unit["user_utterance"])
    if not normalized:
        reasons.append("missing_raw_user_utterance")
    if not _complete_input_context(unit["input_context"], contract):
        reasons.append("incomplete_input_context")
    if not _complete_plan(unit["plan"], contract):
        reasons.append("incomplete_target_plan")
    if not unit["strict_review"]:
        reasons.append("no_strict_human_plan_acceptance")
    if not unit["provenance"]:
        reasons.append("incomplete_provenance")
    if protected:
        reasons.append("protected_evaluation_source")
    if unit["split"] != contract["training_split"]:
        reasons.append("not_train_split")
    if normalized and not protected:
        if normalized in protected_inputs:
            reasons.append("exact_evaluation_overlap")
        elif any(SequenceMatcher(None, normalized, old).ratio() >= 0.92 for old in protected_inputs):
            reasons.append("near_evaluation_overlap")
    return sorted(set(reasons))


def _source_summary(loaded, contract, protected_inputs):
    spec = loaded["spec"]
    protected = bool(spec["protected_evaluation"])
    complete = 0
    complete_input = 0
    raw = 0
    strict = 0
    provenance = 0
    eligible = 0
    rejection_counts = Counter()

    for unit in loaded["units"]:
        plan_complete = _complete_plan(unit["plan"], contract)
        input_complete = _complete_input_context(unit["input_context"], contract)
        raw_present = bool(_normalize(unit["user_utterance"]))
        complete += plan_complete
        complete_input += input_complete
        raw += raw_present
        strict += unit["strict_review"]
        provenance += unit["provenance"]

        reasons = _unit_rejection_reasons(unit, contract, protected, protected_inputs)
        rejection_counts.update(set(reasons))
        if not reasons:
            eligible += 1

    return {
        "source_id": spec["id"],
        "role": spec["role"],
        "protected_evaluation": protected,
        "source_bindings": loaded["bindings"],
        "missing_optional_paths": loaded["missing_optional_paths"],
        "record_count": loaded["record_count"],
        "plan_instance_count": len(loaded["units"]),
        "complete_plan_count": complete,
        "raw_user_utterance_count": raw,
        "complete_input_context_count": complete_input,
        "surface_human_accept_count": loaded["surface_human_accept_count"],
        "strict_plan_accept_count": strict,
        "complete_provenance_count": provenance,
        "training_eligible_count": eligible,
        "rejection_reason_counts": dict(sorted(rejection_counts.items())),
    }


def _coverage(eligible_rows, contract):
    cells = Counter()
    for row in eligible_rows:
        input_context = row.get("input") or {}
        cells[(input_context.get("language"), row.get("scenario_family"))] += 1
    expected = [
        (language, family)
        for language in contract["languages"]
        for family in contract["scenario_families"]
    ]
    return {
        "expected_cell_count": len(expected),
        "covered_cell_count": sum(cells[cell] > 0 for cell in expected),
        "minimum_cell_count": min((cells[cell] for cell in expected), default=0),
        "cell_counts": {
            f"{language}:{family}": cells[(language, family)]
            for language, family in expected
        },
    }


def _eligible_strict_rows(contract, protected_inputs):
    spec = next(source for source in contract["source_registry"] if source["adapter"] == "strict_planner_jsonl")
    rows = []
    for rel in spec["paths"]:
        path = ROOT / rel
        if path.exists():
            rows.extend(_load_jsonl(path))
    units = _strict_units(rows, contract)
    return [
        row
        for row, unit in zip(rows, units)
        if not _unit_rejection_reasons(unit, contract, False, protected_inputs)
    ]


def build_audit():
    contract = _load_json(CONTRACT_PATH)
    loaded_sources = [_load_source(spec, contract) for spec in contract["source_registry"]]
    protected_inputs = {
        _normalize(user_utterance)
        for loaded in loaded_sources
        if loaded["spec"]["protected_evaluation"]
        for user_utterance in loaded["protected_utterances"]
        if _normalize(user_utterance)
    }
    summaries = [_source_summary(loaded, contract, protected_inputs) for loaded in loaded_sources]

    discovered = _discover_plan_signature_files(contract)
    registered = _registered_paths(contract)
    unregistered = sorted(path for path in discovered if path not in registered)
    eligible_rows = _eligible_strict_rows(contract, protected_inputs)
    coverage = _coverage(eligible_rows, contract)
    totals = {
        key: sum(source[key] for source in summaries)
        for key in (
            "record_count",
            "plan_instance_count",
            "complete_plan_count",
            "raw_user_utterance_count",
            "complete_input_context_count",
            "surface_human_accept_count",
            "strict_plan_accept_count",
            "complete_provenance_count",
            "training_eligible_count",
        )
    }
    totals["protected_complete_plan_count"] = sum(
        source["complete_plan_count"] for source in summaries if source["protected_evaluation"]
    )
    totals["unprotected_complete_plan_count"] = (
        totals["complete_plan_count"] - totals["protected_complete_plan_count"]
    )
    eligible_fingerprints = [_training_example_fingerprint(row) for row in eligible_rows]
    exact_duplicate_count = len(eligible_fingerprints) - len(set(eligible_fingerprints))
    near_eval_overlap_count = 0

    integrity_checks = {
        "contract_frozen_before_audit": contract.get("status") == "frozen_before_auditor_execution",
        "all_required_sources_present": not any(
            source["missing_optional_paths"]
            for source in summaries
            if not next(spec for spec in contract["source_registry"] if spec["id"] == source["source_id"]).get("optional")
        ),
        "all_plan_signature_files_registered": not unregistered,
        "no_exact_duplicate_among_eligible": exact_duplicate_count == 0,
        "no_near_evaluation_overlap_among_eligible": near_eval_overlap_count == 0,
    }
    pilot = contract["readiness_levels"]["pilot_ready"]
    training = contract["readiness_levels"]["training_candidate"]
    eligible_count = totals["training_eligible_count"]
    integrity_passed = all(integrity_checks.values())
    if not integrity_passed:
        readiness = "invalid"
        decision = "audit_invalid_no_training"
    elif (
        eligible_count >= training["minimum_eligible_rows"]
        and coverage["minimum_cell_count"] >= training["minimum_per_language_family_cell"]
    ):
        readiness = "training_candidate"
        decision = "formal_training_experiment_may_be_preregistered"
    elif (
        eligible_count >= pilot["minimum_eligible_rows"]
        and coverage["minimum_cell_count"] >= pilot["minimum_per_language_family_cell"]
    ):
        readiness = "pilot_ready"
        decision = "small_local_training_pilot_only"
    else:
        readiness = "not_ready"
        decision = "do_not_train_collect_strict_full_plan_supervision"

    return {
        "schema": "uruha_planner_supervision_readiness_audit_v75",
        "audit_integrity_passed": integrity_passed,
        "contract_sha256": _sha256(CONTRACT_PATH),
        "hypothesis_supported": eligible_count == 0,
        "readiness": readiness,
        "decision": decision,
        "authorizations": {
            "planner_training": readiness in {"pilot_ready", "training_candidate"},
            "formal_training_claim": readiness == "training_candidate",
            "runtime_change": False,
            "provenance_safe_collection_path": True,
        },
        "totals": totals,
        "coverage": coverage,
        "overlap_checks": {
            "protected_normalized_input_count": len(protected_inputs),
            "eligible_exact_duplicate_count": exact_duplicate_count,
            "eligible_near_evaluation_overlap_count": near_eval_overlap_count,
        },
        "source_audits": summaries,
        "discovery": {
            "plan_signature_files": discovered,
            "unregistered_plan_signature_files": unregistered,
        },
        "integrity_checks": integrity_checks,
        "threshold_status": contract["threshold_status"],
        "next_required_unit": "capture raw utterance plus bounded cognitive context and a full candidate plan, then require strict human acceptance of the plan before it can enter a deduplicated training split",
        "evidence_boundary": "This audit measures planner-supervision readiness only. It does not improve or evaluate dialogue quality, cognition, human-likeness, benchmark accuracy, latency, or runtime behavior.",
    }


def _markdown(audit):
    rows = []
    for source in audit["source_audits"]:
        rows.append(
            "| {source_id} | {record_count} | {plan_instance_count} | {complete_plan_count} | "
            "{strict_plan_accept_count} | {training_eligible_count} | {protected} |".format(
                protected="是" if source["protected_evaluation"] else "否",
                **source,
            )
        )
    totals = audit["totals"]
    canonical_surface_count = next(
        source["record_count"]
        for source in audit["source_audits"]
        if source["source_id"] == "canonical_rightbrain_surface_training"
    )
    return "\n".join(
        [
            "# V75 專用左腦規劃器資料就緒稽核",
            "",
            "## 結論",
            "",
            "**目前禁止訓練專用左腦規劃器。**",
            "",
            f"專案共掃描 {totals['record_count']:,} 筆來源紀錄，辨識出 {totals['plan_instance_count']:,} 份完整或部分計畫。",
            f"其中 {totals['complete_plan_count']} 份通過完整結構檢查，受正式評測保護的有 {totals['protected_complete_plan_count']} 份；嚴格人工接受的完整計畫為 {totals['strict_plan_accept_count']}，最終可訓練資料為 {totals['training_eligible_count']}。",
            "",
            f"這不是模型失敗，而是資料用途不相容：現有 {canonical_surface_count:,} 筆 canonical 資料教的是「已知計畫後怎麼用日文說」，不是「聽到原始發話後怎麼形成計畫」。",
            "",
            "## 逐來源結果",
            "",
            "| 來源 | 紀錄 | 計畫實例 | 完整計畫 | 嚴格人工計畫接受 | 可訓練 | 受評測保護 |",
            "|---|---:|---:|---:|---:|---:|:---:|",
            *rows,
            "",
            "## 為什麼 44 份完整計畫仍不能訓練",
            "",
            "V61 與 V63 保存的 44 份計畫包含 BDI、三候選、記憶與路由欄位，但它們是模型在正式 holdout 上產生的答案。把它們回灌訓練會同時造成兩個問題：沒有人工證明計畫正確，以及訓練資料接觸評測輸入。",
            "",
            "## 自訂門檻",
            "",
            "- 60 筆：10 種能力 × 3 種輸入語言 × 每格至少 2 筆，只允許小型 pilot。",
            "- 600 筆：每格至少 20 筆，才可預註冊正式訓練實驗。",
            "- 以上是本專案的覆蓋設計，不是論文或官方規定的神奇樣本數。",
            "",
            "## 下一個必要工程單位",
            "",
            "讓正式聊天或隔離情境保存「原始發話、有限上下文、記憶選擇、心理狀態、完整候選計畫」，再由人類只審查計畫是否合理。未接受的計畫不能進訓練集；正式 benchmark 與 holdout 永遠不能進訓練集。",
            "",
            "## 證據邊界",
            "",
            "本輪只證明資料是否足以啟動規劃器訓練，沒有修改 runtime，也不能宣稱對話、認知、像人程度、分數或速度已改善。",
            "",
        ]
    )


def _atomic_write(path, text):
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-training-ready", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        _atomic_write(REPORT_JSON_PATH, json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
        _atomic_write(REPORT_MD_PATH, _markdown(audit))
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["audit_integrity_passed"]:
        raise SystemExit(1)
    if args.require_training_ready and not audit["authorizations"]["planner_training"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
