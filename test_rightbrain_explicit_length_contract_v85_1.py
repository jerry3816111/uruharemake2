import json
import unittest

from uruha_brain_mac import (
    RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE,
    RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT,
    RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
    RightBrain,
)


class RightBrainExplicitLengthContractV851Tests(unittest.TestCase):
    def setUp(self):
        self.rightbrain = RightBrain(load_model=False)
        self.logic = {
            "jp_summary": "前の会話について短く答える。",
            "core_message_jp": "ポテトならあり。少しもらう。",
            "constraints": {"max_chars": 30},
            "human_speech_plan": {
                "content_units": ["ポテトについて答える"],
                "grounding_terms": ["ポテト"],
            },
            "must_avoid": [],
        }

    def payload(self):
        return json.loads(
            self.rightbrain._build_model_surface_payload(
                self.logic,
                {"mood": 0, "trust": 60},
                30,
            )
        )

    def test_default_preserves_legacy_payload_and_prompt(self):
        self.assertFalse(self.rightbrain.explicit_length_contract_enabled)
        self.assertNotIn("output_budget", self.payload())
        self.assertEqual(
            self.rightbrain._model_surface_system_instruction(),
            RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
        )

    def test_enabled_payload_makes_character_budget_executable(self):
        self.rightbrain.explicit_length_contract_enabled = True
        payload = self.payload()
        self.assertEqual(payload["output_budget"]["maximum_characters"], 30)
        self.assertEqual(payload["output_budget"]["compression_order"][0], "preserve required_marker_groups")
        self.assertIn("at most 30 visible characters", payload["reply_requirements"][-1])

    def test_enabled_system_prompt_prioritizes_meaning_before_compression(self):
        self.rightbrain.explicit_length_contract_enabled = True
        prompt = self.rightbrain._model_surface_system_instruction()
        self.assertTrue(prompt.startswith(RIGHT_BRAIN_MODEL_SYSTEM_PROMPT))
        self.assertIn("maximum_characters", prompt)
        self.assertIn("Preserve required_marker_groups first", prompt)

    def test_repair_uses_the_same_length_contract(self):
        self.rightbrain.explicit_length_contract_enabled = True
        prompt = self.rightbrain._model_surface_system_instruction(repair=True)
        self.assertTrue(prompt.startswith(RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT))
        self.assertTrue(prompt.endswith(RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE))


if __name__ == "__main__":
    unittest.main()
