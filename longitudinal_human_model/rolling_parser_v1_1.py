"""M8.1 numeric-boundary parser; preserves the frozen M8 feature prompt."""

from __future__ import annotations

import hashlib
import math
from typing import Any, Callable, Mapping, Sequence

from .baselines import ProviderError, _extract_json_object
from .transitions import feature_extraction_prompt


def extract_event_features_bounded(
    event_text: str,
    feature_names: Sequence[str],
    *,
    model: str,
    provider: Callable[..., dict[str, Any]],
    options: Mapping[str, Any],
) -> dict[str, Any]:
    prompt = feature_extraction_prompt(event_text, feature_names)
    result = provider(model=model, prompt=prompt, options=dict(options))
    parsed = _extract_json_object(result["text"])
    features = parsed.get("features")
    if not isinstance(features, Mapping) and set(parsed) == set(feature_names):
        features = parsed
    if not isinstance(features, Mapping) or set(features) != set(feature_names):
        raise ProviderError("feature extractor did not return an exact feature map")
    clean, normalizations = {}, []
    for name in feature_names:
        raw = features[name]
        if isinstance(raw, bool):
            raise ProviderError(f"extracted_features.{name} must be numeric")
        try:
            numeric = float(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderError(f"extracted_features.{name} must be numeric") from exc
        if not math.isfinite(numeric):
            raise ProviderError(f"extracted_features.{name} must be finite")
        bounded = max(0.0, min(1.0, numeric))
        if bounded != numeric:
            normalizations.append({"feature": name, "raw_value": numeric, "bounded_value": bounded})
        clean[name] = bounded
    return {
        "features": clean,
        "numeric_boundary_normalizations": normalizations,
        "raw_response": str(result["text"]),
        "raw_response_sha256": hashlib.sha256(str(result["text"]).encode("utf-8")).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_tokens": int(result.get("prompt_tokens") or 0),
        "completion_tokens": int(result.get("completion_tokens") or 0),
        "latency_seconds": float(result.get("latency_seconds") or 0.0),
        "model_reported": result.get("model_reported") or model,
    }
