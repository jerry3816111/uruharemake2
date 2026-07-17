#!/usr/bin/env python3
"""Validate source-provenance V1 preregistration and baseline."""

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
    / "consolidation_source_provenance_v1_preregistration.json"
)
RESULT_PATHS = (
    ROOT
    / "reports"
    / "consolidation_source_provenance_v1_treatment.json",
    ROOT
    / "reports"
    / "consolidation_source_provenance_v1_analysis.md",
    ROOT
    / "configs"
    / "consolidation_source_provenance_v1_result_lock.json",
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_git_file(commit, path):
    content = subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )
    return hashlib.sha256(content).hexdigest()


def _git_file_exists(commit, path):
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


class ConsolidationSourceProvenanceV1PreregistrationTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.baseline = _load(
            ROOT / cls.config["frozen_baseline"]["report_path"]
        )

    def test_identity_and_single_variable_are_explicit(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_source_provenance_v1",
        )
        self.assertEqual(
            self.config["single_manipulated_variable"],
            (
                "post_consolidation_handling_and_provenance_of_"
                "source_turn_episode_records"
            ),
        )
        self.assertIn(
            "working-memory retrieval scoring",
            self.config["controlled_variables"],
        )
        self.assertIn(
            "typed reflection runtime remains disabled",
            self.config["controlled_variables"],
        )

    def test_baseline_is_hash_bound_and_reproduces_the_data_loss(self):
        frozen = self.config["frozen_baseline"]
        self.assertEqual(
            _sha256_git_file(frozen["commit"], frozen["runtime_path"]),
            frozen["runtime_sha256"],
        )
        for key in ("measurement", "report"):
            self.assertEqual(
                _sha256(ROOT / frozen[f"{key}_path"]),
                frozen[f"{key}_sha256"],
            )
        self.assertEqual(
            self.baseline["runtime_commit"], frozen["commit"]
        )
        self.assertEqual(
            self.baseline["source_episode_count_before"], 20
        )
        self.assertEqual(self.baseline["source_episode_count_after"], 0)
        self.assertEqual(
            self.baseline["source_episode_retention_rate"], 0.0
        )
        self.assertEqual(
            self.baseline["derived_records_with_exact_source_ids"], 0
        )
        self.assertEqual(self.baseline["deleted_episode_count"], 20)
        self.assertEqual(self.baseline["external_model_calls"], 0)

    def test_measurement_is_local_temporary_and_deterministic(self):
        source = (
            ROOT / self.config["frozen_baseline"]["measurement_path"]
        ).read_text(encoding="utf-8")
        self.assertIn("TemporaryDirectory", source)
        self.assertIn("StubCompletions", source)
        self.assertNotIn("OpenAI(", source)
        self.assertNotIn("urlopen(", source)
        self.assertTrue(
            self.baseline["measurement_uses_temporary_chroma"]
        )
        self.assertEqual(self.baseline["stub_model_calls_after_first"], 1)
        self.assertEqual(self.baseline["stub_model_calls_after_second"], 1)

    def test_prior_negative_results_are_hash_bound_and_respected(self):
        evidence = self.config["existing_negative_evidence"]
        expected = {
            "typed_reflection_v4_result_closure": (
                "keep_v4_extractor_shadow_only_and_redesign_"
                "planner_consumption"
            ),
            "reflection_layer_audit_v1_result_closure": (
                "reject_atomic_judge_and_do_not_use_for_v5_design"
            ),
            "cascade_v1_result_lock": (
                "fail_stop_qwen35_4b_to_9b_cascade"
            ),
        }
        for name, decision in expected.items():
            item = evidence[name]
            self.assertEqual(_sha256(ROOT / item["path"]), item["sha256"])
            self.assertEqual(item["decision"], decision)
            result = _load(ROOT / item["path"])
            self.assertEqual(result[item["decision_field"]], decision)

    def test_theory_is_primary_bounded_and_not_claimed_as_proof(self):
        urls = {item["url"] for item in self.config["theory_basis"]}
        self.assertIn(
            "https://pubmed.ncbi.nlm.nih.gov/3008780/", urls
        )
        self.assertIn(
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC4526749/", urls
        )
        boundary = self.config["theory_boundary"]
        self.assertIn("do not prove", boundary)
        self.assertIn("biological memory", boundary)

    def test_success_requires_retention_provenance_and_idempotence(self):
        gates = self.config["success_gates"]
        self.assertEqual(gates["source_episode_count_after_exact"], 20)
        self.assertEqual(
            gates["source_episode_retention_rate_exact"], 1.0
        )
        self.assertEqual(
            gates["derived_records_with_exact_source_ids_exact"], 3
        )
        self.assertEqual(gates["deleted_episode_count_exact"], 0)
        self.assertEqual(gates["marked_consolidated_count_exact"], 20)
        self.assertEqual(gates["stub_model_calls_after_second_exact"], 1)
        self.assertTrue(
            gates["second_pass_created_no_duplicate_derived_records"]
        )
        self.assertIn(
            "remain pending", self.config["failure_atomicity_gate"]
        )

    def test_scope_forbids_prompt_ranking_reflection_and_production_changes(self):
        prohibited = " ".join(self.config["prohibited_changes"])
        for phrase in (
            "consolidation model prompt",
            "Enable typed reflection",
            "working-memory ranking",
            "production Chroma",
            "external or paid model",
        ):
            self.assertIn(phrase, prohibited)
        self.assertFalse(
            self.config[
                "runtime_change_before_preregistration_merge_authorized"
            ]
        )
        self.assertTrue(
            all(
                value is False
                for value in self.config["evidence_limits"].values()
            )
        )

    def test_result_artifacts_were_absent_at_frozen_baseline(self):
        frozen_commit = self.config["frozen_baseline"]["commit"]
        for path in RESULT_PATHS:
            self.assertFalse(
                _git_file_exists(
                    frozen_commit,
                    path.relative_to(ROOT).as_posix(),
                ),
                path,
            )


if __name__ == "__main__":
    unittest.main()
