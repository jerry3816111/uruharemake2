#!/usr/bin/env python3
"""Run blind local reviews for the V2 support-equivalence pool."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_equivalence_v2_construction_preregistration.json"
)
MEMORY_KINDS = ("episodic", "wisdom", "procedural")
TOOL_NAME = "submit_support_equivalence_review"
TIMEOUT_SECONDS = 180
KEEP_ALIVE = "20m"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _post_json(url, body, timeout=TIMEOUT_SECONDS):
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(url, timeout=TIMEOUT_SECONDS):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _model_snapshots():
    payload = _get_json("http://127.0.0.1:11434/api/tags")
    return {row["name"]: row for row in payload.get("models", [])}


def _canonical_minimal_sets(raw_sets):
    if not isinstance(raw_sets, list):
        raise ValueError("minimal_support_sets_type")
    parsed = []
    for indices in raw_sets:
        if not isinstance(indices, list):
            raise ValueError("support_set_type")
        if any(
            isinstance(index, bool)
            or not isinstance(index, int)
            or index not in range(1, 7)
            for index in indices
        ):
            raise ValueError("support_index_contract")
        if not indices:
            raise ValueError("empty_minimal_support_set")
        parsed.append(tuple(sorted(set(indices))))
    unique = sorted(set(parsed), key=lambda item: (len(item), item))
    antichain = []
    for candidate in unique:
        candidate_set = set(candidate)
        if any(set(existing) < candidate_set for existing in antichain):
            continue
        antichain.append(candidate)
    return [list(item) for item in antichain]


def _acceptable_unions(minimal_sets):
    if not minimal_sets:
        return []
    unions = set()
    for count in range(1, len(minimal_sets) + 1):
        for selected in itertools.combinations(minimal_sets, count):
            unions.add(
                tuple(
                    sorted(
                        set().union(
                            *(set(indices) for indices in selected)
                        )
                    )
                )
            )
    return [list(item) for item in sorted(unions, key=lambda x: (len(x), x))]


def _tool_contract():
    return {
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": (
                "Return every distinct minimal set of source-event indices "
                "that fully supports the derived memory."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["minimal_support_sets"],
                "properties": {
                    "minimal_support_sets": {
                        "type": "array",
                        "description": (
                            "All smallest sufficient event-index sets. "
                            "Return [] when unsupported."
                        ),
                        "items": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 6,
                            "uniqueItems": True,
                            "items": {
                                "type": "integer",
                                "enum": [1, 2, 3, 4, 5, 6],
                            },
                        },
                    }
                },
            },
        },
    }


def _system_prompt(config):
    rules = config["support_equivalence_contract"][
        "memory_kind_rules"
    ]
    return (
        "You are a blind evidence annotator. You receive one already-"
        "generated memory and six chronological dialogue events. Call "
        f"{TOOL_NAME} exactly once and return no narrative text. List EVERY "
        "distinct minimal support set, not merely one possible set. A "
        "minimal support set is the smallest set of User events that jointly "
        "entails every material claim. If two events each independently "
        "entail the full memory, return two singleton sets; do not add their "
        "union as a minimal set. Assistant text is context only and never "
        "independent evidence about the user. Topic similarity, a third-"
        "party fact, a possibility, an assistant suggestion, a one-time "
        "request, or a contradicted stale state is not support. Return an "
        "empty list if no complete support set exists.\n"
        f"Episodic rule: {rules['episodic']}\n"
        f"Wisdom rule: {rules['wisdom']}\n"
        f"Procedural rule: {rules['procedural']}\n"
        f"Current-state rule: {rules['current_state_override']}"
    )


def _render_user(case, memory_kind):
    memory = case["derived_memories"][memory_kind]
    lines = [
        f"Memory kind: {memory_kind}",
        f"Derived memory: {memory['text']}",
        "",
        "Chronological source events:",
    ]
    for event in case["source_events"]:
        lines.extend(
            [
                f"Event E{event['index']}",
                f"User: {event['user']}",
                f"Assistant: {event['assistant']}",
            ]
        )
    return "\n".join(lines)


def _request_body(config, reviewer, case, memory_kind):
    generation = config["independent_machine_review"][
        "shared_generation_settings"
    ]
    return {
        "model": reviewer["ollama_tag"],
        "messages": [
            {"role": "system", "content": _system_prompt(config)},
            {
                "role": "user",
                "content": _render_user(case, memory_kind),
            },
        ],
        "tools": [_tool_contract()],
        "stream": False,
        "think": generation["thinking"],
        "keep_alive": KEEP_ALIVE,
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "seed": reviewer["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }


def _parse_response(response):
    message = response.get("message") if isinstance(response, dict) else None
    if not isinstance(message, dict):
        raise ValueError("message_shape")
    if str(message.get("content") or "").strip():
        raise ValueError("narrative_content")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        raise ValueError("tool_call_count")
    function = calls[0].get("function")
    if not isinstance(function, dict):
        raise ValueError("function_shape")
    if function.get("name") != TOOL_NAME:
        raise ValueError("function_name")
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if not isinstance(arguments, dict):
        raise ValueError("arguments_shape")
    if set(arguments) != {"minimal_support_sets"}:
        raise ValueError("argument_keys")
    minimal = _canonical_minimal_sets(
        arguments["minimal_support_sets"]
    )
    return {
        "minimal_support_sets": minimal,
        "acceptable_support_unions": _acceptable_unions(minimal),
        "support_universe": sorted(
            set().union(*(set(item) for item in minimal))
            if minimal
            else set()
        ),
        "support_mode": "supported" if minimal else "unsupported",
    }


def _call_key(reviewer_name, case_id, memory_kind):
    return f"{reviewer_name}::{case_id}::{memory_kind}"


def _checkpoint_base(config, pool, snapshots):
    return {
        "schema": "uruha_consolidation_support_equivalence_review_checkpoint_v2",
        "experiment_id": config["experiment_id"],
        "config_sha256": _sha256(CONFIG_PATH),
        "pool_sha256": hashlib.sha256(
            json.dumps(
                pool,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "reviewer_snapshots": snapshots,
        "transport_attempts": 0,
        "candidate_model_calls": 0,
        "production_database_writes": 0,
        "calls": [],
        "complete": False,
    }


def _verify_checkpoint(checkpoint, config, pool, snapshots):
    expected = _checkpoint_base(config, pool, snapshots)
    for key in (
        "experiment_id",
        "config_sha256",
        "pool_sha256",
        "reviewer_snapshots",
        "candidate_model_calls",
        "production_database_writes",
    ):
        if checkpoint.get(key) != expected[key]:
            raise RuntimeError(f"checkpoint drift: {key}")
    keys = [row["call_key"] for row in checkpoint.get("calls", [])]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate checkpoint calls")
    if checkpoint.get("transport_attempts") != len(keys):
        raise RuntimeError("transport attempt count drift")


def _call_reviewer(config, reviewer_name, reviewer, case, memory_kind):
    body = _request_body(
        config,
        reviewer,
        case,
        memory_kind,
    )
    started = time.perf_counter()
    response = None
    transport_error = None
    parse_error = None
    parsed = None
    try:
        response = _post_json(
            "http://127.0.0.1:11434/api/chat",
            body,
        )
        parsed = _parse_response(response)
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        transport_error = f"{type(exc).__name__}: {exc}"
    except (TypeError, ValueError) as exc:
        parse_error = f"{type(exc).__name__}: {exc}"
    return {
        "call_key": _call_key(
            reviewer_name,
            case["id"],
            memory_kind,
        ),
        "reviewer": reviewer_name,
        "case_id": case["id"],
        "language": case["language"],
        "memory_kind": memory_kind,
        "model": reviewer["ollama_tag"],
        "model_digest": reviewer["digest"],
        "request_sha256": hashlib.sha256(
            json.dumps(
                body,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "transport_attempts": 1,
        "transport_error": transport_error,
        "parse_error": parse_error,
        "parse_success": parsed is not None,
        "judgment": parsed,
        "response": response,
        "wall_seconds": round(time.perf_counter() - started, 6),
    }


def _reviewer_snapshots(config):
    installed = _model_snapshots()
    snapshots = {}
    for name in ("reviewer_a", "reviewer_b"):
        expected = config["independent_machine_review"][name]
        observed = installed.get(expected["ollama_tag"])
        if not observed:
            raise RuntimeError(f"missing reviewer model: {name}")
        if observed.get("digest") != expected["digest"]:
            raise RuntimeError(f"reviewer digest drift: {name}")
        snapshots[name] = {
            "ollama_tag": observed["name"],
            "digest": observed["digest"],
            "size": observed.get("size"),
            "details": observed.get("details"),
        }
    return snapshots


def _comparison(config, pool, checkpoint):
    calls = {row["call_key"]: row for row in checkpoint["calls"]}
    retained = []
    cases = []
    retired = []
    for case in pool["cases"]:
        item_rows = []
        case_agreement = True
        for memory_kind in MEMORY_KINDS:
            author = case["derived_memories"][memory_kind][
                "minimal_support_sets"
            ]
            reviewer_sets = {}
            for reviewer_name in ("reviewer_a", "reviewer_b"):
                call = calls[
                    _call_key(
                        reviewer_name,
                        case["id"],
                        memory_kind,
                    )
                ]
                reviewer_sets[reviewer_name] = (
                    call["judgment"]["minimal_support_sets"]
                    if call["parse_success"]
                    else None
                )
            agreement = (
                reviewer_sets["reviewer_a"] == author
                and reviewer_sets["reviewer_b"] == author
            )
            case_agreement = case_agreement and agreement
            item_rows.append(
                {
                    "memory_kind": memory_kind,
                    "support_phenomenon": case["derived_memories"][
                        memory_kind
                    ]["support_phenomenon"],
                    "author_minimal_support_sets": author,
                    "reviewer_a_minimal_support_sets": reviewer_sets[
                        "reviewer_a"
                    ],
                    "reviewer_b_minimal_support_sets": reviewer_sets[
                        "reviewer_b"
                    ],
                    "three_way_canonical_agreement": agreement,
                }
            )
        case_result = {
            "case_id": case["id"],
            "language": case["language"],
            "retained": case_agreement,
            "items": item_rows,
        }
        cases.append(case_result)
        if case_agreement:
            final_case = copy.deepcopy(case)
            final_case["construction_review"] = {
                "three_way_canonical_agreement": True,
                "reviewers": ["qwen3.5:9b", "qwen2.5:7b"],
            }
            retained.append(final_case)
        else:
            retired.append(case_result)

    final_dataset = {
        "schema": "uruha_consolidation_support_equivalence_pilot_v2",
        "experiment_id": config["experiment_id"],
        "created_at": "2026-07-18T04:30:00+09:00",
        "provenance": {
            "source_pool": config["construction_pool"][
                "pool_dataset_path"
            ],
            "retention": "complete_case_three_way_machine_consensus",
            "human_label_validation": False,
            "human_quality_gold": False,
            "candidate_model_output_used": False,
        },
        "cases": retained,
    }
    return final_dataset, cases, retired


def _review_metrics(config, final_dataset, checkpoint):
    cases = final_dataset["cases"]
    memories = [
        memory
        for case in cases
        for memory in case["derived_memories"].values()
    ]
    calls = checkpoint["calls"]
    return {
        "pool_review_call_count": len(calls),
        "transport_attempt_count": checkpoint["transport_attempts"],
        "transport_error_count": sum(
            bool(row["transport_error"]) for row in calls
        ),
        "parse_error_count": sum(
            bool(row["parse_error"]) for row in calls
        ),
        "parse_success_count": sum(row["parse_success"] for row in calls),
        "final_case_count": len(cases),
        "final_derived_memory_count": len(memories),
        "case_count_by_language": dict(
            Counter(case["language"] for case in cases)
        ),
        "derived_memory_count_by_kind": dict(
            Counter(memory["memory_kind"] for memory in memories)
        ),
        "support_phenomenon_counts": dict(
            Counter(memory["support_phenomenon"] for memory in memories)
        ),
        "candidate_model_call_count": checkpoint[
            "candidate_model_calls"
        ],
        "production_database_write_count": checkpoint[
            "production_database_writes"
        ],
        "reviewer_wall_seconds": {
            name: round(
                sum(
                    row["wall_seconds"]
                    for row in calls
                    if row["reviewer"] == name
                ),
                4,
            )
            for name in ("reviewer_a", "reviewer_b")
        },
    }


def run_reviews(resume=True):
    config = _load(CONFIG_PATH)
    pool_path = ROOT / config["construction_pool"]["pool_dataset_path"]
    final_path = ROOT / config["construction_pool"]["final_dataset_path"]
    audit_path = ROOT / config["construction_pool"]["audit_json_path"]
    pool = _load(pool_path)
    snapshots = _reviewer_snapshots(config)

    if final_path.exists():
        raise RuntimeError("final dataset already exists")
    if audit_path.exists():
        checkpoint = _load(audit_path)
        if checkpoint.get("complete"):
            raise RuntimeError("completed review artifact already exists")
        if not resume:
            raise RuntimeError("checkpoint exists but resume disabled")
        _verify_checkpoint(checkpoint, config, pool, snapshots)
    else:
        checkpoint = _checkpoint_base(config, pool, snapshots)
        _atomic_write(audit_path, checkpoint)

    completed = {
        row["call_key"] for row in checkpoint.get("calls", [])
    }
    reviewers = config["independent_machine_review"]
    for reviewer_name in ("reviewer_a", "reviewer_b"):
        reviewer = reviewers[reviewer_name]
        for case in pool["cases"]:
            for memory_kind in MEMORY_KINDS:
                key = _call_key(
                    reviewer_name,
                    case["id"],
                    memory_kind,
                )
                if key in completed:
                    continue
                call = _call_reviewer(
                    config,
                    reviewer_name,
                    reviewer,
                    case,
                    memory_kind,
                )
                checkpoint["calls"].append(call)
                checkpoint["transport_attempts"] += 1
                _atomic_write(audit_path, checkpoint)
                completed.add(key)
                print(
                    f"{len(completed)}/"
                    f"{reviewers['review_call_budget_exact']} "
                    f"{key} parse={call['parse_success']}",
                    flush=True,
                )

    expected_calls = reviewers["review_call_budget_exact"]
    if len(checkpoint["calls"]) != expected_calls:
        raise RuntimeError("review call budget incomplete")
    final_dataset, comparisons, retired = _comparison(
        config,
        pool,
        checkpoint,
    )
    metrics = _review_metrics(config, final_dataset, checkpoint)
    checkpoint.update(
        {
            "schema": (
                "uruha_consolidation_support_equivalence_"
                "construction_audit_v2"
            ),
            "complete": True,
            "comparisons": comparisons,
            "retired_cases": retired,
            "review_metrics": metrics,
            "final_dataset_sha256": hashlib.sha256(
                (
                    json.dumps(
                        final_dataset,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                ).encode("utf-8")
            ).hexdigest(),
        }
    )
    _atomic_write(final_path, final_dataset)
    _atomic_write(audit_path, checkpoint)
    return checkpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Reject an existing incomplete checkpoint.",
    )
    args = parser.parse_args()
    subprocess.run(
        ["git", "diff", "--check"],
        cwd=ROOT,
        check=True,
    )
    result = run_reviews(resume=not args.no_resume)
    print(
        json.dumps(
            result["review_metrics"],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
