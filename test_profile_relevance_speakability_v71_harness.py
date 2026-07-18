import inspect
import json
import unittest
from pathlib import Path

import analyze_profile_relevance_speakability_v71 as analyzer
import run_profile_relevance_speakability_v71 as runner
from uruha_brain_mac import LeftBrain, RightBrain
from uruha_profile_relevance import MultilingualProfileSelector


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_relevance_speakability_v71_preregistration.json"


class ProfileRelevanceSpeakabilityV71HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selector = MultilingualProfileSelector()
        cls.candidates = [
            {
                "memory_id": "dev_drink",
                "metadata": {
                    "fact_type": "like",
                    "value": "抹茶ラテ",
                    "source_utterance": "飲み物なら抹茶ラテが好き。",
                },
            },
            {
                "memory_id": "dev_hobby",
                "metadata": {
                    "fact_type": "like",
                    "value": "陶芸",
                    "source_utterance": "休日の趣味なら陶芸が好き。",
                },
            },
            {
                "memory_id": "dev_name",
                "metadata": {
                    "fact_type": "name",
                    "value": "ユウト",
                    "source_utterance": "ユウトって呼んで。",
                },
            },
        ]

    def test_selector_retrieves_supported_fact_and_suppresses_ordinary_chat(self):
        recalled = self.selector.select(
            "前に好きだと言った飲み物、何だった？",
            self.candidates,
            include_provenance=True,
        )
        self.assertEqual(recalled["contract"]["status"], "selected")
        self.assertEqual(recalled["contract"]["selected_memory_ids"], ["dev_drink"])
        ordinary = self.selector.select(
            "今日は疲れたから少し雑談したい。",
            self.candidates,
            include_provenance=True,
        )
        self.assertEqual(ordinary["contract"]["status"], "not_requested")
        self.assertEqual(ordinary["contract"]["selected_memory_ids"], [])

    def test_selector_abstains_when_requested_fact_is_unavailable(self):
        result = self.selector.select(
            "子どもの頃に住んでた町を前に教えたっけ？",
            self.candidates,
            include_provenance=True,
        )
        self.assertEqual(result["contract"]["status"], "requested_but_unavailable")
        self.assertFalse(result["contract"]["answer_use_authorized"])

    def test_selector_rejects_ambiguous_top_candidates(self):
        candidates = [
            {
                "memory_id": memory_id,
                "metadata": {
                    "fact_type": "like",
                    "value": "紅茶",
                    "source_utterance": "飲み物なら紅茶が好き。",
                },
            }
            for memory_id in ("same_a", "same_b")
        ]
        result = self.selector.select(
            "前に好きだと言った飲み物は何？",
            candidates,
            include_provenance=True,
        )
        self.assertEqual(result["contract"]["status"], "requested_but_ambiguous")
        self.assertEqual(result["contract"]["selected_memory_ids"], [])

    def test_provenance_changes_only_the_candidate_key(self):
        bare = self.selector.candidate_key(self.candidates[0], include_provenance=False)
        enriched = self.selector.candidate_key(self.candidates[0], include_provenance=True)
        self.assertNotIn("以前の発言", bare)
        self.assertEqual(enriched, f"{bare}。以前の発言: 飲み物なら抹茶ラテが好き。")

    def test_unknown_contract_changes_only_explicit_shadow_turns(self):
        left = LeftBrain(None)
        psyche = {"mood": 0, "trust": 50}
        ordinary = left._rule_based_plan("おはよう", psyche, {})
        inert = left._rule_based_plan(
            "おはよう",
            psyche,
            {"profile_memory_selection": {"status": "not_requested"}},
        )
        self.assertEqual(ordinary["intent"], inert["intent"])
        unknown = left._rule_based_plan(
            "前に靴のサイズを教えたっけ？",
            psyche,
            {"profile_memory_selection": {"status": "requested_but_unavailable"}},
        )
        self.assertEqual(unknown["intent"], "memory_unknown")
        right = RightBrain(load_model=False)
        reply = right._template_reply(unknown, "前に靴のサイズを教えたっけ？", psyche, {})
        self.assertTrue(any(marker in reply for marker in ("覚えてない", "聞いてない", "記憶にない")))

    def test_runner_has_no_expected_access_and_selector_has_no_holdout_literals(self):
        self.assertNotIn("expected", inspect.getsource(runner.run_case))
        self.assertNotIn("expected", inspect.getsource(runner._select))
        source = (ROOT / "uruha_profile_relevance.py").read_text(encoding="utf-8")
        runtime = (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
        dataset = json.loads(
            (ROOT / "datasets/profile_relevance_speakability_v71.json").read_text(encoding="utf-8")
        )
        for case in dataset["cases"]:
            self.assertNotIn(case["id"], source)
            self.assertNotIn(case["id"], runtime)
            for row in case["profile_history"]:
                self.assertNotIn(row["value"], source)
                self.assertNotIn(row["value"], runtime)

    def test_analyzer_separates_selector_and_final_answer_failures(self):
        cases = []
        rows = []
        for index in range(24):
            relevant = index < 16
            abstention = 16 <= index < 20
            expected_ids = [f"memory_{index}"] if relevant else []
            required = [[f"answer_{index}"]] if relevant else ([['覚えてない']] if abstention else [])
            forbidden = [f"intrusion_{index}"] if not relevant else []
            cases.append(
                {
                    "id": f"case_{index}",
                    "scenario_family": "synthetic",
                    "expected": {
                        "selected_memory_ids": expected_ids,
                        "required_marker_groups": required,
                        "forbidden_terms": forbidden,
                        "memory_relevant": relevant,
                        "abstention_required": abstention,
                    },
                }
            )
            for condition in runner.CONDITIONS:
                treatment = condition == runner.CONDITIONS[2]
                reply = (f"answer_{index}" if relevant else "覚えてない" if abstention else "普通の返事") if treatment else "失敗"
                rows.append(
                    {
                        "case_id": f"case_{index}",
                        "condition": condition,
                        "reply": reply,
                        "selected_memory_ids": expected_ids if treatment else [],
                        "surface_gate_pass": True,
                        "selection_contract": {"selector_seconds": 0.01, "status": "selected"},
                        "turn_seconds": 1.0,
                        "temporary_database": True,
                    }
                )
        raw = {
            "row_count": 72,
            "conditions": list(runner.CONDITIONS),
            "gold_in_raw": False,
            "locked_preflight": {"passed": True, "observed_test_count": 12, "expected_test_count": 12},
            "rightbrain_model_loading": False,
            "selector_call_count": 48,
            "encoder_load_seconds": 0.5,
            "encoder_peak_rss_delta_bytes": 500_000_000,
            "transport_error_count": 0,
            "production_database_access_count": 0,
            "physical_action_count": 0,
            "rows": rows,
        }
        prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
        report = analyzer.analyze(raw, {"cases": cases}, prereg)
        self.assertTrue(report["selector_gates"]["passed"])
        self.assertTrue(report["ability_gates"]["passed"])
        self.assertEqual(report["decision"], "authorize_answer_path_shadow_only")

if __name__ == "__main__":
    unittest.main()
