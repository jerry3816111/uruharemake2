#!/usr/bin/env python3
"""Lightweight learned reranker for RightBrain surface candidates."""

import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from rightbrain_language_quality import (
    ASCII_WORD_RE as LATIN_TOKEN_RE,
    CHINESE_SPECIFIC_RE,
    INSTRUCTION_MARKERS,
    JAPANESE_RE,
    NONSTANDARD_CJK_RE,
    POLITE_RE,
    UNICODE_REPLACEMENT_CHAR,
)


DEFAULT_SPLIT_SEED = 20260707
DEFAULT_TRAIN_SEED = 20260707

JAPANESE_CHAR_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
KANA_RE = re.compile(r"[ぁ-んァ-ヶー]")

FEATURE_NAMES = (
    "has_japanese",
    "japanese_char_ratio",
    "kana_char_ratio",
    "latin_token_density",
    "chinese_marker_density",
    "nonstandard_cjk_density",
    "polite_pattern_density",
    "instruction_marker_density",
    "first_person_density",
    "required_group_hit_rate",
    "required_group_missing_rate",
    "required_marker_member_coverage",
    "grounding_term_hit_rate",
    "semantic_reference_unigram_dice",
    "semantic_reference_bigram_dice",
    "user_input_unigram_dice",
    "forbidden_marker_density",
    "length_ratio",
    "over_limit_ratio",
    "sentence_density",
    "whitespace_density",
)


def _safe_ratio(numerator, denominator):
    return float(numerator) / float(denominator) if denominator else 0.0


def _count_occurrences(text, markers):
    return sum(text.count(str(marker)) for marker in markers if str(marker))


def _semantic_chars(text):
    return "".join(JAPANESE_CHAR_RE.findall(str(text or "").lower()))


def _char_ngrams(text, width):
    chars = _semantic_chars(text)
    if not chars:
        return set()
    if len(chars) < width:
        return {chars}
    return {chars[index : index + width] for index in range(len(chars) - width + 1)}


def _dice_similarity(first, second, width):
    first_grams = _char_ngrams(first, width)
    second_grams = _char_ngrams(second, width)
    if not first_grams or not second_grams:
        return 0.0
    return _safe_ratio(2 * len(first_grams & second_grams), len(first_grams) + len(second_grams))


def _semantic_references(payload):
    plan = payload.get("leftbrain_plan") or {}
    values = [
        plan.get("meaning"),
        *(plan.get("content_units") or []),
    ]
    references = []
    for value in values:
        value = str(value or "").strip()
        if value and value not in references:
            references.append(value)
    return references


def _grounding_terms(payload):
    plan = payload.get("leftbrain_plan") or {}
    return [
        str(term).strip()
        for term in plan.get("grounding_terms") or []
        if str(term).strip()
    ]


