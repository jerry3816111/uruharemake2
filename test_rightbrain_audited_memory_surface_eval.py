import unittest

from eval_rightbrain_audited_memory_surface import _has_bad_language, build_report


class RightBrainAuditedMemorySurfaceEvalTest(unittest.TestCase):
    def test_final_reply_keeps_explicit_audited_memory_anchor(self):
        report = build_report()
        explicit_rows = [
            row for row in report["cases"] if row["explicit_anchor_required"]
        ]

        self.assertGreaterEqual(len(explicit_rows), 2)
        self.assertTrue(all(row["explicit_anchor_success"] for row in explicit_rows))
        self.assertEqual(report["summary"]["explicit_anchor_success_rate"], 1.0)

    def test_background_and_private_memory_stay_hidden_in_final_reply(self):
        report = build_report()
        protected_rows = [
            row for row in report["cases"]
            if row["expected_policy"] in {"background_only", "do_not_mention"}
        ]

        self.assertTrue(protected_rows)
        self.assertTrue(all(row["background_or_private_safe"] for row in protected_rows))
        self.assertEqual(report["summary"]["background_private_safety_rate"], 1.0)

    def test_final_reply_has_no_raw_memory_or_unrelated_settings_template(self):
        report = build_report()

        self.assertEqual(report["summary"]["forbidden_surface_leak_rate"], 0.0)
        self.assertEqual(report["summary"]["unrelated_settings_template_rate"], 0.0)
        self.assertEqual(report["summary"]["generic_template_hit_rate"], 0.0)
        self.assertEqual(report["summary"]["normalized_duplicate_reply_rate"], 0.0)
        self.assertTrue(all(row["language_clean"] for row in report["cases"]))

    def test_surface_quality_holdout_hits_required_markers(self):
        report = build_report()
        quality_rows = [
            row for row in report["cases"] if row["expected_policy"] == "surface_quality"
        ]

        self.assertGreaterEqual(len(quality_rows), 6)
        self.assertEqual(report["summary"]["required_marker_success_rate"], 1.0)
        self.assertTrue(all(row["required_marker_success"] for row in quality_rows))

    def test_report_scope_is_final_surface_not_payload_only(self):
        report = build_report()

        self.assertIn("RightBrain.speak", report["controlled_variables"]["surface_runtime"])
        self.assertIn("final-surface", report["research_boundary"])
        self.assertGreater(report["summary"]["surface_quality_case_count"], 0)

    def test_external_quality_rejects_actual_model_pollution(self):
        self.assertTrue(_has_bad_language("今日は无理しないで休め。"))
        self.assertTrue(_has_bad_language("今日は範�だけ決める。"))
        self.assertTrue(_has_bad_language("今日はBODY CHEMISTRYを見る。"))
        self.assertFalse(_has_bad_language("今日は無理しないで休め。"))


if __name__ == "__main__":
    unittest.main()
