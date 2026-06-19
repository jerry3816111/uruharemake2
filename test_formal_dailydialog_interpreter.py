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


if __name__ == "__main__":
    unittest.main()
