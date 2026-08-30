"""Paired statistical evaluation for probabilistic behavior forecasts.

The functions in this module deliberately operate on already materialized
per-example probability distributions.  They do not regenerate answers, tune
models, or select a baseline from test performance.
"""

from __future__ import annotations

from itertools import product
import math
import random
from typing import Any, Iterable


EPSILON = 1e-12


def _normalized_probabilities(row: dict[str, Any]) -> dict[str, float]:
    raw = row.get("probabilities")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("row must contain a non-empty probabilities object")
    values: dict[str, float] = {}
    for label, value in raw.items():
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"invalid probability for {label!r}")
        if float(value) < 0:
            raise ValueError(f"negative probability for {label!r}")
        values[str(label)] = float(value)
    total = sum(values.values())
    if total <= 0:
        raise ValueError("probability distribution has no mass")
    return {label: value / total for label, value in values.items()}


def probability_losses(row: dict[str, Any], *, top_k: int = 3) -> dict[str, Any]:
    """Return per-instance proper scores and rank-based diagnostics."""

    probabilities = _normalized_probabilities(row)
    actual = row.get("actual_observed_behavior")
    if actual not in probabilities:
        raise ValueError("actual label is absent from probability distribution")
    acceptable = set(row.get("acceptable_behavior_labels") or [actual])
    if not acceptable <= set(probabilities):
        raise ValueError("acceptable labels are absent from probability distribution")
    ranked = sorted(probabilities, key=lambda label: (-probabilities[label], label))
    predicted = ranked[0]
    brier = sum(
        (probability - float(label == actual)) ** 2
        for label, probability in probabilities.items()
    )
    return {
        "brier": brier,
        "nll": -math.log(max(probabilities[actual], EPSILON)),
        "top1": int(predicted in acceptable),
        "top3": int(bool(set(ranked[: min(top_k, len(ranked))]) & acceptable)),
        "predicted": predicted,
        "actual": actual,
        "confidence": probabilities[predicted],
    }


