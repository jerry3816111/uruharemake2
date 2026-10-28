from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from longitudinal_human_model.pub_pragmatics import prospective_exact_mcnemar_power
from run_m15_deixis_confirmation import CONDITIONS, CONFIG_PATH, MANIFEST_PATH, condition_order, prepare_manifest, validate_power_plan


ROOT = Path(__file__).resolve().parent


class M15Tests(unittest.TestCase):
    def test_power_plan_is_exact_and_minimal(self):
        config = json.loads(CONFIG_PATH.read_text())
        self.assertAlmostEqual(0.9007238501618088, validate_power_plan(config), places=12)
        plan = config["power_analysis"]
        previous = prospective_exact_mcnemar_power(299, accuracy_delta=plan["smallest_effect_size_of_interest_accuracy_delta"], discordance_rate=plan["planning_discordance_rate"], alpha=plan["alpha"])
        self.assertLess(previous, plan["target_power"])

    def test_manifest_is_answer_free_and_disjoint(self):
        manifest = prepare_manifest()
        self.assertEqual(300, manifest["case_count"])
        self.assertFalse(manifest["answer_content_in_manifest"])
        self.assertEqual(0, manifest["overlap_with_m13_or_m14"])
        ids = {case["sample_id"] for case in manifest["cases"]}
        self.assertEqual(300, len(ids))
        old = set()
        for path in ("configs/m13_pub_pragmatics_case_manifest.json", "configs/m14_pub_schema_replication_case_manifest.json"):
            old.update(case["sample_id"] for case in json.loads((ROOT / path).read_text())["cases"])
        self.assertFalse(ids & old)

    def test_preregistration_binds_manifest_and_strong_baseline(self):
        config = json.loads(CONFIG_PATH.read_text())
        self.assertEqual(list(CONDITIONS), config["conditions"])
        self.assertEqual("OURS_PRAGMATIC_LOOP versus B1_GENERIC_DELIBERATION", config["primary_comparison"])
        self.assertEqual(0.15, config["success_gate"]["primary_accuracy_delta_minimum"])
        self.assertEqual(0, config["generation"]["retries"])
        self.assertEqual(config["case_manifest"]["sha256"], hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest())

    def test_condition_order_is_counterbalanced_and_deterministic(self):
        manifest = json.loads(MANIFEST_PATH.read_text())
        orders = [tuple(condition_order(case["sample_id"])) for case in manifest["cases"]]
        self.assertEqual(orders, [tuple(condition_order(case["sample_id"])) for case in manifest["cases"]])
        forward = sum(order == CONDITIONS for order in orders)
        self.assertGreater(forward, 120)
        self.assertLess(forward, 180)

    def test_result_lock_preserves_focused_pass_and_artifact_hashes(self):
        lock = json.loads((ROOT / "configs/m15_deixis_confirmation_result_lock.json").read_text())
        self.assertEqual("pass_focused_deixis_advantage", lock["decision"])
        self.assertTrue(lock["all_preregistered_gates_passed"])
        self.assertEqual(0.16, lock["ours_minus_generic_accuracy"])
        self.assertEqual([0.07, 0.25], lock["ours_minus_generic_bootstrap_95_ci"])
        self.assertLess(lock["ours_minus_generic_exact_mcnemar_p"], 0.001)
        self.assertFalse(lock["population_effect_at_least_SESOI_established"])
        self.assertEqual(0, lock["production_memory_writes"])
        for artifact in lock["artifacts"].values():
            self.assertEqual(
                artifact["sha256"],
                hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
