import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

from public_persona_contrast_source_manifest_v4 import (
    DEFAULT_EVENT_SCHEMA,
    DEFAULT_MANIFEST,
    DEFAULT_PREREGISTRATION,
    DEFAULT_READINESS,
    DEFAULT_REFERENCE_MANIFEST,
    DEFAULT_RIGHTS_REVIEW,
    DEFAULT_V3_RESULT,
    EXPECTED_ACTORS,
    EXPECTED_ANCHORS,
    EXPECTED_SOURCES,
    FAIL_DECISION,
    PASS_DECISION,
    ROOT,
    audit,
    build_audit_from_paths,
    build_markdown,
    load_json,
)


PYTHON = Path(
    "/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python"
)


class PublicPersonaContrastSourceManifestV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)
        cls.manifest = load_json(DEFAULT_MANIFEST)
        cls.rights_review = load_json(DEFAULT_RIGHTS_REVIEW)
        cls.v3_result = load_json(DEFAULT_V3_RESULT)
        cls.reference_manifest = load_json(DEFAULT_REFERENCE_MANIFEST)
        cls.event_schema = load_json(DEFAULT_EVENT_SCHEMA)
        cls.readiness = load_json(DEFAULT_READINESS)

    def run_audit(self, **overrides):
        names = (
            "preregistration",
            "manifest",
            "rights_review",
            "v3_result",
            "reference_manifest",
            "event_schema",
            "readiness",
        )
        values = [
            copy.deepcopy(overrides.get(name, getattr(self, name))) for name in names
        ]
        return audit(*values, root=ROOT)

    def source_index(self, manifest=None):
        manifest = self.manifest if manifest is None else manifest
        return {row["source_id"]: row for row in manifest["sources"]}

    def test_protocol_passes_but_formal_execution_remains_blocked(self):
        report = self.run_audit()
        self.assertTrue(report["protocol_passed"])
        self.assertFalse(report["formal_execution_ready"])
        self.assertFalse(report["persona_score_computed"])
        self.assertEqual(report["decision"], PASS_DECISION)
        self.assertEqual(report["summary"]["protocol_check_pass_count"], 14)
        self.assertEqual(report["summary"]["protocol_check_count"], 14)
        self.assertEqual(report["summary"]["formal_readiness_pass_count"], 4)
        self.assertEqual(report["summary"]["formal_readiness_check_count"], 19)
        self.assertEqual(report["violations"], {})

    def test_failed_manifest_reports_observed_not_expected_source_counts(self):
        mutated = copy.deepcopy(self.manifest)
        removed = mutated["sources"].pop()
        report = self.run_audit(manifest=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertEqual(report["summary"]["contrast_source_reservation_count"], 8)
        self.assertEqual(report["summary"]["topic_cell_count"], 8)
        self.assertEqual(
            report["summary"]["broad_family_match_source_count"],
            2 if removed["match_granularity"] == "broad_family_only" else 3,
        )

    def test_three_preselected_actors_match_reference_channels(self):
        actors = {row["actor_id"]: row for row in self.manifest["actors"]}
        self.assertEqual(set(actors), set(EXPECTED_ACTORS))
        for actor_id, expected in EXPECTED_ACTORS.items():
            self.assertEqual(actors[actor_id]["public_name"], expected["public_name"])
            self.assertEqual(
                actors[actor_id]["official_channel_id"], expected["channel_id"]
            )

    def test_each_actor_has_exactly_three_topic_cells(self):
        for actor_id in EXPECTED_ACTORS:
            rows = [
                row for row in self.manifest["sources"] if row["actor_id"] == actor_id
            ]
            self.assertEqual(len(rows), 3)
            self.assertEqual(
                {row["topic_cell"] for row in rows}, set(EXPECTED_ANCHORS)
            )

    def test_exactly_nine_official_source_reservations_are_registered(self):
        sources = self.source_index()
        self.assertEqual(set(sources), set(EXPECTED_SOURCES))
        self.assertEqual(len(sources), 9)
        for source_id, expected in EXPECTED_SOURCES.items():
            row = sources[source_id]
            channel_id = EXPECTED_ACTORS[expected["actor_id"]]["channel_id"]
            self.assertEqual(row["publisher_channel_id"], channel_id)
            self.assertEqual(row["authority"], "actor_official")
            self.assertEqual(row["availability"], "public")
            self.assertEqual(row["live_status"], "was_live")

    def test_six_exact_game_and_three_broad_family_matches_are_separate(self):
        rows = self.manifest["sources"]
        exact = [row for row in rows if row["match_granularity"] == "exact_game"]
        broad = [
            row for row in rows if row["match_granularity"] == "broad_family_only"
        ]
        self.assertEqual(len(exact), 6)
        self.assertEqual(len(broad), 3)
        self.assertTrue(
            all(row["game_family"] == row["target_anchor_game_family"] for row in exact)
        )
        self.assertTrue(
            all(row["game_family"] != row["target_anchor_game_family"] for row in broad)
        )

    def test_source_partitions_are_unique_and_disjoint_from_target(self):
        rows = self.manifest["sources"]
        partitions = {row["source_partition_key"] for row in rows}
        urls = {row["url"] for row in rows}
        self.assertEqual(len(partitions), 9)
        self.assertEqual(len(urls), 9)
        target_partitions = {
            row["source_partition_key"]
            for row in self.reference_manifest["sources"]
        }
        target_urls = {row["url"] for row in self.reference_manifest["sources"]}
        self.assertFalse(partitions & target_partitions)
        self.assertFalse(urls & target_urls)

    def test_manifest_stores_metadata_but_no_behavior_or_language_payload(self):
        common = self.manifest["common_source_flags"]
        for field in (
            "content_reviewed_for_behavior",
            "labels_available",
            "raw_media_stored",
            "raw_transcript_stored",
            "candidate_answer_available",
            "model_output_available",
            "title_stored",
            "selected_from_behavior_content",
            "selected_from_model_outputs_or_similarity_scores",
        ):
            self.assertFalse(common[field], field)
        serialized = str(self.manifest)
        self.assertNotIn("reference_answer", serialized)
        self.assertNotIn("target_reply", serialized)

    def test_planned_event_caps_do_not_create_event_counts(self):
        self.assertTrue(
            all(row["planned_event_cap"] == 10 for row in self.manifest["sources"])
        )
        counts = self.manifest["current_counts"]
        self.assertEqual(counts["contrast_behavior_event_count"], 0)
        self.assertEqual(counts["independently_reviewed_event_count"], 0)
        self.assertEqual(counts["same_topic_reference_pair_count"], 0)

    def test_all_nine_sources_have_metadata_only_rights_review(self):
        reviews = self.rights_review["source_reviews"]
        self.assertEqual(len(reviews), 9)
        self.assertEqual(
            {row["source_id"] for row in reviews}, set(EXPECTED_SOURCES)
        )
        self.assertTrue(all(row["public_access_verified"] for row in reviews))
        self.assertTrue(all(row["official_channel_verified"] for row in reviews))
        self.assertFalse(
            self.rights_review["review_completion"][
                "contrast_behavior_use_authorized"
            ]
        )

    def test_rights_review_does_not_claim_license_or_allow_training(self):
        policy = self.rights_review["review_policy"]
        self.assertTrue(policy["public_access_is_not_training_permission"])
        self.assertTrue(policy["public_access_is_not_a_rights_holder_license"])
        self.assertFalse(policy["rights_holder_permission_claimed"])
        self.assertFalse(policy["legal_opinion_claimed"])
        self.assertFalse(policy["model_training"])
        self.assertFalse(policy["prompt_memory_or_retrieval_use"])

    def test_counts_remain_zero_and_no_persona_score_exists(self):
        report = self.run_audit()
        for field in (
            "contrast_behavior_event_count",
            "independently_reviewed_event_count",
            "same_topic_reference_pair_count",
            "model_response_count",
            "persona_score_count",
            "holdout_content_review_count",
            "runtime_change_count",
            "model_call_count",
        ):
            self.assertEqual(report["summary"][field], 0, field)

    def test_pass_authorizes_only_next_preregistration(self):
        auth = self.run_audit()["authorizations"]
        self.assertTrue(auth["contrast_event_coding_preregistration"])
        for field in (
            "contrast_behavior_content_review",
            "target_calibration_behavior_coding",
            "rater_recruitment",
            "rating_collection",
            "model_execution",
            "runtime_change",
            "prompt_change",
            "memory_change",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(auth[field], field)

    def test_mutation_wrong_official_channel_fails(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["sources"][0]["publisher_channel_id"] = "wrong"
        report = self.run_audit(manifest=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("sources", report["violations"])

    def test_mutation_broad_match_labeled_exact_fails(self):
        mutated = copy.deepcopy(self.manifest)
        row = next(
            row
            for row in mutated["sources"]
            if row["match_granularity"] == "broad_family_only"
        )
        row["match_granularity"] = "exact_game"
        report = self.run_audit(manifest=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("sources", report["violations"])

    def test_mutation_content_review_flag_fails(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["common_source_flags"]["content_reviewed_for_behavior"] = True
        report = self.run_audit(manifest=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("content_boundary", report["violations"])

    def test_mutation_behavior_authorization_fails(self):
        mutated = copy.deepcopy(self.rights_review)
        mutated["review_policy"]["bounded_manual_behavior_observation"] = True
        report = self.run_audit(rights_review=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("rights", report["violations"])

    def test_markdown_explains_source_is_not_event_and_match_strength(self):
        markdown = build_markdown(self.run_audit())
        self.assertIn("來源仍不是行為事件", markdown)
        self.assertIn("同遊戲", markdown)
        self.assertIn("同類型", markdown)
        self.assertIn("不得被寫成『同一遊戲』", markdown)
        self.assertIn("4/19", markdown)

    def test_path_builder_hash_binds_all_inputs(self):
        report = build_audit_from_paths()
        self.assertTrue(report["protocol_passed"])
        self.assertEqual(len(report["inputs"]), 7)
        for artifact in report["inputs"].values():
            self.assertEqual(len(artifact["sha256"]), 64)
            self.assertTrue((ROOT / artifact["path"]).is_file())

    def test_cli_refuses_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_json = Path(temp_dir) / "report.json"
            output_md = Path(temp_dir) / "report.md"
            output_json.write_text("existing", encoding="utf-8")
            result = subprocess.run(
                [
                    str(PYTHON),
                    str(ROOT / "public_persona_contrast_source_manifest_v4.py"),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output_json.read_text(encoding="utf-8"), "existing")


if __name__ == "__main__":
    unittest.main()
