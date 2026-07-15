#!/usr/bin/env python3

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "event_role_governor_v59_holdout_construction_preregistration.json"
)


class EventRoleGovernorV59HoldoutConstructionPreregistrationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_external_selection_is_exactly_sixteen_unique_unused_ids(self):
        selected = set(cls_id for cls_id in self.config["external_source"]["selected_sentence_ids"])
        self.assertEqual(len(selected), 16)
        future_snapshot = ROOT / self.config["external_source"]["selected_snapshot_path"]
        prior_ids = set()
        for path in (ROOT / "datasets" / "sources").glob("*.tsv"):
            if path == future_snapshot:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if line:
                    prior_ids.add(int(line.split("\t", 1)[0]))
        self.assertTrue(selected.isdisjoint(prior_ids))

    def test_controlled_matrix_covers_every_target_in_every_family(self):
        matrix = self.config["controlled_matrix"]
        self.assertEqual(len(matrix["families"]), 4)
        self.assertEqual(len(matrix["target_ids_per_family"]), 14)
        self.assertEqual(matrix["case_count_per_family"], 14)
        self.assertTrue(matrix["all_cases_single_target"])
        self.assertEqual(
            set(matrix["families"]),
            {
                "controlled_embedded_speech_content",
                "controlled_third_party_habitual_description",
                "controlled_past_experiential_description",
                "controlled_direct_focus_request_contrast",
            },
        )

    def test_expected_counts_are_arithmetically_consistent(self):
        counts = self.config["expected_construction_counts"]
        self.assertEqual(counts["case_count"], 16 + 4 * 14)
        self.assertEqual(counts["grounded_target_count"], 17 + 4 * 14)
        self.assertEqual(counts["requested_target_count"], 14)
        self.assertEqual(counts["not_requested_target_count"], 59)
        self.assertEqual(counts["action_case_count"], 14)
        self.assertEqual(counts["no_action_case_count"], 58)

    def test_construction_has_no_model_state_or_compiler_evaluation(self):
        firewall = self.config["causal_firewall"]
        self.assertEqual(firewall["model_calls_authorized_during_construction"], 0)
        self.assertFalse(firewall["v58_state_evaluation_authorized_during_construction"])
        self.assertFalse(firewall["v59_state_evaluation_authorized_during_construction"])
        self.assertFalse(firewall["compiler_evaluation_authorized_during_construction"])
        self.assertFalse(firewall["gold_visible_to_future_model_state_or_compiler"])

    def test_provenance_does_not_overclaim_controlled_or_external_data(self):
        source = self.config["external_source"]
        matrix = self.config["controlled_matrix"]
        self.assertFalse(source["base_model_pretraining_exclusion_guaranteed"])
        self.assertFalse(matrix["model_assistance_used"])
        self.assertFalse(matrix["human_blind_review_used"])
        self.assertFalse(matrix["official_corpus_claimed"])

    def test_builder_and_dataset_were_absent_at_preregistration_commit(self):
        paths = self.config["construction_paths"]
        for key in ("builder", "auditor", "dataset"):
            current = ROOT / paths[key]
            if not current.exists():
                self.assertFalse(current.exists())
                continue
            preregistration_commit = subprocess.check_output(
                [
                    "git",
                    "log",
                    "--diff-filter=A",
                    "--format=%H",
                    "-1",
                    "--",
                    str(CONFIG_PATH.relative_to(ROOT)),
                ],
                cwd=ROOT,
                text=True,
            ).strip()
            self.assertTrue(preregistration_commit)
            historical = subprocess.run(
                ["git", "cat-file", "-e", f"{preregistration_commit}:{paths[key]}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(historical.returncode, 0)

    def test_no_evaluation_or_deployment_claim_is_authorized(self):
        for key in (
            "evaluation_before_construction_freeze_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
