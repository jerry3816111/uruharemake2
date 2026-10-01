import unittest

from longitudinal_human_model.realization import (
    DIRECT,
    ORACLE,
    PREDICTED,
    build_realization_packet,
    parse_classifier_reply,
)


LABELS = [
    "accept_support_and_continue",
    "acknowledge_then_continue",
    "ask_clarification",
    "defer_commitment",
    "direct_rejection",
    "pause_and_reassess",
]
EVENT = {
    "observable_text": "A requester repeats an unsafe request.",
    "actual_observed_behavior": "direct_rejection",
    "previous_state": {"caution": 0.8},
}
PREDICTION = {
    "selected_behavior": "ask_clarification",
    "probabilities": {
        "accept_support_and_continue": 0.02,
        "acknowledge_then_continue": 0.03,
        "ask_clarification": 0.7,
        "defer_commitment": 0.05,
        "direct_rejection": 0.15,
        "pause_and_reassess": 0.05,
    },
    "features": {"state.caution": 0.9},
}


class M10RealizationTests(unittest.TestCase):
    def test_predicted_authority_cannot_see_oracle_label(self):
        packet = build_realization_packet(
            condition=PREDICTED,
            event=EVENT,
            prediction=PREDICTION,
            labels=LABELS,
            persona_evidence_refs=["persona_dev_v1_002"],
        )
        authority = packet["behavior_authority"]
        self.assertEqual(authority["selected_behavior"], "ask_clarification")
        self.assertFalse(authority["future_information_used"])
        self.assertNotIn("actual_observed_behavior", packet)
        self.assertIn("behavior_authority", packet["style_evidence"]["must_not_override"])

    def test_direct_and_oracle_are_explicitly_separated(self):
        direct = build_realization_packet(
            condition=DIRECT,
            event=EVENT,
            prediction=PREDICTION,
            labels=LABELS,
            persona_evidence_refs=[],
        )
        oracle = build_realization_packet(
            condition=ORACLE,
            event=EVENT,
            prediction=PREDICTION,
            labels=LABELS,
            persona_evidence_refs=[],
        )
        self.assertFalse(direct["behavior_authority"]["available"])
        self.assertTrue(oracle["behavior_authority"]["future_information_used"])
        self.assertEqual(oracle["behavior_authority"]["selected_behavior"], "direct_rejection")

    def test_classifier_contract_normalizes_probabilities(self):
        decoded = parse_classifier_reply(
            '{"probabilities":{"accept_support_and_continue":0,"acknowledge_then_continue":0,'
            '"ask_clarification":2,"defer_commitment":0,"direct_rejection":0,'
            '"pause_and_reassess":0},"brief_evidence":"question"}',
            LABELS,
        )
        self.assertEqual(decoded["selected_behavior"], "ask_clarification")
        self.assertAlmostEqual(sum(decoded["probabilities"].values()), 1.0)


if __name__ == "__main__":
    unittest.main()