def extract_candidate_features(text, payload):
    """Extract contract-relative features without reading labels or candidate metadata."""
    text = str(text or "").strip()
    char_count = max(1, len(text))
    max_chars = max(1, int((payload.get("context") or {}).get("max_chars") or 80))
    required_groups = payload.get("required_marker_groups") or []
    required_hits = sum(
        1
        for group in required_groups
        if any(str(marker) and str(marker) in text for marker in group)
    )
    required_total = len(required_groups)
    required_members = [str(marker) for group in required_groups for marker in group if str(marker)]
    required_member_hits = sum(marker in text for marker in required_members)
    grounding_terms = _grounding_terms(payload)
    grounding_hits = sum(term in text for term in grounding_terms)
    semantic_references = _semantic_references(payload)
    semantic_unigram = max(
        (_dice_similarity(text, reference, 1) for reference in semantic_references),
        default=0.0,
    )
    semantic_bigram = max(
        (_dice_similarity(text, reference, 2) for reference in semantic_references),
        default=0.0,
    )
    user_input = str(payload.get("user_input") or "")
    forbidden = [str(marker) for marker in payload.get("forbidden_markers") or [] if str(marker)]
    japanese_count = len(JAPANESE_CHAR_RE.findall(text))
    kana_count = len(KANA_RE.findall(text))
    latin_count = len(LATIN_TOKEN_RE.findall(text))
    chinese_count = len(CHINESE_SPECIFIC_RE.findall(text))
    nonstandard_count = len(NONSTANDARD_CJK_RE.findall(text)) + text.count(UNICODE_REPLACEMENT_CHAR)
    polite_count = len(POLITE_RE.findall(text))
    instruction_count = sum(text.lower().count(marker.lower()) for marker in INSTRUCTION_MARKERS)
    forbidden_count = _count_occurrences(text, forbidden)
    sentence_count = len(re.findall(r"[。！？!?]", text))
    overflow = max(0, len(text) - (max_chars + 2))

    return {
        "has_japanese": 1.0 if JAPANESE_RE.search(text) else 0.0,
        "japanese_char_ratio": _safe_ratio(japanese_count, char_count),
        "kana_char_ratio": _safe_ratio(kana_count, char_count),
        "latin_token_density": _safe_ratio(latin_count, char_count),
        "chinese_marker_density": _safe_ratio(chinese_count, char_count),
        "nonstandard_cjk_density": _safe_ratio(nonstandard_count, char_count),
        "polite_pattern_density": _safe_ratio(polite_count, char_count),
        "instruction_marker_density": _safe_ratio(instruction_count, char_count),
        "first_person_density": _safe_ratio(text.count("私"), char_count),
        "required_group_hit_rate": _safe_ratio(required_hits, required_total) if required_total else 1.0,
        "required_group_missing_rate": _safe_ratio(required_total - required_hits, required_total),
        "required_marker_member_coverage": (
            _safe_ratio(required_member_hits, len(required_members)) if required_members else 1.0
        ),
        "grounding_term_hit_rate": (
            _safe_ratio(grounding_hits, len(grounding_terms)) if grounding_terms else 1.0
        ),
        "semantic_reference_unigram_dice": semantic_unigram,
        "semantic_reference_bigram_dice": semantic_bigram,
        "user_input_unigram_dice": _dice_similarity(text, user_input, 1),
        "forbidden_marker_density": _safe_ratio(forbidden_count, char_count),
        "length_ratio": _safe_ratio(len(text), max_chars),
        "over_limit_ratio": _safe_ratio(overflow, max_chars),
        "sentence_density": _safe_ratio(sentence_count, char_count),
        "whitespace_density": _safe_ratio(sum(char.isspace() for char in text), char_count),
    }


def feature_vector(text, payload):
    features = extract_candidate_features(text, payload)
    return [float(features[name]) for name in FEATURE_NAMES]


def validate_model_artifact(model):
    if not isinstance(model, dict):
        raise ValueError("Selector model artifact must be a JSON object.")
    if model.get("model_type") != "standardized_logistic_contract_reranker":
        raise ValueError("Unsupported selector model_type.")
    if tuple(model.get("feature_names") or ()) != FEATURE_NAMES:
        raise ValueError("Selector feature schema does not match runtime FEATURE_NAMES.")
    width = len(FEATURE_NAMES)
    for key in ("means", "scales", "weights"):
        values = model.get(key)
        if not isinstance(values, list) or len(values) != width:
            raise ValueError(f"Selector {key} must contain {width} values.")
        if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in values):
            raise ValueError(f"Selector {key} contains a non-finite value.")
    if any(float(value) <= 0 for value in model["scales"]):
        raise ValueError("Selector scales must be positive.")
    if not isinstance(model.get("intercept"), (int, float)) or not math.isfinite(float(model["intercept"])):
        raise ValueError("Selector intercept must be finite.")
    return model


def load_model_artifact(path):
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_model_artifact(model)


def grouped_contract_split(rows, seed=DEFAULT_SPLIT_SEED, train_ratio=0.7, validation_ratio=0.15):
    """Split complete contract groups so equivalent contracts cannot cross partitions."""
    if train_ratio <= 0 or validation_ratio <= 0 or train_ratio + validation_ratio >= 1:
        raise ValueError("Split ratios must leave non-empty train, validation, and test targets.")
    by_fingerprint = defaultdict(list)
    for row in rows:
        fingerprint = str(row.get("source_contract_fingerprint") or "").strip()
        if not fingerprint:
            raise ValueError(f"Missing source_contract_fingerprint for {row.get('id')}")
        by_fingerprint[fingerprint].append(row)

    groups = list(by_fingerprint.items())
    random.Random(seed).shuffle(groups)
    targets = {
        "train": len(rows) * train_ratio,
        "validation": len(rows) * validation_ratio,
        "test": len(rows) * (1.0 - train_ratio - validation_ratio),
    }
    split_rows = {name: [] for name in targets}
    for _, group_rows in groups:
        split_name = max(
            targets,
            key=lambda name: (targets[name] - len(split_rows[name]), targets[name], name),
        )
        split_rows[split_name].extend(group_rows)
    for name in split_rows:
        split_rows[name].sort(key=lambda row: str(row.get("id") or ""))
    return split_rows


