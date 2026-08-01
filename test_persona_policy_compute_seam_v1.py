import copy
import json
import os
import unittest
from types import SimpleNamespace

import torch

os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")

import public_persona_contract_v3 as public_contract
import persona_policy_compute_seam_v1 as construction
import uruha_compute_ledger as ledger_module
import uruha_persona_policy as persona_policy
from uruha_brain_mac import RIGHT_BRAIN_BASE_MODEL, RightBrain, UruhaBrainV4_Mac


ACTIVE_LOGIC = {
    "public_persona_context": "fatigue_update_with_near_term_plan",
    "scene": "support",
    "intent": "state_update",
    "jp_summary": "少し疲れているが、次にすることを話している。",
    "core_message_jp": "今の状態を短く伝えて、次の行動を一つ示す",
    "required_marker_groups": [["疲れ", "休む"], ["次", "あとで"]],
    "memory_anchor": {"kind": "working_memory", "id": "wm-1"},
    "memory_speakability": "allowed",
    "memory_use_expected": True,
    "action_intent_frame": {"kind": "reply_only"},
    "authorized_action": None,
    "tool_calls": [],
    "human_speech_plan": {
        "content_units": ["状態", "次の行動"],
        "grounding_terms": ["疲れ"],
    },
}
PSYCHE = {"mood": -20, "trust": 68}


def _structural_paths(value, prefix="$"):
    paths = []
    if isinstance(value, dict):
        paths.append((prefix, "dict", len(value)))
        for key in sorted(value):
            paths.extend(_structural_paths(value[key], f"{prefix}.{key}"))
    elif isinstance(value, list):
        paths.append((prefix, "list", len(value)))
        for index, item in enumerate(value):
            paths.extend(_structural_paths(item, f"{prefix}[{index}]"))
    else:
        paths.append((prefix, "scalar", None))
    return paths


def _all_keys(value):
    keys = set()
    if isinstance(value, dict):
        keys.update(value)
        for child in value.values():
            keys.update(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_all_keys(child))
    return keys


class FakeCompletions:
    def __init__(self, reply="ok", error=None):
        self.reply = reply
        self.error = error

    def create(self, **kwargs):
        if self.error is not None:
            raise self.error
        usage = SimpleNamespace(prompt_tokens=7, completion_tokens=3, total_tokens=10)
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


class FakeOpenAIClient:
    def __init__(self, reply="ok", error=None):
        completions = FakeCompletions(reply=reply, error=error)
        self.chat = SimpleNamespace(completions=completions)


class FakeTokenizer:
    eos_token_id = 0

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "private prompt text"

    def __call__(self, prompt, return_tensors="pt"):
        return {"input_ids": torch.tensor([[1, 2, 3]])}

    def decode(self, token_ids, skip_special_tokens=False):
        return "短い返事。"


class FakeModel:
    def generate(self, **kwargs):
        return torch.tensor([[1, 2, 3, 4, 5]])


