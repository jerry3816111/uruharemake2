import unittest

import uruha_brain_mac as ubm
import uruha_memory_runtime as umr


def memory_item(text, score=0.9, trace_id="stored:episode:example-1", source="episode"):
    return {
        "source": source,
        "collection_name": source,
        "memory_id": trace_id.rsplit(":", 1)[-1],
        "trace_id": trace_id,
        "text": text,
        "score": score,
    }


def memory_data(*items):
    return {
        "working_memory_items": list(items),
        "profile_structured": {},
        "recent_turns": [],
        "memory_provenance": {
            "passed_to_leftbrain": [
                umr.memory_trace_row(item, channel="selected_working_memory")
                for item in items
            ]
        },
    }


class HighConfidenceMemoryRecallV1Tests(unittest.TestCase):
    def setUp(self):
        self.left = ubm.LeftBrain(client_logic=None)
        self.psyche = {"mood": 0, "trust": 50}

    def test_selects_one_clear_explicit_recall_record(self):
        selected = memory_item("前に青い鉢の観葉植物をアオバと呼ぶと決めた。", 0.91)
        irrelevant = memory_item(
            "昨日は玄関の傘を一本片づけた。",
            0.39,
            "stored:episode:example-2",
        )

        decision = umr.select_high_confidence_recall_item(
            "前に話した観葉植物の呼び名、覚えてる？",
            memory_data(selected, irrelevant),
        )

        self.assertTrue(decision["selected"])
        self.assertEqual(decision["trace_id"], selected["trace_id"])
        self.assertAlmostEqual(decision["margin"], 0.52)

    def test_non_recall_input_never_activates(self):
        decision = umr.select_high_confidence_recall_item(
            "今日は観葉植物に水をあげた。",
            memory_data(memory_item("観葉植物をアオバと呼ぶ。")),
        )
        self.assertEqual(decision["status"], "not_requested")
        self.assertFalse(decision["selected"])

    def test_close_candidates_are_ambiguous(self):
        decision = umr.select_high_confidence_recall_item(
            "前に決めた待ち合わせ場所、どこだっけ？",
            memory_data(
                memory_item("待ち合わせは北口にすると言った。", 0.83),
                memory_item("待ち合わせは東口にすると言った。", 0.76, "stored:episode:example-2"),
            ),
        )
        self.assertEqual(decision["status"], "ambiguous")
        self.assertFalse(decision["selected"])

    def test_sensitive_memory_is_suppressed(self):
        decision = umr.select_high_confidence_recall_item(
            "前に話したパスワード、覚えてる？",
            memory_data(memory_item("パスワードはsample-secretだと言った。")),
        )
        self.assertEqual(decision["status"], "suppressed")
        self.assertFalse(decision["selected"])
        self.assertEqual(decision["speakability"]["reason"], "sensitive_memory")

    def test_broad_presence_probe_keeps_existing_dialogue_path(self):
        for user_input in ("うちのこと覚えてる？", "覚えてる？"):
            with self.subTest(user_input=user_input):
                decision = umr.select_high_confidence_recall_item(
                    user_input,
                    memory_data(memory_item("前に青い帽子を買ったと言った。")),
                )
                self.assertEqual(decision["status"], "presence_only")
                self.assertFalse(decision["selected"])

    def test_presence_phrase_does_not_match_remember_meeting_prefix(self):
        decision = umr.select_high_confidence_recall_item(
            "Do you remember meeting at the north gate?",
            memory_data(memory_item("We met at the north gate.")),
        )
        self.assertEqual(decision["status"], "selected")
        self.assertTrue(decision["selected"])

    def test_rule_plan_uses_selected_record_without_case_specific_logic(self):
        selected = memory_item("前に白い陶器の鳥をシロと呼ぶと決めた。", 0.92)
        irrelevant = memory_item(
            "朝に赤い封筒を机へ置いた。",
            0.31,
            "stored:episode:example-2",
        )

        plan = self.left._rule_based_plan(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            self.psyche,
            memory_data(selected, irrelevant),
        )

        self.assertEqual(plan["planner_path"], "high_confidence_memory_recall_v1")
        self.assertEqual(plan["hidden_intent"], "memory_probe")
        self.assertIn("シロ", plan["core_message_jp"])
        self.assertEqual(
            plan["memory_recall_contract"]["trace_id"],
            selected["trace_id"],
        )

    def test_memory_anchor_supports_non_person_named_entity(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        selected = memory_item("前に白い陶器の鳥をシロと呼ぶと決めた。", 0.92)

        anchor = brain._extract_actionable_memory_anchor(
            "前に話した陶器の鳥の名前、覚えてる？",
            memory_data(selected),
        )

        self.assertEqual(anchor["kind"], "context")
        self.assertEqual(anchor["trace_id"], selected["trace_id"])
        self.assertTrue(anchor["expected"])

    def test_normalization_preserves_auditable_recall_contract(self):
        selected = memory_item("前に白い陶器の鳥をシロと呼ぶと決めた。", 0.92)
        raw = self.left._rule_based_plan(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            self.psyche,
            memory_data(selected),
        )

        normalized = self.left._normalize_plan(raw)

        self.assertEqual(normalized["planner_path"], "high_confidence_memory_recall_v1")
        self.assertEqual(
            normalized["memory_recall_contract"]["trace_id"],
            selected["trace_id"],
        )

    def test_leftbrain_think_completes_without_model_client(self):
        selected = memory_item("前に白い陶器の鳥をシロと呼ぶと決めた。", 0.92)

        plan = self.left.think(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            memory_data(selected),
            self.psyche,
        )

        self.assertEqual(plan["planner_path"], "high_confidence_memory_recall_v1")
        self.assertEqual(plan["memory_recall_contract"]["trace_id"], selected["trace_id"])


if __name__ == "__main__":
    unittest.main()