def split_fingerprint_overlap(split_rows):
    fingerprints = {
        name: {str(row.get("source_contract_fingerprint")) for row in rows}
        for name, rows in split_rows.items()
    }
    return {
        "train_validation": len(fingerprints["train"] & fingerprints["validation"]),
        "train_test": len(fingerprints["train"] & fingerprints["test"]),
        "validation_test": len(fingerprints["validation"] & fingerprints["test"]),
    }


def _candidate_examples(rows):
    examples = []
    for row in rows:
        payload = row["contract_payload"]
        for candidate in row["candidates"]:
            examples.append(
                {
                    "row_id": row["id"],
                    "candidate_id": candidate["candidate_id"],
                    "x": feature_vector(candidate.get("text"), payload),
                    "y": 1.0 if candidate["candidate_id"] == row["gold_candidate_id"] else 0.0,
                }
            )
    return examples


def _fit_standardizer(examples):
    width = len(FEATURE_NAMES)
    means = []
    scales = []
    for index in range(width):
        values = [row["x"][index] for row in examples]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        means.append(mean)
        scales.append(math.sqrt(variance) if variance > 1e-12 else 1.0)
    return means, scales


def _standardize(vector, means, scales):
    return [(value - mean) / scale for value, mean, scale in zip(vector, means, scales)]


def _sigmoid(value):
    if value >= 0:
        exp_value = math.exp(-min(value, 60.0))
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(max(value, -60.0))
    return exp_value / (1.0 + exp_value)


def _binary_metrics(model, rows):
    examples = _candidate_examples(rows)
    if not examples:
        return {"candidate_count": 0, "brier_score": None, "log_loss": None}
    brier = 0.0
    log_loss = 0.0
    for example in examples:
        probability = predict_probability(model, example["x"])
        target = example["y"]
        brier += (probability - target) ** 2
        clipped = min(max(probability, 1e-9), 1.0 - 1e-9)
        log_loss -= target * math.log(clipped) + (1.0 - target) * math.log(1.0 - clipped)
    return {
        "candidate_count": len(examples),
        "brier_score": round(brier / len(examples), 6),
        "log_loss": round(log_loss / len(examples), 6),
    }


def predict_probability(model, vector):
    standardized = _standardize(vector, model["means"], model["scales"])
    logit = float(model["intercept"]) + sum(
        weight * value for weight, value in zip(model["weights"], standardized)
    )
    return _sigmoid(logit)


def score_candidate(model, candidate, payload):
    return predict_probability(model, feature_vector(candidate.get("text"), payload))


def select_learned_candidate(model, row):
    payload = row["contract_payload"]
    ranked = []
    for index, candidate in enumerate(row["candidates"]):
        probability = score_candidate(model, candidate, payload)
        ranked.append((probability, -index, candidate))
    ranked.sort(reverse=True)
    return ranked[0][2], ranked[0][0]


def _selection_rate(model, rows):
    if not rows:
        return 0.0
    correct = sum(
        select_learned_candidate(model, row)[0]["candidate_id"] == row["gold_candidate_id"]
        for row in rows
    )
    return correct / len(rows)


def train_selector(
    train_rows,
    validation_rows,
    seed=DEFAULT_TRAIN_SEED,
    epochs=700,
    learning_rate=0.04,
    l2=0.002,
):
    """Train a class-balanced logistic scorer and select its epoch on validation rows."""
    examples = _candidate_examples(train_rows)
    means, scales = _fit_standardizer(examples)
    standardized_examples = [
        (_standardize(example["x"], means, scales), example["y"])
        for example in examples
    ]
    positives = sum(target for _, target in standardized_examples)
    negatives = len(standardized_examples) - positives
    positive_weight = negatives / positives if positives else 1.0
    weights = [0.0] * len(FEATURE_NAMES)
    intercept = 0.0
    best_model = None
    best_key = None
    history = []

    for epoch in range(1, epochs + 1):
        gradient = [0.0] * len(weights)
        intercept_gradient = 0.0
        total_weight = 0.0
        weighted_loss = 0.0
        for vector, target in standardized_examples:
            probability = _sigmoid(intercept + sum(w * x for w, x in zip(weights, vector)))
            sample_weight = positive_weight if target else 1.0
            error = (probability - target) * sample_weight
            intercept_gradient += error
            for index, value in enumerate(vector):
                gradient[index] += error * value
            clipped = min(max(probability, 1e-9), 1.0 - 1e-9)
            weighted_loss -= sample_weight * (
                target * math.log(clipped) + (1.0 - target) * math.log(1.0 - clipped)
            )
            total_weight += sample_weight
        for index in range(len(weights)):
            gradient[index] = gradient[index] / total_weight + l2 * weights[index]
            weights[index] -= learning_rate * gradient[index]
        intercept -= learning_rate * intercept_gradient / total_weight

        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            candidate_model = {
                "model_type": "standardized_logistic_contract_reranker",
                "feature_names": list(FEATURE_NAMES),
                "means": list(means),
                "scales": list(scales),
                "weights": list(weights),
                "intercept": intercept,
            }
            validation_rate = _selection_rate(candidate_model, validation_rows)
            validation_binary = _binary_metrics(candidate_model, validation_rows)
            key = (
                validation_rate,
                -float(validation_binary["brier_score"] or 1.0),
                -float(validation_binary["log_loss"] or 99.0),
                -epoch,
            )
            history.append(
                {
                    "epoch": epoch,
                    "weighted_train_loss": round(weighted_loss / total_weight, 6),
                    "validation_gold_selection_rate": round(validation_rate, 6),
                    **validation_binary,
                }
            )
            if best_key is None or key > best_key:
                best_key = key
                best_model = dict(candidate_model)
                best_model["best_epoch"] = epoch

    best_model.update(
        {
            "schema_version": 2,
            "training_seed": seed,
            "training_row_count": len(train_rows),
            "validation_row_count": len(validation_rows),
            "positive_class_weight": positive_weight,
            "learning_rate": learning_rate,
            "l2": l2,
            "requested_epochs": epochs,
        }
    )
    return best_model, history


