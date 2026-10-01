"""Utilities for the M13 PUB same-model pragmatics benchmark.

The module deliberately keeps external PUB rows outside the repository.  Formal
artifacts retain only selected public IDs, hashes, model outputs, and scores.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import re
from typing import Any, Iterable
from urllib import request
import zipfile


CONDITIONS = ("B0_DIRECT", "B1_GENERIC_DELIBERATION", "OURS_PRAGMATIC_LOOP")
EXPECTED_PAYLOAD_KEYS = {
    "B0_DIRECT": {"answer_index"},
    "B1_GENERIC_DELIBERATION": {
        "observations", "reasoning_step_1", "reasoning_step_2",
        "counterargument", "uncertainty", "answer_index",
    },
    "OURS_PRAGMATIC_LOOP": {
        "literal_content", "pragmatic_target", "context_evidence",
        "alternative_interpretation", "uncertainty", "answer_index",
    },
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def download_verified(url: str, path: Path, expected_sha256: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and sha256_bytes(path.read_bytes()) == expected_sha256:
        return path
    temporary = path.with_suffix(path.suffix + ".download")
    with request.urlopen(url, timeout=120) as response:
        payload = response.read()
    actual = sha256_bytes(payload)
    if actual != expected_sha256:
        raise ValueError(
            f"download hash mismatch for {url}: expected {expected_sha256}, got {actual}"
        )
    temporary.write_bytes(payload)
    temporary.replace(path)
    return path


def load_task_rows(zip_path: Path, task_id: int) -> list[dict[str, Any]]:
    member = f"task_{task_id}.jsonl"
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if names != [member]:
            raise ValueError(f"unexpected PUB task archive members: {names}")
        lines = archive.read(member).decode("utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    ids = [str(row.get("id")) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"task {task_id} contains duplicate IDs")
    for row in rows:
        if not isinstance(row.get("pretext"), str):
            raise ValueError(f"task {task_id} row {row.get('id')} lacks pretext")
        if not isinstance(row.get("options"), list) or len(row["options"]) < 2:
            raise ValueError(f"task {task_id} row {row.get('id')} lacks options")
        if row.get("correct answer") not in row["options"]:
            raise ValueError(f"task {task_id} row {row.get('id')} has invalid answer")
    return rows


def deterministic_case_ids(
    rows: Iterable[dict[str, Any]],
    *,
    task_id: int,
    count: int,
    seed: str,
    excluded_ids: set[str],
    offset: int = 0,
) -> list[str]:
    eligible = [str(row["id"]) for row in rows if str(row["id"]) not in excluded_ids]
    ranked = sorted(
        eligible,
        key=lambda item_id: hashlib.sha256(
            f"{seed}|task={task_id}|id={item_id}".encode("utf-8")
        ).hexdigest(),
    )
    if len(ranked) < offset + count:
        raise ValueError(f"task {task_id} has only {len(ranked)} eligible rows")
    return ranked[offset : offset + count]


def option_permutation(option_count: int, *, task_id: int, item_id: str, seed: str) -> list[int]:
    indices = list(range(option_count))
    rng_seed = int.from_bytes(
        hashlib.sha256(
            f"{seed}|options|task={task_id}|id={item_id}".encode("utf-8")
        ).digest()[:8],
        "big",
    )
    random.Random(rng_seed).shuffle(indices)
    return indices


def build_case_manifest(protocol: dict[str, Any], task_rows: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    sampling = protocol["sampling"]
    count = int(sampling["items_per_task"])
    seed = str(sampling["seed"])
    excluded = {str(value) for value in sampling["excluded_ids"]}
    cases = []
    for task in protocol["dataset"]["tasks"]:
        task_id = int(task["task_id"])
        rows = task_rows[task_id]
        if len(rows) != int(task["expected_row_count"]):
            raise ValueError(
                f"task {task_id} row count {len(rows)} != {task['expected_row_count']}"
            )
        by_id = {str(row["id"]): row for row in rows}
        for item_id in deterministic_case_ids(
            rows,
            task_id=task_id,
            count=count,
            seed=seed,
            excluded_ids=excluded,
        ):
            row = by_id[item_id]
            cases.append(
                {
                    "sample_id": f"PUB-T{task_id}-{item_id}",
                    "task_id": task_id,
                    "phenomenon": task["phenomenon"],
                    "task_name": task["task_name"],
                    "item_id": item_id,
                    "option_count": len(row["options"]),
                    "option_permutation": option_permutation(
                        len(row["options"]), task_id=task_id, item_id=item_id, seed=seed
                    ),
                }
            )
    return {
        "schema_version": "m13-pub-case-manifest-v1",
        "sampling_seed": seed,
        "excluded_previously_viewed_ids": sorted(excluded),
        "case_count": len(cases),
        "answer_content_in_manifest": False,
        "cases": cases,
    }


def materialize_case(
    manifest_case: dict[str, Any], task_rows: dict[int, list[dict[str, Any]]]
) -> dict[str, Any]:
    task_id = int(manifest_case["task_id"])
    item_id = str(manifest_case["item_id"])
    by_id = {str(row["id"]): row for row in task_rows[task_id]}
    source = by_id[item_id]
    permutation = [int(index) for index in manifest_case["option_permutation"]]
    options = [str(source["options"][index]) for index in permutation]
    correct_source_index = source["options"].index(source["correct answer"])
    correct_index = permutation.index(correct_source_index)
    return {
        **manifest_case,
        "pretext": str(source["pretext"]),
        "options": options,
        "correct_index": correct_index,
        "correct_answer": options[correct_index],
    }


def _options_text(options: list[str]) -> str:
    return "\n".join(f"[{index}] {option}" for index, option in enumerate(options))


def build_prompt(case: dict[str, Any], condition: str) -> str:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    shared = (
        "This is an internal research multiple-choice task. Do not role-play.\n"
        "Use only the supplied text. Do not add unstated facts.\n\n"
        f"TASK FAMILY: {case['task_name']}\n"
        f"INPUT:\n{case['pretext'].strip()}\n\n"
        f"OPTIONS:\n{_options_text(case['options'])}\n\n"
    )
    if condition == "B0_DIRECT":
        return shared + (
            "Choose the best option. Return JSON only, with exactly one integer field:\n"
            '{"answer_index": 0}\n'
            "The value must be the plain zero-based integer shown beside the option. "
            "Do not wrap the integer in a list or string."
        )
    if condition == "B1_GENERIC_DELIBERATION":
        return shared + (
            "Reason carefully before choosing. Check the context, compare all options, "
            "and consider a counterargument. Return JSON only with exactly these fields "
            "in this order: observations, reasoning_step_1, reasoning_step_2, "
            "counterargument, uncertainty, answer_index. uncertainty must be low, medium, "
            "or high. Keep each text field at 20 words or fewer. answer_index must be the "
            "plain zero-based integer shown beside the option, not a list or string."
        )
    return shared + (
        "Apply the internal pragmatic-understanding loop before choosing. Keep literal "
        "content separate from the context-dependent target; identify the observable "
        "context evidence; retain one plausible alternative instead of inventing motives; "
        "then resolve the communicative intent, stance/sarcasm, presupposition, or deictic "
        "reference required by this task family. Return JSON only with exactly these fields "
        "in this order: literal_content, pragmatic_target, context_evidence, "
        "alternative_interpretation, uncertainty, answer_index. uncertainty must be low, "
        "medium, or high. Keep each text field at 20 words or fewer. answer_index must be "
        "the plain zero-based integer shown beside the option, not a list or string."
    )


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_answer_index(raw: str, option_count: int) -> dict[str, Any]:
    match = _JSON_OBJECT_RE.search(str(raw or ""))
    if not match:
        return {"valid": False, "answer_index": None, "error": "missing_json_object"}
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"valid": False, "answer_index": None, "error": "invalid_json"}
    value = payload.get("answer_index") if isinstance(payload, dict) else None
    if isinstance(value, bool) or not isinstance(value, int):
        return {"valid": False, "answer_index": None, "error": "answer_index_not_integer"}
    if value < 0 or value >= option_count:
        return {"valid": False, "answer_index": None, "error": "answer_index_out_of_range"}
    return {"valid": True, "answer_index": value, "error": None, "payload": payload}


def audit_payload_contract(condition: str, payload: Any) -> dict[str, Any]:
    expected = EXPECTED_PAYLOAD_KEYS[condition]
    if not isinstance(payload, dict):
        return {
            "valid": False,
            "missing_keys": sorted(expected),
            "extra_keys": [],
            "types_valid": False,
        }
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    types_valid = isinstance(payload.get("answer_index"), int) and not isinstance(
        payload.get("answer_index"), bool
    )
    if condition != "B0_DIRECT":
        for key in expected - {"answer_index", "uncertainty"}:
            types_valid = types_valid and isinstance(payload.get(key), str)
        types_valid = types_valid and payload.get("uncertainty") in {"low", "medium", "high"}
    return {
        "valid": not missing and not extra and types_valid,
        "missing_keys": missing,
        "extra_keys": extra,
        "types_valid": types_valid,
    }


def json_schema_for_condition(condition: str, option_count: int) -> dict[str, Any]:
    expected = EXPECTED_PAYLOAD_KEYS[condition]
    properties: dict[str, Any] = {}
    for key in expected:
        if key == "answer_index":
            properties[key] = {
                "type": "integer",
                "minimum": 0,
                "maximum": option_count - 1,
            }
        elif key == "uncertainty":
            properties[key] = {"type": "string", "enum": ["low", "medium", "high"]}
        else:
            properties[key] = {"type": "string", "maxLength": 240}
    ordered_required = [key for key in (
        "observations", "reasoning_step_1", "reasoning_step_2", "counterargument",
        "literal_content", "pragmatic_target", "context_evidence",
        "alternative_interpretation", "uncertainty", "answer_index",
    ) if key in expected]
    return {
        "type": "object",
        "properties": properties,
        "required": ordered_required,
        "additionalProperties": False,
    }


def exact_mcnemar_pvalue(candidate_wins: int, baseline_wins: int) -> float:
    discordant = candidate_wins + baseline_wins
    if discordant == 0:
        return 1.0
    smaller = min(candidate_wins, baseline_wins)
    tail = sum(math.comb(discordant, index) for index in range(smaller + 1)) / (2**discordant)
    return min(1.0, 2 * tail)


def paired_accuracy_comparison(
    rows: list[dict[str, Any]],
    *,
    candidate: str,
    baseline: str,
    bootstrap_repetitions: int,
    seed: int,
) -> dict[str, Any]:
    by_condition = {
        condition: {row["sample_id"]: row for row in rows if row["condition"] == condition}
        for condition in (candidate, baseline)
    }
    if set(by_condition[candidate]) != set(by_condition[baseline]):
        raise ValueError("paired comparison requires identical sample IDs")
    sample_ids = sorted(by_condition[candidate])
    deltas = []
    candidate_wins = baseline_wins = ties = 0
    for sample_id in sample_ids:
        candidate_correct = int(by_condition[candidate][sample_id]["correct"])
        baseline_correct = int(by_condition[baseline][sample_id]["correct"])
        delta = candidate_correct - baseline_correct
        deltas.append(delta)
        if delta > 0:
            candidate_wins += 1
        elif delta < 0:
            baseline_wins += 1
        else:
            ties += 1
    mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
    rng = random.Random(seed)
    boot = []
    for _ in range(bootstrap_repetitions):
        boot.append(sum(rng.choice(deltas) for _ in deltas) / len(deltas))
    boot.sort()
    lower = boot[int(0.025 * bootstrap_repetitions)]
    upper = boot[min(bootstrap_repetitions - 1, int(0.975 * bootstrap_repetitions))]
    return {
        "candidate": candidate,
        "baseline": baseline,
        "sample_count": len(sample_ids),
        "accuracy_delta": round(mean_delta, 6),
        "bootstrap_95_ci": [round(lower, 6), round(upper, 6)],
        "candidate_wins": candidate_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "exact_mcnemar_pvalue": round(
            exact_mcnemar_pvalue(candidate_wins, baseline_wins), 8
        ),
    }


def summarize_rows(
    rows: list[dict[str, Any]],
    *,
    conditions: Iterable[str] = CONDITIONS,
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for condition in conditions:
        subset = [row for row in rows if row["condition"] == condition]
        if not subset:
            raise ValueError(f"no rows for condition {condition}")
        task_summary = {}
        for task_id in sorted({int(row["task_id"]) for row in subset}):
            task_rows = [row for row in subset if int(row["task_id"]) == task_id]
            task_summary[str(task_id)] = {
                "count": len(task_rows),
                "accuracy": round(sum(row["correct"] for row in task_rows) / len(task_rows), 6),
                "parse_rate": round(sum(row["parse_valid"] for row in task_rows) / len(task_rows), 6),
            }
        summary[condition] = {
            "count": len(subset),
            "accuracy": round(sum(row["correct"] for row in subset) / len(subset), 6),
            "parse_rate": round(sum(row["parse_valid"] for row in subset) / len(subset), 6),
            "schema_contract_rate": round(
                sum(row.get("schema_contract_valid", False) for row in subset) / len(subset), 6
            ),
            "prompt_tokens": sum(int(row["prompt_tokens"]) for row in subset),
            "completion_tokens": sum(int(row["completion_tokens"]) for row in subset),
            "latency_seconds": round(sum(float(row["latency_seconds"]) for row in subset), 3),
            "by_task": task_summary,
        }
    return summary


def prospective_exact_mcnemar_power(
    sample_count: int,
    *,
    accuracy_delta: float,
    discordance_rate: float,
    alpha: float = 0.05,
) -> float:
    """Exact unconditional power for a directional benefit using two-sided McNemar.

    The alternative is parameterized by the paired accuracy difference ``b-c``
    and total discordance ``b+c``.  For every possible discordant-pair count,
    this sums the probability that the candidate wins enough pairs for the
    exact two-sided binomial/McNemar p-value to be at most ``alpha``.
    """

    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    if not (0 < discordance_rate <= 1):
        raise ValueError("discordance_rate must be in (0, 1]")
    if not (0 < accuracy_delta < discordance_rate):
        raise ValueError("accuracy_delta must be in (0, discordance_rate)")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")

    candidate_win_given_discordance = (
        discordance_rate + accuracy_delta
    ) / (2 * discordance_rate)

    def binomial_probabilities(trials: int, probability: float) -> list[float]:
        mode = min(trials, max(0, int(math.floor((trials + 1) * probability))))
        log_mode_probability = (
            math.lgamma(trials + 1)
            - math.lgamma(mode + 1)
            - math.lgamma(trials - mode + 1)
            + mode * math.log(probability)
            + (trials - mode) * math.log1p(-probability)
        )
        values = [0.0] * (trials + 1)
        values[mode] = math.exp(log_mode_probability)
        for index in range(mode, 0, -1):
            values[index - 1] = (
                values[index]
                * index
                / (trials - index + 1)
                * (1 - probability)
                / probability
            )
        for index in range(mode, trials):
            values[index + 1] = (
                values[index]
                * (trials - index)
                / (index + 1)
                * probability
                / (1 - probability)
            )
        total = sum(values)
        return [value / total for value in values]

    discordant_count_probabilities = binomial_probabilities(
        sample_count, discordance_rate
    )
    power = 0.0
    for discordant_count, count_probability in enumerate(
        discordant_count_probabilities
    ):
        if discordant_count == 0 or count_probability == 0:
            continue
        null_probabilities = binomial_probabilities(discordant_count, 0.5)
        null_lower_tail = 0.0
        critical_candidate_wins: int | None = None
        for baseline_wins in range((discordant_count - 1) // 2 + 1):
            null_lower_tail += null_probabilities[baseline_wins]
            if min(1.0, 2 * null_lower_tail) <= alpha + 1e-15:
                critical_candidate_wins = discordant_count - baseline_wins
            else:
                break
        if critical_candidate_wins is None:
            continue
        alternative_probabilities = binomial_probabilities(
            discordant_count, candidate_win_given_discordance
        )
        power += count_probability * sum(
            alternative_probabilities[critical_candidate_wins:]
        )
    return power
