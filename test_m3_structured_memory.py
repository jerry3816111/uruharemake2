from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from longitudinal_human_model.memory import (
    COMPONENTS,
    MemoryQuery,
    MemoryRecord,
    MemoryStrengthConfig,
    eligibility_reasons,
    retrieve_memories,
    score_memory,
)
from run_m3_structured_memory import run_memory_ablation, validate_fixture


UTC = timezone.utc


def record(memory_id: str = "m1", **overrides) -> MemoryRecord:
    base = {
        "memory_id": memory_id,
        "subject": "person-a",
        "event": "The teammate asked for the planned route and the subject continued.",
        "timestamp_start": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "timestamp_end": datetime(2026, 1, 1, 12, 1, tzinfo=UTC),
        "available_at": datetime(2026, 1, 1, 12, 2, tzinfo=UTC),
        "entities": ("teammate",),
        "topics": ("planned-route", "cooperation"),
        "source_url_or_id": f"source-{memory_id}",
        "source_timestamp": datetime(2026, 1, 1, 12, 2, tzinfo=UTC),
        "confidence": 0.9,
        "importance": 0.6,
        "emotional_salience": {"calm": 0.8},
        "relationship_tags": {"teammate": 0.9},
        "embedding_ref": None,
        "extraction_model": "fixture-extractor-v1",
        "dataset_version": "fixture-v1",
        "observation_count": 2,
    }
    base.update(overrides)
    return MemoryRecord(**base)


def query(**overrides) -> MemoryQuery:
    base = {
        "query_id": "q1",
        "subject": "person-a",
        "text": "A teammate asks to continue using the planned route.",
        "prediction_time": datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
        "available_history_cutoff": datetime(2026, 2, 1, 11, 59, tzinfo=UTC),
        "entities": ("teammate",),
        "topics": ("planned-route", "cooperation"),
        "relationship_context": {"teammate": 1.0},
        "emotion_context": {"calm": 1.0},
    }
    base.update(overrides)
    return MemoryQuery(**base)


def config(**overrides) -> MemoryStrengthConfig:
    base = {
        "weights": {name: 1.0 for name in COMPONENTS},
        "recency_half_life_days": 30.0,
        "frequency_saturation_count": 3.0,
    }
    base.update(overrides)
    return MemoryStrengthConfig(**base)


