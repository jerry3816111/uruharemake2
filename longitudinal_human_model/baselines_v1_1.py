"""M1 V1.1 protocol adapter.

V1 expected ``{"probabilities": {...}}``.  The local model's JSON mode often
returned the exact six-label probability object at the top level.  This adapter
accepts that semantically equivalent transport shape without changing prompts,
labels, model options, probabilities, retrieval, or scoring.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from . import baselines as frozen_v1


def _transport_compatible_provider(
    provider: Callable[..., dict[str, Any]], labels: list[str]
) -> Callable[..., dict[str, Any]]:
    def wrapped(**kwargs: Any) -> dict[str, Any]:
        result = provider(**kwargs)
        parsed = frozen_v1._extract_json_object(result["text"])
        if "probabilities" not in parsed and set(parsed) == set(labels):
            if all(isinstance(parsed[label], (int, float)) for label in labels):
                result = dict(result)
                result["text"] = json.dumps(
                    {"probabilities": parsed, "brief_evidence": ""},
                    ensure_ascii=False,
                    sort_keys=True,
                )
        return result
    return wrapped


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
    compatible = provider
    if provider is not None:
        compatible = _transport_compatible_provider(
            provider, list(model_input["candidate_behavior_labels"])
        )
    return frozen_v1.predict_baseline(
        baseline,
        model_input,
        model=model,
        provider=compatible,
        options=options,
        prior_smoothing=prior_smoothing,
        rag_top_n=rag_top_n,
    )
