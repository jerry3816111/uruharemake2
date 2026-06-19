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

    def test_short_thanks_remains_inform_act(self):
        pred = self._predict("Thanks a lot.", ["Here are your passports."])
        self.assertEqual(pred["pred_act"], 1)

    def test_mixed_refund_utterance_keeps_question_act(self):
        pred = self._predict("Here I'll take taxi instead, how do you refund us?", ["I'm sorry to say no."])
        self.assertEqual(pred["pred_act"], 2)

    def test_service_command_maps_to_directive_act(self):
        pred = self._predict(
            "Yes, sir. I'll get them for you right away. Would you please sign this bill first?",
            ["Tomato or orange juice, please."],
        )
        self.assertEqual(pred["pred_act"], 3)

    def test_refusal_maps_to_commissive_act(self):
        pred = self._predict(
            "We can't. If we went that fast, we would break the speed limit.",
            ["That's fast!"],
        )
        self.assertEqual(pred["pred_act"], 4)

    def test_service_delivery_preface_remains_inform_act(self):
        pred = self._predict("OK. Here you are.", ["A draft beer please."])
        self.assertEqual(pred["pred_act"], 1)

    def test_polite_service_instruction_maps_to_directive_act(self):
        pred = self._predict(
            "Of course. Please wait a moment. I'll go and get it.",
            ["I'll have my bill, please."],
        )
        self.assertEqual(pred["pred_act"], 3)

    def test_inability_reply_maps_to_commissive_act(self):
        pred = self._predict("I can't find it now.", ["So, show me the note please."])
        self.assertEqual(pred["pred_act"], 4)

    def test_alternative_topic_proposal_maps_to_commissive_act(self):
        pred = self._predict("What about water pollution instead of pollution?", ["You should narrow down your topic."])
        self.assertEqual(pred["pred_act"], 4)

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

    def test_thanks_for_information_is_neutral_emotion(self):
        pred = self._predict("Thanks for letting me know.", ["I just wanted to give you the good news."])
        self.assertEqual(pred["pred_emotion"], 0)

    def test_enjoyment_statement_maps_to_happiness(self):
        pred = self._predict(
            "It is OK with me. I enjoy being busy and learning new things.",
            ["You will be busy."],
        )
        self.assertEqual(pred["pred_emotion"], 4)

    def test_unfair_jealous_statement_maps_to_sadness(self):
        pred = self._predict("I'm so jealous! It's so unfair!", ["A local man won the lottery."])
        self.assertEqual(pred["pred_emotion"], 5)

    def test_forgotten_birthday_maps_to_surprise(self):
        pred = self._predict("My birthday? I forgot it, thank you for remembering my birthday.", ["Happy birthday."])
        self.assertEqual(pred["pred_emotion"], 6)

    def test_not_worried_remains_neutral_emotion(self):
        pred = self._predict("Fine with me. I know the laws of the road. I'm not worried.", ["Drive carefully."])
        self.assertEqual(pred["pred_emotion"], 0)


if __name__ == "__main__":
    unittest.main()
