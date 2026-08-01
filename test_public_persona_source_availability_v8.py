import json
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

import public_persona_source_availability_v8 as v8


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_source_availability_v8_preregistration.json"
LOCK = ROOT / "configs/public_persona_source_availability_v8_harness_lock.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PublicPersonaSourceAvailabilityV8Test(unittest.TestCase):
    def test_selection_is_exact_and_excludes_holdout(self):
        sources = v8.select_sources(v8.load(v8.TARGET_MANIFEST), v8.load(v8.CONTRAST_MANIFEST))
        self.assertEqual(len(sources), 12)
        self.assertEqual(sum(source["source_group"] == "target_calibration" for source in sources), 3)
        self.assertEqual(sum(source["source_group"] == "matched_contrast" for source in sources), 9)
        self.assertFalse(any(source.get("sealed") is True for source in sources))
        self.assertFalse(any(source.get("dataset_role") == "final_holdout" for source in sources))

    def test_watch_metadata_parser_extracts_only_channel_and_date(self):
        parsed = v8.parse_watch_metadata(
            '<meta itemprop="datePublished" content="2026-03-18T10:19:01-07:00">'
            '"channelId":"UC_expected" "title":"must not be returned"'
        )
        self.assertEqual(parsed, {"channel_id": "UC_expected", "published_date": "2026-03-18"})

    def test_verification_compares_manifest_without_storing_content(self):
        source = {
            "source_id": "source",
            "source_group": "target_calibration",
            "actor_id": "actor",
            "video_id": "video",
            "publisher_channel_id": "UC_expected",
            "published_at": "2026-03-18",
        }
        oembed = json.dumps({"author_url": "https://www.youtube.com/@official", "title": "not stored"})
        watch = '<meta itemprop="datePublished" content="2026-03-18T00:00:00Z">"channelId":"UC_expected"'
        with patch.object(v8, "_request", side_effect=[(200, oembed, 0.1), (200, watch, 0.2)]):
            row = v8.verify_source(source)
        self.assertTrue(row["channel_match"])
        self.assertTrue(row["published_date_match"])
        self.assertNotIn("title", row)
        self.assertNotIn("description", row)
        self.assertFalse(row["stored_transcript"])
        self.assertFalse(row["behavior_content_reviewed"])

    def test_mismatch_fails_channel_and_date_checks(self):
        source = {
            "source_id": "source",
            "source_group": "matched_contrast",
            "actor_id": "actor",
            "video_id": "video",
            "publisher_channel_id": "UC_expected",
            "published_at": "2026-03-18",
        }
        with patch.object(
            v8,
            "_request",
            side_effect=[
                (200, json.dumps({"author_url": "https://www.youtube.com/@other"}), 0.1),
                (200, '<meta itemprop="datePublished" content="2025-01-01T00:00:00Z">"channelId":"UC_other"', 0.2),
            ],
        ):
            row = v8.verify_source(source)
        self.assertFalse(row["channel_match"])
        self.assertFalse(row["published_date_match"])

    def test_preregistration_forbids_holdout_content_and_runtime_use(self):
        preregistration = v8.load(PREREGISTRATION)
        self.assertEqual(preregistration["scope"]["final_holdout_source_request_count_exact"], 0)
        self.assertFalse(preregistration["request_policy"]["caption_or_transcript_access"])
        self.assertFalse(preregistration["request_policy"]["media_download"])
        self.assertFalse(preregistration["decision_policy"]["holdout_unsealing"])
        self.assertFalse(preregistration["decision_policy"]["runtime_change"])
        self.assertFalse(preregistration["decision_policy"]["training"])

    def test_harness_lock_hashes_match(self):
        lock = v8.load(LOCK)
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(sha(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
