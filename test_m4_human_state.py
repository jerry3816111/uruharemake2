from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from longitudinal_human_model.state import (
    EvidenceRef,
    HumanStateSnapshot,
    StateEstimate,
    build_human_state_snapshot,
)
from run_m4_human_state import run_state_snapshots, validate_inputs


UTC = timezone.utc


def estimate(value, confidence=0.8, status="inferred", evidence_ids=("event:q",)):
    return {
        "value": value,
        "confidence": confidence,
        "status": status,
        "evidence_ids": list(evidence_ids),
        "updated_at": "2026-01-02T12:00:00+00:00",
        "hypothesis_note": "Model variable bounded by observable fixture evidence.",
    }


def unknown():
    return estimate(None, confidence=0.0, status="unknown", evidence_ids=())


def draft():
    relationship_fields = {
        "role": estimate("teammate", status="observed"),
        "familiarity": estimate(0.7),
        "trust": estimate(0.6),
        "affinity": estimate(0.7),
        "conflict": estimate(0.1),
        "interaction_frequency": estimate(0.8),
    }
    return {
        "subject": "person-a",
        "timestamp": "2026-01-02T12:00:00+00:00",
        "available_history_cutoff": "2026-01-02T11:59:59+00:00",
        "current_event_id": "q",
        "current_event_source_id": "event-source-q",
        "current_event_observed_at": "2026-01-02T11:59:59+00:00",
        "current_event_available_at": "2026-01-02T12:00:00+00:00",
        "event_extraction_model": "fixture-v1",
        "state_model_id": "state-schema-fixture-v1",
        "dataset_version": "fixture-v1",
        "dimensions": {
            "emotion": {"model_estimated_focus": estimate(0.8)},
            "preferences": {"task_continuity": estimate(0.7)},
            "goals": {"continue_task": estimate(0.8)},
            "habits": {"cooperative_follow_through": estimate(0.75)},
            "personality": {"cooperative_tendency": estimate(0.7)},
            "context": {
                "activity": estimate("team practice", status="observed"),
                "private_fatigue": unknown(),
            },
        },
        "relationships": {
            "teammate-a": {"entity_id": "teammate-a", "fields": relationship_fields}
        },
    }


def retrieval_row():
    return {
        "selected": [
            {
                "memory_id": "m1",
                "score": 0.7,
                "components": {"semantic": 0.8, "recency": 0.6},
                "contributions": {"semantic": 0.4, "recency": 0.3},
                "provenance": {
                    "source_url_or_id": "memory-source-m1",
                    "source_timestamp": "2026-01-01T12:00:00+00:00",
                    "available_at": "2026-01-01T12:01:00+00:00",
                    "extraction_model": "fixture-v1",
                    "dataset_version": "fixture-v1",
                },
            }
        ]
    }


class StateEstimateTests(unittest.TestCase):
    def test_unknown_cannot_hide_a_value_or_evidence(self):
        with self.assertRaisesRegex(ValueError, "unknown estimate"):
            StateEstimate(
                value=0.5,
                confidence=0.0,
                status="unknown",
                evidence_ids=(),
                updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                hypothesis_note="Unknown private state.",
            )

    def test_inferred_estimate_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, "requires evidence"):
            StateEstimate(
                value=0.5,
                confidence=0.4,
                status="inferred",
                evidence_ids=(),
                updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                hypothesis_note="Bounded inference.",
            )


class HumanStateSnapshotTests(unittest.TestCase):
    def test_build_snapshot_is_deterministic_and_replayable(self):
        first = build_human_state_snapshot(draft(), retrieval_row(), low_confidence_threshold=0.5)
        second = build_human_state_snapshot(draft(), retrieval_row(), low_confidence_threshold=0.5)
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        replay = HumanStateSnapshot.from_dict(first.to_dict())
        self.assertEqual(first.snapshot_id, replay.snapshot_id)
        self.assertEqual(first.to_dict(), replay.to_dict())

    def test_snapshot_exposes_unknown_and_memory_provenance(self):
        state = build_human_state_snapshot(draft(), retrieval_row(), low_confidence_threshold=0.5)
        self.assertIn("context.private_fatigue", state.uncertainty.unknown_fields)
        self.assertEqual("m1", state.memory_activations[0].memory_id)
        self.assertEqual("memory:m1", state.memory_activations[0].evidence_id)
        self.assertEqual(0.7, state.memory_activations[0].score)

    def test_future_memory_evidence_fails_closed(self):
        row = retrieval_row()
        row["selected"][0]["provenance"]["available_at"] = "2026-01-03T12:01:00+00:00"
        with self.assertRaisesRegex(ValueError, "unavailable"):
            build_human_state_snapshot(draft(), row, low_confidence_threshold=0.5)

    def test_unknown_evidence_reference_fails_closed(self):
        modified = draft()
        modified["dimensions"]["emotion"]["model_estimated_focus"]["evidence_ids"] = [
            "memory:missing"
        ]
        with self.assertRaisesRegex(ValueError, "unknown evidence IDs"):
            build_human_state_snapshot(modified, retrieval_row(), low_confidence_threshold=0.5)

    def test_evidence_ref_requires_availability_after_observation(self):
        with self.assertRaisesRegex(ValueError, "must not precede"):
            EvidenceRef(
                evidence_id="bad",
                evidence_kind="memory",
                source_url_or_id="source",
                observed_at=datetime(2026, 1, 2, tzinfo=UTC),
                available_at=datetime(2026, 1, 1, tzinfo=UTC),
                extraction_model="fixture",
                dataset_version="fixture",
            )


class FrozenM4RunnerTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent
        self.dataset = json.loads(
            (root / "datasets/m4_human_state_synthetic_fixture_v1.json").read_text()
        )
        self.config = json.loads(
            (root / "configs/m4_human_state_preregistration.json").read_text()
        )
        self.m3_dataset = json.loads(
            (root / "datasets/m3_structured_memory_synthetic_fixture_v1.json").read_text()
        )
        self.m3_result = json.loads(
            (root / "analysis/m3_structured_memory_synthetic_first_result.json").read_text()
        )

    def test_frozen_m4_inputs_are_valid(self):
        validation = validate_inputs(
            self.dataset, self.config, self.m3_dataset, self.m3_result
        )
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(2, validation["snapshot_count"])

    def test_frozen_snapshot_and_replay_gates_pass(self):
        result = run_state_snapshots(
            self.dataset, self.config, self.m3_dataset, self.m3_result
        )
        self.assertEqual("complete_snapshot_run", result["status"])
        self.assertTrue(result["gate_pass"])
        self.assertEqual(2, result["summary"]["snapshot_count"])
        self.assertEqual(2, result["summary"]["unique_snapshot_ids"])
        self.assertGreaterEqual(result["summary"]["unknown_field_count"], 2)
        self.assertEqual(0, result["summary"]["future_evidence_count"])
        self.assertEqual(0, result["summary"]["unresolved_evidence_reference_count"])
        self.assertFalse(result["state_transition_enabled"])
        self.assertFalse(result["behavior_predictor_enabled"])


if __name__ == "__main__":
    unittest.main()