class MemorySchemaTests(unittest.TestCase):
    def test_requires_timezone_aware_temporal_provenance(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            record(timestamp_start=datetime(2026, 1, 1, 12, 0))

    def test_rejects_invalid_confidence_and_missing_provenance(self):
        with self.assertRaisesRegex(ValueError, "confidence"):
            record(confidence=1.1)
        with self.assertRaisesRegex(ValueError, "source_url_or_id"):
            record(source_url_or_id="")

    def test_config_requires_exact_named_components(self):
        with self.assertRaisesRegex(ValueError, "exactly match"):
            MemoryStrengthConfig(
                weights={"recency": 1.0},
                recency_half_life_days=30,
                frequency_saturation_count=3,
            )


class TemporalEligibilityTests(unittest.TestCase):
    def test_future_available_source_is_excluded_fail_closed(self):
        future = record(
            "future",
            timestamp_start=datetime(2026, 2, 2, 12, 0, tzinfo=UTC),
            timestamp_end=datetime(2026, 2, 2, 12, 1, tzinfo=UTC),
            available_at=datetime(2026, 2, 2, 12, 2, tzinfo=UTC),
            source_timestamp=datetime(2026, 2, 2, 12, 2, tzinfo=UTC),
        )
        reasons = eligibility_reasons(future, query())
        self.assertIn("event_after_cutoff", reasons)
        self.assertIn("available_after_cutoff", reasons)
        self.assertIn("source_after_cutoff", reasons)

    def test_expired_not_yet_valid_and_other_subject_are_excluded(self):
        now = query().prediction_time
        rows = [
            record("expired", valid_until=now - timedelta(seconds=1)),
            record("not-yet", valid_from=now + timedelta(seconds=1)),
            record("other", subject="person-b"),
        ]
        result = retrieve_memories(rows, query(), config(), top_k=2)
        self.assertEqual([], result["selected"])
        excluded = {row["memory_id"]: row["reasons"] for row in result["excluded"]}
        self.assertIn("expired", excluded["expired"])
        self.assertIn("not_yet_valid", excluded["not-yet"])
        self.assertIn("subject_mismatch", excluded["other"])


class StrengthAndAblationTests(unittest.TestCase):
    def test_recency_decays_monotonically(self):
        q = query()
        recent = record(
            "recent",
            timestamp_start=q.prediction_time - timedelta(days=2, minutes=2),
            timestamp_end=q.prediction_time - timedelta(days=2, minutes=1),
            available_at=q.prediction_time - timedelta(days=2),
            source_timestamp=q.prediction_time - timedelta(days=2),
        )
        old = record("old")
        recent_score = score_memory(recent, q, config())["components"]["recency"]
        old_score = score_memory(old, q, config())["components"]["recency"]
        self.assertGreater(recent_score, old_score)

    def test_every_component_is_inspectable_and_contributions_sum_to_score(self):
        trace = score_memory(record(), query(), config())
        self.assertEqual(set(COMPONENTS), set(trace["components"]))
        self.assertAlmostEqual(trace["score"], sum(trace["contributions"].values()))
        self.assertEqual("source-m1", trace["provenance"]["source_url_or_id"])

    def test_ablation_zeroes_only_named_component_and_changes_score(self):
        full = score_memory(record(), query(), config())
        ablated = score_memory(record(), query(), config(), ablate=("semantic_relevance",))
        self.assertGreater(full["effective_weights"]["semantic_relevance"], 0)
        self.assertEqual(0.0, ablated["effective_weights"]["semantic_relevance"])
        self.assertEqual(
            full["components"]["semantic_relevance"],
            ablated["components"]["semantic_relevance"],
        )
        self.assertNotEqual(full["score"], ablated["score"])

    def test_unknown_ablation_fails(self):
        with self.assertRaisesRegex(ValueError, "unknown ablation"):
            score_memory(record(), query(), config(), ablate=("magic",))

    def test_retrieval_is_deterministic_and_reports_exclusions(self):
        exact = record("exact")
        unrelated = record(
            "unrelated",
            event="A private schedule was deferred.",
            entities=("producer",),
            topics=("schedule",),
            relationship_tags={"producer": 0.8},
            emotional_salience={"pressure": 0.7},
        )
        other = record("other-person", subject="person-b")
        result = retrieve_memories([unrelated, other, exact], query(), config(), top_k=2)
        self.assertEqual("exact", result["selected"][0]["memory_id"])
        self.assertEqual(["other-person"], [row["memory_id"] for row in result["excluded"]])
        self.assertEqual(
            ["exact", "unrelated"],
            [row["memory_id"] for row in result["eligible_ranked"]],
        )


class FrozenFixtureRunnerTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent
        self.dataset = json.loads(
            (root / "datasets/m3_structured_memory_synthetic_fixture_v1.json").read_text()
        )
        self.config = json.loads(
            (root / "configs/m3_structured_memory_mechanism_preregistration.json").read_text()
        )

    def test_frozen_fixture_is_valid(self):
        validation = validate_fixture(self.dataset, self.config)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(14, validation["record_count"])
        self.assertEqual(6, validation["query_count"])

    def test_full_memory_and_ablation_gate(self):
        result = run_memory_ablation(self.dataset, self.config)
        self.assertEqual("complete_mechanism_run", result["status"])
        self.assertTrue(result["gate_pass"])
        self.assertEqual(1.0, result["conditions"]["none"]["metrics"]["recall_at_k"])
        self.assertEqual(0, result["future_memory_selected_count"])
        self.assertEqual(0, result["expired_memory_selected_count"])
        self.assertTrue(all(result["observed_component_nonzero"].values()))
        self.assertTrue(
            any(
                payload["metrics"]["rank_order_changed_queries"] > 0
                or payload["metrics"]["mean_absolute_score_delta_from_full"] > 0
                for name, payload in result["conditions"].items()
                if name != "none"
            )
        )


if __name__ == "__main__":
    unittest.main()
