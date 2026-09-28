"""Frozen P4-BD evidence-boundary evaluator; no model or product-runtime calls.

Only a prospectively enumerated, source-exact span may replace the single-gold
boundary. The role, source identity, canonical slots, and every downstream gate
remain independent checks. This is a developer-authored proxy, not a semantic
similarity model or proof of pragmatic understanding.
"""
from __future__ import annotations


def score_atoms(case: dict, atoms: object) -> dict:
    """Score three ordered role atoms against explicit per-role span sets only."""
    source = case["source"]["text"]
    expected_roles = [atom["role"] for atom in case["expected_spec"]["evidence_atoms"]]
    result = {
        "role_order_exact": False,
        "source_exact_atom_count": 0,
        "accepted_atom_count": 0,
        "per_role": {},
        "all_accepted": False,
    }
    if not isinstance(atoms, list) or len(atoms) != len(expected_roles):
        return result
    if not all(isinstance(atom, dict) and set(atom) == {"role", "text"} for atom in atoms):
        return result
    roles = [atom["role"] for atom in atoms]
    if roles != expected_roles or len(set(roles)) != len(roles):
        return result
    result["role_order_exact"] = True
    for atom in atoms:
        role = atom["role"]
        value = atom["text"]
        annotation = case["role_annotations"][role]
        exact_source = isinstance(value, str) and bool(value) and value in source
        accepted = exact_source and value in annotation["accepted_exact_spans"]
        result["per_role"][role] = {
            "source_exact": exact_source,
            "accepted": accepted,
        }
        result["source_exact_atom_count"] += int(exact_source)
        result["accepted_atom_count"] += int(accepted)
    result["all_accepted"] = result["accepted_atom_count"] == len(expected_roles)
    return result


def score_packet(case: dict, normalized_spec: dict | None, raw_atoms: object) -> dict:
    """Keep raw evidence diagnostic separate from eligible normalized packets."""
    raw = score_atoms(case, raw_atoms)
    if not isinstance(normalized_spec, dict):
        return {
            "raw_role_aware_evidence": raw["all_accepted"],
            "raw_accepted_atom_count": raw["accepted_atom_count"],
            "role_aware_evidence": False,
            "accepted_atom_count": 0,
            "non_span_exact": False,
            "role_aware_packet_exact": False,
            "per_role": raw["per_role"],
        }
    observed_non_span = {key: value for key, value in normalized_spec.items() if key != "evidence_atoms"}
    expected_non_span = {
        key: value for key, value in case["expected_spec"].items()
        if key != "evidence_atoms"
    }
    scored = score_atoms(case, normalized_spec.get("evidence_atoms"))
    non_span_exact = observed_non_span == expected_non_span
    return {
        "raw_role_aware_evidence": raw["all_accepted"],
        "raw_accepted_atom_count": raw["accepted_atom_count"],
        "role_aware_evidence": scored["all_accepted"],
        "accepted_atom_count": scored["accepted_atom_count"],
        "non_span_exact": non_span_exact,
        "role_aware_packet_exact": bool(non_span_exact and scored["all_accepted"]),
        "per_role": scored["per_role"],
    }
