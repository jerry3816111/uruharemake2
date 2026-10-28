"""One-key classifier parser remediation for M10.1."""

from __future__ import annotations

from typing import Any

from .metrics import normalize_distribution
from .realization import extract_json_object


class ClassifierAliasParser:
    def __init__(self):
        self.normalizations: list[dict[str, Any]] = []

    def __call__(self, text: str, labels: list[str]) -> dict[str, Any]:
        parsed = extract_json_object(text)
        probabilities = parsed.get("probabilities")
        source_key = "probabilities"
        if probabilities is None and isinstance(parsed.get("classification"), dict):
            candidate = parsed["classification"]
            if set(candidate) != set(labels):
                raise ValueError("classification alias label set differs from frozen taxonomy")
            probabilities = candidate
            source_key = "classification"
            self.normalizations.append(
                {
                    "normalization": "classification_to_probabilities",
                    "raw_distribution": dict(candidate),
                }
            )
        if not isinstance(probabilities, dict):
            raise ValueError("classifier output lacks probabilities")
        normalized = normalize_distribution(probabilities, labels)
        selected = max(labels, key=lambda label: (normalized[label], -labels.index(label)))
        return {
            "probabilities": normalized,
            "selected_behavior": selected,
            "brief_evidence": str(parsed.get("brief_evidence") or "")[:500],
            "distribution_source_key": source_key,
        }
