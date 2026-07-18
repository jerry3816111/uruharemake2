import hashlib
import json
import unittest
from pathlib import Path

from uruha_brain_mac import MemoryManager


ROOT = Path(__file__).resolve().parent


class FakeCollection:
    def __init__(self):
        self.add_calls = []

    def add(self, **kwargs):
        self.add_calls.append(kwargs)


class ProfileAssertionBoundaryV68IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.memory = object.__new__(MemoryManager)

    def test_production_extractor_matches_all_frozen_v68_cases(self):
        dataset = json.loads((ROOT / "datasets/profile_assertion_boundary_v68.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            observed = [
                {"fact_type": fact_type, "value": value}
                for fact_type, value in self.memory._extract_profile_facts(case["utterance"])
            ]
            self.assertEqual(observed, case["expected_facts"], case["id"])

    def test_false_profile_scope_does_not_mutate_session_or_chroma(self):
        self.memory.profile_col = FakeCollection()
        self.memory.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
        for utterance in (
            "Do you think I like curry?",
            "My friend said, 'I like coffee.'",
            "友達は紅茶が好き。",
        ):
            self.memory._remember_profile_facts(utterance)
        self.assertEqual(self.memory.session_profile, {"name": None, "likes": [], "dislikes": [], "favorites": []})
        self.assertFalse(self.memory.profile_col.add_calls)

    def test_direct_assertion_still_updates_session_and_chroma(self):
        self.memory.profile_col = FakeCollection()
        self.memory.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
        self.memory._remember_profile_facts("I really like astronomy.")
        self.assertEqual(self.memory.session_profile["likes"], ["astronomy"])
        self.assertEqual(len(self.memory.profile_col.add_calls), 1)
        metadata = self.memory.profile_col.add_calls[0]["metadatas"][0]
        self.assertEqual(metadata["fact_type"], "like")
        self.assertEqual(metadata["value"], "astronomy")

    def test_frozen_result_authorizes_guard_but_not_stateful_writer(self):
        lock = json.loads((ROOT / "configs/profile_assertion_boundary_v68_result_lock.json").read_text(encoding="utf-8"))
        self.assertTrue(lock["runtime_change_authorized"])
        self.assertFalse(lock["stateful_writer_authorized"])

    def test_only_profile_boundary_artifacts_drifted_from_harness_lock(self):
        lock = json.loads((ROOT / "configs/profile_assertion_boundary_v68_harness_lock.json").read_text(encoding="utf-8"))
        drifted = []
        for name, artifact in lock["frozen_artifacts"].items():
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            if digest != artifact["sha256"]:
                drifted.append(name)
        self.assertEqual(drifted, ["unchanged_extractor_runtime", "candidate"])


if __name__ == "__main__":
    unittest.main()
