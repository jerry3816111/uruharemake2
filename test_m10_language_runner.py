import json
import unittest
from pathlib import Path

import run_m10_behavior_authoritative_language as m10


ROOT = Path(__file__).resolve().parent


REPLIES = {
    "accept_support_and_continue": "助かる、そのまま続けるわ。",
    "acknowledge_then_continue": "分かった、そのまま続けるわ。",
    "ask_clarification": "そこ、どっちの意味かだけ教えて。",
    "defer_commitment": "今は決めず、確認してから返すわ。",
    "direct_rejection": "それは無理、出さない。",
    "pause_and_reassess": "一回止めて、見直してからやるわ。",
}


class FakeProvider:
    def __call__(self, *, model, prompt, options):
        if "Classify only the observable dialogue act" in prompt:
            selected = "acknowledge_then_continue"
            for label, reply in REPLIES.items():
                if reply in prompt:
                    selected = label
                    break
            probabilities = {label: float(label == selected) for label in REPLIES}
            text = json.dumps({"probabilities": probabilities, "brief_evidence": "fake"})
        elif int(options.get("num_predict", 0)) == 1:
            text = "。"
        else:
            selected = None
            for label in REPLIES:
                if f'"selected_behavior":"{label}"' in prompt:
                    selected = label
                    break
            text = REPLIES[selected or "acknowledge_then_continue"]
        return {
            "text": text,
            "latency_seconds": 0.01,
            "prompt_tokens": 128,
            "completion_tokens": 8,
            "total_duration_ns": 1,
            "model_reported": model,
        }


class M10RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads((ROOT / "datasets/m9_second_person_mira_synthetic_fixture_v1.json").read_text())
        cls.result = json.loads((ROOT / "analysis/m9_1_second_person_transfer_summary_alias_result.json").read_text())
        cls.persona = json.loads((ROOT / "datasets/public_persona_evidence_v1.json").read_text())
        cls.persona_lock = json.loads((ROOT / "configs/public_persona_evidence_v1_result_lock.json").read_text())
        cls.config = json.loads((ROOT / "configs/m10_behavior_authoritative_language_preregistration.json").read_text())

    def test_fake_provider_runs_all_conditions_without_future_leak(self):
        validation = m10.validate_inputs(
            self.dataset, self.result, self.persona, self.persona_lock, self.config
        )
        self.assertTrue(validation["valid"], validation["errors"])
        provider = FakeProvider()
        result = m10.run_experiment(
            self.dataset,
            self.result,
            self.persona,
            self.persona_lock,
            self.config,
            text_provider=provider,
            classifier_provider=provider,
        )
        self.assertEqual(len(result["rows"]), 48)
        self.assertEqual(result["resources"]["preflight_calls"], 48)
        self.assertEqual(result["resources"]["generation_calls"], 48)
        self.assertEqual(result["resources"]["classifier_calls"], 48)
        predicted = [row for row in result["rows"] if row["condition"] == m10.PREDICTED]
        oracle = [row for row in result["rows"] if row["condition"] == m10.ORACLE]
        self.assertTrue(all(not row["future_information_used"] for row in predicted))
        self.assertTrue(all(row["future_information_used"] for row in oracle))
        self.assertEqual(result["metrics"][m10.PREDICTED]["authority_alignment_rate"], 1.0)

    def test_blind_packet_hides_condition_labels(self):
        provider = FakeProvider()
        result = m10.run_experiment(
            self.dataset,
            self.result,
            self.persona,
            self.persona_lock,
            self.config,
            text_provider=provider,
            classifier_provider=provider,
        )
        packet, key = m10.build_blind_packet(result)
        self.assertEqual(len(packet["items"]), 16)
        self.assertNotIn("L1_PREDICTED_BEHAVIOR", json.dumps(packet, ensure_ascii=False))
        self.assertIn("L1_PREDICTED_BEHAVIOR", json.dumps(key, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
