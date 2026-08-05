import copy
import json
import unittest
from pathlib import Path

import analyze_memory_item_causal_intervention_v1 as analyzer
import memory_item_causal_intervention_v1 as experiment
import run_memory_item_causal_intervention_v1 as runner


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "configs/memory_item_causal_intervention_v1_cases.json"
PREREG = ROOT / "configs/memory_item_causal_intervention_v1_preregistration.json"
LOCK = ROOT / "configs/memory_item_causal_intervention_v1_harness_lock.json"


def synthetic_memory(case):
    target = {
        "source": "episode",
        "collection_name": "episode",
        "memory_id": experiment.target_memory_id(case),
        "trace_id": experiment.target_trace_id(case),
        "text": case["target_text"],
        "score": 0.9,
    }
    irrelevant = {
        "source": "episode",
        "collection_name": "episode",
        "memory_id": experiment.irrelevant_memory_id(case),
        "trace_id": experiment.irrelevant_trace_id(case),
        "text": case["irrelevant_text"],
        "score": 0.4,
    }
    return {
        "working_memory_items": [target, irrelevant],
        "working_memory_summary": f"{case['target_text']} / {case['irrelevant_text']}",
        "episodes": f"{case['target_text']} || {case['irrelevant_text']}",
        "wisdom": "無相關經驗",
        "procedural": "無相關程序記憶",
        "profile": "無穩定使用者資料",
        "profile_structured": {},
        "recent_dialogue": "無近期對話",
        "recent_turns": [],
        "short_term_summary": "無短期記憶",
        "memory_provenance": {
            "schema": "uruha_memory_provenance_trace_v1",
            "retrieved_candidates": [copy.deepcopy(target), copy.deepcopy(irrelevant)],
            "candidate_pool": [copy.deepcopy(target), copy.deepcopy(irrelevant)],
            "selected_working_memory_trace_ids": [target["trace_id"], irrelevant["trace_id"]],
            "passed_to_leftbrain": [
                {**copy.deepcopy(target), "channel": "selected_working_memory"},
                {**copy.deepcopy(irrelevant), "channel": "selected_working_memory"},
            ],
            "passed_to_leftbrain_trace_ids": [target["trace_id"], irrelevant["trace_id"]],
        },
    }


class FakeRuntime:
    def __init__(self):
        self.working_memory = []
        self.last_user_input = "question"
        self.last_attention_frame = {}
        self.blackboard = []


class FakeBot:
    def __init__(self):
        self.runtime = FakeRuntime()

    def _build_attention_frame(self, _user, memory_data):
        return {"ids": [row["trace_id"] for row in memory_data["working_memory_items"]]}


class FakeCompletions:
    def __init__(self, fail=False):
        self.fail = fail
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.fail:
            raise RuntimeError("transport failed")
        return {"ok": True}


class MemoryItemCausalInterventionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = experiment.load_cases(CASES)
        cls.case = cls.cases[0]
        cls.prereg = json.loads(PREREG.read_text(encoding="utf-8"))

    def event(self):
        return {"memory_data": synthetic_memory(self.case)}

    def test_cases_are_nonbenchmark_and_have_unique_markers(self):
        self.assertEqual(len(self.cases), 8)
        serialized = CASES.read_text(encoding="utf-8").lower()
        for forbidden in ("tombench", "ipip", "benchmark_answer", "gold_answer"):
            self.assertNotIn(forbidden, serialized)
        for case in self.cases:
            self.assertFalse(experiment.contains_any(case["user_input"], case["target_markers"]))
            self.assertFalse(experiment.contains_any(case["user_input"], case["replacement_markers"]))

    def test_retrieval_audit_distinguishes_selected_and_passed(self):
        audit = experiment.capture_retrieval_audit(self.event()["memory_data"], self.case)
        self.assertTrue(audit["target_selected"])
        self.assertTrue(audit["target_passed"])
        self.assertTrue(audit["irrelevant_selected"])
        self.assertTrue(audit["irrelevant_passed"])

    def test_intact_strips_audit_text_but_preserves_decision_records(self):
        event = self.event()
        experiment.apply_condition(FakeBot(), event, self.case, experiment.C0)
        provenance = event["memory_data"]["memory_provenance"]
        self.assertNotIn("retrieved_candidates", provenance)
        self.assertNotIn("candidate_pool", provenance)
        self.assertIn(experiment.target_trace_id(self.case), provenance["passed_to_leftbrain_trace_ids"])

    def test_remove_target_changes_only_target_passage(self):
        event = self.event()
        before = synthetic_memory(self.case)
        experiment.apply_condition(FakeBot(), event, self.case, experiment.T1)
        view = experiment.decision_view(event["memory_data"])
        self.assertFalse(experiment.contains_any(view, [self.case["target_text"], experiment.target_trace_id(self.case)]))
        self.assertTrue(experiment.contains_any(view, [self.case["irrelevant_text"]]))
        self.assertEqual(before["wisdom"], event["memory_data"]["wisdom"])

    def test_replace_target_preserves_slot_and_uses_new_trace(self):
        event = self.event()
        experiment.apply_condition(FakeBot(), event, self.case, experiment.T2)
        items = event["memory_data"]["working_memory_items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["trace_id"], experiment.replacement_trace_id(self.case))
        self.assertEqual(items[0]["text"], self.case["replacement_text"])
        self.assertNotIn(experiment.target_trace_id(self.case), event["memory_data"]["memory_provenance"]["passed_to_leftbrain_trace_ids"])

    def test_remove_irrelevant_preserves_target(self):
        event = self.event()
        experiment.apply_condition(FakeBot(), event, self.case, experiment.N1)
        view = experiment.decision_view(event["memory_data"])
        self.assertTrue(experiment.contains_any(view, [self.case["target_text"]]))
        self.assertFalse(experiment.contains_any(view, [self.case["irrelevant_text"]]))

    def test_balanced_sequence_has_32_unique_case_conditions(self):
        sequence = experiment.expected_sequence(self.cases)
        self.assertEqual(len(sequence), 32)
        self.assertEqual(
            len({(case["id"], condition) for case, condition in sequence}),
            32,
        )
        first = [condition for index, (_case, condition) in enumerate(sequence) if index % 4 == 0]
        self.assertEqual(set(first), set(experiment.CONDITIONS))

    def test_analysis_requires_target_removal_and_negative_control(self):
        rows = []
        for case in self.cases:
            base = {
                "case_id": case["id"],
                "retrieval_audit": {
                    "schema": "uruha_memory_provenance_trace_v1",
                    "target_selected": True,
                    "target_passed": True,
                    "irrelevant_selected": True,
                    "irrelevant_passed": True,
                },
                "decision_view_target_absent_when_required": True,
                "decision_view_irrelevant_absent_when_required": True,
                "target_marker_in_reply": True,
                "replacement_marker_in_reply": False,
                "elapsed_seconds": 1.0,
                "leftbrain_call_count": 1,
                "transport_error_count": 0,
                "production_memory_write_count": 0,
                "physical_vrm_action_count": 0,
            }
            rows.extend(
                [
                    {**base, "condition": experiment.C0, "target_anchor": True, "replacement_anchor": False, "target_marker_in_plan": True, "replacement_marker_in_plan": False},
                    {**base, "condition": experiment.T1, "target_anchor": False, "replacement_anchor": False, "target_marker_in_plan": False, "replacement_marker_in_plan": False},
                    {**base, "condition": experiment.T2, "target_anchor": False, "replacement_anchor": True, "target_marker_in_plan": False, "replacement_marker_in_plan": True},
                    {**base, "condition": experiment.N1, "target_anchor": True, "replacement_anchor": False, "target_marker_in_plan": True, "replacement_marker_in_plan": False},
                ]
            )
        report = analyzer.build_report(rows, self.prereg)
        self.assertEqual(report["decision"], "exact_memory_record_causally_supported_bounded")
        broken = copy.deepcopy(rows)
        for row in broken:
            if row["condition"] == experiment.T1:
                row["target_marker_in_plan"] = True
        self.assertNotEqual(
            analyzer.build_report(broken, self.prereg)["decision"],
            "exact_memory_record_causally_supported_bounded",
        )

    def test_preregistration_forbids_runtime_and_benchmark_claims(self):
        self.assertFalse(self.prereg["authorization"]["production_runtime_change"])
        self.assertFalse(self.prereg["authorization"]["benchmark_claim"])
        self.assertEqual(self.prereg["scope"]["expected_decision_run_count"], 32)

    def test_audited_client_freezes_seed_and_records_transport_status(self):
        log = []
        target = FakeCompletions()
        client = runner._AuditedClient(target, 17, log)
        self.assertEqual(client.chat.completions.create(model="qwen", temperature=1.0), {"ok": True})
        self.assertEqual(target.kwargs["seed"], 17)
        self.assertEqual(target.kwargs["temperature"], 0.0)
        self.assertEqual(log[0]["status"], "returned")

        failed_log = []
        failed = runner._AuditedClient(FakeCompletions(fail=True), 19, failed_log)
        with self.assertRaises(RuntimeError):
            failed.chat.completions.create(model="qwen")
        self.assertEqual(failed_log[0]["status"], "error")

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(
                experiment.file_sha256(ROOT / artifact["path"]),
                artifact["sha256"],
            )

    def test_experiment_does_not_modify_production_runtime(self):
        marker = "memory_item_causal_intervention_v1"
        for name in ("uruha_brain_mac.py", "uruha_memory_runtime.py", "uruha_web_ui.py"):
            self.assertNotIn(marker, (ROOT / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
