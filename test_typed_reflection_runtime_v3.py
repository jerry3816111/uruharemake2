import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import uruha_reflection_runtime as reflection
import uruha_brain_mac as brain_module


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "typed_reflection_v3_development_pilot.json"


class FakeCompletions:
    def __init__(self, payload):
        self.payloads = payload if isinstance(payload, list) else [payload]
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self.payloads) - 1)
        message = SimpleNamespace(
            content=json.dumps(self.payloads[index], ensure_ascii=False)
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeLogicClient:
    def __init__(self, payload):
        self.completions = FakeCompletions(payload)
        self.chat = SimpleNamespace(completions=self.completions)


class ExplodingLogicClient:
    class Completions:
        def create(self, **kwargs):
            raise AssertionError("no-reflection input must not call the model")

    def __init__(self):
        self.chat = SimpleNamespace(completions=self.Completions())


class TypedReflectionHelpersV3Test(unittest.TestCase):
    def test_failed_v4_runtime_is_opt_in_not_default(self):
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))
        self.assertFalse(
            reflection.typed_reflection_runtime_enabled(
                {"URUHA_ENABLE_TYPED_REFLECTION": "0"}
            )
        )
        self.assertTrue(
            reflection.typed_reflection_runtime_enabled(
                {"URUHA_ENABLE_TYPED_REFLECTION": "true"}
            )
        )

    def test_frozen_development_types_are_classified_before_model_use(self):
        payload = json.loads(DATASET.read_text(encoding="utf-8"))
        observed = {
            case["id"]: reflection.classify_reflection_type(case["seed_user"])
            for case in payload["cases"]
        }
        expected = {
            case["id"]: case["expected_reflection_type"]
            for case in payload["cases"]
        }
        self.assertEqual(observed, expected)

    def test_unseen_stable_facts_generalize_without_catching_transient_wants(self):
        examples = {
            "I love walking beside the river on quiet mornings.": "semantic",
            "私は納豆が嫌い。": "semantic",
            "我不能喝牛奶，會肚子痛。": "semantic",
            "以後先回答我的問題，再補理由。": "procedural",
            "我今天突然想喝咖啡。": "none",
            "What coffee would you choose today?": "none",
        }
        self.assertEqual(
            {
                text: reflection.classify_reflection_type(text)
                for text in examples
            },
            examples,
        )

    def test_validator_requires_exact_type_grounded_quote_and_japanese(self):
        valid = {
            "reflection_type": "procedural",
            "content_jp": "次回は結論を先に答える。",
            "trigger_jp": "理由を説明する前",
            "evidence_quote": "結論を先に",
            "confidence": 0.9,
        }
        accepted = reflection.validate_reflection_payload(
            valid,
            user_input="下次請把結論先說。結論を先に。",
            expected_type="procedural",
            source_episode_id="episode-1",
        )
        self.assertIsNotNone(accepted)
        self.assertEqual(accepted["collection"], "procedural")
        self.assertEqual(accepted["source_episode_id"], "episode-1")

        for changed in (
            {**valid, "reflection_type": "semantic"},
            {**valid, "evidence_quote": "not in the source"},
            {**valid, "content_jp": "answer first"},
            {**valid, "content_jp": "Rule: NO_RULE"},
            {**valid, "extra": "forbidden"},
        ):
            self.assertIsNone(
                reflection.validate_reflection_payload(
                    changed,
                    user_input="下次請把結論先說。結論を先に。",
                    expected_type="procedural",
                    source_episode_id="episode-1",
                )
            )

    def test_v4_surface_rejects_source_external_language_but_allows_source_quote(self):
        rejected = reflection.validate_reflection_surface(
            {
                "content_jp": "『也许以后』は時間が必要という意味です。",
                "trigger_jp": "この表現を使う時",
            },
            user_input="When I say maybe later, I need more time.",
        )
        self.assertFalse(rejected["valid"])
        self.assertTrue(rejected["retryable"])
        self.assertTrue(
            any(reason.startswith("source_external_language") for reason in rejected["reasons"])
        )

        accepted = reflection.validate_reflection_surface(
            {
                "content_jp": "『maybe later』は時間が必要という意味です。",
                "trigger_jp": "『maybe later』と言う時",
            },
            user_input="When I say maybe later, I need more time.",
        )
        self.assertTrue(accepted["valid"])

    def test_v4_deterministic_fields_keep_exact_source_and_provenance(self):
        source = "I usually rest after lunch."
        fields = reflection.deterministic_reflection_fields(
            source,
            reflection_type="semantic",
            source_episode_id="episode-9",
        )
        self.assertEqual(fields["evidence_quote"], source)
        self.assertEqual(fields["source_episode_id"], "episode-9")
        self.assertEqual(fields["confidence"], 0.95)
        self.assertEqual(fields["collection"], "wisdom")