def _length_baseline_candidate(row):
    max_chars = int((row["contract_payload"].get("context") or {}).get("max_chars") or 80)
    target_length = min(max_chars, 42)
    return min(
        enumerate(row["candidates"]),
        key=lambda item: (abs(len(str(item[1].get("text") or "")) - target_length), item[0]),
    )[1]


def _seeded_random_candidate(row, seed):
    digest = hashlib.sha256(f"{seed}:{row['id']}".encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(row["candidates"])
    return row["candidates"][index]


def evaluate_strategy(rows, selector, failure_limit=25):
    correct = 0
    category_totals = Counter()
    category_correct = Counter()
    selected_source_counts = Counter()
    failures = []
    for row in rows:
        selected = selector(row)
        category = str(row.get("category") or "uncategorized")
        is_correct = selected["candidate_id"] == row["gold_candidate_id"]
        category_totals[category] += 1
        category_correct[category] += int(is_correct)
        selected_source_counts[str(selected.get("source") or "unknown")] += 1
        correct += int(is_correct)
        if not is_correct and len(failures) < max(0, failure_limit):
            failures.append(
                {
                    "id": row["id"],
                    "category": category,
                    "selected_candidate_id": selected["candidate_id"],
                    "selected_source": selected.get("source"),
                    "gold_candidate_id": row["gold_candidate_id"],
                }
            )
    return {
        "case_count": len(rows),
        "gold_selection_count": correct,
        "gold_selection_rate": round(_safe_ratio(correct, len(rows)), 6),
        "invalid_selection_count": len(rows) - correct,
        "invalid_selection_rate": round(_safe_ratio(len(rows) - correct, len(rows)), 6),
        "category_rates": {
            category: {
                "count": category_totals[category],
                "correct": category_correct[category],
                "rate": round(_safe_ratio(category_correct[category], category_totals[category]), 6),
            }
            for category in sorted(category_totals)
        },
        "selected_source_counts": dict(sorted(selected_source_counts.items())),
        "failures": failures,
    }


def evaluate_baselines(rows, model, random_seed=DEFAULT_SPLIT_SEED):
    learned = evaluate_strategy(rows, lambda row: select_learned_candidate(model, row)[0])
    learned["candidate_metrics"] = _binary_metrics(model, rows)
    return {
        "first_candidate": evaluate_strategy(rows, lambda row: row["candidates"][0], failure_limit=0),
        "seeded_random": evaluate_strategy(
            rows,
            lambda row: _seeded_random_candidate(row, random_seed),
            failure_limit=0,
        ),
        "length_only": evaluate_strategy(rows, _length_baseline_candidate, failure_limit=0),
        "learned_selector": learned,
    }


def split_summary(split_rows):
    return {
        "row_counts": {name: len(rows) for name, rows in split_rows.items()},
        "contract_fingerprint_counts": {
            name: len({row["source_contract_fingerprint"] for row in rows})
            for name, rows in split_rows.items()
        },
        "fingerprint_overlap_counts": split_fingerprint_overlap(split_rows),
        "category_counts": {
            name: dict(sorted(Counter(str(row.get("category") or "uncategorized") for row in rows).items()))
            for name, rows in split_rows.items()
        },
    }


def model_to_json(model):
    return json.dumps(model, ensure_ascii=False, indent=2) + "\n"