def percentile_bootstrap_ci(
    values: Iterable[float],
    *,
    repetitions: int = 20_000,
    seed: int = 20260817,
    alpha: float = 0.05,
) -> list[float]:
    """Deterministic percentile bootstrap interval for a paired mean delta."""

    materialized = [float(value) for value in values]
    if not materialized:
        raise ValueError("bootstrap requires at least one value")
    if repetitions < 1 or not 0 < alpha < 1:
        raise ValueError("invalid bootstrap configuration")
    rng = random.Random(seed)
    count = len(materialized)
    estimates = sorted(
        sum(materialized[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(repetitions)
    )
    lower_index = max(0, min(repetitions - 1, int((alpha / 2) * repetitions)))
    upper_index = max(
        0,
        min(repetitions - 1, int((1 - alpha / 2) * repetitions) - 1),
    )
    return [estimates[lower_index], estimates[upper_index]]


def exact_sign_flip_pvalue(values: Iterable[float]) -> float:
    """Two-sided exact paired randomization p-value for a mean difference."""

    materialized = [float(value) for value in values]
    if not materialized:
        raise ValueError("permutation test requires at least one value")
    if len(materialized) > 20:
        raise ValueError("exact sign-flip test is intentionally bounded to 20 pairs")
    observed = abs(sum(materialized) / len(materialized))
    extreme = 0
    total = 0
    for signs in product((-1.0, 1.0), repeat=len(materialized)):
        statistic = abs(
            sum(sign * value for sign, value in zip(signs, materialized))
            / len(materialized)
        )
        extreme += int(statistic >= observed - 1e-15)
        total += 1
    return extreme / total


def exact_mcnemar_pvalue(candidate_only: int, baseline_only: int) -> float:
    """Two-sided exact McNemar/binomial p-value for discordant correctness."""

    discordant = candidate_only + baseline_only
    if discordant == 0:
        return 1.0
    tail = min(candidate_only, baseline_only)
    probability = sum(math.comb(discordant, k) for k in range(tail + 1)) / (2**discordant)
    return min(1.0, 2 * probability)


def _condition_rows(
    rows: Iterable[dict[str, Any]], condition: str
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("condition") != condition and row.get("transfer_condition") != condition:
            continue
        sample_id = str(row["sample_id"])
        if sample_id in selected:
            raise ValueError(f"duplicate {condition} row for {sample_id}")
        selected[sample_id] = row
    if not selected:
        raise ValueError(f"condition has no rows: {condition}")
    return selected


def compare_conditions(
    rows: Iterable[dict[str, Any]],
    *,
    candidate_condition: str,
    baseline_condition: str,
    bootstrap_repetitions: int = 20_000,
    seed: int = 20260817,
) -> dict[str, Any]:
    """Compare two systems on exactly the same instances.

    Deltas are candidate minus baseline, so negative Brier/NLL is better.
    """

    materialized = list(rows)
    candidate_rows = _condition_rows(materialized, candidate_condition)
    baseline_rows = _condition_rows(materialized, baseline_condition)
    if set(candidate_rows) != set(baseline_rows):
        raise ValueError("candidate and baseline sample IDs do not match")

    pairs = []
    candidate_only = baseline_only = 0
    brier_deltas: list[float] = []
    nll_deltas: list[float] = []
    top1_deltas: list[float] = []
    top3_deltas: list[float] = []
    brier_wins = brier_ties = brier_losses = 0
    for sample_id in sorted(candidate_rows):
        candidate = probability_losses(candidate_rows[sample_id])
        baseline = probability_losses(baseline_rows[sample_id])
        if candidate["actual"] != baseline["actual"]:
            raise ValueError(f"ground truth mismatch for {sample_id}")
        brier_delta = candidate["brier"] - baseline["brier"]
        nll_delta = candidate["nll"] - baseline["nll"]
        top1_delta = candidate["top1"] - baseline["top1"]
        top3_delta = candidate["top3"] - baseline["top3"]
        candidate_only += int(top1_delta > 0)
        baseline_only += int(top1_delta < 0)
        if brier_delta < -EPSILON:
            brier_wins += 1
        elif brier_delta > EPSILON:
            brier_losses += 1
        else:
            brier_ties += 1
        brier_deltas.append(brier_delta)
        nll_deltas.append(nll_delta)
        top1_deltas.append(top1_delta)
        top3_deltas.append(top3_delta)
        pairs.append(
            {
                "sample_id": sample_id,
                "actual": candidate["actual"],
                "candidate_prediction": candidate["predicted"],
                "baseline_prediction": baseline["predicted"],
                "candidate_brier": candidate["brier"],
                "baseline_brier": baseline["brier"],
                "brier_delta": brier_delta,
                "candidate_nll": candidate["nll"],
                "baseline_nll": baseline["nll"],
                "nll_delta": nll_delta,
                "top1_delta": top1_delta,
                "top3_delta": top3_delta,
            }
        )

    def mean(values: list[float]) -> float:
        return sum(values) / len(values)

    brier_ci = percentile_bootstrap_ci(
        brier_deltas, repetitions=bootstrap_repetitions, seed=seed
    )
    nll_ci = percentile_bootstrap_ci(
        nll_deltas, repetitions=bootstrap_repetitions, seed=seed + 1
    )
    brier_p = exact_sign_flip_pvalue(brier_deltas)
    nll_p = exact_sign_flip_pvalue(nll_deltas)
    mean_brier_delta = mean(brier_deltas)
    mean_nll_delta = mean(nll_deltas)
    accuracy_delta = mean(top1_deltas)
    if mean_brier_delta < 0 and mean_nll_delta < 0 and accuracy_delta >= 0:
        directional_verdict = "directionally_favors_candidate"
    elif mean_brier_delta > 0 and mean_nll_delta > 0 and accuracy_delta <= 0:
        directional_verdict = "directionally_favors_baseline"
    else:
        directional_verdict = "mixed"
    if brier_ci[1] < 0 and nll_ci[1] < 0 and brier_p <= 0.05 and nll_p <= 0.05:
        inferential_verdict = "statistically_favors_candidate"
    elif brier_ci[0] > 0 and nll_ci[0] > 0 and brier_p <= 0.05 and nll_p <= 0.05:
        inferential_verdict = "statistically_favors_baseline"
    else:
        inferential_verdict = "inconclusive"

    return {
        "candidate": candidate_condition,
        "baseline": baseline_condition,
        "sample_count": len(pairs),
        "delta_definition": "candidate_minus_baseline; negative Brier/NLL is better",
        "brier": {
            "mean_delta": mean_brier_delta,
            "bootstrap_95_ci": brier_ci,
            "exact_sign_flip_two_sided_p": brier_p,
            "candidate_wins": brier_wins,
            "ties": brier_ties,
            "baseline_wins": brier_losses,
        },
        "nll": {
            "mean_delta": mean_nll_delta,
            "bootstrap_95_ci": nll_ci,
            "exact_sign_flip_two_sided_p": nll_p,
        },
        "top1": {
            "mean_delta": accuracy_delta,
            "candidate_only_correct": candidate_only,
            "baseline_only_correct": baseline_only,
            "exact_mcnemar_two_sided_p": exact_mcnemar_pvalue(candidate_only, baseline_only),
        },
        "top3_mean_delta": mean(top3_deltas),
        "directional_verdict": directional_verdict,
        "inferential_verdict": inferential_verdict,
        "pairs": pairs,
    }
