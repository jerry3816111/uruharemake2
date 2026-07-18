import hashlib
import json
import unittest
from pathlib import Path

from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/rightbrain_shared_final_plan_v63.json"
RAW_PATH = ROOT / "reports/rightbrain_shared_final_plan_v63_raw.json"
ANALYSIS_PATH = ROOT / "reports/rightbrain_shared_final_plan_v63_analysis.json"
DIAGNOSIS_PATH = ROOT / "reports/rightbrain_shared_final_plan_v63_diagnosis.json"
LOCK_PATH = ROOT / "configs/rightbrain_shared_final_plan_v63_result_lock.json"
T1 = "t1_final_logic_with_speech_plan"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RightBrainSharedFinalPlanV63ResultTest(unittest.TestCase):
    def test_formal_accounting_is_complete_and_isolated(self):
        raw = _load(RAW_PATH)
        self.assertEqual(raw["plan_capture_count"], 14)
        self.assertEqual(
            raw["plan_source_distribution"],
            {"model_high_road": 12, "rule_high_road": 2},
        )
        self.assertEqual(raw["leftbrain_call_count"], 12)
        self.assertEqual(raw["logical_model_call_count"], 28)
        self.assertEqual(raw["transport_attempt_count"], 28)
        self.assertEqual(raw["transport_error_count"], 0)
        self.assertEqual(raw["production_memory_write_count"], 0)
        self.assertEqual(raw["physical_vrm_action_count"], 0)

    def test_frozen_negative_result_matches_raw_scores(self):
        analysis = _load(ANALYSIS_PATH)
        control = analysis["condition_summaries"][
            "c0_final_logic_without_speech_plan"
        ]
        treatment = analysis["condition_summaries"][T1]

        self.assertEqual(control["raw_required_meaning_hit_count"], 8)
        self.assertEqual(treatment["raw_required_meaning_hit_count"], 6)
        self.assertEqual(treatment["raw_required_meaning_total"], 27)
        self.assertEqual(control["raw_case_complete_count"], 3)
        self.assertEqual(treatment["raw_case_complete_count"], 2)
        self.assertFalse(analysis["automatic_gates"]["passed"])
        self.assertEqual(
            analysis["decision"],
            "freeze_negative_result_and_stop_full_speech_plan_payload_hypothesis",
        )

    def test_plan_to_output_decomposition_is_recomputable(self):
        dataset = _load(DATASET_PATH)
        raw = _load(RAW_PATH)
        diagnosis = _load(DIAGNOSIS_PATH)["plan_to_output_decomposition"]
        right_brain = RightBrain(load_model=False)
        case_by_id = {case["id"]: case for case in dataset["cases"]}
        t1_by_id = {
            row["case_id"]: row
            for row in raw["model_rows"]
            if row["condition"] == T1
        }
        totals = {
            "plan_hit_count": 0,
            "treatment_output_hit_count": 0,
            "plan_and_output_both_hit": 0,
            "plan_hit_output_missed": 0,
            "plan_missed_output_added": 0,
            "plan_and_output_both_missed": 0,
        }
        for capture in raw["captures"]:
            case = case_by_id[capture["case_id"]]
            plan_text = " / ".join(
                str(item)
                for item in capture["runtime_speech_plan"]["content_units"]
            )
            output_rows = {
                row["id"]: row
                for row in t1_by_id[capture["case_id"]]["raw_score"][
                    "required_meaning_propositions"
                ]
            }
            for proposition in case["required_meaning_propositions"]:
                plan_hit = any(
                    right_brain._semantic_marker_hit(plan_text, surface)
                    for surface in proposition["accepted_surfaces"]
                )
                output_hit = bool(output_rows[proposition["id"]]["hit"])
                totals["plan_hit_count"] += int(plan_hit)
                totals["treatment_output_hit_count"] += int(output_hit)
                if plan_hit and output_hit:
                    totals["plan_and_output_both_hit"] += 1
                elif plan_hit:
                    totals["plan_hit_output_missed"] += 1
                elif output_hit:
                    totals["plan_missed_output_added"] += 1
                else:
                    totals["plan_and_output_both_missed"] += 1
        for key, value in totals.items():
            self.assertEqual(value, diagnosis[key], key)

    def test_result_lock_binds_artifacts_and_forbids_rollout(self):
        lock = _load(LOCK_PATH)
        for name, artifact in lock["frozen_artifacts"].items():
            path = ROOT / artifact["path"]
            self.assertTrue(path.exists(), name)
            self.assertEqual(_sha256(path), artifact["sha256"], name)
        for key in (
            "same_dataset_retest_authorized",
            "threshold_change_authorized",
            "human_blind_review_authorized",
            "runtime_change_authorized",
            "production_rightbrain_replacement_authorized",
            "official_benchmark_claim_authorized",
            "broad_human_likeness_claim_authorized",
            "target_person_replication_claim_authorized",
        ):
            self.assertFalse(lock[key])


if __name__ == "__main__":
    unittest.main()
