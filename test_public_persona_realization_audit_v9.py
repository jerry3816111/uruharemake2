import copy
import hashlib
import json
import unittest
from pathlib import Path

import public_persona_contract_v3 as v3
import public_persona_realization_audit_v9 as v9


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION = ROOT / "configs/public_persona_realization_audit_v9_preregistration.json"
V8_RESULT_LOCK = ROOT / "configs/public_persona_missing_role_v8_model_result_lock.json"
HARNESS_LOCK = ROOT / "configs/public_persona_realization_audit_v9_harness_lock.json"


class PublicPersonaRealizationAuditV9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        cls.preregistration = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
        cls.v8_lock = json.loads(V8_RESULT_LOCK.read_text(encoding="utf-8"))

    def test_plan_role_schemas_cover_all_and_only_v3_contexts(self):
        self.assertEqual(set(v9.PLAN_ROLE_MARKERS), set(v3.POLICIES))
        self.assertEqual(set(v9.REPLY_ROLE_MARKERS), set(v3.POLICIES))

    def test_role_names_match_v8_required_role_schema(self):
        import public_persona_missing_role_v8 as v8

        for context, roles in v8.ROLE_SCHEMAS.items():
            expected = {item["role"] for item in roles}
            self.assertEqual(set(v9.PLAN_ROLE_MARKERS[context]), expected)

    def test_planning_evidence_excludes_evaluation_fields(self):
        case = self.dataset["cases"][0]
        evidence = v9.planning_evidence(case["logic"])
        self.assertNotIn("required_marker_groups", evidence)
        self.assertNotIn("persona_evaluation", evidence)
        self.assertNotIn("marker_groups", json.dumps(evidence, ensure_ascii=False))

    def test_compiler_does_not_mutate_logic(self):
        source = copy.deepcopy(self.dataset["cases"][0]["logic"])
        frozen = copy.deepcopy(source)
        v9.compile_plan_coverage(source)
        self.assertEqual(source, frozen)

    def test_contract_has_no_fixed_reply_or_authorization(self):
        for case in self.dataset["cases"]:
            contract = v9.compile_plan_coverage(case["logic"])
            self.assertFalse(contract["contains_fixed_reply"])
            self.assertFalse(contract["runtime_authorized"])
            self.assertFalse(contract["training_authorized"])

    def test_notice_target_entry_point_is_present_in_plan(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_notice_01")
        coverage = v9.compile_plan_coverage(case["logic"])
        self.assertIn("entry_point", coverage["covered_roles"])
        role = next(item for item in coverage["roles"] if item["role"] == "entry_point")
        self.assertTrue(set(role["plan_marker_hits"]) & {"案内", "入口", "視聴者"})

    def test_inactive_cases_have_no_role_classification(self):
        inactive = 0
        for case in self.dataset["cases"]:
            if case["context"] in v3.POLICIES:
                continue
            coverage = v9.compile_plan_coverage(case["logic"])
            self.assertEqual(coverage["status"], "inactive_no_supported_context")
            self.assertEqual(coverage["roles"], [])
            inactive += 1
        self.assertEqual(inactive, 5)

    def test_missing_reason_maps_to_canonical_roles(self):
        self.assertEqual(
            v9.missing_required_roles(["missing_required:current_state", "wrong_order:x->y"]),
            ["current_state"],
        )
        self.assertEqual(
            v9.missing_required_roles(["missing_required:entry_point"]), ["entry_point"]
        )

    def test_classification_detects_lexical_scorer_gap(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_fatigue_02")
        result = v9.classify_missing_role(case["logic"], "へろへろだから少し休む", "current_state")
        self.assertEqual(result["classification"], "lexical_scorer_gap")

    def test_classification_detects_planned_but_unrealized(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_notice_01")
        result = v9.classify_missing_role(case["logic"], "ゲーム配信を始めた", "entry_point")
        self.assertEqual(result["classification"], "planned_but_unrealized")

    def test_classification_detects_actual_planner_gap(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_notice_01")
        logic = copy.deepcopy(case["logic"])
        logic["jp_summary"] = "ゲーム配信を開始した。"
        logic["core_message_jp"] = "ゲーム配信を始めたと伝える"
        logic["human_speech_plan"]["content_units"] = ["開始を知らせる", "ゲーム配信を伝える"]
        result = v9.classify_missing_role(logic, "ゲーム配信を始めた", "entry_point")
        self.assertEqual(result["classification"], "planner_role_missing")

    def test_v8_dependency_authorizes_only_narrow_research(self):
        self.assertTrue(
            self.v8_lock["authorizations"]["model_readable_missing_role_semantics_research"]
        )
        self.assertFalse(self.v8_lock["authorizations"]["runtime_default_enable"])

    def test_preregistration_forbids_runtime_model_scorer_training_and_holdout_changes(self):
        decision = self.preregistration["decision_policy"]
        self.assertFalse(decision["runtime_default_enable"])
        self.assertFalse(decision["model_change"])
        self.assertFalse(decision["scorer_rewrite"])
        self.assertFalse(decision["training"])
        self.assertFalse(decision["holdout_unsealing"])
        self.assertFalse(decision["persona_fidelity_claim"])

    def test_scope_is_zero_model_and_zero_side_effect(self):
        scope = self.preregistration["scope"]
        self.assertEqual(scope["model_call_count_exact"], 0)
        self.assertEqual(scope["holdout_content_review_count_exact"], 0)
        self.assertEqual(scope["production_memory_write_count_exact"], 0)
        self.assertEqual(scope["physical_vrm_action_count_exact"], 0)

    def test_harness_lock_hashes_match(self):
        lock = json.loads(HARNESS_LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
