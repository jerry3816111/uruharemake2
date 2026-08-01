import copy
import hashlib
import json
import re
import unittest
from pathlib import Path

import uruha_persona_policy as persona_policy
import uruha_surface_payload_v2 as surface_payload
from persona_policy_local_model_pilot_v1 import EMPTY_MEMORY, PSYCHE
from uruha_brain_mac import RightBrain, StructuredSurfaceUnavailableError


ROOT = Path(__file__).resolve().parent


class CompactJapanesePayloadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(
            (ROOT / "configs/persona_policy_local_model_pilot_v1_cases.json").read_text(
                encoding="utf-8"
            )
        )["cases"]
        cls.baseline = json.loads(
            (
                ROOT
                / "configs/rightbrain_compact_japanese_payload_v1_legacy_baseline.json"
            ).read_text(encoding="utf-8")
        )

    @staticmethod
    def build(provider_id, mode, case):
        rightbrain = RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                provider_id
            ),
        )
        rightbrain.structured_payload_mode = mode
        logic = copy.deepcopy(case["logic"])
        logic["public_persona_context"] = case["context"]
        payload = rightbrain._build_model_surface_payload(
            logic,
            PSYCHE,
            int(case["logic"]["constraints"]["max_chars"]),
            memory_data=copy.deepcopy(EMPTY_MEMORY),
        )
        return rightbrain, logic, payload

    def test_legacy_payload_hashes_are_unchanged(self):
        expected = {
            (row["case_id"], row["provider_id"]): row["payload_sha256"]
            for row in self.baseline["rows"]
        }
        actual = {}
        for case in self.cases:
            for provider_id in case["condition_order"]:
                _, _, payload = self.build(
                    provider_id,
                    surface_payload.LEGACY_JSON_V1,
                    case,
                )
                actual[(case["case_id"], provider_id)] = hashlib.sha256(
                    payload.encode("utf-8")
                ).hexdigest()
        self.assertEqual(expected, actual)

    def test_compact_payload_is_japanese_and_preserves_contract(self):
        for case in self.cases:
            for provider_id in case["condition_order"]:
                _, _, legacy = self.build(
                    provider_id,
                    surface_payload.LEGACY_JSON_V1,
                    case,
                )
                rightbrain, _, compact = self.build(
                    provider_id,
                    surface_payload.COMPACT_JAPANESE_V2,
                    case,
                )
                contract = json.loads(legacy)
                direct = surface_payload.serialize_compact_japanese_payload(contract)
                self.assertEqual(compact, direct.text)
                self.assertIsNone(re.search(r"[A-Za-z]", compact))
                self.assertIsNone(
                    re.search(
                        r"[A-Za-z]",
                        rightbrain._model_surface_system_instruction(),
                    )
                )
                self.assertEqual(
                    direct.audit["semantic_contract"]["required_marker_groups"],
                    contract["required_marker_groups"],
                )
                self.assertEqual(
                    direct.audit["persona_policy"],
                    contract["context"]["persona_expression_brief"],
                )
                self.assertEqual(
                    direct.audit["memory_policy"],
                    contract["context"]["audited_memory_brief"],
                )

    def test_unknown_control_code_fails_closed(self):
        case = copy.deepcopy(self.cases[0])
        case["logic"]["intent"] = "unsupported_synthetic_intent"
        with self.assertRaises(StructuredSurfaceUnavailableError) as caught:
            self.build(
                persona_policy.TARGET_PROVIDER,
                surface_payload.COMPACT_JAPANESE_V2,
                case,
            )
        self.assertIn(
            "compact_payload_serialization_failed:plan.intent:unsupported_value",
            caught.exception.reason,
        )

    def test_explicit_length_contract_remains_japanese(self):
        case = self.cases[0]
        rightbrain = RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                persona_policy.TARGET_PROVIDER
            ),
        )
        rightbrain.structured_payload_mode = surface_payload.COMPACT_JAPANESE_V2
        rightbrain.explicit_length_contract_enabled = True
        logic = copy.deepcopy(case["logic"])
        logic["public_persona_context"] = case["context"]
        payload = rightbrain._build_model_surface_payload(
            logic,
            PSYCHE,
            64,
            memory_data=copy.deepcopy(EMPTY_MEMORY),
        )
        self.assertIn("64字以内", payload)
        self.assertIsNone(re.search(r"[A-Za-z]", payload))
        self.assertIsNone(
            re.search(r"[A-Za-z]", rightbrain._model_surface_system_instruction())
        )

    def test_explicit_memory_cue_is_rendered(self):
        case = self.cases[0]
        rightbrain = RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                persona_policy.TARGET_PROVIDER
            ),
        )
        rightbrain.structured_payload_mode = surface_payload.COMPACT_JAPANESE_V2
        logic = copy.deepcopy(case["logic"])
        logic["public_persona_context"] = case["context"]
        logic["memory_anchor"] = {
            "kind": "preference",
            "jp_anchor": "協力ゲームが好き",
            "terms": ["協力ゲーム"],
        }
        logic["memory_use_expected"] = True
        logic["memory_speakability"] = "explicit_allowed"
        payload = rightbrain._build_model_surface_payload(
            logic,
            PSYCHE,
            64,
            memory_data=copy.deepcopy(EMPTY_MEMORY),
        )
        self.assertIn("明示許可された記憶だけ使える", payload)
        self.assertIn("協力ゲームが好き", payload)

    def test_nonempty_procedural_guidance_fails_closed(self):
        case = copy.deepcopy(self.cases[0])
        case["logic"]["procedural_guidance"] = {"unsupported": "value"}
        with self.assertRaises(StructuredSurfaceUnavailableError) as caught:
            self.build(
                persona_policy.TARGET_PROVIDER,
                surface_payload.COMPACT_JAPANESE_V2,
                case,
            )
        self.assertIn(
            "context.procedural_guidance:unsupported_nonempty_guidance",
            caught.exception.reason,
        )

    def test_default_mode_remains_legacy(self):
        rightbrain = RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                persona_policy.TARGET_PROVIDER
            ),
        )
        self.assertEqual(
            rightbrain.structured_payload_mode,
            surface_payload.LEGACY_JSON_V1,
        )

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            surface_payload.normalize_mode("unknown")


if __name__ == "__main__":
    unittest.main()
