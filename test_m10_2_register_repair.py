import unittest

from longitudinal_human_model.register_repair import build_register_repair_packet, render_register_repair_prompt


class M102RegisterRepairTests(unittest.TestCase):
    def test_repair_packet_preserves_behavior_and_limits_change(self):
        packet = build_register_repair_packet(
            event_context="A friend offers help.",
            relationship_context="familiar_friend",
            authoritative_behavior="accept_support_and_continue",
            original_utterance="ありがとうございます、そのまま続けます。",
            persona_evidence_refs=["persona_dev_v1_002"],
        )
        self.assertEqual(packet["authoritative_behavior"], "accept_support_and_continue")
        self.assertIn("affirmation_or_rejection_polarity", packet["must_preserve"])
        self.assertEqual(packet["allowed_change"], "casual Japanese register and surface naturalness only")
        prompt = render_register_repair_prompt(packet)
        self.assertIn("表面だけ", prompt)
        self.assertIn("ありがとうございます", prompt)


if __name__ == "__main__":
    unittest.main()