class PersonaPolicyProviderV1Test(unittest.TestCase):
    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            persona_policy.build_persona_policy_provider("unknown")

    def test_legacy_provider_reproduces_existing_prompt_and_brief(self):
        provider = persona_policy.build_persona_policy_provider(persona_policy.LEGACY_PROVIDER)
        self.assertEqual(
            provider.planner_goal_line(),
            "- Final output should sound like Ichinose Uruha.",
        )
        brief, _ = provider.expression_brief(ACTIVE_LOGIC, PSYCHE)
        self.assertEqual(brief, public_contract.baseline_expression_brief(PSYCHE))

    def test_target_and_neutral_have_identical_structure(self):
        target = persona_policy.build_persona_policy_provider(persona_policy.TARGET_PROVIDER)
        neutral = persona_policy.build_persona_policy_provider(persona_policy.NEUTRAL_PROVIDER)
        target_projection = target.compile(ACTIVE_LOGIC, PSYCHE)
        neutral_projection = neutral.compile(ACTIVE_LOGIC, PSYCHE)

        self.assertEqual(
            _structural_paths(target_projection),
            _structural_paths(neutral_projection),
        )
        self.assertNotEqual(target_projection, neutral_projection)
        self.assertEqual(len(target_projection["source_observation_ids"]), 1)
        self.assertEqual(len(neutral_projection["source_observation_ids"]), 1)
        self.assertTrue(neutral_projection["source_observation_ids"][0].startswith("neutral_control_"))

    def test_provider_contains_policy_not_final_reply_content(self):
        forbidden_keys = {
            "answer",
            "expected_reply",
            "final_output",
            "final_reply",
            "target_reply",
            "utterance",
            "verbatim_text",
        }
        for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER):
            projection = persona_policy.build_persona_policy_provider(provider_id).compile(
                ACTIVE_LOGIC,
                PSYCHE,
            )
            keys = _all_keys(projection)
            self.assertTrue(forbidden_keys.isdisjoint(keys))
            self.assertFalse(projection["contains_fixed_reply"])
            self.assertFalse(projection["contains_target_utterance"])

    def test_attach_preserves_input_and_all_cognitive_fields(self):
        provider = persona_policy.build_persona_policy_provider(persona_policy.TARGET_PROVIDER)
        source = copy.deepcopy(ACTIVE_LOGIC)
        before = copy.deepcopy(source)
        projected = provider.attach_to_plan(source, PSYCHE)

        self.assertEqual(source, before)
        self.assertEqual(
            {key: projected.get(key) for key in persona_policy.PROTECTED_PLAN_FIELDS},
            {key: before.get(key) for key in persona_policy.PROTECTED_PLAN_FIELDS},
        )
        without_policy = copy.deepcopy(projected)
        without_policy.pop("public_persona_policy")
        self.assertEqual(without_policy, before)

    def test_default_and_legacy_rightbrain_payloads_are_byte_identical(self):
        default = RightBrain(load_model=False)
        legacy = RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                persona_policy.LEGACY_PROVIDER
            ),
        )
        default_logic = copy.deepcopy(ACTIVE_LOGIC)
        legacy_logic = copy.deepcopy(ACTIVE_LOGIC)
        self.assertEqual(
            default._build_model_surface_payload(default_logic, PSYCHE, 64),
            legacy._build_model_surface_payload(legacy_logic, PSYCHE, 64),
        )

    def test_target_and_neutral_payloads_differ_only_in_persona_brief(self):
        target = RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                persona_policy.TARGET_PROVIDER
            ),
        )
        neutral = RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                persona_policy.NEUTRAL_PROVIDER
            ),
        )
        target_payload = json.loads(
            target._build_model_surface_payload(copy.deepcopy(ACTIVE_LOGIC), PSYCHE, 64)
        )
        neutral_payload = json.loads(
            neutral._build_model_surface_payload(copy.deepcopy(ACTIVE_LOGIC), PSYCHE, 64)
        )
        target_brief = target_payload["context"].pop("persona_expression_brief")
        neutral_brief = neutral_payload["context"].pop("persona_expression_brief")
        self.assertEqual(target_payload, neutral_payload)
        self.assertNotEqual(target_brief, neutral_brief)
        self.assertEqual(_structural_paths(target_brief), _structural_paths(neutral_brief))


