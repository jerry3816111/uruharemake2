#!/usr/bin/env python3
"""Blind human-rating instrument and analyzer for V2.14.

The analyzer fails closed: fewer than three independent complete raters can be
reported only as a pilot and cannot support a system-over-baseline claim.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


DIMENSIONS = (
    "implicit_need_caught_without_overclaiming",
    "overinterpretation_or_fabrication_reverse_scored",
    "quality_of_revision_after_user_denial",
    "cross_turn_consistency",
    "felt_understanding",
    "public_uruha_persona_naturalness_secondary",
)
PREFERENCES = {"A", "B", "tie", "both_bad"}
RATING_RUBRIC = {
    "implicit_need_caught_without_overclaiming": "1=只答字面或接錯核心；5=接住言外需要且保留可否定空間",
    "overinterpretation_or_fabrication_reverse_scored": "1=強斷言、捏造或假裝讀心；5=有洞察但證據邊界清楚",
    "quality_of_revision_after_user_denial": "1=硬套舊理解或辯解；5=承認誤讀並依新證據自然更新",
    "cross_turn_consistency": "1=遺忘、矛盾或重複錯猜；5=正確沿用並在必要時撤銷舊模型",
    "felt_understanding": "1=沒有被接住；5=核心困境或真正目的被精準接住",
    "public_uruha_persona_naturalness_secondary": "1=不像自然日文或人格漂移；5=自然且符合公開證據限定的うるは表達",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_ratings(path):
    rows = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL line {line_number}: {exc}") from exc
        row["_line_number"] = line_number
        rows.append(row)
    return rows


def rating_template(packet, rater_id="REPLACE_WITH_RATER_ID"):
    return [
        {
            "rater_id": rater_id,
            "item_id": item["item_id"],
            "scores": {
                dimension: {"A": None, "B": None}
                for dimension in (item.get("rating_dimensions") or DIMENSIONS)
            },
            "preference": None,
            "both_bad_reason": "",
            "error_tags": [],
            "notes": "",
        }
        for item in packet.get("items") or []
    ]


def validate_ratings(packet, key, ratings, minimum_raters=3):
    item_ids = {item["item_id"] for item in packet.get("items") or []}
    key_map = {item["item_id"]: item for item in key.get("items") or []}
    item_dimensions = {
        item["item_id"]: tuple(item.get("rating_dimensions") or DIMENSIONS)
        for item in packet.get("items") or []
    }
    errors = []
    seen = set()
    by_rater = defaultdict(set)
    for row in ratings:
        rater = str(row.get("rater_id") or "").strip()
        item_id = str(row.get("item_id") or "").strip()
        if not rater or rater == "REPLACE_WITH_RATER_ID":
            errors.append(f"missing_rater:line={row.get('_line_number')}")
        if item_id not in item_ids or item_id not in key_map:
            errors.append(f"unknown_item:{item_id}")
        if (rater, item_id) in seen:
            errors.append(f"duplicate_rating:{rater}:{item_id}")
        seen.add((rater, item_id))
        by_rater[rater].add(item_id)
        scores = row.get("scores") or {}
        required_dimensions = item_dimensions.get(item_id, DIMENSIONS)
        if set(scores) != set(required_dimensions):
            errors.append(f"dimension_set:{rater}:{item_id}")
        for dimension in required_dimensions:
            value = scores.get(dimension)
            if not isinstance(value, dict) or set(value) != {"A", "B"}:
                errors.append(f"invalid_paired_score_shape:{rater}:{item_id}:{dimension}")
                continue
            for label in ("A", "B"):
                score = value.get(label)
                if not isinstance(score, int) or not 1 <= score <= 5:
                    errors.append(
                        f"invalid_score:{rater}:{item_id}:{dimension}:{label}:{score}"
                    )
        if row.get("preference") not in PREFERENCES:
            errors.append(f"invalid_preference:{rater}:{item_id}:{row.get('preference')}")
    incomplete = {
        rater: sorted(item_ids - rated)
        for rater, rated in by_rater.items()
        if rated != item_ids
    }
    if incomplete:
        errors.append(f"incomplete_raters:{sorted(incomplete)}")
    eligible_raters = sorted(
        rater for rater, rated in by_rater.items() if rater and rated == item_ids
    )
    return {
        "passed_for_formal_claim": not errors and len(eligible_raters) >= int(minimum_raters),
        "instrument_valid": not errors,
        "errors": errors,
        "rater_count": len(eligible_raters),
        "eligible_raters": eligible_raters,
        "item_count": len(item_ids),
        "rating_count": len(ratings),
        "minimum_raters": int(minimum_raters),
        "missing_rater_count": max(0, int(minimum_raters) - len(eligible_raters)),
    }


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * float(q)
    low = int(index)
    high = min(len(ordered) - 1, low + 1)
    fraction = index - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def _bootstrap_delta(judgments, dimension, seed=20260811, samples=4000):
    judgments = [
        row for row in judgments if dimension in (row.get("system_scores") or {})
    ]
    if not judgments:
        return {"mean_delta": None, "ci95": [None, None]}
    by_item = defaultdict(list)
    for row in judgments:
        by_item[row["item_id"]].append(
            row["system_scores"][dimension] - row["baseline_scores"][dimension]
        )
    item_ids = sorted(by_item)

    def item_cluster_mean(selected_items):
        values = [delta for item_id in selected_items for delta in by_item[item_id]]
        return _mean(values)

    rng = random.Random(seed)
    deltas = [
        item_cluster_mean(
            [item_ids[rng.randrange(len(item_ids))] for _ in item_ids]
        )
        for _ in range(int(samples))
    ]
    observed = item_cluster_mean(item_ids)
    return {
        "mean_delta": round(observed, 4),
        "ci95": [round(_percentile(deltas, 0.025), 4), round(_percentile(deltas, 0.975), 4)],
        "cluster_unit": "blind_item",
    }


def _bootstrap_preference(preference_rows, seed=20260811, samples=4000):
    by_item = defaultdict(list)
    for row in preference_rows:
        by_item[row["item_id"]].append(row["winner"])
    item_ids = sorted(by_item)
    if not item_ids:
        return {"rate": 0.0, "ci95": [None, None], "decisive_count": 0}

    def rate(selected_items):
        values = [winner for item_id in selected_items for winner in by_item[item_id]]
        decisive = [winner for winner in values if winner in {"system", "baseline"}]
        if not decisive:
            return 0.0
        return sum(winner == "system" for winner in decisive) / len(decisive)

    observed = rate(item_ids)
    rng = random.Random(seed)
    boot = [
        rate([item_ids[rng.randrange(len(item_ids))] for _ in item_ids])
        for _ in range(int(samples))
    ]
    decisive_count = sum(
        winner in {"system", "baseline"}
        for values in by_item.values()
        for winner in values
    )
    return {
        "rate": round(observed, 4),
        "ci95": [round(_percentile(boot, 0.025), 4), round(_percentile(boot, 0.975), 4)],
        "decisive_count": decisive_count,
        "cluster_unit": "blind_item",
    }


def analyze(packet, key, ratings, minimum_raters=3):
    validation = validate_ratings(packet, key, ratings, minimum_raters=minimum_raters)
    if not validation["instrument_valid"]:
        return {
            "schema": "uruha_v2_14_human_eval_result",
            "status": "invalid_ratings",
            "validation": validation,
            "claim_authorized": False,
        }
    key_map = {row["item_id"]: row for row in key.get("items") or []}
    judgments = []
    preference_rows = []
    preference_counts = {"system": 0, "baseline": 0, "tie": 0, "both_bad": 0}
    for row in ratings:
        mapping = key_map[row["item_id"]]
        scores = row["scores"]
        system_label = "A" if mapping["A"] == "system" else "B"
        baseline_label = "B" if system_label == "A" else "A"
        # One rating row scores the two replies comparatively on each dimension
        # using nested A/B scores when available.  For backward-compatible
        # templates, a scalar score is rejected by the formal analyzer below.
        if not all(isinstance(scores.get(dimension), dict) for dimension in DIMENSIONS):
            validation["errors"].append(f"paired_scores_required:{row['item_id']}")
            continue
        system_scores = {
            dimension: scores[dimension][system_label] for dimension in scores
        }
        baseline_scores = {
            dimension: scores[dimension][baseline_label] for dimension in scores
        }
        preference = row["preference"]
        if preference in {"A", "B"}:
            preference_counts[mapping[preference]] += 1
            winner = mapping[preference]
        else:
            preference_counts[preference] += 1
            winner = preference
        preference_rows.append({"item_id": row["item_id"], "winner": winner})
        judgments.append(
            {
                "rater_id": row["rater_id"],
                "item_id": row["item_id"],
                "system_scores": system_scores,
                "baseline_scores": baseline_scores,
            }
        )

    if validation["errors"]:
        validation["instrument_valid"] = False
        validation["passed_for_formal_claim"] = False
        return {
            "schema": "uruha_v2_14_human_eval_result",
            "status": "invalid_ratings",
            "validation": validation,
            "claim_authorized": False,
        }

    dimensions = {
        dimension: _bootstrap_delta(judgments, dimension, seed=20260811 + index)
        for index, dimension in enumerate(DIMENSIONS)
    }
    preference_bootstrap = _bootstrap_preference(preference_rows)
    preference_rate = preference_bootstrap["rate"]
    primary = dimensions["felt_understanding"]
    implicit = dimensions["implicit_need_caught_without_overclaiming"]
    correction = dimensions["quality_of_revision_after_user_denial"]
    overclaim = dimensions["overinterpretation_or_fabrication_reverse_scored"]
    gates = {
        "minimum_three_complete_independent_raters": validation["passed_for_formal_claim"],
        "felt_understanding_delta_at_least_0_40": (primary["mean_delta"] or -99) >= 0.40,
        "implicit_need_delta_at_least_0_40": (implicit["mean_delta"] or -99) >= 0.40,
        "correction_delta_at_least_0_40": (correction["mean_delta"] or -99) >= 0.40,
        "overinterpretation_not_worse": (overclaim["mean_delta"] or -99) >= 0.0,
        "system_decisive_preference_above_0_60": preference_rate > 0.60,
        "system_preference_ci_lower_above_0_50": (
            preference_bootstrap["ci95"][0] is not None
            and preference_bootstrap["ci95"][0] > 0.50
        ),
    }
    claim = all(gates.values())
    return {
        "schema": "uruha_v2_14_human_eval_result",
        "status": "formal_human_result" if validation["passed_for_formal_claim"] else "pilot_only",
        "validation": validation,
        "dimension_deltas_system_minus_baseline": dimensions,
        "preference_counts": preference_counts,
        "system_decisive_preference_rate": round(preference_rate, 4),
        "system_preference_cluster_bootstrap": preference_bootstrap,
        "gates": gates,
        "claim_authorized": claim,
        "claim_scope": (
            "only this frozen model, holdout, persona contract and hardware condition"
            if claim
            else "no system-superiority claim"
        ),
        "evidence_boundary": "This analyzer does not establish consciousness, mind reading, general human understanding, persona identity, or production readiness.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--ratings")
    parser.add_argument("--make-template")
    parser.add_argument("--rater-id", default="REPLACE_WITH_RATER_ID")
    parser.add_argument("--output")
    args = parser.parse_args()
    packet = load_json(args.packet)
    key = load_json(args.key)
    if args.make_template:
        template = rating_template(packet, args.rater_id)
        Path(args.make_template).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in template),
            encoding="utf-8",
        )
        print(json.dumps({"template": args.make_template, "item_count": len(template)}, ensure_ascii=False))
        return
    if not args.ratings:
        raise SystemExit("--ratings is required unless --make-template is used")
    result = analyze(packet, key, load_ratings(args.ratings))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
