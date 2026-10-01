from __future__ import annotations

import json
import hashlib
from pathlib import Path
import unittest

from longitudinal_human_model.pub_pragmatics import CONDITIONS, audit_payload_contract, json_schema_for_condition
from run_m14_pub_schema_replication import CONFIG_PATH, MANIFEST_PATH, prepare_manifest


ROOT = Path(__file__).resolve().parent


class M14Tests(unittest.TestCase):
    def test_condition_schemas_require_exact_contract(self):
        for condition in CONDITIONS:
            schema = json_schema_for_condition(condition, 5)
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(set(schema["required"]), set(schema["properties"]))
            self.assertEqual(4, schema["properties"]["answer_index"]["maximum"])

    def test_a_schema_shaped_ours_payload_passes_audit(self):
        payload = {
            "literal_content":"x","pragmatic_target":"y","context_evidence":"z",
            "alternative_interpretation":"a","uncertainty":"low","answer_index":0,
        }
        self.assertTrue(audit_payload_contract("OURS_PRAGMATIC_LOOP",payload)["valid"])

    def test_preregistration_preserves_single_change_and_strong_baseline(self):
        config=json.loads(CONFIG_PATH.read_text())
        self.assertEqual("OURS_PRAGMATIC_LOOP versus B1_GENERIC_DELIBERATION",config["primary_comparison"])
        self.assertIn("single_changed_mechanism",config["predecessor"])
        self.assertEqual(16,config["sampling"]["rank_offset_per_task"])
        self.assertEqual(0,config["sampling"]["required_overlap_with_m13"])
        self.assertEqual(
            config["case_manifest"]["sha256"],
            hashlib.sha256((ROOT/config["case_manifest"]["path"]).read_bytes()).hexdigest(),
        )

    def test_manifest_is_disjoint_and_answer_free(self):
        manifest=prepare_manifest(); m13=json.loads((ROOT/"configs/m13_pub_pragmatics_case_manifest.json").read_text())
        ids={x["sample_id"] for x in manifest["cases"]}; old={x["sample_id"] for x in m13["cases"]}
        self.assertEqual(64,len(ids)); self.assertFalse(ids & old); self.assertFalse(manifest["answer_content_in_manifest"])

    def test_result_lock_preserves_inconclusive_gain_and_all_hashes(self):
        lock=json.loads((ROOT/"configs/m14_pub_schema_replication_result_lock.json").read_text())
        self.assertEqual("fail_schema_enforced_pragmatic_gain",lock["decision"])
        self.assertEqual(1.0,lock["all_conditions_schema_rate"])
        self.assertGreater(lock["ours_minus_generic_accuracy"],0)
        self.assertGreater(lock["ours_minus_generic_mcnemar_p"],0.05)
        self.assertFalse(lock["effect_direction_replicated_from_m13"])
        for artifact in lock["artifacts"].values():
            self.assertEqual(artifact["sha256"],hashlib.sha256((ROOT/artifact["path"]).read_bytes()).hexdigest())


if __name__ == "__main__": unittest.main()