class TypedReflectionMemoryV3Test(unittest.TestCase):
    def setUp(self):
        self.original_db_path = brain_module.DB_PATH
        self.tempdir = tempfile.TemporaryDirectory(prefix="uruha_typed_reflection_v3_")
        brain_module.DB_PATH = self.tempdir.name
        self.memory = brain_module.MemoryManager()

    def tearDown(self):
        brain_module.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_procedural_reflection_routes_with_episode_provenance_and_retrieves(self):
        user_input = "你剛剛一次給太多建議了。下次先給我一個最重要的就好。"
        self.memory.save_episode(user_input, "分かった。", {"mood": 0, "trust": 50})
        source_episode_id = self.memory.get_runtime_snapshot()["last_saved_episode_id"]
        client = FakeLogicClient(
            {
                "content_jp": "次回は最も重要な提案を一つだけ先に伝える。",
                "trigger_jp": "複数の問題について助言する時",
            }
        )

        result = self.memory.reflect_experience(
            user_input,
            "分かった。",
            {"intent": "feedback"},
            client,
        )

        self.assertEqual(result["status"], "stored")
        self.assertEqual(result["collection"], "procedural")
        self.assertEqual(result["source_episode_id"], source_episode_id)
        stored = self.memory.procedural_col.get(ids=[result["memory_id"]], include=["metadatas"])
        metadata = stored["metadatas"][0]
        self.assertEqual(metadata["source"], "typed_reflection")
        self.assertEqual(metadata["reflection_type"], "procedural")
        self.assertEqual(metadata["source_episode_id"], source_episode_id)
        self.assertEqual(len(client.completions.calls), 1)
        self.assertEqual(client.completions.calls[0]["temperature"], 0.0)
        self.assertEqual(
            client.completions.calls[0]["response_format"]["type"],
            "json_schema",
        )

        later = self.memory.query_all_layers("仕事と睡眠と食事が乱れている。まず何をする？")
        procedural_items = [
            item for item in later["working_memory_items"] if item.get("source") == "procedural"
        ]
        self.assertTrue(procedural_items)
        self.assertIn("一つ", later["procedural_summary"])

    def test_none_type_performs_no_model_call_and_no_memory_write(self):
        user_input = "我同事通常下午喝兩杯咖啡，那是他的習慣。"
        self.memory.save_episode(user_input, "そうなんだ。", {"mood": 0, "trust": 50})
        before = self.memory.wisdom_col.count() + self.memory.procedural_col.count()

        result = self.memory.reflect_experience(
            user_input,
            "そうなんだ。",
            {"intent": "chat"},
            ExplodingLogicClient(),
        )

        after = self.memory.wisdom_col.count() + self.memory.procedural_col.count()
        self.assertIsNone(result)
        self.assertEqual(before, after)
        self.assertEqual(
            self.memory.get_runtime_snapshot()["last_reflection_result"]["status"],
            "no_trigger",
        )

    def test_duplicate_source_is_not_written_twice(self):
        user_input = "我通常晚上喝無咖啡因的花草茶，咖啡會讓我失眠。"
        self.memory.save_episode(user_input, "分かった。", {"mood": 0, "trust": 50})
        client = FakeLogicClient(
            {
                "content_jp": "ユーザーは夜にコーヒーを避けてハーブ茶を選ぶ。",
                "trigger_jp": "夜の飲み物を提案する時",
            }
        )
        first = self.memory.reflect_experience(user_input, "分かった。", {}, client)
        second = self.memory.reflect_experience(user_input, "分かった。", {}, client)

        self.assertEqual(first["status"], "stored")
        self.assertEqual(second["status"], "duplicate_skipped")
        self.assertEqual(self.memory.wisdom_col.count(), 1)

    def test_language_pollution_gets_one_bounded_retry(self):
        user_input = (
            "When I say 'not now', I mean I need a pause, not that I reject the idea."
        )
        self.memory.save_episode(user_input, "分かった。", {"mood": 0, "trust": 50})
        client = FakeLogicClient(
            [
                {
                    "content_jp": "『也许以后』は拒否ではありません。",
                    "trigger_jp": "この表現を使う時",
                },
                {
                    "content_jp": "『not now』は休止が必要で、拒否ではないという意味です。",
                    "trigger_jp": "『not now』と言う時",
                },
            ]
        )

        result = self.memory.reflect_experience(user_input, "分かった。", {}, client)

        self.assertEqual(result["status"], "stored")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(len(client.completions.calls), 2)
        self.assertEqual(self.memory.wisdom_col.count(), 1)


class TypedReflectionPlannerV3Test(unittest.TestCase):
    def test_generic_answer_first_procedure_favors_direct_plan(self):
        planner = brain_module.LeftBrain(client_logic=None)
        memory = {
            "working_memory_items": [
                {
                    "source": "procedural",
                    "text": "Procedure[procedural]: 次回は結論を先に答える。",
                }
            ]
        }
        direct = {
            "response_mode": "direct_answer",
            "surface_act": "plain_reply",
            "scene": "casual",
            "payload_level": "low",
        }
        indirect = {
            "response_mode": "reframe_large_question",
            "surface_act": "plain_reply",
            "scene": "casual",
            "payload_level": "high",
        }
        self.assertGreater(
            planner._procedural_fit_score(direct, memory),
            planner._procedural_fit_score(indirect, memory),
        )


class TypedReflectionProductionGateTest(unittest.TestCase):
    def test_default_turn_path_does_not_call_failed_reflection_writer(self):
        memory = SimpleNamespace(
            reflect_experience=lambda *_args, **_kwargs: self.fail(
                "disabled runtime must not call reflection writer"
            )
        )
        brain = brain_module.UruhaBrainV4_Mac.__new__(brain_module.UruhaBrainV4_Mac)
        brain.memory = memory
        brain.client_logic = object()
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(
                brain._write_typed_reflection_if_enabled("input", "reply", {})
            )

    def test_explicit_research_opt_in_keeps_shadow_writer_available(self):
        calls = []
        memory = SimpleNamespace(
            reflect_experience=lambda *args: calls.append(args) or {"status": "stored"}
        )
        brain = brain_module.UruhaBrainV4_Mac.__new__(brain_module.UruhaBrainV4_Mac)
        brain.memory = memory
        brain.client_logic = object()
        with patch.dict(
            os.environ, {"URUHA_ENABLE_TYPED_REFLECTION": "1"}, clear=True
        ):
            result = brain._write_typed_reflection_if_enabled("input", "reply", {})
        self.assertEqual(result, {"status": "stored"})
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
