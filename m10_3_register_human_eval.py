#!/usr/bin/env python3
"""M10.3 blinded human-rating instrument and offline analyzer.

The collection surface never needs the hidden key.  This analyzer uses the key
only after collection and fails closed for incomplete, malformed, un-attested,
or fewer-than-three-rater evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_PACKET = ROOT / "analysis/m10_2_behavior_preserving_register_blind_packet.json"
DEFAULT_KEY = ROOT / "analysis/m10_2_behavior_preserving_register_blind_key.json"
DEFAULT_PREREG = ROOT / "configs/m10_3_register_human_eval_preregistration.json"
DEFAULT_LOCK = ROOT / "configs/m10_3_register_human_eval_lock.json"
DEFAULT_RATINGS_DIR = ROOT / "analysis/m10_3_register_ratings"

DIMENSIONS = (
    "semantic_preservation",
    "behavior_fit",
    "natural_casual_japanese",
    "non_overclaiming",
)
PREFERENCES = {"A", "B", "tie", "both_bad"}
CONDITIONS = {"S0_ONE_PASS", "S1_REGISTER_REPAIR"}
PACKET_SHA256 = "dd953d604ca6caa545c4b5f3f8d7486ea921a7c624836c88c9678ae4aecac294"
RUBRIC = {
    "semantic_preservation": "1=扭曲或新增關鍵事實；5=完整保留事件語意與承諾邊界",
    "behavior_fit": "1=沒有實現指定行為；5=清楚且自然地實現指定行為",
    "natural_casual_japanese": "1=敬體、翻譯腔或不自然；5=自然、口語且不做作的日文",
    "non_overclaiming": "1=捏造私事、讀心或過度斷言；5=完全守住可知證據邊界",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pseudonymize_rater_id(raw_rater_id):
    normalized = str(raw_rater_id or "").strip().casefold()
    if len(normalized) < 4:
        raise ValueError("rater identifier must contain at least four characters")
    return hashlib.sha256(("m10.3::" + normalized).encode("utf-8")).hexdigest()


def load_rating_rows(path_or_directory):
    path = Path(path_or_directory)
    files = sorted(path.glob("ratings-*.jsonl")) if path.is_dir() else [path]
    rows = []
    for file_path in files:
        if not file_path.exists():
            continue
        for line_number, line in enumerate(
            file_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL {file_path}:{line_number}: {exc}") from exc
            row["_source"] = str(file_path)
            row["_line_number"] = line_number
            rows.append(row)
    return rows


def rating_template(packet, rater_id_hash):
    return [
        {
            "schema": "m10_3_register_rating_v1",
            "rater_id_hash": rater_id_hash,
            "independent_human_attestation": True,
            "key_unseen_attestation": True,
            "packet_sha256": PACKET_SHA256,
            "item_id": item["item_id"],
            "scores": {
                dimension: {"A": None, "B": None} for dimension in DIMENSIONS
            },
            "preference": None,
            "notes": "",
        }
        for item in packet.get("items") or []
    ]


def validate_locked_artifacts(prereg_path=DEFAULT_PREREG, lock_path=DEFAULT_LOCK):
    prereg = load_json(prereg_path)
    lock = load_json(lock_path)
    errors = []
    paths = {
        "preregistration": Path(prereg_path),
        "blind_packet": ROOT / prereg["artifacts"]["blind_packet"]["path"],
        "hidden_key": ROOT / prereg["artifacts"]["hidden_key"]["path"],
    }
    for name, path in paths.items():
        expected = lock["artifacts"][name]["sha256"]
        actual = sha256_file(path)
        if actual != expected:
            errors.append(f"locked_artifact_hash:{name}:{expected}:{actual}")
    return {"passed": not errors, "errors": errors}


def validate_ratings(packet, key, ratings, minimum_raters=3):
    items = packet.get("items") or []
    item_ids = {item.get("item_id") for item in items}
    key_rows = key.get("items") or []
    key_map = {row.get("item_id"): row.get("mapping") for row in key_rows}
    errors = []
    if len(items) != 18 or len(item_ids) != 18:
        errors.append(f"packet_item_count:{len(items)}:{len(item_ids)}")
    if item_ids != set(key_map):
        errors.append("packet_key_item_mismatch")
    for item_id, mapping in key_map.items():
        if set(mapping or {}) != {"A", "B"} or set(mapping.values()) != CONDITIONS:
            errors.append(f"invalid_key_mapping:{item_id}")

    seen = set()
    by_rater = defaultdict(set)
    valid_rows = []
    for row in ratings:
        rater_hash = str(row.get("rater_id_hash") or "")
        item_id = str(row.get("item_id") or "")
        location = f"{row.get('_source', '?')}:{row.get('_line_number', '?')}"
        row_errors = []
        if "rater_id" in row:
            row_errors.append(f"raw_rater_id_forbidden:{location}")
        if not re.fullmatch(r"[0-9a-f]{64}", rater_hash):
            row_errors.append(f"invalid_rater_hash:{location}")
        if item_id not in item_ids:
            row_errors.append(f"unknown_item:{item_id}:{location}")
        if (rater_hash, item_id) in seen:
            row_errors.append(f"duplicate_rating:{rater_hash}:{item_id}")
        seen.add((rater_hash, item_id))
        if row.get("schema") != "m10_3_register_rating_v1":
            row_errors.append(f"schema:{location}")
        if row.get("packet_sha256") != PACKET_SHA256:
            row_errors.append(f"packet_sha256:{location}")
        if row.get("independent_human_attestation") is not True:
            row_errors.append(f"independence_attestation:{location}")
        if row.get("key_unseen_attestation") is not True:
            row_errors.append(f"key_unseen_attestation:{location}")
        scores = row.get("scores") or {}
        if set(scores) != set(DIMENSIONS):
            row_errors.append(f"dimension_set:{rater_hash}:{item_id}")
        for dimension in DIMENSIONS:
            paired = scores.get(dimension)
            if not isinstance(paired, dict) or set(paired) != {"A", "B"}:
                row_errors.append(f"score_shape:{rater_hash}:{item_id}:{dimension}")
                continue
            for label in ("A", "B"):
                score = paired.get(label)
                if not isinstance(score, int) or not 1 <= score <= 5:
                    row_errors.append(
                        f"score_range:{rater_hash}:{item_id}:{dimension}:{label}:{score}"
                    )
        if row.get("preference") not in PREFERENCES:
            row_errors.append(f"preference:{rater_hash}:{item_id}")
        errors.extend(row_errors)
        if not row_errors:
            valid_rows.append(row)
            by_rater[rater_hash].add(item_id)

    complete_raters = sorted(
        rater for rater, rated_items in by_rater.items() if rated_items == item_ids
    )
    incomplete_raters = {
        rater: sorted(item_ids - rated_items)
        for rater, rated_items in by_rater.items()
        if rated_items != item_ids
    }
    return {
        "instrument_valid": not errors,
        "errors": errors,
        "item_count": len(item_ids),
        "rating_count": len(ratings),
        "valid_rating_count": len(valid_rows),
        "complete_rater_count": len(complete_raters),
        "complete_raters": complete_raters,
        "incomplete_raters": incomplete_raters,
        "minimum_raters": int(minimum_raters),
        "minimum_raters_met": len(complete_raters) >= int(minimum_raters),
        "eligible_rows": [
            row for row in valid_rows if row["rater_id_hash"] in complete_raters
        ],
    }


def _mean(values):
    return sum(values) / len(values) if values else None


def _percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * float(q)
    low = int(index)
    high = min(len(ordered) - 1, low + 1)
    fraction = index - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def _quadratic_weighted_kappa(left, right, minimum=1, maximum=5):
    if len(left) != len(right) or not left:
        return None
    categories = list(range(minimum, maximum + 1))
    size = len(categories)
    observed = [[0.0] * size for _ in range(size)]
    left_counts = Counter(left)
    right_counts = Counter(right)
    for a, b in zip(left, right):
        observed[a - minimum][b - minimum] += 1.0
    denominator = float(len(left))
    weighted_observed = 0.0
    weighted_expected = 0.0
    span_sq = float((maximum - minimum) ** 2)
    for i, a in enumerate(categories):
        for j, b in enumerate(categories):
            weight = ((a - b) ** 2) / span_sq
            weighted_observed += weight * observed[i][j] / denominator
            expected = left_counts[a] * right_counts[b] / (denominator * denominator)
            weighted_expected += weight * expected
    if math.isclose(weighted_expected, 0.0):
        return 1.0 if all(a == b for a, b in zip(left, right)) else 0.0
    return 1.0 - weighted_observed / weighted_expected


def _reliability(eligible_rows):
    by_rater = defaultdict(dict)
    for row in eligible_rows:
        by_rater[row["rater_id_hash"]][row["item_id"]] = row
    raters = sorted(by_rater)
    by_dimension = {}
    all_pair_values = []
    for dimension in DIMENSIONS:
        kappas = []
        for left_id, right_id in itertools.combinations(raters, 2):
            common = sorted(set(by_rater[left_id]) & set(by_rater[right_id]))
            left = []
            right = []
            for item_id in common:
                for candidate in ("A", "B"):
                    left.append(by_rater[left_id][item_id]["scores"][dimension][candidate])
                    right.append(by_rater[right_id][item_id]["scores"][dimension][candidate])
            kappa = _quadratic_weighted_kappa(left, right)
            if kappa is not None:
                kappas.append(kappa)
                all_pair_values.append(kappa)
        by_dimension[dimension] = {
            "mean_pairwise_quadratic_weighted_kappa": (
                round(_mean(kappas), 4) if kappas else None
            ),
            "pair_count": len(kappas),
        }
    return {
        "by_dimension": by_dimension,
        "overall_mean_pairwise_quadratic_weighted_kappa": (
            round(_mean(all_pair_values), 4) if all_pair_values else None
        ),
    }


def _bootstrap_condition_delta(judgments, dimension, seed, samples):
    by_item = defaultdict(list)
    for row in judgments:
        by_item[row["item_id"]].append(row["deltas"][dimension])
    item_ids = sorted(by_item)
    if not item_ids:
        return {"mean_delta_s1_minus_s0": None, "ci95": [None, None]}

    def cluster_mean(selected):
        values = [value for item_id in selected for value in by_item[item_id]]
        return _mean(values)

    observed = cluster_mean(item_ids)
    rng = random.Random(seed)
    boot = [
        cluster_mean([item_ids[rng.randrange(len(item_ids))] for _ in item_ids])
        for _ in range(int(samples))
    ]
    return {
        "mean_delta_s1_minus_s0": round(observed, 4),
        "ci95": [
            round(_percentile(boot, 0.025), 4),
            round(_percentile(boot, 0.975), 4),
        ],
        "cluster_unit": "blind_item",
    }


def analyze(packet, key, ratings, prereg=None):
    prereg = prereg or load_json(DEFAULT_PREREG)
    minimum_raters = prereg["minimum_complete_independent_raters"]
    validation = validate_ratings(packet, key, ratings, minimum_raters)
    public_validation = {k: v for k, v in validation.items() if k != "eligible_rows"}
    if not validation["instrument_valid"]:
        return {
            "schema": "m10_3_register_human_eval_result_v1",
            "status": "invalid_ratings",
            "validation": public_validation,
            "claim_authorized": False,
        }

    key_map = {row["item_id"]: row["mapping"] for row in key.get("items") or []}
    item_map = {row["item_id"]: row for row in packet.get("items") or []}
    judgments = []
    preference_counts = Counter()
    changed_decisive = []
    case_rows = defaultdict(list)
    for row in validation["eligible_rows"]:
        mapping = key_map[row["item_id"]]
        s0_label = "A" if mapping["A"] == "S0_ONE_PASS" else "B"
        s1_label = "B" if s0_label == "A" else "A"
        deltas = {
            dimension: row["scores"][dimension][s1_label]
            - row["scores"][dimension][s0_label]
            for dimension in DIMENSIONS
        }
        judgment = {
            "rater_id_hash": row["rater_id_hash"],
            "item_id": row["item_id"],
            "case_id": item_map[row["item_id"]]["case_id"],
            "s0_label": s0_label,
            "s1_label": s1_label,
            "deltas": deltas,
        }
        judgments.append(judgment)
        case_rows[judgment["case_id"]].append(judgment)
        preference = row["preference"]
        if preference in {"A", "B"}:
            winner = mapping[preference]
        else:
            winner = preference
        preference_counts[winner] += 1
        item = item_map[row["item_id"]]
        changed = item["candidates"]["A"] != item["candidates"]["B"]
        if changed and winner in CONDITIONS:
            changed_decisive.append(winner)

    seed = int(prereg["bootstrap"]["seed"])
    samples = int(prereg["bootstrap"]["samples"])
    dimensions = {
        dimension: _bootstrap_condition_delta(
            judgments, dimension, seed + index, samples
        )
        for index, dimension in enumerate(DIMENSIONS)
    }
    reliability = _reliability(validation["eligible_rows"])
    s1_preference_rate = (
        sum(winner == "S1_REGISTER_REPAIR" for winner in changed_decisive)
        / len(changed_decisive)
        if changed_decisive
        else None
    )
    r_ja_06 = case_rows.get("R-JA-06", [])
    required_case_report = {
        "case_id": "R-JA-06",
        "eligible_rating_count": len(r_ja_06),
        "mean_deltas_s1_minus_s0": {
            dimension: (
                round(_mean([row["deltas"][dimension] for row in r_ja_06]), 4)
                if r_ja_06
                else None
            )
            for dimension in DIMENSIONS
        },
        "automatic_proxy_disagreement_retained": True,
    }

    thresholds = prereg["gates"]
    natural = dimensions["natural_casual_japanese"]
    gates = {
        "minimum_complete_independent_raters": validation["minimum_raters_met"],
        "reliability_at_least_0_40": (
            reliability["overall_mean_pairwise_quadratic_weighted_kappa"] is not None
            and reliability["overall_mean_pairwise_quadratic_weighted_kappa"]
            >= thresholds["mean_pairwise_quadratic_weighted_kappa_min"]
        ),
        "naturalness_delta_at_least_0_50": (
            natural["mean_delta_s1_minus_s0"] is not None
            and natural["mean_delta_s1_minus_s0"]
            >= thresholds["natural_casual_japanese_delta_min"]
        ),
        "naturalness_ci_lower_above_zero": (
            natural["ci95"][0] is not None
            and natural["ci95"][0]
            > thresholds["natural_casual_japanese_ci95_lower_strictly_above"]
        ),
        "semantic_preservation_noninferior": (
            dimensions["semantic_preservation"]["mean_delta_s1_minus_s0"] is not None
            and dimensions["semantic_preservation"]["mean_delta_s1_minus_s0"]
            >= thresholds["semantic_preservation_delta_min"]
        ),
        "behavior_fit_noninferior": (
            dimensions["behavior_fit"]["mean_delta_s1_minus_s0"] is not None
            and dimensions["behavior_fit"]["mean_delta_s1_minus_s0"]
            >= thresholds["behavior_fit_delta_min"]
        ),
        "non_overclaiming_noninferior": (
            dimensions["non_overclaiming"]["mean_delta_s1_minus_s0"] is not None
            and dimensions["non_overclaiming"]["mean_delta_s1_minus_s0"]
            >= thresholds["non_overclaiming_delta_min"]
        ),
        "changed_decisive_s1_preference_above_0_60": (
            s1_preference_rate is not None
            and s1_preference_rate
            > thresholds["changed_decisive_pair_s1_preference_rate_strictly_above"]
        ),
        "r_ja_06_reported": True,
    }
    claim_authorized = all(gates.values())
    return {
        "schema": "m10_3_register_human_eval_result_v1",
        "status": (
            "formal_human_result"
            if validation["minimum_raters_met"]
            else "pilot_or_collection_incomplete"
        ),
        "validation": public_validation,
        "reliability": reliability,
        "dimension_deltas_s1_minus_s0": dimensions,
        "preference_counts": dict(sorted(preference_counts.items())),
        "changed_decisive_pair": {
            "count": len(changed_decisive),
            "s1_preference_rate": (
                round(s1_preference_rate, 4) if s1_preference_rate is not None else None
            ),
        },
        "required_case_reports": [required_case_report],
        "gates": gates,
        "claim_authorized": claim_authorized,
        "claim_scope": (
            "this frozen 18-pair remediation packet and these independent raters only"
            if claim_authorized
            else "no M10.2 human naturalness or preservation claim"
        ),
        "evidence_boundary": "No general superiority, felt-understanding, consciousness, mind-reading, real-person identity, or production claim.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--key", default=str(DEFAULT_KEY))
    parser.add_argument("--ratings", default=str(DEFAULT_RATINGS_DIR))
    parser.add_argument("--prereg", default=str(DEFAULT_PREREG))
    parser.add_argument("--check-lock", action="store_true")
    parser.add_argument("--make-template")
    parser.add_argument("--rater-id")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.check_lock:
        lock_result = validate_locked_artifacts(args.prereg, DEFAULT_LOCK)
        print(json.dumps(lock_result, ensure_ascii=False, indent=2))
        if not lock_result["passed"]:
            raise SystemExit(2)
        if not args.make_template and not args.output:
            return

    packet = load_json(args.packet)
    if args.make_template:
        rater_hash = pseudonymize_rater_id(args.rater_id)
        rows = rating_template(packet, rater_hash)
        Path(args.make_template).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        print(json.dumps({"template": args.make_template, "item_count": len(rows)}))
        return

    result = analyze(
        packet,
        load_json(args.key),
        load_rating_rows(args.ratings),
        load_json(args.prereg),
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
