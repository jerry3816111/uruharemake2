"""B4/B5 strong history baselines for temporal behavior prediction."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Any, Callable

from .baselines import ProviderError, _extract_json_object
from .metrics import normalize_distribution


STRONG_BASELINES = ("B4_FULL_HISTORY_SUMMARY", "B5_STRUCTURED_HISTORY")


def history_signature(model_input: dict[str, Any]) -> str:
    payload = {
        "target_id": model_input["target"]["target_id"],
        "history": model_input["available_history"],
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _summary_prompt(model_input: dict[str, Any]) -> str:
    payload = {
        "task": "Condense all authorized pre-cutoff observations into a behavior-prediction summary.",
        "target": {
            "target_id": model_input["target"]["target_id"],
            "display_name": model_input["target"]["display_name"],
        },
        "history_snapshot_available_through": max(
            row["available_at"] for row in model_input["available_history"]
        ),
        "candidate_behavior_labels": model_input["candidate_behavior_labels"],
        "authorized_pre_cutoff_observations": model_input["available_history"],
        "output_contract": {
            "summary": "A concise evidence-grounded description of observable behavioral tendencies."
        },
        "constraints": [
            "Return JSON only.",
            "Use only the provided observations.",
            "Do not infer private thoughts, diagnoses, childhood, or unseen facts.",
            "Retain uncertainty and conflicting tendencies.",
            "Do not predict any specific future event.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def summarize_full_history(
    model_input: dict[str, Any],
    *,
    model: str,
    provider: Callable[..., dict[str, Any]],
    options: dict[str, Any],
) -> dict[str, Any]:
    prompt = _summary_prompt(model_input)
    provider_result = provider(model=model, prompt=prompt, options=options)
    parsed = _extract_json_object(provider_result["text"])
    summary = parsed.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ProviderError("summary output did not contain a non-empty summary string")
    return {
        "history_signature": history_signature(model_input),
        "history_ids": [row["history_id"] for row in model_input["available_history"]],
        "summary": summary.strip()[:4000],
        "summary_sha256": hashlib.sha256(summary.strip().encode("utf-8")).hexdigest(),
        "runtime": {
            "prompt_sha256": _prompt_hash(prompt),
            "prompt_tokens": int(provider_result.get("prompt_tokens") or 0),
            "completion_tokens": int(provider_result.get("completion_tokens") or 0),
            "latency_seconds": float(provider_result.get("latency_seconds") or 0.0),
            "total_duration_ns": int(provider_result.get("total_duration_ns") or 0),
            "model_reported": provider_result.get("model_reported") or model,
        },
    }


def build_structured_history(model_input: dict[str, Any]) -> dict[str, Any]:
    """Create a strong prompt representation without performing state transition."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in model_input["available_history"]:
        grouped[row["behavior_label"]].append(row)
    patterns = []
    for label in model_input["candidate_behavior_labels"]:
        rows = sorted(grouped.get(label, []), key=lambda row: (row["available_at"], row["history_id"]))
        patterns.append(
            {
                "behavior_label": label,
                "observed_count": len(rows),
                "latest_available_at": rows[-1]["available_at"] if rows else None,
                "evidence": [
                    {
                        "history_id": row["history_id"],
                        "event_time": row["event_time"],
                        "observable_summary": row["observable_summary"],
                    }
                    for row in rows
                ],
            }
        )
    return {
        "history_cutoff": model_input["available_history_cutoff"],
        "history_record_count": len(model_input["available_history"]),
        "behavior_patterns": patterns,
    }


def _prediction_prompt(
    baseline: str,
    model_input: dict[str, Any],
    *,
    summary_artifact: dict[str, Any] | None,
) -> str:
    labels = model_input["candidate_behavior_labels"]
    payload: dict[str, Any] = {
        "task": "Predict the distribution of the target person's next observable behavior.",
        "prediction_time": model_input["prediction_time"],
        "event_context": model_input["event_context"],
        "participants": model_input["participants"],
        "candidate_behavior_labels": labels,
        "output_contract": {
            "probabilities": {label: "number from 0 to 1" for label in labels},
            "brief_evidence": "at most two short sentences",
        },
        "constraints": [
            "Return JSON only.",
            "Use every candidate label exactly once in probabilities.",
            "Probabilities must sum to 1.",
            "Do not invent private thoughts or unseen facts.",
        ],
    }
    if baseline == "B4_FULL_HISTORY_SUMMARY":
        if not summary_artifact:
            raise ValueError("B4 requires a frozen pre-cutoff summary artifact")
        payload["target"] = {
            "target_id": model_input["target"]["target_id"],
            "display_name": model_input["target"]["display_name"],
        }
        payload["full_history_summary"] = summary_artifact["summary"]
        payload["summary_history_ids"] = summary_artifact["history_ids"]
        payload["information_condition"] = "current event plus model-condensed full pre-cutoff history"
    elif baseline == "B5_STRUCTURED_HISTORY":
        payload["target"] = model_input["target"]
        payload["structured_full_history"] = build_structured_history(model_input)
        payload["information_condition"] = (
            "current event, frozen persona summary, and all pre-cutoff history grouped by behavior"
        )
    else:
        raise ValueError(f"unsupported strong baseline: {baseline}")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_probabilities(text: str, labels: list[str]) -> tuple[dict[str, float], str]:
    parsed = _extract_json_object(text)
    probabilities = parsed.get("probabilities")
    evidence = parsed.get("brief_evidence")
    if not isinstance(probabilities, dict) and set(parsed) == set(labels):
        probabilities = parsed
        evidence = ""
    if not isinstance(probabilities, dict):
        raise ProviderError("model JSON did not contain an exact probability map")
    if set(probabilities) != set(labels):
        missing = sorted(set(labels) - set(probabilities))
        unknown = sorted(set(probabilities) - set(labels))
        raise ProviderError(
            f"probability map must contain every frozen label exactly once; missing={missing}, unknown={unknown}"
        )
    try:
        normalized = normalize_distribution(probabilities, labels)
    except (TypeError, ValueError) as exc:
        raise ProviderError(str(exc)) from exc
    if not isinstance(evidence, str):
        evidence = ""
    return normalized, evidence[:500]


def predict_strong_baseline(
    baseline: str,
    model_input: dict[str, Any],
    *,
    summary_artifact: dict[str, Any] | None,
    model: str,
    provider: Callable[..., dict[str, Any]],
    options: dict[str, Any],
) -> dict[str, Any]:
    if baseline not in STRONG_BASELINES:
        raise ValueError(f"unsupported strong baseline {baseline!r}")
    prompt = _prediction_prompt(baseline, model_input, summary_artifact=summary_artifact)
    provider_result = provider(model=model, prompt=prompt, options=options)
    probabilities, evidence = _parse_probabilities(
        provider_result["text"], list(model_input["candidate_behavior_labels"])
    )
    if baseline == "B4_FULL_HISTORY_SUMMARY":
        evidence_ids = list(summary_artifact["history_ids"] if summary_artifact else [])
    else:
        evidence_ids = [row["history_id"] for row in model_input["available_history"]]
    return {
        "probabilities": probabilities,
        "brief_evidence": evidence,
        "evidence_history_ids": evidence_ids,
        "prompt_sha256": _prompt_hash(prompt),
        "latency_seconds": float(provider_result.get("latency_seconds") or 0.0),
        "prompt_tokens": int(provider_result.get("prompt_tokens") or 0),
        "completion_tokens": int(provider_result.get("completion_tokens") or 0),
        "total_duration_ns": int(provider_result.get("total_duration_ns") or 0),
        "model_reported": provider_result.get("model_reported") or model,
    }
