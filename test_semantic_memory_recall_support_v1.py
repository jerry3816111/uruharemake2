import unittest

import uruha_brain_mac as ubm
import uruha_memory_runtime as umr
from test_high_confidence_memory_recall_v1 import memory_data, memory_item


class SemanticMemoryRecallSupportV1Tests(unittest.TestCase):
    def setUp(self):
        self.left = ubm.LeftBrain(client_logic=None)
        self.psyche = {"mood": 0, "trust": 50}

    def test_japanese_focus_support_ignores_higher_scored_irrelevant_memory(self):
        target = memory_item("陶器の鳥の呼び名はシロに決めた。", 0.82)
        irrelevant = memory_item(
            "玄関の傘を片づけた。",
            0.97,
            "stored:episode:irrelevant",
        )

        decision = umr.select_high_confidence_recall_item(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            memory_data(target, irrelevant, experimental=True),
        )

        self.assertTrue(decision["selected"])
        self.assertEqual(decision["trace_id"], target["trace_id"])
        self.assertEqual(decision["supported_candidate_count"], 1)
        self.assertIn("陶器", decision["shared_focus_units"])

    def test_target_removed_irrelevant_memory_is_unsupported(self):
        irrelevant = memory_item("玄関の傘を片づけた。", 0.99)

        decision = umr.select_high_confidence_recall_item(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            memory_data(irrelevant, experimental=True),
        )

        self.assertEqual(decision["status"], "unsupported")
        self.assertFalse(decision["selected"])
        self.assertEqual(decision["supported_candidate_count"], 0)

    def test_two_supported_close_candidates_remain_ambiguous(self):
        decision = umr.select_high_confidence_recall_item(
            "前に決めた待ち合わせ場所、どこだっけ？",
            memory_data(
                memory_item("待ち合わせ場所は北口に決めた。", 0.83),
                memory_item("待ち合わせ場所は東口に決めた。", 0.76, "stored:episode:east"),
            ),
        )

        self.assertEqual(decision["status"], "ambiguous")
        self.assertEqual(decision["supported_candidate_count"], 2)

    def test_chinese_explicit_recall_has_auditable_support(self):
        decision = umr.select_high_confidence_recall_item(
            "你還記得我們約好的集合地點嗎？",
            memory_data(memory_item("我們約好在南門集合。", 0.91)),
        )

        self.assertTrue(decision["selected"])
        self.assertGreaterEqual(decision["shared_focus_unit_count"], 1)

    def test_english_explicit_recall_has_auditable_support(self):
        decision = umr.select_high_confidence_recall_item(
            "Do you remember meeting at the north gate?",
            memory_data(memory_item("We met at the north gate.", 0.91)),
        )

        self.assertTrue(decision["selected"])
        self.assertEqual(set(decision["shared_focus_units"]), {"gate", "north"})

    def test_plan_preserves_support_evidence(self):
        target = memory_item("陶器の鳥の呼び名はシロに決めた。", 0.91)
        payload = memory_data(target, experimental=True)

        plan = self.left._rule_based_plan(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            self.psyche,
            payload,
        )

        contract = plan["memory_recall_contract"]
        self.assertEqual(contract["support_schema"], "uruha_memory_query_support_v1")
        self.assertGreaterEqual(contract["shared_focus_unit_count"], 1)
        self.assertEqual(
            payload["experimental_memory_recall_selection_trace_v1"]["status"],
            "selected",
        )

    def test_actionable_anchor_refuses_unsupported_only_memory(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        brain.psyche = type("Psyche", (), {"get_state": lambda self: {"trust": 50}})()
        payload = memory_data(
            memory_item("玄関の傘を片づけた。", 0.99),
            experimental=True,
        )

        anchor = brain._extract_actionable_memory_anchor(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            payload,
        )

        self.assertEqual(anchor, {})

    def test_disabled_experiment_preserves_existing_anchor_behavior(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        payload = memory_data(memory_item("玄関の傘を片づけた。", 0.99))

        anchor = brain._extract_actionable_memory_anchor(
            "前に話した陶器の鳥の呼び名、覚えてる？",
            payload,
        )

        self.assertEqual(anchor["kind"], "context")
        self.assertTrue(anchor["expected"])


if __name__ == "__main__":
    unittest.main()
