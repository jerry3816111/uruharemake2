import unittest

import diagnose_rightbrain_memory_surface_v86 as diagnosis
import rightbrain_memory_surface_v86 as v86


class RightBrainMemorySurfaceV86DiagnosisTests(unittest.TestCase):
    def test_stale_recent_opening_conflict_requires_direct_semantic_overlap(self):
        packet = {"outcome_contract": {"required_semantic_groups": [["何を言っているの"]]} }
        candidate = {
            "target_plan": {
                "core_message_jp": "何を言っているのか聞き返す。",
                "must_avoid": ["何を言ってい", "そうなんだ", "私"],
                "human_speech_plan": {
                    "content_units": ["何を言っているのか聞く"],
                    "grounding_terms": [],
                    "forbidden_repetition": {"recent_openings": ["何を言ってい"]},
                },
            }
        }
        self.assertEqual(diagnosis.stale_opening_conflicts(packet, candidate), ["何を言ってい"])

    def test_diagnosis_explains_only_matching_forbidden_violations(self):
        packets = [
            {
                "candidate_id": "case-a",
                "outcome_contract": {"required_semantic_groups": [["回復する"]]},
            }
        ]
        candidates = [
            {
                "id": "case-a",
                "target_plan": {
                    "core_message_jp": "今は回復する。",
                    "must_avoid": ["今は回復する"],
                    "human_speech_plan": {
                        "content_units": [],
                        "grounding_terms": [],
                        "forbidden_repetition": {"recent_openings": ["今は回復する"]},
                    },
                },
            }
        ]
        rows = [
            {
                "candidate_id": "case-a",
                "condition": v86.T2,
                "raw_reply": "今は回復するね。",
                "score": {"forbidden_violation": True},
            }
        ]
        report = diagnosis.diagnose(packets, rows, candidates)
        self.assertTrue(report["mechanism_supported"])
        self.assertEqual(report["conflict_explained_violation_count_by_condition"][v86.T2], 1)


if __name__ == "__main__":
    unittest.main()
