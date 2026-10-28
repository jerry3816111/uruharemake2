"""P3-C1 controlled context-flip contract, blinded packet, and offline metrics.

This module intentionally makes no model or network call.  It freezes the
comparison inputs and target-side scoring contract before a later execution
stage can expose results.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import fmean
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_c1_controlled_context_flip_lane_v1.json"
DATASET_PATH = ROOT / "datasets" / "p3_c1_controlled_context_flip_pairs_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_c1_controlled_context_flip_implementation_freeze_2026-09-20.json"

TARGET_LABELS = ["LITERAL_READING", "PRAGMATIC_READING", "UNCERTAIN"]
CONDITIONS = ["BASELINE_DIRECT", "SYSTEM_PRAGMATIC_STATE"]
SPLITS = ["train", "dev", "holdout"]
LANGUAGES = ["zh", "en", "ja"]
VARIANTS = ["literal_control", "pragmatic_flip"]
PAIR_ID_RE = re.compile(r"^(train|dev|holdout)_(zh|en|ja)_[0-9]{2}$")
FAMILY_ID_RE = re.compile(r"^sf_(zh|en|ja)_[a-z0-9_]+$")
JAPANESE_SCRIPT_RE = re.compile(r"[\u3040-\u30ff]")


class C1ContractError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise C1ContractError(f"not_object:{path}")
    return value


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def load_dataset() -> dict[str, Any]:
    return load_json(DATASET_PATH)


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_c1_controlled_context_flip_lane_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_offline_contract_before_any_p3_c_model_call":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    dataset = contract.get("dataset") or {}
    if dataset.get("path") != "datasets/p3_c1_controlled_context_flip_pairs_v1.json":
        errors.append("dataset:path")
    if dataset.get("pair_count_exact") != 18:
        errors.append("dataset:pair_count")
    if dataset.get("split_pair_counts") != {"train": 6, "dev": 6, "holdout": 6}:
        errors.append("dataset:splits")
    if dataset.get("language_pair_counts") != {"zh": 6, "en": 6, "ja": 6}:
        errors.append("dataset:languages")
    if dataset.get("target_labels") != TARGET_LABELS:
        errors.append("dataset:labels")
    for field, value in {
        "same_surface_form_required_within_pair": True,
        "surface_family_overlap_across_splits_allowed": False,
        "developer_authored": True,
        "human_validated": False,
        "independent_holdout": False,
    }.items():
        if dataset.get(field) is not value:
            errors.append(f"dataset:{field}")
    conditions = contract.get("conditions") or {}
    if list(conditions) != CONDITIONS:
        errors.append("conditions")
    else:
        evaluated = [
            "probabilities",
            "selected_interpretation",
            "visible_reply_ja",
            "brief_evidence_anchor_ids",
        ]
        if conditions["BASELINE_DIRECT"].get("evaluated_output_fields") != evaluated:
            errors.append("conditions:baseline_output")
        if conditions["SYSTEM_PRAGMATIC_STATE"].get("evaluated_output_fields") != evaluated:
            errors.append("conditions:system_output")
        if len(conditions["SYSTEM_PRAGMATIC_STATE"].get("additional_observable_state_fields") or []) != 8:
            errors.append("conditions:system_state")
    fairness = contract.get("fairness") or {}
    required_true = {
        "same_base_model",
        "same_complete_observable_input",
        "same_interpretation_options",
        "same_persona_and_visible_language_boundary",
        "same_provider_hardware_and_condition_order_schedule",
        "same_decoding_options_and_completion_ceiling",
        "condition_order_balanced_by_pair",
        "actual_prompt_completion_tokens_latency_and_failures_recorded",
        "extra_system_state_tokens_count_toward_same_ceiling",
        "baseline_may_reason_normally",
    }
    for field in required_true:
        if fairness.get(field) is not True:
            errors.append(f"fairness:{field}")
    if fairness.get("baseline_literal_restriction") is not False:
        errors.append("fairness:baseline_literal_restriction")
    if fairness.get("same_call_count_each_item") != 1:
        errors.append("fairness:call_count")
    if fairness.get("total_completion_token_ceiling_each_condition_item") != 384:
        errors.append("fairness:token_ceiling")
    model = contract.get("model") or {}
    if model != {
        "provider": "local_ollama",
        "endpoint": "http://127.0.0.1:11434/api/generate",
        "name": "qwen3.5:9b",
        "timeout_seconds": 180,
        "think": False,
        "options": {
            "temperature": 0,
            "seed": 260920,
            "top_p": 1,
            "num_ctx": 8192,
            "num_predict": 384,
        },
    }:
        errors.append("model")
    limits = contract.get("execution_limits") or {}
    expected_limit_names = {
        "model_call_count",
        "network_request_count",
        "new_uruha_source_content_access_count",
        "uruha_future_access_count",
        "human_label_count",
        "production_memory_write_count",
        "formal_m56_write_count",
    }
    if set(limits) != expected_limit_names or any(value != 0 for value in limits.values()):
        errors.append("execution_limits")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    path = Path(root) / FREEZE_PATH.relative_to(ROOT)
    if not path.is_file():
        raise C1ContractError("implementation freeze missing")
    freeze = load_json(path)
    errors: list[str] = []
    if freeze.get("schema") != "uruha_p3_c1_controlled_context_flip_implementation_freeze_v1":
        errors.append("schema")
    if freeze.get("status") != "frozen_before_any_p3_c_model_call":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        artifact_path = Path(root) / str((artifact or {}).get("path") or "")
        if not artifact_path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(artifact_path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    counts = freeze.get("counts_at_freeze") or {}
    if any(
        counts.get(field) != 0
        for field in (
            "model_calls",
            "network_requests",
            "new_uruha_source_content_accesses",
            "uruha_future_accesses",
            "human_labels",
            "production_memory_writes",
            "formal_m56_writes",
        )
    ):
        errors.append("counts_at_freeze")
    if freeze.get("model_execution_authorized_by_freeze") is not False:
        errors.append("execution_authorization")
    if errors:
        raise C1ContractError("invalid implementation freeze:" + ";".join(errors))
    return {
        "valid": True,
        "frozen_artifact_count": len(freeze.get("frozen_artifacts") or {}),
        "model_calls_at_freeze": counts["model_calls"],
    }


def _distribution_errors(
    distribution: Any, labels: list[str], tolerance: float, prefix: str
) -> list[str]:
    errors: list[str] = []
    if not isinstance(distribution, dict) or set(distribution) != set(labels):
        return [f"{prefix}:labels"]
    for label in labels:
        value = distribution[label]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not 0 <= float(value) <= 1
        ):
            errors.append(f"{prefix}:value:{label}")
    if not errors and abs(math.fsum(float(distribution[label]) for label in labels) - 1.0) > tolerance:
        errors.append(f"{prefix}:sum")
    return errors


def validate_dataset(
    dataset: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dataset = deepcopy(dataset or load_dataset())
    contract = contract or load_contract()
    errors: list[str] = []
    if dataset.get("schema") != "uruha_p3_c1_controlled_context_flip_dataset_v1":
        errors.append("schema")
    provenance = dataset.get("provenance") or {}
    if provenance != {
        "kind": "developer_authored_controlled_proxy",
        "created_at": "2026-09-20",
        "human_validated": False,
        "independent_holdout": False,
        "real_person_observation": False,
        "private_motive_ground_truth": False,
    }:
        errors.append("provenance")
    labels = dataset.get("target_labels")
    if labels != TARGET_LABELS:
        errors.append("target_labels")
        labels = TARGET_LABELS
    pairs = dataset.get("pairs")
    if not isinstance(pairs, list):
        return {"valid": False, "errors": errors + ["pairs"]}
    if len(pairs) != contract["dataset"]["pair_count_exact"]:
        errors.append("pair_count")
    split_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    pair_ids: set[str] = set()
    family_splits: dict[str, set[str]] = defaultdict(set)
    surface_splits: dict[str, set[str]] = defaultdict(set)
    tolerance = float(contract["dataset"]["target_distribution_sum_tolerance"])
    for index, pair in enumerate(pairs):
        prefix = f"pair:{index}"
        if not isinstance(pair, dict):
            errors.append(prefix)
            continue
        pair_id = pair.get("pair_id")
        split = pair.get("split")
        language = pair.get("language")
        family = pair.get("surface_family_id")
        surface = pair.get("surface_utterance")
        if not isinstance(pair_id, str) or not PAIR_ID_RE.fullmatch(pair_id):
            errors.append(f"{prefix}:pair_id")
        elif pair_id in pair_ids:
            errors.append(f"{prefix}:pair_id_duplicate")
        else:
            pair_ids.add(pair_id)
        if split not in SPLITS:
            errors.append(f"{prefix}:split")
        else:
            split_counts[split] += 1
        if language not in LANGUAGES:
            errors.append(f"{prefix}:language")
        else:
            language_counts[language] += 1
        if (
            not isinstance(family, str)
            or not FAMILY_ID_RE.fullmatch(family)
            or (language in LANGUAGES and not family.startswith(f"sf_{language}_"))
        ):
            errors.append(f"{prefix}:surface_family")
        elif split in SPLITS:
            family_splits[family].add(split)
        if not isinstance(surface, str) or not surface.strip():
            errors.append(f"{prefix}:surface")
        elif split in SPLITS:
            surface_splits[surface].add(split)
        options = pair.get("interpretation_options")
        if not isinstance(options, dict) or set(options) != set(labels) or any(
            not isinstance(options.get(label), str) or not options[label].strip()
            for label in labels
        ):
            errors.append(f"{prefix}:options")
        modality = pair.get("modality")
        if modality != {
            "text_available": True,
            "acoustic_summary_status": "unavailable",
            "acoustic_features": None,
        }:
            errors.append(f"{prefix}:modality")
        variants = pair.get("variants")
        if not isinstance(variants, list) or [row.get("variant_id") for row in variants if isinstance(row, dict)] != VARIANTS:
            errors.append(f"{prefix}:variants")
            continue
        for variant in variants:
            variant_id = variant["variant_id"]
            variant_prefix = f"{prefix}:{variant_id}"
            context = variant.get("context_text")
            if not isinstance(context, str) or not context.strip():
                errors.append(f"{variant_prefix}:context")
            elif isinstance(surface, str) and surface not in context:
                errors.append(f"{variant_prefix}:surface_not_exact")
            anchors = variant.get("evidence_anchors")
            if not isinstance(anchors, list) or len(anchors) < 2:
                errors.append(f"{variant_prefix}:anchors")
            else:
                anchor_ids = [anchor.get("id") for anchor in anchors if isinstance(anchor, dict)]
                if len(anchor_ids) != len(anchors) or len(anchor_ids) != len(set(anchor_ids)):
                    errors.append(f"{variant_prefix}:anchor_ids")
                for anchor in anchors:
                    if (
                        not isinstance(anchor, dict)
                        or not isinstance(anchor.get("id"), str)
                        or not isinstance(anchor.get("text"), str)
                        or not anchor["text"].strip()
                    ):
                        errors.append(f"{variant_prefix}:anchor")
            distribution = variant.get("expected_distribution")
            errors.extend(_distribution_errors(distribution, labels, tolerance, f"{variant_prefix}:distribution"))
            top1 = variant.get("expected_top1")
            if not isinstance(distribution, dict) or not all(label in distribution for label in labels):
                continue
            calculated_top1 = max(labels, key=lambda label: (float(distribution[label]), -labels.index(label)))
            expected_direction = "LITERAL_READING" if variant_id == "literal_control" else "PRAGMATIC_READING"
            if top1 != calculated_top1:
                errors.append(f"{variant_prefix}:top1_mismatch")
            if top1 != expected_direction:
                errors.append(f"{variant_prefix}:direction")
    if dict(split_counts) != contract["dataset"]["split_pair_counts"]:
        errors.append("split_counts")
    if dict(language_counts) != contract["dataset"]["language_pair_counts"]:
        errors.append("language_counts")
    if any(len(splits) != 1 for splits in family_splits.values()):
        errors.append("surface_family_split_leak")
    if any(len(splits) != 1 for splits in surface_splits.values()):
        errors.append("surface_text_split_leak")
    return {
        "valid": not errors,
        "errors": errors,
        "counts": {
            "pairs": len(pairs),
            "variants": sum(len(pair.get("variants") or []) for pair in pairs if isinstance(pair, dict)),
            "by_split": dict(sorted(split_counts.items())),
            "by_language": dict(sorted(language_counts.items())),
        },
    }


def _pair_common_input(pair: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    return {
        "pair_id": pair["pair_id"],
        "variant_id": variant["variant_id"],
        "language": pair["language"],
        "phenomenon": pair["phenomenon"],
        "surface_utterance": pair["surface_utterance"],
        "context_text": variant["context_text"],
        "evidence_anchors": deepcopy(variant["evidence_anchors"]),
        "interpretation_options": deepcopy(pair["interpretation_options"]),
        "modality": deepcopy(pair["modality"]),
    }


def build_prediction_packet(
    split: str, dataset: dict[str, Any] | None = None
) -> dict[str, Any]:
    dataset = dataset or load_dataset()
    validation = validate_dataset(dataset)
    if not validation["valid"]:
        raise C1ContractError("invalid dataset:" + ";".join(validation["errors"]))
    if split not in SPLITS:
        raise C1ContractError("unknown split")
    items: list[dict[str, Any]] = []
    for pair in dataset["pairs"]:
        if pair["split"] != split:
            continue
        for variant in pair["variants"]:
            common = _pair_common_input(pair, variant)
            common["input_sha256"] = sha256_bytes(canonical_json(common).encode("utf-8"))
            items.append(common)
    return {
        "schema": "uruha_p3_c1_controlled_context_flip_prediction_packet_v1",
        "split": split,
        "item_count": len(items),
        "targets_visible": False,
        "human_validated": False,
        "items": items,
    }


def build_prompt_payload(
    condition: str,
    item: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract()
    if condition not in CONDITIONS:
        raise C1ContractError("unknown condition")
    common_input = {
        key: deepcopy(value)
        for key, value in item.items()
        if key != "input_sha256"
    }
    expected_hash = sha256_bytes(canonical_json(common_input).encode("utf-8"))
    if item.get("input_sha256") != expected_hash:
        raise C1ContractError("input hash mismatch")
    payload: dict[str, Any] = {
        "task": "Infer a probability distribution over the supplied interpretations, then write one short natural Japanese reply that would appropriately respond to the speaker without exposing analysis.",
        "condition": condition,
        "condition_instruction": contract["conditions"][condition]["instruction"],
        "common_observable_input": common_input,
        "common_input_sha256": expected_hash,
        "boundaries": [
            "Use only the observable text and listed evidence anchors.",
            "Acoustic evidence is unavailable; do not infer tone, pause, volume, or prosody.",
            "Do not assert a private motive as fact; keep alternatives and uncertainty when warranted.",
            "The visible reply must be natural Japanese and must not reveal the internal analysis.",
        ],
        "evaluated_output_fields": contract["conditions"][condition]["evaluated_output_fields"],
    }
    if condition == "SYSTEM_PRAGMATIC_STATE":
        payload["additional_observable_state_fields"] = contract["conditions"][condition][
            "additional_observable_state_fields"
        ]
    return payload


def validate_prediction(
    prediction: dict[str, Any],
    item: dict[str, Any],
    condition: str,
    *,
    tolerance: float = 0.000001,
) -> list[str]:
    errors: list[str] = []
    if prediction.get("schema") != "uruha_p3_c1_interpretation_prediction_v1":
        errors.append("schema")
    if condition not in CONDITIONS or prediction.get("condition") != condition:
        errors.append("condition")
    for field in ("pair_id", "variant_id", "input_sha256"):
        if prediction.get(field) != item.get(field):
            errors.append(field)
    probabilities = prediction.get("probabilities")
    errors.extend(_distribution_errors(probabilities, TARGET_LABELS, tolerance, "probabilities"))
    if isinstance(probabilities, dict) and set(probabilities) == set(TARGET_LABELS):
        selected = max(
            TARGET_LABELS,
            key=lambda label: (float(probabilities[label]), -TARGET_LABELS.index(label)),
        )
        if prediction.get("selected_interpretation") != selected:
            errors.append("selected_interpretation")
    reply = prediction.get("visible_reply_ja")
    if (
        not isinstance(reply, str)
        or not reply.strip()
        or len(reply) > 180
        or not JAPANESE_SCRIPT_RE.search(reply)
    ):
        errors.append("visible_reply_ja")
    anchor_ids = prediction.get("brief_evidence_anchor_ids")
    allowed_anchor_ids = {anchor["id"] for anchor in item["evidence_anchors"]}
    if (
        not isinstance(anchor_ids, list)
        or not anchor_ids
        or len(anchor_ids) != len(set(anchor_ids))
        or any(anchor_id not in allowed_anchor_ids for anchor_id in anchor_ids)
    ):
        errors.append("brief_evidence_anchor_ids")
    state = prediction.get("pragmatic_state")
    if condition == "SYSTEM_PRAGMATIC_STATE":
        required_state = {
            "literal_content",
            "communicative_intent",
            "affect_or_stance",
            "relationship_signal",
            "implicit_need_or_action_tendency",
            "alternative_hypothesis",
            "unknowns",
            "confidence",
        }
        if not isinstance(state, dict) or set(state) != required_state:
            errors.append("pragmatic_state")
        else:
            for field in required_state - {"confidence"}:
                if not isinstance(state[field], str) or not state[field].strip() or len(state[field]) > 180:
                    errors.append(f"pragmatic_state:{field}")
            confidence = state["confidence"]
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not math.isfinite(float(confidence))
                or not 0 <= float(confidence) <= 1
            ):
                errors.append("pragmatic_state:confidence")
    elif state is not None:
        errors.append("baseline_extra_pragmatic_state")
    return errors


def _target_lookup(dataset: dict[str, Any], split: str) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for pair in dataset["pairs"]:
        if pair["split"] != split:
            continue
        for variant in pair["variants"]:
            lookup[(pair["pair_id"], variant["variant_id"])] = {
                "language": pair["language"],
                "phenomenon": pair["phenomenon"],
                "expected_distribution": variant["expected_distribution"],
                "expected_top1": variant["expected_top1"],
            }
    return lookup


def _mean(values: list[float]) -> float:
    return round(fmean(values), 6) if values else 0.0


def score_predictions(
    predictions: list[dict[str, Any]],
    split: str,
    dataset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dataset = dataset or load_dataset()
    validation = validate_dataset(dataset)
    if not validation["valid"]:
        raise C1ContractError("invalid dataset:" + ";".join(validation["errors"]))
    packet = build_prediction_packet(split, dataset)
    items = {(row["pair_id"], row["variant_id"]): row for row in packet["items"]}
    targets = _target_lookup(dataset, split)
    expected_keys = {
        (pair_id, variant_id, condition)
        for pair_id, variant_id in items
        for condition in CONDITIONS
    }
    provided: dict[tuple[str, str, str], dict[str, Any]] = {}
    validation_errors: list[str] = []
    for index, prediction in enumerate(predictions):
        key = (
            str(prediction.get("pair_id") or ""),
            str(prediction.get("variant_id") or ""),
            str(prediction.get("condition") or ""),
        )
        if key in provided:
            validation_errors.append(f"duplicate:{key}")
            continue
        if key not in expected_keys:
            validation_errors.append(f"unexpected:{key}")
            continue
        item_key = (key[0], key[1])
        row_errors = validate_prediction(prediction, items[item_key], key[2])
        validation_errors.extend(f"row:{index}:{error}" for error in row_errors)
        provided[key] = prediction
    missing = expected_keys.difference(provided)
    validation_errors.extend(f"missing:{key}" for key in sorted(missing))
    if validation_errors:
        raise C1ContractError("prediction validation:" + ";".join(validation_errors))

    row_scores: list[dict[str, Any]] = []
    for pair_id, variant_id, condition in sorted(expected_keys):
        prediction = provided[(pair_id, variant_id, condition)]
        target = targets[(pair_id, variant_id)]
        probabilities = prediction["probabilities"]
        expected = target["expected_distribution"]
        brier = math.fsum(
            (float(probabilities[label]) - float(expected[label])) ** 2
            for label in TARGET_LABELS
        )
        log_loss = -math.fsum(
            float(expected[label]) * math.log(max(float(probabilities[label]), 1e-15))
            for label in TARGET_LABELS
        )
        selected = prediction["selected_interpretation"]
        target_top1 = target["expected_top1"]
        row_scores.append(
            {
                "pair_id": pair_id,
                "variant_id": variant_id,
                "condition": condition,
                "language": target["language"],
                "phenomenon": target["phenomenon"],
                "brier": brier,
                "log_loss": log_loss,
                "top1_correct": selected == target_top1,
                "selected": selected,
                "target_top1": target_top1,
                "max_probability": max(float(value) for value in probabilities.values()),
                "pragmatic_probability": float(probabilities["PRAGMATIC_READING"]),
            }
        )

    by_condition: dict[str, dict[str, Any]] = {}
    for condition in CONDITIONS:
        rows = [row for row in row_scores if row["condition"] == condition]
        literal_rows = [row for row in rows if row["variant_id"] == "literal_control"]
        pragmatic_rows = [row for row in rows if row["variant_id"] == "pragmatic_flip"]
        paired_flip: list[bool] = []
        delta_direction: list[bool] = []
        for pair_id in sorted({row["pair_id"] for row in rows}):
            literal = next(row for row in rows if row["pair_id"] == pair_id and row["variant_id"] == "literal_control")
            pragmatic = next(row for row in rows if row["pair_id"] == pair_id and row["variant_id"] == "pragmatic_flip")
            paired_flip.append(literal["top1_correct"] and pragmatic["top1_correct"])
            delta_direction.append(pragmatic["pragmatic_probability"] > literal["pragmatic_probability"])
        by_condition[condition] = {
            "row_count": len(rows),
            "pair_count": len(paired_flip),
            "mean_multiclass_brier": _mean([row["brier"] for row in rows]),
            "mean_log_loss": _mean([row["log_loss"] for row in rows]),
            "target_top1_accuracy": _mean([float(row["top1_correct"]) for row in rows]),
            "paired_context_flip_top1_accuracy": _mean([float(value) for value in paired_flip]),
            "context_delta_direction_accuracy": _mean([float(value) for value in delta_direction]),
            "literal_control_overinterpretation_rate": _mean(
                [float(row["selected"] == "PRAGMATIC_READING") for row in literal_rows]
            ),
            "pragmatic_underreading_rate": _mean(
                [float(row["selected"] == "LITERAL_READING") for row in pragmatic_rows]
            ),
            "wrong_top1_at_or_above_0_70_rate": _mean(
                [float((not row["top1_correct"]) and row["max_probability"] >= 0.7) for row in rows]
            ),
        }
    baseline = by_condition["BASELINE_DIRECT"]
    system = by_condition["SYSTEM_PRAGMATIC_STATE"]
    brier_improvement = round(
        baseline["mean_multiclass_brier"] - system["mean_multiclass_brier"], 6
    )
    primary_pass = brier_improvement >= 0.03
    overinterpretation_guard = (
        system["literal_control_overinterpretation_rate"]
        <= baseline["literal_control_overinterpretation_rate"]
    )
    paired_flip_guard = (
        system["paired_context_flip_top1_accuracy"]
        >= baseline["paired_context_flip_top1_accuracy"]
    )
    return {
        "schema": "uruha_p3_c1_controlled_context_flip_score_report_v1",
        "split": split,
        "target_kind": "developer_authored_distribution_proxy_not_human_ground_truth",
        "conditions": by_condition,
        "comparison": {
            "system_minus_baseline_brier_improvement": brier_improvement,
            "primary_sesoi_at_least_0_03": primary_pass,
            "literal_overinterpretation_not_worse": overinterpretation_guard,
            "paired_context_flip_top1_not_worse": paired_flip_guard,
            "controlled_lane_success": primary_pass and overinterpretation_guard and paired_flip_guard,
        },
        "strata": _score_strata(row_scores),
        "claim_boundary": load_contract()["claim_boundary"],
    }


def _score_strata(row_scores: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for field in ("language", "phenomenon"):
        output[field] = {}
        for value in sorted({str(row[field]) for row in row_scores}):
            output[field][value] = {}
            for condition in CONDITIONS:
                rows = [
                    row
                    for row in row_scores
                    if row[field] == value and row["condition"] == condition
                ]
                output[field][value][condition] = {
                    "row_count": len(rows),
                    "mean_multiclass_brier": _mean([row["brier"] for row in rows]),
                    "target_top1_accuracy": _mean(
                        [float(row["top1_correct"]) for row in rows]
                    ),
                }
    return output


def build_readiness_result() -> dict[str, Any]:
    contract = load_contract()
    contract_validation = validate_contract(contract)
    dataset = load_dataset()
    dataset_validation = validate_dataset(dataset, contract)
    if not contract_validation["valid"] or not dataset_validation["valid"]:
        raise C1ContractError(
            "offline validation failed:"
            + ";".join(contract_validation["errors"] + dataset_validation["errors"])
        )
    packets = {split: build_prediction_packet(split, dataset) for split in SPLITS}
    return {
        "schema": "uruha_p3_c1_controlled_context_flip_readiness_v1",
        "version": "1.0.0",
        "status": "offline_contract_dataset_and_metric_harness_ready_model_execution_not_started",
        "contract_sha256": sha256_file(CONFIG_PATH),
        "dataset_sha256": sha256_file(DATASET_PATH),
        "pair_count": dataset_validation["counts"]["pairs"],
        "variant_count": dataset_validation["counts"]["variants"],
        "prediction_item_counts": {
            split: packets[split]["item_count"] for split in SPLITS
        },
        "target_visibility_in_prediction_packets": False,
        "human_validated_targets": False,
        "independent_holdout": False,
        "execution_counts": deepcopy(contract["execution_limits"]),
        "model_execution_authorized_by_c1": False,
        "next_gate": "hash_freeze_then_separately_execute_train_format_and_dev_before_one_holdout_run_without_target_edits",
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(build_readiness_result(), ensure_ascii=False, indent=2, sort_keys=True))
