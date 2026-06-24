import json
import unittest

from build_rightbrain_contract_v1_training_dataset import build_dataset
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RIGHT_BRAIN_MODEL_SYSTEM_PROMPT


class RightBrainContractV1TrainingDatasetTest(unittest.TestCase):
    def test_builder_hides_raw_input_and_preserves_contract(self):
        source = [
            {
                "id": "source-1",
                "category": "support",
                "messages": [
                    {"role": "system", "content": "legacy"},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "user_input": "今天頭痛",
                                "leftbrain_plan": {
                                    "scene": "support",
                                    "intent": "headache_support",
                                    "surface_act": "rest",
                                    "dialogue_act": "emotional_containment",
                                    "meaning": "頭痛がつらいので休むように返す。",
                                    "content_units": ["頭痛", "休む"],
                                    "style_operators": ["casual"],
                                    "grounding_terms": ["頭痛"],
                                },
                                "context": {"max_chars": 40},
                                "required_marker_groups": [["頭痛"], ["休"]],
                                "forbidden_markers": ["大げさ"],
                            },
                            ensure_ascii=False,
                        ),
                    },
                    {"role": "assistant", "content": "頭痛きついなら休め。"},
                ],
            }
        ]

        rows, stats, _ = build_dataset(source, set())

        self.assertEqual(stats["kept_rows"], 1)
        payload = json.loads(rows[0]["messages"][1]["content"])
        self.assertEqual(payload["contract_version"], RIGHT_BRAIN_MODEL_CONTRACT_VERSION)
        self.assertEqual(payload["user_input"], "頭痛がつらいので休むように返す。")
        self.assertNotIn("今天頭痛", rows[0]["messages"][1]["content"])
        self.assertEqual(rows[0]["messages"][0]["content"], RIGHT_BRAIN_MODEL_SYSTEM_PROMPT)
        self.assertEqual(payload["context"]["audited_memory_brief"]["policy"], "no_memory")
        self.assertEqual(payload["context"]["audited_memory_brief"]["allowed_memory_cues"], [])
        self.assertEqual(payload["context"]["persona_expression_brief"]["role"], "surface_style_only")

    def test_builder_excludes_development_overlap_and_bad_register(self):
        def row(source_id, user_input, reply):
            return {
                "id": source_id,
                "messages": [
                    {"role": "system", "content": "legacy"},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "user_input": user_input,
                                "leftbrain_plan": {"meaning": "返事を待つ。"},
                                "context": {"max_chars": 40},
                                "required_marker_groups": [["待"]],
                                "forbidden_markers": [],
                            },
                            ensure_ascii=False,
                        ),
                    },
                    {"role": "assistant", "content": reply},
                ],
            }

        rows, stats, _ = build_dataset(
            [row("overlap", "朋友下午到現在還沒回。", "少し待て。"), row("polite", "x", "少し待ちます。")],
            {"朋友下午到現在還沒回。"},
        )

        self.assertEqual(rows, [])
        self.assertEqual(stats["skip_development_overlap"], 1)
        self.assertEqual(stats["skip_register_violation"], 1)


if __name__ == "__main__":
    unittest.main()
