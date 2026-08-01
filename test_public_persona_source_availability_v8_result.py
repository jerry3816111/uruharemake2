import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "reports/public_persona_source_availability_v8_result.json"
LOCK = ROOT / "configs/public_persona_source_availability_v8_result_lock.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PublicPersonaSourceAvailabilityV8ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_frozen_result_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(sha(ROOT / artifact["path"]), artifact["sha256"])

    def test_all_twelve_sources_resolve_to_expected_channel_and_date(self):
        summary = self.result["summary"]
        self.assertTrue(self.result["passed"])
        self.assertEqual(summary["source_count"], 12)
        self.assertEqual(summary["oembed_resolution_count"], 12)
        self.assertEqual(summary["watch_metadata_resolution_count"], 12)
        self.assertEqual(summary["publisher_channel_match_count"], 12)
        self.assertEqual(summary["publication_date_match_count"], 12)
        self.assertTrue(all(row["channel_match"] for row in self.result["rows"]))
        self.assertTrue(all(row["published_date_match"] for row in self.result["rows"]))

    def test_no_holdout_content_title_or_transcript_was_stored(self):
        summary = self.result["summary"]
        self.assertEqual(summary["final_holdout_source_request_count"], 0)
        self.assertEqual(summary["behavior_content_review_count"], 0)
        self.assertEqual(summary["stored_title_count"], 0)
        self.assertEqual(summary["stored_description_count"], 0)
        self.assertEqual(summary["stored_transcript_count"], 0)
        serialized = json.dumps(self.result, ensure_ascii=False).lower()
        self.assertNotIn('"title":', serialized)
        self.assertNotIn('"description":', serialized)
        self.assertNotIn('"transcript":', serialized)

    def test_scope_is_metadata_only_and_model_free(self):
        summary = self.result["summary"]
        self.assertEqual(self.result["formal_git_head"], self.lock["formal_git_head"])
        self.assertEqual(summary["request_count"], 24)
        self.assertEqual(summary["request_error_count"], 0)
        self.assertEqual(summary["model_call_count"], 0)
        self.assertEqual(summary["production_memory_write_count"], 0)

    def test_authorization_remains_narrow(self):
        authorization = self.result["authorizations"]
        self.assertTrue(authorization["existing_v7_human_coding_source_access"])
        self.assertFalse(authorization["holdout_unsealing"])
        self.assertFalse(authorization["model_execution"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["training"])
        self.assertFalse(authorization["persona_fidelity_claim"])


if __name__ == "__main__":
    unittest.main()