class ComputeLedgerV1Test(unittest.TestCase):
    def test_chat_wrapper_records_hashes_usage_and_no_raw_text(self):
        ledger = ledger_module.ComputeLedger()
        client = ledger_module.instrument_openai_client(
            FakeOpenAIClient(reply="private model reply"),
            ledger,
        )
        with ledger.item_scope("item-1", "target"):
            with ledger.stage("leftbrain_general_plan"):
                client.chat.completions.create(
                    model="qwen2.5:7b",
                    messages=[{"role": "user", "content": "private user input"}],
                    temperature=0.1,
                    max_tokens=40,
                )

        snapshot = ledger.snapshot()
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertEqual(snapshot["call_count"], 1)
        self.assertFalse(snapshot["contains_raw_prompt_or_reply"])
        self.assertNotIn("private user input", serialized)
        self.assertNotIn("private model reply", serialized)
        call = snapshot["calls"][0]
        self.assertEqual(call["item_id"], "item-1")
        self.assertEqual(call["condition_id"], "target")
        self.assertEqual(call["stage"], "leftbrain_general_plan")
        self.assertEqual(call["response"]["total_tokens"], 10)
        self.assertEqual(call["error_type"], "")

    def test_chat_wrapper_records_failure_and_reraises(self):
        ledger = ledger_module.ComputeLedger()
        client = ledger_module.instrument_openai_client(
            FakeOpenAIClient(error=RuntimeError("private failure")),
            ledger,
        )
        with self.assertRaises(RuntimeError):
            client.chat.completions.create(
                model="qwen2.5:7b",
                messages=[{"role": "user", "content": "secret"}],
                temperature=0.0,
            )
        call = ledger.snapshot()["calls"][0]
        self.assertEqual(call["error_type"], "RuntimeError")
        self.assertNotIn("private failure", json.dumps(call))

    def test_scope_context_does_not_leak_to_later_calls(self):
        ledger = ledger_module.ComputeLedger()
        client = ledger_module.instrument_openai_client(FakeOpenAIClient(), ledger)
        with ledger.item_scope("item-1", "target"):
            with ledger.stage("stage-1"):
                client.chat.completions.create(model="m", messages=[])
        client.chat.completions.create(model="m", messages=[])
        calls = ledger.snapshot()["calls"]
        self.assertEqual(calls[0]["item_id"], "item-1")
        self.assertEqual(calls[1]["item_id"], "unscoped")
        self.assertEqual(calls[1]["condition_id"], "unscoped")
        self.assertEqual(calls[1]["stage"], "unscoped")

    def test_compute_envelope_checks_schedule_not_content(self):
        left = ledger_module.ComputeLedger()
        right = ledger_module.ComputeLedger()
        for condition, ledger, content in (
            ("target", left, "target policy"),
            ("neutral", right, "neutral policy"),
        ):
            client = ledger_module.instrument_openai_client(FakeOpenAIClient(), ledger)
            with ledger.item_scope("item-1", condition):
                with ledger.stage("rightbrain_surface_generation"):
                    client.chat.completions.create(
                        model="qwen3:8b",
                        messages=[{"role": "user", "content": content}],
                        temperature=0.0,
                        max_tokens=64,
                    )
        parity = ledger_module.compare_compute_envelopes(left.snapshot(), right.snapshot())
        self.assertTrue(parity["parity_pass"])
        right._calls[0]["model"] = "different-model"
        self.assertFalse(
            ledger_module.compare_compute_envelopes(left.snapshot(), right.snapshot())["parity_pass"]
        )

    def test_local_generation_records_stage_and_token_counts(self):
        ledger = ledger_module.ComputeLedger()
        rightbrain = RightBrain(load_model=False, compute_ledger=ledger)
        rightbrain.model = FakeModel()
        rightbrain.tokenizer = FakeTokenizer()
        rightbrain.device = "cpu"

        reply = rightbrain._run_model_surface_generation(
            [{"role": "user", "content": "{}"}],
            {"do_sample": False},
        )
        self.assertEqual(reply, "短い返事。")
        call = ledger.snapshot()["calls"][0]
        self.assertEqual(call["stage"], "rightbrain_surface_generation")
        self.assertEqual(call["model"], RIGHT_BRAIN_BASE_MODEL)
        self.assertEqual(call["response"]["prompt_tokens"], 3)
        self.assertEqual(call["response"]["completion_tokens"], 2)
        self.assertNotIn("private prompt text", json.dumps(call, ensure_ascii=False))

    def test_invalid_ledger_is_rejected(self):
        with self.assertRaises(TypeError):
            ledger_module.instrument_openai_client(FakeOpenAIClient(), object())


class PersonaPolicyConstructionV1Test(unittest.TestCase):
    def test_six_synthetic_cases_meet_projection_contract(self):
        rows = construction.construct_cases()
        self.assertEqual(len(rows), 6)
        self.assertEqual(sum(row["supported_context"] for row in rows), 5)
        for row in rows:
            self.assertTrue(row["default_vs_legacy_payload_byte_identical"])
            self.assertTrue(row["target_vs_neutral_projection_structure_equal"])
            self.assertTrue(row["target_vs_neutral_brief_structure_equal"])
            self.assertTrue(row["target_vs_neutral_nonpersona_payload_equal"])
            self.assertTrue(row["protected_fields_unchanged"])
            self.assertTrue(row["target_and_neutral_values_differ"])
            self.assertFalse(row["contains_fixed_reply"])
            self.assertFalse(row["contains_target_utterance"])

    def test_all_declared_model_stages_are_present(self):
        audit = construction.source_stage_audit()
        self.assertTrue(all(audit["stage_presence"].values()))
        self.assertTrue(audit["instrumented_client_present"])
        self.assertTrue(audit["default_provider_is_optional"])
        self.assertTrue(audit["default_ledger_is_optional"])

    def test_partial_controller_without_constructor_has_no_ledger_snapshot(self):
        partial = UruhaBrainV4_Mac.__new__(UruhaBrainV4_Mac)
        self.assertIsNone(partial.get_compute_ledger_snapshot())


if __name__ == "__main__":
    unittest.main()
