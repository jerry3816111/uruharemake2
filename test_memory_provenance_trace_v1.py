import datetime
import unittest

import uruha_brain_mac as ubm
import uruha_memory_runtime as umr


class FakeCollection:
    def __init__(self, source):
        self.source = source

    def query(self, **_kwargs):
        return {
            "documents": [["", f"{self.source} primary", f"{self.source} secondary"]],
            "ids": [[f"{self.source}-blank", f"{self.source}-1", f"{self.source}-2"]],
            "metadatas": [[{}, {"rank": 1}, {"rank": 2}]],
            "distances": [[9.0, 0.1, 0.2]],
        }


class MemoryProvenanceTraceV1Test(unittest.TestCase):
    def test_stored_and_transient_trace_ids_are_stable(self):
        stored = {
            "source": "episode",
            "collection_name": "episode",
            "memory_id": "episode-7",
            "text": "same text",
        }
        transient = {
            "source": "recent_turn",
            "text": "User:hi -> Uruha:hello",
            "metadata": {"timestamp": "2026-08-05 12:00:00"},
        }

        self.assertEqual(
            umr.memory_trace_id(stored),
            "stored:episode:episode-7",
        )
        self.assertEqual(
            umr.memory_trace_id(transient),
            umr.memory_trace_id(dict(transient)),
        )
        changed = dict(transient, text="different text")
        self.assertNotEqual(umr.memory_trace_id(transient), umr.memory_trace_id(changed))

    def test_trace_does_not_change_working_memory_ranking_or_scores(self):
        candidates = [
            {"source": "wisdom", "text": "tea preference", "distance": 0.01},
            {"source": "short_term", "text": "tea today", "distance": 0.5},
            {"source": "knowledge", "text": "unrelated", "distance": 0.99},
        ]
        reference_time = datetime.datetime(2026, 8, 5, 12, 0, 0)
        without_trace = umr.build_working_memory(
            "tea",
            candidates,
            working_memory_limit=2,
            reference_time=reference_time,
        )
        trace = {}
        with_trace = umr.build_working_memory(
            "tea",
            candidates,
            working_memory_limit=2,
            reference_time=reference_time,
            trace_sink=trace,
        )

        self.assertEqual(
            [(row["text"], row["score"]) for row in without_trace],
            [(row["text"], row["score"]) for row in with_trace],
        )
        self.assertEqual(trace["schema"], umr.MEMORY_PROVENANCE_SCHEMA)
        self.assertEqual(trace["retrieved_candidate_count"], 3)
        self.assertEqual(trace["candidate_count"], 3)
        self.assertEqual(
            trace["selected_working_memory_trace_ids"],
            [row["trace_id"] for row in with_trace],
        )
        self.assertEqual(
            [row["rank"] for row in trace["candidate_pool"]],
            [1, 2, 3],
        )

    def test_retrieved_trace_retains_deduplicated_candidate(self):
        trace = {}
        candidates = [
            {"source": "episode", "text": "same memory", "memory_id": "a"},
            {"source": "episode", "text": "same memory", "memory_id": "b"},
        ]

        selected = umr.build_working_memory(
            "same",
            candidates,
            working_memory_limit=2,
            reference_time=datetime.datetime(2026, 8, 5, 12, 0, 0),
            trace_sink=trace,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(trace["retrieved_candidate_count"], 2)
        self.assertEqual(trace["candidate_count"], 1)
        self.assertEqual(
            [row["ranking_status"] for row in trace["retrieved_candidates"]],
            ["ranked", "deduplicated"],
        )
        self.assertEqual(
            trace["retrieved_candidates"][1]["duplicate_of_trace_id"],
            trace["retrieved_candidates"][0]["trace_id"],
        )

    def test_query_trace_preserves_nonempty_document_id_alignment(self):
        manager = object.__new__(ubm.MemoryManager)
        trace_items = {}

        summary = manager._safe_query(
            FakeCollection("episode"),
            "query",
            "none",
            source="episode",
            trace_items=trace_items,
        )

        self.assertEqual(summary, "episode primary || episode secondary")
        self.assertEqual(
            [row["memory_id"] for row in trace_items["episode"]],
            ["episode-1", "episode-2"],
        )

    def test_query_all_layers_distinguishes_selected_and_passed_records(self):
        manager = object.__new__(ubm.MemoryManager)
        manager.kb_col = FakeCollection("knowledge")
        manager.episode_col = FakeCollection("episode")
        manager.wisdom_col = FakeCollection("wisdom")
        manager.procedural_col = FakeCollection("procedural")
        manager.session_turns = [
            {
                "timestamp": "2026-08-05 11:00:00",
                "user": "納豆は苦手。",
                "reply": "覚えた。",
                "intent": "memory_seed",
                "scene": "memory",
            }
        ]
        manager.short_term_buffer = [
            {
                "timestamp": "2026-08-05 11:00:00",
                "text": "User:納豆は苦手。 -> Uruha:覚えた。",
                "strength": 0.8,
            }
        ]
        manager._last_working_memory_provenance = {
            "schema": umr.MEMORY_PROVENANCE_SCHEMA,
            "candidate_count": 1,
            "candidate_pool": [],
            "selected_working_memory_trace_ids": ["stored:episode:episode-1"],
        }
        manager._decay_short_term_memory = lambda: None
        manager._build_working_memory = lambda _text: [
            {
                "source": "episode",
                "collection_name": "episode",
                "memory_id": "episode-1",
                "trace_id": "stored:episode:episode-1",
                "text": "episode primary",
                "score": 0.9,
                "attention_factors": {"score": 0.9},
            }
        ]
        manager._mark_working_memory_access = lambda _items: None
        manager._profile_snapshot = lambda: {
            "name": "Jerry",
            "likes": [],
            "dislikes": ["納豆"],
            "favorites": [],
        }
        manager._profile_summary = lambda: "Name=Jerry | Dislikes=納豆"
        manager._recent_dialogue_summary = lambda: "recent"
        manager._short_term_summary = lambda: "short"
        manager._working_memory_summary = lambda _items: "episode primary"

        result = manager.query_all_layers("納豆でいい？")
        provenance = result["memory_provenance"]
        channels = {row["channel"] for row in provenance["passed_to_leftbrain"]}

        self.assertIn("selected_working_memory", channels)
        self.assertIn("direct_episode", channels)
        self.assertIn("profile_structured", channels)
        self.assertIn("recent_turns", channels)
        self.assertIn("short_term_summary", channels)
        self.assertIn(
            "stored:episode:episode-1",
            provenance["passed_to_leftbrain_trace_ids"],
        )

    def test_memory_anchor_links_back_to_selected_trace_id(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        item = {
            "source": "recent_turn",
            "text": "User:納豆だけは苦手。 -> Uruha:覚えた。",
            "score": 0.9,
            "trace_id": "derived:recent_turn:abc123",
        }
        memory_data = {
            "profile_structured": {},
            "working_memory_items": [item],
            "memory_provenance": {
                "passed_to_leftbrain": [
                    umr.memory_trace_row(item, channel="selected_working_memory")
                ]
            },
        }

        anchor = brain._extract_actionable_memory_anchor(
            "朝ごはん納豆でいい？",
            memory_data,
        )

        self.assertEqual(anchor["kind"], "natto_dislike")
        self.assertEqual(anchor["trace_id"], item["trace_id"])
        self.assertEqual(anchor["provenance_channel"], "selected_working_memory")

    def test_profile_anchor_links_back_to_passed_profile_record(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        profile_candidate = {
            "source": "profile",
            "text": "Name=Jerry",
            "metadata": {"field": "name"},
        }
        profile_row = umr.memory_trace_row(
            profile_candidate,
            channel="profile_structured",
        )
        memory_data = {
            "profile_structured": {
                "name": "Jerry",
                "likes": [],
                "dislikes": [],
                "favorites": [],
            },
            "working_memory_items": [],
            "memory_provenance": {"passed_to_leftbrain": [profile_row]},
        }

        anchor = brain._extract_actionable_memory_anchor(
            "你還記得我叫什麼嗎？",
            memory_data,
        )

        self.assertEqual(anchor["kind"], "name")
        self.assertEqual(anchor["trace_id"], profile_row["trace_id"])
        self.assertEqual(anchor["provenance_channel"], "profile_structured")


if __name__ == "__main__":
    unittest.main()
