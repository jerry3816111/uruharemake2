import json
import subprocess
import unittest
from pathlib import Path

import planner_supervision_proxy_review_v80 as v80
import planner_supervision_v76 as v76
import quarantine_planner_self_reviews_v80 as quarantine_v80
import analyze_planner_supervision_proxy_review_v80 as analyze_v80


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v80_proxy_review_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v80_proxy_review.json"


class ProxyReviewV80Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def packet(self, index=1):
        payload = {
            "input_context": {"user_utterance": "今日は疲れた", "working_memory": []},
            "target_plan": {"reply_goal": "疲れを認めて休息を提案する"},
        }
        return {
            "pilot_index": index,
            "candidate_id": f"candidate-{index}",
            "candidate_binding_sha256": f"binding-{index}",
            "scenario_family": "emotional_support",
            "packet_payload": payload,
            "packet_sha256": v76.canonical_sha256(payload),
        }

    def raw(self, packet, model, decision="accept", confidence=0.9, codes=None):
        parsed = {
            "decision": decision,
            "failure_codes": codes or [],
            "rationale": "The plan is grounded and directly addresses the user.",
            "confidence": confidence,
        }
        request = v80.build_request(packet, self.contract, model)
        judge = next(row for row in self.contract["judges"] if row["model"] == model)
        return {
            "candidate_id": packet["candidate_id"],
            "packet_sha256": packet["packet_sha256"],
            "model": model,
            "model_digest": judge["digest"],
            "request_sha256": v76.canonical_sha256(request),
            "parsed": parsed,
            "elapsed_seconds": 1.0,
        }

    def test_request_contains_no_gold_or_benchmark_answer(self):
        request = v80.build_request(self.packet(), self.contract, self.contract["judges"][0]["model"])
        payload = json.dumps(request).lower()
        self.assertNotIn("gold_answer", payload)
        self.assertNotIn("correct_option", payload)
        self.assertIn("internal speech plan", payload)

    def test_parser_rejects_accept_with_failure(self):
        value = {
            "decision": "accept",
            "failure_codes": ["unsupported_inference"],
            "rationale": "bad",
            "confidence": 0.8,
        }
        with self.assertRaisesRegex(ValueError, "cannot have"):
            v80.parse_judgment(value, self.contract)

    def test_unanimous_accept_is_required(self):
        packets = [self.packet()]
        rows = [
            self.raw(packets[0], self.contract["judges"][0]["model"]),
            self.raw(
                packets[0],
                self.contract["judges"][1]["model"],
                decision="reject",
                codes=["internally_inconsistent"],
            ),
        ]
        contract = json.loads(json.dumps(self.contract))
        for key in contract["integrity_gates"]:
            contract["integrity_gates"][key] = {
                "packet_count": 1,
                "attempt_count": 2,
                "parsed_count": 2,
                "model_digest_match_count": 2,
                "packet_hash_match_count": 2,
                "request_hash_match_count": 2,
                "strict_human_rows_created": 0,
                "production_runtime_files_changed": 0,
            }[key]
        report = v80.analyze(packets, rows, contract, strict_human_rows_created=0, production_runtime_files_changed=0)
        self.assertEqual(report["consensus_counts"], {"disagreement": 1})
        self.assertEqual(report["proxy_approved_weak_supervision_count"], 0)
        self.assertFalse(report["strict_human_training_authorized"])

    def test_low_confidence_unanimous_accept_is_uncertain(self):
        packets = [self.packet()]
        rows = [self.raw(packets[0], judge["model"], confidence=0.5) for judge in self.contract["judges"]]
        contract = json.loads(json.dumps(self.contract))
        contract["integrity_gates"].update(
            packet_count=1,
            attempt_count=2,
            parsed_count=2,
            model_digest_match_count=2,
            packet_hash_match_count=2,
            request_hash_match_count=2,
        )
        report = v80.analyze(packets, rows, contract, strict_human_rows_created=0, production_runtime_files_changed=0)
        self.assertEqual(report["consensus_counts"], {"uncertain": 1})

    def test_resume_accepts_only_exact_frozen_prefix(self):
        packets = [self.packet(1), self.packet(2)]
        first_model = self.contract["judges"][0]["model"]
        first = self.raw(packets[0], first_model)
        digests = {row["model"]: row["digest"] for row in self.contract["judges"]}
        sequence = v80.validate_resume_prefix(packets, [first], self.contract, digests)
        self.assertEqual(len(sequence), 4)
        first["candidate_id"] = packets[1]["candidate_id"]
        with self.assertRaisesRegex(ValueError, "frozen run order"):
            v80.validate_resume_prefix(packets, [first], self.contract, digests)

    def test_runtime_is_unchanged(self):
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", self.contract["parent_commit"], "--", "uruha_brain_mac.py", "uruha_web_ui.py"],
            cwd=ROOT,
            text=True,
        )
        self.assertEqual(changed.strip(), "")

    def test_disclaimed_pilot_self_reviews_are_archived_not_retained(self):
        pilot = [{"candidate_id": "candidate-1"}]
        strict = [
            {"id": "candidate-1", "human_review": {"reviewer_id": "jerry"}},
            {"id": "candidate-2", "human_review": {"reviewer_id": "expert"}},
        ]
        retained, archived = quarantine_v80.quarantine_rows(strict, pilot, reviewer_id="jerry")
        self.assertEqual([row["id"] for row in retained], ["candidate-2"])
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["original_row"], strict[0])
        self.assertEqual(len(archived[0]["original_row_sha256"]), 64)

    def test_quarantine_cannot_reclassify_failed_formal_integrity(self):
        quarantine_report = {
            "schema": "uruha_planner_self_review_quarantine_report_v80",
            "strict_rows_before": 12,
            "pilot_self_review_rows_quarantined": 12,
            "v80_formal_integrity_reclassified_as_pass": False,
        }
        self.assertEqual(
            analyze_v80.strict_human_rows_created_for_formal_run(0, quarantine_report),
            12,
        )

    def test_tracked_report_is_aggregate_only_when_present(self):
        if not REPORT_PATH.exists():
            self.skipTest("formal local run has not produced the aggregate report yet")
        payload = REPORT_PATH.read_text(encoding="utf-8")
        self.assertNotIn('"candidate_id"', payload)
        self.assertNotIn('"user_utterance"', payload)
        self.assertNotIn('"rationale"', payload)
        self.assertNotIn('"session_id"', payload)


if __name__ == "__main__":
    unittest.main()
