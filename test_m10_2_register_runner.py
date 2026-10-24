import json
import unittest
from pathlib import Path

import run_m10_2_behavior_preserving_register as m102


ROOT = Path(__file__).resolve().parent
CASUAL = {
    "accept_support_and_continue": "助かる、そのまま続けるわ。",
    "acknowledge_then_continue": "分かった、そのまま続けるわ。",
    "ask_clarification": "そこ、どっちかだけ教えて。",
    "defer_commitment": "今は決めず、後で返すわ。",
    "direct_rejection": "それは無理、やらない。",
    "pause_and_reassess": "一回止めて、見直すわ。",
}


class FakeProvider:
    def __call__(self, *, model, prompt, options):
        selected = next((label for label in CASUAL if f'"authoritative_behavior":"{label}"' in prompt or f'"selected_behavior":"{label}"' in prompt), "acknowledge_then_continue")
        if "Classify only the observable dialogue act" in prompt:
            selected = next((label for label, reply in CASUAL.items() if reply in prompt), selected)
            text = json.dumps({"probabilities": {label: float(label == selected) for label in CASUAL}})
        elif "表面だけを直す層" in prompt:
            text = CASUAL[selected]
        else:
            text = CASUAL[selected].replace("わ。", "ます。")
        return {
            "text": text,
            "latency_seconds": 0.01,
            "prompt_tokens": 100,
            "completion_tokens": 8,
            "total_duration_ns": 1,
            "model_reported": model,
        }


class M102RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "configs/m10_2_behavior_preserving_register_preregistration.json").read_text())
        cls.fixture = json.loads((ROOT / "datasets/m10_2_behavior_preserving_register_synthetic_fixture_v1.json").read_text())
        cls.result_lock = json.loads((ROOT / "configs/m10_1_behavior_authoritative_language_result_lock.json").read_text())
        cls.m10_result = json.loads((ROOT / cls.result_lock["result"]["path"]).read_text())
        cls.persona = json.loads((ROOT / "datasets/public_persona_evidence_v1.json").read_text())
        cls.persona_lock = json.loads((ROOT / "configs/public_persona_evidence_v1_result_lock.json").read_text())

    def test_fake_run_preserves_authority_and_repairs_register(self):
        result = m102.run_experiment(
            self.fixture, self.result_lock, self.m10_result, self.persona, self.persona_lock,
            self.config, provider=FakeProvider(),
        )
        self.assertEqual(len(result["rows"]), 36)
        self.assertEqual(result["resources"]["total_model_calls"], 72)
        self.assertEqual(result["metrics"][m102.REGISTER_REPAIR]["authority_alignment_rate"], 1.0)
        self.assertEqual(result["metrics"][m102.REGISTER_REPAIR]["visible_contract_pass_rate"], 1.0)
        self.assertEqual(result["aligned_to_misaligned_regression_count"], 0)

    def test_blind_packet_separates_key(self):
        result = m102.run_experiment(
            self.fixture, self.result_lock, self.m10_result, self.persona, self.persona_lock,
            self.config, provider=FakeProvider(),
        )
        packet, key = m102.build_blind_packet(result)
        self.assertEqual(len(packet["items"]), 18)
        self.assertNotIn("S1_REGISTER_REPAIR", json.dumps(packet))
        self.assertIn("S1_REGISTER_REPAIR", json.dumps(key))


if __name__ == "__main__":
    unittest.main()
