import json
import subprocess
import unittest
from pathlib import Path

import planner_supervision_pilot_review_v79 as v79
import planner_supervision_session_review_v78 as v78
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v79_pilot_review_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v79_pilot_review.json"


FAMILIES = [
    "ordinary_direct",
    "emotional_support",
    "ambiguity_clarification",
    "memory_recall_update",
    "pragmatic_implicature",
    "relationship_personality",
    "reflection_repair",
]


def candidate(index, family, session):
    target = {"human_speech_plan": f"plan {index}", "reply_goal": f"goal {index}"}
    source = {"session_id": session, "turn_index": index, "logic": target}
    return {
        "id": f"candidate-{index:02d}",
        "scenario_family": family,
        "source_session_id": session,
        "source_turn_index": index,
        "input": {"language": "zh", "user_utterance": f"utterance {index}"},
        "source_record": source,
        "target_plan": target,
        "target_plan_sha256": v76.canonical_sha256(target),
        "provenance": {"source_sha256": v76.canonical_sha256(source)},
        "collection_checks": {
            "session_quarantine_applied": True,
            "evaluation_contaminated_session": False,
        },
    }


def manifest(candidates, certified_sessions=None):
    certified_sessions = set(certified_sessions or {row["source_session_id"] for row in candidates})
    rows = []
    for unit in v78.build_session_review_units(candidates):
        if unit["source_session_id"] not in certified_sessions:
            continue
        rows.append(
            {
                "session_id": unit["source_session_id"],
                "decision": "certify_nonbenchmark",
                "benchmark_origin": "none",
                "consent_to_training": True,
                "candidate_set_sha256": unit["candidate_set_sha256"],
                "session_summary_sha256": unit["session_summary_sha256"],
            }
        )
    return rows


class PilotSelectionTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            candidate(index, FAMILIES[index % len(FAMILIES)], f"session-{index % 6}")
            for index in range(24)
        ]
        self.manifest = manifest(self.candidates)

    def test_pilot_is_deterministic_and_covers_families_and_sessions(self):
        eligible_a, units_a = v79.select_pilot(self.candidates, self.manifest, budget=12, seed="fixed")
        eligible_b, units_b = v79.select_pilot(self.candidates, self.manifest, budget=12, seed="fixed")
        self.assertEqual(units_a, units_b)
        self.assertEqual(len(eligible_a), 24)
        self.assertEqual(len(units_a), 12)
        self.assertEqual({unit["scenario_family"] for unit in units_a}, set(FAMILIES))
        candidate_map = {row["id"]: row for row in self.candidates}
        self.assertEqual(
            {candidate_map[unit["candidate_id"]]["source_session_id"] for unit in units_a},
            {f"session-{index}" for index in range(6)},
        )

    def test_uncertified_sessions_are_excluded(self):
        eligible, units = v79.select_pilot(
            self.candidates,
            manifest(self.candidates, {"session-0", "session-1", "session-2"}),
            budget=12,
            seed="fixed",
        )
        self.assertEqual({row["source_session_id"] for row in eligible}, {"session-0", "session-1", "session-2"})
        self.assertTrue(all(unit["candidate_id"] in {row["id"] for row in eligible} for unit in units))

    def test_tampered_candidate_is_rejected(self):
        self.candidates[0]["target_plan"]["reply_goal"] = "tampered"
        with self.assertRaisesRegex(ValueError, "unbound"):
            v79.select_pilot(self.candidates, self.manifest, budget=12, seed="fixed")

    def test_stale_session_manifest_is_rejected(self):
        self.manifest[0]["candidate_set_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not bind"):
            v79.select_pilot(self.candidates, self.manifest, budget=12, seed="fixed")

    def test_budget_must_cover_all_strata(self):
        with self.assertRaisesRegex(ValueError, "cannot cover"):
            v79.select_pilot(self.candidates, self.manifest, budget=5, seed="fixed")

    def test_pilot_units_do_not_contain_raw_dialogue_or_session_ids(self):
        _eligible, units = v79.select_pilot(self.candidates, self.manifest, budget=12, seed="fixed")
        payload = json.dumps(units)
        self.assertNotIn("session-", payload)
        self.assertNotIn("user_utterance", payload)
        self.assertNotIn("source_record", payload)

    def test_status_counts_only_selected_human_decisions(self):
        _eligible, units = v79.select_pilot(self.candidates, self.manifest, budget=12, seed="fixed")
        first, second = units[0]["candidate_id"], units[1]["candidate_id"]
        status = v79.pilot_status(
            units,
            [
                {"candidate_id": first, "decision": "accept"},
                {"candidate_id": second, "decision": "reject"},
                {"candidate_id": "outside", "decision": "accept"},
            ],
            [{"id": first}, {"id": "outside"}],
        )
        self.assertEqual(status["reviewed_count"], 2)
        self.assertEqual(status["accepted_count"], 1)
        self.assertEqual(status["rejected_count"], 1)
        self.assertEqual(status["pending_count"], 10)
        self.assertEqual(status["training_rows_created"], 1)

    def test_tracked_report_contains_only_aggregate_private_evidence(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        payload = REPORT_PATH.read_text(encoding="utf-8")
        self.assertTrue(report["construction_gates"]["passed"])
        self.assertNotIn('"candidate_id"', payload)
        self.assertNotIn('"session_id"', payload)
        self.assertNotIn('"user_utterance"', payload)
        self.assertNotIn('"recent_dialogue"', payload)

    def test_runtime_does_not_contain_v79_experiment_code(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        changed = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                contract["parent_commit"],
                "--",
                "uruha_brain_mac.py",
                "uruha_web_ui.py",
            ],
            cwd=ROOT,
            text=True,
        )
        self.assertEqual(changed.strip(), "")


if __name__ == "__main__":
    unittest.main()
