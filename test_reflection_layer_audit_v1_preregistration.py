import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "reflection_layer_audit_v1_preregistration.json"
DATASET = ROOT / "datasets" / "reflection_layer_audit_v1_calibration.json"
V4_DATASET = ROOT / "datasets" / "typed_reflection_v4_development_pilot.json"
LOCK = ROOT / "configs" / "reflection_layer_audit_v1_construction_lock.json"


def normalized(text):
    return "".join(str(text or "").lower().split())


class ReflectionLayerAuditV1PreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_accounting_and_balance_are_frozen(self):
        cases = self.dataset["cases"]
        self.assertEqual(len(cases), self.config["case_count"])
        self.assertEqual(len({row["id"] for row in cases}), len(cases))
        self.assertEqual(len({row["pair_id"] for row in cases}), 6)
        self.assertEqual(sum(row["expected_accept"] for row in cases), 6)
        self.assertEqual(sum(not row["expected_accept"] for row in cases), 6)
        self.assertEqual(sum(len(row["claims"]) for row in cases), 36)
        self.assertEqual(Counter(row["family"] for row in cases), {
            "semantic": 4,
            "procedural": 4,
            "interpretive": 4,
        })

    def test_each_pair_has_one_accept_and_one_reject(self):
        grouped = {}
        for row in self.dataset["cases"]:
            grouped.setdefault(row["pair_id"], []).append(row)
        for pair_id, rows in grouped.items():
            self.assertEqual(len(rows), 2, pair_id)
            self.assertEqual(sorted(row["expected_accept"] for row in rows), [False, True])
            for row in rows:
                self.assertEqual(len(row["claims"]), 3)
                self.assertEqual(len({claim["id"] for claim in row["claims"]}), 3)
                self.assertTrue(all(claim["critical"] for claim in row["claims"]))

    def test_calibration_sources_are_not_v4_sources(self):
        v4 = json.loads(V4_DATASET.read_text(encoding="utf-8"))
        old_sources = {normalized(row["seed_user"]) for row in v4["cases"]}
        new_sources = {normalized(row["source_text"]) for row in self.dataset["cases"]}
        self.assertTrue(old_sources.isdisjoint(new_sources))

    def test_no_runtime_or_rescore_is_authorized(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["v4_rescore_authorized"])
        self.assertFalse(self.config["independent_holdout_authorized"])
        self.assertEqual(
            self.config["decision_rule"]["any_gate_fails"],
            "reject_atomic_judge_and_do_not_use_for_v5_design",
        )

    def test_construction_lock_binds_frozen_inputs(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for relative, expected in lock["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)
        self.assertFalse(lock["model_inference_on_frozen_cases_performed"])
        self.assertFalse(lock["runner_implemented"])


if __name__ == "__main__":
    unittest.main()
