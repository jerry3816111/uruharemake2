"""Corrected V87.2 replay with the V86 treatment settings held constant."""

from __future__ import annotations

import copy

import rightbrain_forbidden_projection_v87 as v87


def evaluate_all(right_brain, packets, raw_rows, candidates, contract):
    bound = v87.bind_cases(packets, raw_rows, candidates, contract)
    previous = (
        right_brain.memory_cue_canonicalization_enabled,
        right_brain.explicit_length_contract_enabled,
        right_brain.forbidden_conflict_projection_enabled,
    )
    right_brain.memory_cue_canonicalization_enabled = True
    right_brain.explicit_length_contract_enabled = True
    right_brain.forbidden_conflict_projection_enabled = False
    rows = []
    try:
        for packet, row, candidate in bound:
            observed_groups = [
                list(group)
                for group in right_brain._model_required_semantic_groups(
                    copy.deepcopy(candidate["target_plan"])
                )
            ]
            result = v87.evaluate_pair(right_brain, packet, row, candidate)
            result["required_contract_matches"] = (
                observed_groups == packet["outcome_contract"]["required_semantic_groups"]
            )
            result["fixed_runtime_settings_match"] = (
                right_brain.memory_cue_canonicalization_enabled is True
                and right_brain.explicit_length_contract_enabled is True
                and right_brain.forbidden_conflict_projection_enabled is False
            )
            rows.append(result)
    finally:
        (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        ) = previous
    return rows
