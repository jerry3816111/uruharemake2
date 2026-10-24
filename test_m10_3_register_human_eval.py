import copy
import unittest

import m10_3_register_human_eval as human_eval


class M103RegisterHumanEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = human_eval.load_json(human_eval.DEFAULT_PACKET)
        cls.key = human_eval.load_json(human_eval.DEFAULT_KEY)
        cls.prereg = human_eval.load_json(human_eval.DEFAULT_PREREG)

    def _ratings(self, rater_count):
        key_map = {row["item_id"]: row["mapping"] for row in self.key["items"]}
        rows = []
        for rater_index in range(rater_count):
            rater_hash = human_eval.pseudonymize_rater_id(f"human-{rater_index}")
            for item in self.packet["items"]:
                mapping = key_map[item["item_id"]]
                s1 = "A" if mapping["A"] == "S1_REGISTER_REPAIR" else "B"
                s0 = "B" if s1 == "A" else "A"
                scores = {
                    dimension: {"A": 5, "B": 5}
                    for dimension in human_eval.DIMENSIONS
                }
                scores["natural_casual_japanese"][s0] = 3
                scores["natural_casual_japanese"][s1] = 5
                changed = item["candidates"]["A"] != item["candidates"]["B"]
                rows.append(
                    {
                        "schema": "m10_3_register_rating_v1",
                        "rater_id_hash": rater_hash,
                        "independent_human_attestation": True,
                        "key_unseen_attestation": True,
                        "packet_sha256": human_eval.PACKET_SHA256,
                        "item_id": item["item_id"],
                        "scores": scores,
                        "preference": s1 if changed else "tie",
                        "notes": "",
                    }
                )
        return rows

    def test_locked_packet_preregistration_and_key_are_intact(self):
        self.assertTrue(human_eval.validate_locked_artifacts()["passed"])

    def test_fewer_than_three_complete_raters_cannot_authorize_claim(self):
        result = human_eval.analyze(
            self.packet, self.key, self._ratings(1), self.prereg
        )
        self.assertEqual(result["status"], "pilot_or_collection_incomplete")
        self.assertFalse(result["claim_authorized"])
        self.assertFalse(result["gates"]["minimum_complete_independent_raters"])

    def test_three_consistent_complete_raters_pass_synthetic_contract(self):
        result = human_eval.analyze(
            self.packet, self.key, self._ratings(3), self.prereg
        )
        self.assertEqual(result["status"], "formal_human_result")
        self.assertTrue(result["claim_authorized"])
        self.assertEqual(result["validation"]["complete_rater_count"], 3)
        self.assertEqual(
            result["reliability"]["overall_mean_pairwise_quadratic_weighted_kappa"],
            1.0,
        )
        self.assertGreaterEqual(
            result["dimension_deltas_s1_minus_s0"]["natural_casual_japanese"][
                "mean_delta_s1_minus_s0"
            ],
            0.5,
        )
        self.assertEqual(result["required_case_reports"][0]["case_id"], "R-JA-06")

    def test_raw_rater_identity_and_unattested_rows_fail_closed(self):
        ratings = self._ratings(1)
        bad = copy.deepcopy(ratings[0])
        bad["rater_id"] = "real name"
        bad["key_unseen_attestation"] = False
        validation = human_eval.validate_ratings(
            self.packet, self.key, [bad], minimum_raters=3
        )
        self.assertFalse(validation["instrument_valid"])
        self.assertTrue(any("raw_rater_id_forbidden" in row for row in validation["errors"]))
        self.assertTrue(any("key_unseen_attestation" in row for row in validation["errors"]))

    def test_partial_rater_is_reported_but_not_analyzed_as_complete(self):
        ratings = self._ratings(1)[:-1]
        result = human_eval.analyze(self.packet, self.key, ratings, self.prereg)
        self.assertEqual(result["validation"]["complete_rater_count"], 0)
        self.assertEqual(len(result["validation"]["incomplete_raters"]), 1)
        self.assertIsNone(
            result["dimension_deltas_s1_minus_s0"]["natural_casual_japanese"][
                "mean_delta_s1_minus_s0"
            ]
        )


if __name__ == "__main__":
    unittest.main()
