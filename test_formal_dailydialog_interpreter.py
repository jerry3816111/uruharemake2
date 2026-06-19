import unittest

from run_formal_brain_benchmarks import predict_dailydialog_official_labels


class TestFormalDailyDialogInterpreter(unittest.TestCase):
    def _predict(self, utterance, context=None):
        item = {
            "id": "unit",
            "utterances": [*(context or []), utterance],
            "gold_reply": utterance,
        }
        return predict_dailydialog_official_labels(item)

    def test_question_target_maps_to_question(self):
        pred = self._predict("What time is the meeting?", ["Hello."])
        self.assertEqual(pred["pred_act"], 2)
        self.assertEqual(pred["labeler"], "official_utterance_interpreter_v3_v2")

    def test_imperative_target_maps_to_directive(self):
        pred = self._predict("Please wait here.", ["I am lost."])
        self.assertEqual(pred["pred_act"], 3)

    def test_accepting_future_action_maps_to_commissive(self):
        pred = self._predict("Sure, I will help you.", ["Can you help me?"])
        self.assertEqual(pred["pred_act"], 4)

    def test_plain_social_reply_remains_inform(self):
        pred = self._predict("You are welcome.", ["Thanks."])
        self.assertEqual(pred["pred_act"], 1)

    def test_short_incredulous_question_maps_to_surprise(self):
        pred = self._predict("Really? I will slow down then.", ["You are driving too fast."])
        self.assertEqual(pred["pred_emotion"], 6)

    def test_direct_rebuke_maps_to_anger(self):
        pred = self._predict("Get out of my store, you jerk!", ["Can I return this?"])
        self.assertEqual(pred["pred_emotion"], 1)

    def test_plain_thanks_remains_neutral_emotion(self):
        pred = self._predict("Thank you.", ["Here is your receipt."])
        self.assertEqual(pred["pred_emotion"], 0)

    def test_caretaking_positive_reply_maps_to_happiness(self):
        pred = self._predict(
            "Ok. Don't forget to bring your umbrella. The rain can start up again anytime.",
            ["I will go out now."],
        )
        self.assertEqual(pred["pred_emotion"], 4)


if __name__ == "__main__":
    unittest.main()
