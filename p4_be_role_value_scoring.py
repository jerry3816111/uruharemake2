"""Prospective, source-bound P4-BE role/value scorer; no model calls.

This is a bounded developer-authored proxy. A role's source window and semantic
anchors must be frozen before either compared prompt is executed. It is not a
general semantic-understanding judge or a substitute for human evaluation.
"""
from __future__ import annotations


def score_atoms(case: dict, atoms: object) -> dict:
    source = case["source"]["text"]
    roles = [atom["role"] for atom in case["expected_spec"]["evidence_atoms"]]
    result = {
        "role_order_exact": False,
        "source_exact_atom_count": 0,
        "accepted_atom_count": 0,
        "per_role": {},
        "all_accepted": False,
    }
    if not isinstance(atoms, list) or len(atoms) != len(roles):
        return result
    if not all(isinstance(atom, dict) and set(atom) == {"role", "text"} for atom in atoms):
        return result
    if [atom["role"] for atom in atoms] != roles or len(set(roles)) != len(roles):
        return result
    result["role_order_exact"] = True
    for atom in atoms:
        role = atom["role"]
        value = atom["text"]
        annotation = case["role_annotations"][role]
        window = annotation["allowed_window"]
        source_exact = isinstance(value, str) and bool(value) and value in source
        window_unique = source.count(window) == 1
        within_window = bool(source_exact and window_unique and value in window)
        examples = (annotation["benign_short"], annotation["benign_long"])
        allowed_starts = {window.index(example) for example in examples}
        allowed_ends = {window.index(example) + len(example) for example in examples}
        boundary_valid = bool(
            within_window and any(
                window.startswith(value, position)
                and position in allowed_starts
                and position + len(value) in allowed_ends
                for position in range(len(window))
            )
        )
        required_present = bool(
            within_window and all(anchor in value for anchor in annotation["required_anchors"])
        )
        forbidden_absent = bool(
            within_window and not any(anchor in value for anchor in annotation["forbidden_anchors"])
        )
        # Boundary shape is diagnostic, not a gate: otherwise this becomes the
        # same two-span enumeration that produced P4-BD false negatives.
        accepted = bool(required_present and forbidden_absent)
        result["per_role"][role] = {
            "source_exact": source_exact,
            "within_window": within_window,
            "boundary_valid": boundary_valid,
            "required_present": required_present,
            "forbidden_absent": forbidden_absent,
            "accepted": accepted,
        }
        result["source_exact_atom_count"] += int(source_exact)
        result["accepted_atom_count"] += int(accepted)
    result["all_accepted"] = result["accepted_atom_count"] == len(roles)
    return result


def score_packet(case: dict, normalized_spec: dict | None, raw_atoms: object) -> dict:
    """Raw quote diagnostics never rescue an invalid or unavailable packet."""
    raw = score_atoms(case, raw_atoms)
    if not isinstance(normalized_spec, dict):
        return {
            "raw_role_value_evidence": raw["all_accepted"],
            "raw_accepted_atom_count": raw["accepted_atom_count"],
            "role_value_evidence": False,
            "accepted_atom_count": 0,
            "non_span_exact": False,
            "role_value_packet_exact": False,
            "per_role": raw["per_role"],
        }
    scored = score_atoms(case, normalized_spec.get("evidence_atoms"))
    observed_non_span = {
        key: value for key, value in normalized_spec.items() if key != "evidence_atoms"
    }
    expected_non_span = {
        key: value for key, value in case["expected_spec"].items() if key != "evidence_atoms"
    }
    non_span_exact = observed_non_span == expected_non_span
    return {
        "raw_role_value_evidence": raw["all_accepted"],
        "raw_accepted_atom_count": raw["accepted_atom_count"],
        "role_value_evidence": scored["all_accepted"],
        "accepted_atom_count": scored["accepted_atom_count"],
        "non_span_exact": non_span_exact,
        "role_value_packet_exact": bool(non_span_exact and scored["all_accepted"]),
        "per_role": scored["per_role"],
    }
