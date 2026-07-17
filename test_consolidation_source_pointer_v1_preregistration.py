#!/usr/bin/env python3
"""Validate source-pointer V1 preregistration and baseline."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_source_pointer_v1_preregistration.json"
)
RESULT_PATHS = (
    ROOT / "reports" / "consolidation_source_pointer_v1_treatment.json",
    ROOT / "reports" / "consolidation_source_pointer_v1_analysis.md",
    ROOT / "configs" / "consolidation_source_pointer_v1_result_lock.json",
)
PREREGISTRATION_MERGE_COMMIT = (
    "c5b56665ef6deb218ddb595c9c2bdcb09a9e0753"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_file_sha256(commit, path):
    content = subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )
    return hashlib.sha256(content).hexdigest()


class ConsolidationSourcePointerV1PreregistrationTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.baseline = _load(
            ROOT / cls.config["frozen_baseline"]["report_path"]
        )
        cls.dataset = _load(
            ROOT / cls.config["frozen_baseline"]["dataset_path"]
        )

    def test_identity_and_single_variable_are_explicit(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_source_pointer_v1",
        )
        self.assertEqual(
            self.config["single_manipulated_variable"],
            (
                "attach_one_digest_verified_exact_source_episode_to_"
                "an_already_selected_consolidated_memory_item"
            ),
        )
        self.assertIn(
            "top-level candidate generation and ranking",
            self.config["controlled_variables"],
        )

    def test_frozen_artifacts_and_runtime_are_hash_bound(self):
        frozen = self.config["frozen_baseline"]
        self.assertEqual(
            _git_file_sha256(frozen["commit"], frozen["runtime_path"]),
            frozen["runtime_sha256"],
        )
        for name in ("dataset", "measurement", "report"):
            self.assertEqual(
                _sha256(ROOT / frozen[f"{name}_path"]),
                frozen[f"{name}_sha256"],
            )
        self.assertEqual(
            self.baseline["runtime_commit"],
            frozen["commit"],
        )

    def test_dataset_has_frozen_multilingual_matched_structure(self):
        cases = self.dataset["cases"]
        self.assertEqual(len(cases), 12)
        self.assertEqual(
            sum(case["split"] == "positive" for case in cases),
            6,
        )
        self.assertEqual(
            sum(case["split"] == "integrity" for case in cases),
            4,
        )
        self.assertEqual(
            sum(case["split"] == "unrelated" for case in cases),
            2,
        )
        self.assertEqual(
            {case["language"] for case in cases},
            {"en", "ja", "zh"},
        )
        self.assertEqual(self.dataset["global_distractor_count"], 24)
        self.assertEqual(self.dataset["local_distractor_count"], 7)

    def test_baseline_proves_selected_gist_but_missing_sources(self):
        positives = [
            row
            for row in self.baseline["cases"]
            if row["split"] == "positive"
        ]
        self.assertEqual(len(positives), 6)
        self.assertTrue(all(row["derived_selected"] for row in positives))
        self.assertEqual(
            self.baseline["summary"][
                "positive_target_source_hits"
            ],
            0,
        )
        self.assertEqual(
            self.baseline["summary"][
                "positive_target_source_recall"
            ],
            0.0,
        )
        self.assertEqual(self.baseline["external_model_calls"], 0)
        self.assertFalse(
            self.baseline["gold_or_expected_answer_passed_to_runtime"]
        )

    def test_prior_negative_reread_result_is_not_repeated(self):
        prior = self.config["prior_evidence"][
            "memory_provenance_reread_v3"
        ]
        self.assertEqual(
            _sha256(ROOT / prior["preregistration_path"]),
            prior["preregistration_sha256"],
        )
        self.assertEqual(
            _sha256(ROOT / prior["result_path"]),
            prior["result_sha256"],
        )
        result = _load(ROOT / prior["result_path"])
        self.assertEqual(result["decision"], prior["decision"])
        self.assertFalse(
            result["research_boundary"]["runtime_change_authorized"]
        )
        prohibited = " ".join(self.config["prohibited_changes"])
        for phrase in (
            "highlighted full-session reread",
            "sufficiency gate",
            "generated gist",
            "span contract",
        ):
            self.assertIn(phrase, prohibited)

    def test_success_requires_gain_integrity_and_unchanged_ranking(self):
        gates = self.config["success_gates"]
        self.assertEqual(
            gates["treatment_positive_target_source_hits_min"],
            5,
        )
        self.assertEqual(gates["paired_positive_net_gain_min"], 5)
        self.assertEqual(
            gates["treatment_wrong_source_injections_exact"],
            0,
        )
        self.assertEqual(
            gates["treatment_integrity_pointer_activations_exact"],
            0,
        )
        self.assertEqual(
            gates[
                "treatment_top_level_selection_unchanged_count_exact"
            ],
            12,
        )
        self.assertEqual(
            gates["treatment_maximum_source_evidence_count_max"],
            1,
        )

    def test_scope_forbids_answer_leakage_and_broad_runtime_changes(self):
        prohibited = " ".join(self.config["prohibited_changes"])
        for phrase in (
            "top-level working-memory",
            "answer-generation prompt",
            "target source IDs",
            "case-specific keywords",
            "production Chroma",
        ):
            self.assertIn(phrase, prohibited)
        self.assertFalse(
            self.config[
                "runtime_change_before_preregistration_merge_authorized"
            ]
        )
        self.assertFalse(
            self.config["evidence_limits"][
                "dialogue_improvement_claim_authorized"
            ]
        )
        self.assertFalse(
            self.config["evidence_limits"][
                "human_likeness_claim_authorized"
            ]
        )

    def test_result_artifacts_do_not_exist_before_implementation(self):
        for path in RESULT_PATHS:
            relative_path = path.relative_to(ROOT).as_posix()
            completed = subprocess.run(
                [
                    "git",
                    "cat-file",
                    "-e",
                    f"{PREREGISTRATION_MERGE_COMMIT}:{relative_path}",
                ],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.assertNotEqual(completed.returncode, 0, relative_path)


if __name__ == "__main__":
    unittest.main()
