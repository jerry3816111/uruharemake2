"""B0-B3 temporal baselines under a shared probability-output contract."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
import time
from typing import Any, Callable
from urllib import error, request

from .metrics import normalize_distribution


BASELINES = ("B0_PRIOR", "B1_BASE_LLM", "B2_PERSONA_PROMPT", "B3_RAG")


class ProviderError(RuntimeError):
    """Raised when the local model does not produce the frozen output contract."""


class OllamaProvider:
    def __init__(self, *, endpoint: str = "http://127.0.0.1:11434/api/generate", timeout: int = 180):
        self.endpoint = endpoint
        self.timeout = timeout

    def __call__(self, *, model: str, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": options,
        }
        started = time.perf_counter()
        http_request = request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        elapsed = time.perf_counter() - started
        if not isinstance(body, dict) or not isinstance(body.get("response"), str):
            raise ProviderError("Ollama response did not contain a text response")
        return {
            "text": body["response"],
            "latency_seconds": elapsed,
            "prompt_tokens": int(body.get("prompt_eval_count") or 0),
            "completion_tokens": int(body.get("eval_count") or 0),
            "total_duration_ns": int(body.get("total_duration") or 0),
            "model_reported": body.get("model"),
        }


def _stable_prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1))
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        candidates.append(text[first : last + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ProviderError("model output was not a JSON object")


def _parse_probability_response(text: str, labels: list[str]) -> tuple[dict[str, float], str]:
    parsed = _extract_json_object(text)
    probabilities = parsed.get("probabilities")
    if not isinstance(probabilities, dict):
        raise ProviderError("model JSON did not contain a probabilities object")
    try:
        normalized = normalize_distribution(probabilities, labels)
    except (TypeError, ValueError) as exc:
        raise ProviderError(str(exc)) from exc
    rationale = parsed.get("brief_evidence")
    if not isinstance(rationale, str):
        rationale = ""
    return normalized, rationale[:500]


def _prior_distribution(model_input: dict[str, Any], *, smoothing: float) -> dict[str, float]:
    labels = model_input["candidate_behavior_labels"]
    counts = Counter(item["behavior_label"] for item in model_input["available_history"])
    raw = {label: counts[label] + smoothing for label in labels}
    return normalize_distribution(raw, labels)


def _lexical_tokens(text: str) -> set[str]:
    return set(re.findall(r"[\w\u3040-\u30ff\u3400-\u9fff]+", text.lower()))


def _retrieve_history(model_input: dict[str, Any], *, top_n: int) -> list[dict[str, Any]]:
    query = _lexical_tokens(str(model_input["event_context"]))
    ranked = []
    for item in model_input["available_history"]:
        tokens = _lexical_tokens(item["observable_summary"])
        union = query | tokens
        similarity = len(query & tokens) / len(union) if union else 0.0
        ranked.append((similarity, item["available_at"], item["history_id"], item))
    ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
    return [item for _, _, _, item in ranked[:top_n]]


def _prompt_for(baseline: str, model_input: dict[str, Any], *, rag_top_n: int) -> str:
    labels = model_input["candidate_behavior_labels"]
    common = {
        "task": "Predict the distribution of the target person's next observable behavior.",
        "prediction_time": model_input["prediction_time"],
        "event_context": model_input["event_context"],
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
    if baseline == "B1_BASE_LLM":
        common["target"] = {"display_name": model_input["target"]["display_name"]}
        common["information_condition"] = "current event only"
    elif baseline == "B2_PERSONA_PROMPT":
        common["target"] = model_input["target"]
        common["information_condition"] = "current event plus frozen persona summary"
    elif baseline == "B3_RAG":
        common["target"] = model_input["target"]
        common["retrieved_past_observations"] = _retrieve_history(model_input, top_n=rag_top_n)
        common["information_condition"] = "current event, persona summary, and pre-cutoff retrieved history"
    else:
        raise ValueError(f"unsupported prompt baseline: {baseline}")
    return json.dumps(common, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def predict_baseline(
    baseline: str,
    model_input: dict[str, Any],
    *,
    model: str,
    provider: Callable[..., dict[str, Any]] | None,
    options: dict[str, Any],
    prior_smoothing: float = 1.0,
    rag_top_n: int = 4,
) -> dict[str, Any]:
    if baseline not in BASELINES:
        raise ValueError(f"unsupported baseline {baseline!r}")
    labels = model_input["candidate_behavior_labels"]
    if baseline == "B0_PRIOR":
        return {
            "probabilities": _prior_distribution(model_input, smoothing=prior_smoothing),
            "brief_evidence": "Smoothed label frequency in the authorized pre-cutoff history.",
            "prompt_sha256": None,
            "latency_seconds": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_duration_ns": 0,
            "model_reported": "deterministic_prior",
            "retrieved_history_ids": [],
        }
    if provider is None:
        raise ValueError("a model provider is required for B1-B3")

    prompt = _prompt_for(baseline, model_input, rag_top_n=rag_top_n)
    provider_result = provider(model=model, prompt=prompt, options=options)
    probabilities, rationale = _parse_probability_response(provider_result["text"], labels)
    retrieved_ids = []
    if baseline == "B3_RAG":
        retrieved_ids = [item["history_id"] for item in _retrieve_history(model_input, top_n=rag_top_n)]
    return {
        "probabilities": probabilities,
        "brief_evidence": rationale,
        "prompt_sha256": _stable_prompt_hash(prompt),
        "latency_seconds": float(provider_result.get("latency_seconds") or 0.0),
        "prompt_tokens": int(provider_result.get("prompt_tokens") or 0),
        "completion_tokens": int(provider_result.get("completion_tokens") or 0),
        "total_duration_ns": int(provider_result.get("total_duration_ns") or 0),
        "model_reported": provider_result.get("model_reported") or model,
        "retrieved_history_ids": retrieved_ids,
    }
