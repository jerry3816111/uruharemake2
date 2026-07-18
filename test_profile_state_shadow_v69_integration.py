import inspect
import json
import tempfile
import unittest
from pathlib import Path

import chromadb

from uruha_brain_mac import MemoryManager
from uruha_profile_memory import profile_state_shadow_snapshot


ROOT = Path(__file__).resolve().parent


class ProfileStateShadowV69IntegrationTests(unittest.TestCase):
    def test_real_temp_chroma_tracks_current_and_history_without_answer_use(self):
        with tempfile.TemporaryDirectory(prefix="uruha_profile_shadow_integration_") as tempdir:
            collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection(
                "profile_shadow_integration"
            )
            memory = self._memory(collection)
            memory._remember_profile_facts("I like coffee.")
            memory._remember_profile_facts("I hate coffee.")

            payload = collection.get(include=["documents", "metadatas"])
            self.assertEqual(
                set(payload["documents"]),
                {"FactType=like | Value=coffee", "FactType=dislike | Value=coffee"},
            )
            self.assertEqual(len(payload["ids"]), 2)
            self.assertTrue(all(metadata["subject"] == "user" for metadata in payload["metadatas"]))
            snapshot = memory._last_profile_state_shadow
            self.assertEqual(snapshot["typed_candidate_count"], 2)
            self.assertEqual(snapshot["legacy_candidate_count"], 0)
            self.assertEqual(len(snapshot["active_ids"]), 1)
            self.assertEqual(snapshot["typed_active_ids"], snapshot["active_ids"])
            self.assertEqual(snapshot["legacy_eligible_ids"], [])
            self.assertEqual(len(snapshot["historical_ids"]), 1)
            self.assertFalse(snapshot["affects_working_memory"])
            self.assertFalse(snapshot["answer_use_authorized"])

    def test_new_memory_manager_can_observe_same_persistent_state(self):
        with tempfile.TemporaryDirectory(prefix="uruha_profile_shadow_restart_") as tempdir:
            collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection(
                "profile_shadow_restart"
            )
            first = self._memory(collection)
            first._remember_profile_facts("Call me Aki.")
            first._remember_profile_facts("Call me Nao.")
            second = self._memory(collection)
            snapshot = second._refresh_profile_state_shadow()
            self.assertEqual(snapshot["candidate_count"], 2)
            self.assertEqual(len(snapshot["active_ids"]), 1)
            self.assertEqual(len(snapshot["historical_ids"]), 1)

    def test_mixed_legacy_rows_are_visible_but_not_silently_migrated(self):
        class Collection:
            def get(self, include):
                return {
                    "ids": ["legacy"],
                    "documents": ["FactType=like | Value=tea"],
                    "metadatas": [{"fact_type": "like", "value": "tea"}],
                }

        snapshot = profile_state_shadow_snapshot(
            Collection(),
            reference_time="2026-07-18T00:00:00+09:00",
        )
        self.assertEqual(snapshot["legacy_candidate_count"], 1)
        self.assertEqual(snapshot["typed_candidate_count"], 0)
        self.assertEqual(snapshot["decision_reasons"]["legacy"], "legacy_metadata_fail_open")
        self.assertEqual(snapshot["typed_active_ids"], [])
        self.assertEqual(snapshot["legacy_eligible_ids"], ["legacy"])
        self.assertFalse(snapshot["affects_working_memory"])
        self.assertFalse(snapshot["answer_use_authorized"])

    def test_shadow_is_absent_from_working_memory_and_query_output_paths(self):
        build_source = inspect.getsource(MemoryManager._build_working_memory)
        query_source = inspect.getsource(MemoryManager.query_all_layers)
        self.assertNotIn("profile_state_shadow", build_source)
        self.assertNotIn("profile_state_shadow", query_source)
        self.assertNotIn("profile_col", build_source)

    def test_result_lock_authorizes_shadow_but_not_activation_or_migration(self):
        lock = json.loads(
            (ROOT / "configs/profile_state_transition_v69_result_lock.json").read_text(encoding="utf-8")
        )
        self.assertTrue(lock["production_shadow_integration_authorized"])
        self.assertFalse(lock["production_database_migration_authorized"])
        self.assertFalse(lock["runtime_activation_authorized"])

    @staticmethod
    def _memory(collection):
        memory = object.__new__(MemoryManager)
        memory.profile_col = collection
        memory.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
        memory._last_profile_state_shadow = {
            "status": "not_refreshed",
            "shadow_only": True,
            "affects_working_memory": False,
            "answer_use_authorized": False,
        }
        return memory


if __name__ == "__main__":
    unittest.main()
