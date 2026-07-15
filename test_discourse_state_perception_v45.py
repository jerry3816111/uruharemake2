#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from discourse_state_perception_v45 import detect_focus_discourse_signals


class DiscourseStatePerceptionV45Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = json.loads(
            Path("configs/discourse_state_perception_v45_preregistration.json").read_text(
                encoding="utf-8"
            )
        )
        cls.patterns = config["deterministic_discourse_signals"]["patterns"]

    def _candidate(self, text, anchor_text):
        start = text.index(anchor_text)
        return {
            "anchors": [
                {"text": anchor_text, "start": start, "end": start + len(anchor_text)}
            ]
        }

    def _types(self, text, anchor_text):
        rows = detect_focus_discourse_signals(
            text, self._candidate(text, anchor_text), self.patterns
        )
        return {row["signal_type"] for row in rows[0]["signals"]}

    def test_detects_cessation_pending_hypothesis_and_withdrawal(self):
        self.assertIn(
            "ongoing_action_cessation",
            self._types("今は手を振るのをやめて。", "手を振"),
        )
        pending = self._types("手を振るかは、もう少し後で決める。", "手を振")
        self.assertIn("pending_choice", pending)
        self.assertNotIn("conditional_hypothesis", pending)
        hypothetical = self._types("もし笑顔だったら話しやすい。", "笑顔")
        self.assertIn("conditional_hypothesis", hypothetical)
        withdrawal = self._types("うなずいて。いや、その頼みは取り消し。", "うなず")
        self.assertNotIn("referential_request_withdrawal", withdrawal)
        same_sentence = self._types("うなずいて、いや、その頼みは取り消し。", "うなず")
        self.assertIn("referential_request_withdrawal", same_sentence)

    def test_cessation_does_not_cross_a_sentence_boundary(self):
        types = self._types("手を振る話をした。別の作業はやめて。", "手を振")
        self.assertNotIn("ongoing_action_cessation", types)


if __name__ == "__main__":
    unittest.main()
