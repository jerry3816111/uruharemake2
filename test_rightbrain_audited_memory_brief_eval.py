import unittest

from eval_rightbrain_audited_memory_brief import build_report


class RightBrainAuditedMemoryBriefEvalTest(unittest.TestCase):
    def test_explicit_memory_cue_exists_only_with_audited_brief(self):
        report = build_report()
        explicit_rows = [
            row for row in report["cases"] if row["expected_policy"] == "explicit_allowed"
        ]

        self.assertGreaterEqual(len(explicit_rows), 2)
        self.assertTrue(all(row["explicit_anchor_present_with_brief"] for row in explicit_rows))
        self.assertFalse(any(row["explicit_anchor_present_without_brief"] for row in explicit_rows))
        self.assertEqual(report["summary"]["explicit_cue_available_with_brief_rate"], 1.0)
        self.assertEqual(report["summary"]["explicit_cue_available_without_brief_rate"], 0.0)

    def test_background_and_private_memory_do_not_become_surface_cues(self):
        report = build_report()
        background = next(row for row in report["cases"] if row["id"] == "background_family_pressure")
        private = next(row for row in report["cases"] if row["id"] == "private_do_not_mention")

        self.assertEqual(background["with_brief_policy"], "background_only")
        self.assertEqual(background["with_brief_allowed_cues"], [])
        self.assertTrue(background["with_brief_background_cues"])
        self.assertTrue(background["background_nonverbal_with_brief"])
        self.assertEqual(private["with_brief_policy"], "do_not_mention")
        self.assertEqual(private["with_brief_allowed_cues"], [])
        self.assertTrue(private["do_not_mention_blocks_cues"])

    def test_raw_memory_never_leaks_into_rightbrain_payload(self):
        report = build_report()

        self.assertEqual(report["summary"]["raw_memory_leak_rate"], 0.0)
        self.assertEqual(report["summary"]["schema_match_rate"], 1.0)
        self.assertTrue(all(not row["raw_memory_leak_hits"] for row in report["cases"]))

    def test_report_keeps_scope_as_contract_eval_not_naturalness_claim(self):
        report = build_report()

        self.assertIn("payload/contract evaluation", report["research_boundary"])
        self.assertEqual(
            report["controlled_variables"]["payload_builder"],
            "RightBrain._build_model_surface_payload",
        )
        self.assertEqual(report["summary"]["policy_match_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
