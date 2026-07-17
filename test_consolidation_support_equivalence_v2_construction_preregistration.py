#!/usr/bin/env python3
"""Validate the V2 support-equivalence construction preregistration."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_equivalence_v2_construction_preregistration.json"
)
PREREGISTRATION_MERGE_COMMIT = (
    "ea62631f5dd448cae0354dca619caa47b213b15f"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ConsolidationSupportEquivalenceV2ConstructionPreregistrationTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)

    def test_identity_boundary_and_priority_are_explicit(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_support_equivalence_v2_construction",
        )
        self.assertEqual(
            self.config["target_ability"],
            "long_term_memory_consolidation_source_grounding",
        )
        ranking = self.config["priority_selection"]
        scores = {
            row["task"]: row["priority_score"]
            for row in ranking["candidates"]
        }
        selected = ranking["selected_task"]
        self.assertEqual(selected, max(scores, key=scores.get))
        self.assertEqual(scores[selected], 40.0)
        self.assertIn(
            "construction",
            self.config["evidence_boundary"].lower(),
        )

    def test_primary_method_sources_support_multi_evidence_scoring(self):
        methods = {
            row["name"]: row for row in self.config["method_basis"]
        }
        self.assertEqual(set(methods), {"FEVER", "ERASER", "LongMemEval"})
        self.assertEqual(
            methods["FEVER"]["primary_source"],
            "https://aclanthology.org/W18-5501/",
        )
        self.assertIn(
            "multiple complete evidence sets",
            methods["FEVER"]["adopted_principle"],
        )
        self.assertIn(
            "sufficient",
            methods["ERASER"]["adopted_principle"],
        )
        self.assertIn(
            "abstention",
            methods["LongMemEval"]["adopted_principle"],
        )

    def test_pool_is_balanced_and_no_consumed_case_may_be_reused(self):
        pool = self.config["construction_pool"]
        self.assertEqual(pool["pool_case_count"], 18)
        self.assertEqual(pool["pool_derived_memory_count"], 54)
        self.assertEqual(
            pool["language_case_counts"],
            {"eng": 6, "jpn": 6, "cmn": 6},
        )
        self.assertEqual(
            pool["memory_kind_counts"],
            {"episodic": 18, "wisdom": 18, "procedural": 18},
        )
        self.assertEqual(
            sum(pool["support_phenomenon_counts"].values()),
            54,
        )
        freshness = self.config["freshness_and_leakage_controls"]
        for path in freshness["excluded_consumed_datasets"]:
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertEqual(freshness["exact_user_text_overlap_allowed"], 0)
        self.assertEqual(
            freshness["prior_scenario_family_reuse_allowed"],
            0,
        )
        self.assertFalse(freshness["consumed_v1_case_relabeling_allowed"])

    def test_equivalence_contract_separates_sufficiency_and_soundness(self):
        contract = self.config["support_equivalence_contract"]
        self.assertTrue(contract["minimal_set_antichain_required"])
        self.assertIn(
            "one or more minimal support sets",
            contract["acceptable_support_unions"],
        )
        self.assertIn("complete minimal support set", contract["sufficient"])
        self.assertIn("support universe", contract["sound"])
        self.assertIn(
            "both sufficient and sound",
            contract["fully_valid"],
        )
        self.assertIn(
            "future-facing User instruction",
            contract["memory_kind_rules"]["procedural"],
        )
        self.assertIn(
            "stale or contradicted",
            contract["memory_kind_rules"]["current_state_override"],
        )

    def test_two_blind_reviewers_are_distinct_from_future_candidate(self):
        review = self.config["independent_machine_review"]
        identities = {
            review[name]["digest"]
            for name in ("reviewer_a", "reviewer_b", "future_candidate")
        }
        self.assertEqual(len(identities), 3)
        self.assertEqual(review["review_call_budget_exact"], 108)
        self.assertEqual(
            review["shared_generation_settings"][
                "transport_attempts_per_derived_memory"
            ],
            1,
        )
        self.assertFalse(
            review["human_review_required_for_this_development_phase"]
        )
        self.assertFalse(review["human_quality_gold_claim_authorized"])
        self.assertIn(
            "both are Qwen-family models",
            review["review_independence_limit"],
        )
        self.assertIn(
            "Only if construction and the later machine-consensus pilot both pass",
            review["later_human_audit_trigger"],
        )
        blindness = " ".join(review["blindness"])
        self.assertIn("Neither reviewer receives researcher gold", blindness)
        self.assertIn(
            "future Qwen3.5 4B candidate is not called",
            blindness,
        )
        self.assertIn(
            "all-or-nothing",
            review["case_retention_policy"],
        )
        self.assertIn(
            "retire the entire six-event case",
            review["case_retention_policy"],
        )

    def test_construction_gates_and_second_failure_stop_are_frozen(self):
        gates = self.config["construction_success_gates"]
        self.assertEqual(gates["final_case_count_min"], 12)
        self.assertEqual(gates["final_derived_memory_count_min"], 36)
        self.assertEqual(
            gates["retained_item_three_way_canonical_agreement"],
            1.0,
        )
        self.assertEqual(gates["candidate_model_call_count_exact"], 0)
        self.assertEqual(
            gates["production_database_write_count_exact"],
            0,
        )
        decision = self.config["decision_rule"]
        self.assertIn(
            "second failed",
            decision["future_pilot_fail"],
        )
        self.assertIn(
            "stop the mechanism",
            decision["future_pilot_fail"],
        )

    def test_no_construction_or_candidate_work_preceded_merge(self):
        pool = self.config["construction_pool"]
        for key in (
            "pool_dataset_path",
            "final_dataset_path",
            "builder_path",
            "reviewer_path",
            "auditor_path",
            "audit_json_path",
            "audit_markdown_path",
            "closure_path",
        ):
            completed = subprocess.run(
                [
                    "git",
                    "cat-file",
                    "-e",
                    (
                        f"{PREREGISTRATION_MERGE_COMMIT}:"
                        f"{pool[key]}"
                    ),
                ],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.assertNotEqual(completed.returncode, 0, key)
        self.assertFalse(
            self.config[
                "construction_outputs_before_preregistration_merge_authorized"
            ]
        )
        self.assertFalse(
            self.config[
                "candidate_model_inference_before_construction_closure_authorized"
            ]
        )
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(
            self.config["production_database_access_authorized"]
        )
        self.assertFalse(self.config["human_task_required_now"])
        self.assertFalse(
            self.config["broad_human_likeness_claim_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
