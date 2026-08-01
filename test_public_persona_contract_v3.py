import copy
import hashlib
import json
import os
import subprocess
import unittest
from pathlib import Path

os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")

import public_persona_contract_v3 as contract
import analyze_public_persona_contract_v3_development as analyzer
from build_public_persona_contract_v3_development import build_dataset
from rightbrain_preverbal_payload_v31 import KEY_TRANSLATIONS
from run_public_persona_contract_v3_development import CONDITIONS, build_payload, build_request
from uruha_brain_mac import PUBLIC_PERSONA_CONDITIONAL_BRIEF_ENABLED, RightBrain


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/public_persona_contract_v3_development.json"
LOCK_PATH = ROOT / "configs/public_persona_contract_v3_harness_lock.json"


def _protected(logic):
    speech = logic.get("human_speech_plan") or {}
    return {
        "core_message_jp": logic.get("core_message_jp"),
        "required_marker_groups": logic.get("required_marker_groups"),
        "memory_anchor": logic.get("memory_anchor"),
        "memory_speakability": logic.get("memory_speakability"),
        "memory_use_expected": logic.get("memory_use_expected"),
        "action_intent_frame": logic.get("action_intent_frame"),
        "authorized_action": logic.get("authorized_action"),
        "tool_calls": logic.get("tool_calls"),
        "speech_content_units": speech.get("content_units"),
        "speech_grounding_terms": speech.get("grounding_terms"),
    }


def _without_persona(payload):
    copied = copy.deepcopy(payload)
    copied["context"].pop("persona_expression_brief", None)
    return copied


class PublicPersonaContractV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.right_brain = RightBrain(load_model=False)

    def test_generated_dataset_matches_frozen_file(self):
        self.assertEqual(build_dataset(), self.dataset)

    def test_case_accounting_is_exact(self):
        accounting = self.dataset["accounting"]
        self.assertEqual(accounting["case_count"], 20)
        self.assertEqual(accounting["active_context_case_count"], 15)
        self.assertEqual(accounting["inactive_control_case_count"], 5)
        for context_name in contract.POLICIES:
            self.assertEqual(accounting["context_counts"][context_name], 3)

    def test_policies_bind_all_and_only_v2_development_observations(self):
        observation_ids = {
            observation_id
            for policy in contract.POLICIES.values()
            for observation_id in policy["source_observation_ids"]
        }
        self.assertEqual(
            observation_ids,
            {f"persona_obs_v2_dev_{index:03d}" for index in range(1, 6)},
        )

    def test_compiler_requires_explicit_supported_context(self):
        for row in self.dataset["cases"]:
            compiled = contract.compile_persona_contract(row["logic"])
            self.assertEqual(compiled["status"], row["expected_contract_status"])
            if row["context"] in contract.POLICIES:
                self.assertTrue(compiled["planning_policy"])
                self.assertTrue(compiled["surface_policy"])
            else:
                self.assertEqual(compiled["planning_policy"], {})
                self.assertEqual(compiled["surface_policy"], {})

    def test_compiler_does_not_mutate_logic(self):
        for row in self.dataset["cases"]:
            logic = copy.deepcopy(row["logic"])
            before = copy.deepcopy(logic)
            contract.compile_persona_contract(logic)
            self.assertEqual(logic, before)

    def test_contract_contains_no_reply_or_training_authorization(self):
        serialized = json.dumps(contract.POLICIES, ensure_ascii=False).casefold()
        for marker in ("target_reply", "expected_reply", "fixed_response", "verbatim_text"):
            self.assertNotIn(marker, serialized)
        for row in self.dataset["cases"]:
            compiled = contract.compile_persona_contract(row["logic"])
            self.assertFalse(compiled["contains_fixed_reply"])
            self.assertFalse(compiled["training_authorized"])
            self.assertFalse(compiled["runtime_default_authorized"])

    def test_baseline_brief_reproduces_pre_v3_behavior(self):
        self.assertEqual(
            contract.baseline_expression_brief({"mood": -30, "trust": 75}),
            {
                "role": "surface_style_only",
                "state": "low_energy",
                "relationship_distance": "familiar",
                "stable_traits": ["lazy_short", "slightly_bratty", "not_customer_service"],
                "must_not_override": [
                    "leftbrain_plan",
                    "required_marker_groups",
                    "audited_memory_policy",
                ],
            },
        )

    def test_runtime_feature_is_disabled_by_default(self):
        self.assertFalse(PUBLIC_PERSONA_CONDITIONAL_BRIEF_ENABLED)
        self.assertFalse(self.right_brain.public_persona_conditional_brief_enabled)

    def test_disabled_runtime_returns_exact_baseline_for_active_context(self):
        row = self.dataset["cases"][0]
        logic = copy.deepcopy(row["logic"])
        brief = self.right_brain._persona_expression_brief(row["psyche"], logic)
        self.assertEqual(brief, contract.baseline_expression_brief(row["psyche"]))
        self.assertNotIn("public_persona_contract_trace", logic)

    def test_treatment_projects_surface_but_not_planning_policy(self):
        row = self.dataset["cases"][0]
        logic = copy.deepcopy(row["logic"])
        self.right_brain.public_persona_conditional_brief_enabled = True
        try:
            brief = self.right_brain._persona_expression_brief(row["psyche"], logic)
        finally:
            self.right_brain.public_persona_conditional_brief_enabled = False
        self.assertEqual(brief["conditional_context"], row["context"])
        self.assertIn("expression_policy", brief)
        self.assertNotIn("planning_policy", brief)
        self.assertNotIn("source_observation_ids", brief)
        self.assertTrue(logic["public_persona_contract_trace"]["planning_policy"])

    def test_target_payload_changes_only_persona_brief(self):
        for row in self.dataset["cases"]:
            if row["context"] not in contract.POLICIES:
                continue
            control_logic = copy.deepcopy(row["logic"])
            treatment_logic = copy.deepcopy(row["logic"])
            self.right_brain.public_persona_conditional_brief_enabled = False
            control = json.loads(
                self.right_brain._build_model_surface_payload(
                    control_logic, row["psyche"], row["persona_evaluation"]["maximum_characters"]
                )
            )
            self.right_brain.public_persona_conditional_brief_enabled = True
            try:
                treatment = json.loads(
                    self.right_brain._build_model_surface_payload(
                        treatment_logic, row["psyche"], row["persona_evaluation"]["maximum_characters"]
                    )
                )
            finally:
                self.right_brain.public_persona_conditional_brief_enabled = False
            self.assertEqual(_without_persona(control), _without_persona(treatment))
            self.assertNotEqual(
                control["context"]["persona_expression_brief"],
                treatment["context"]["persona_expression_brief"],
            )

    def test_inactive_payload_is_byte_identical_between_conditions(self):
        for row in self.dataset["cases"]:
            if row["context"] in contract.POLICIES:
                continue
            control_logic = copy.deepcopy(row["logic"])
            treatment_logic = copy.deepcopy(row["logic"])
            self.right_brain.public_persona_conditional_brief_enabled = False
            control = self.right_brain._build_model_surface_payload(
                control_logic, row["psyche"], row["persona_evaluation"]["maximum_characters"]
            )
            self.right_brain.public_persona_conditional_brief_enabled = True
            try:
                treatment = self.right_brain._build_model_surface_payload(
                    treatment_logic, row["psyche"], row["persona_evaluation"]["maximum_characters"]
                )
            finally:
                self.right_brain.public_persona_conditional_brief_enabled = False
            self.assertEqual(control, treatment)

    def test_payload_build_preserves_memory_action_and_semantic_fields(self):
        for row in self.dataset["cases"]:
            logic = copy.deepcopy(row["logic"])
            before = _protected(logic)
            self.right_brain.public_persona_conditional_brief_enabled = True
            try:
                self.right_brain._build_model_surface_payload(
                    logic, row["psyche"], row["persona_evaluation"]["maximum_characters"]
                )
            finally:
                self.right_brain.public_persona_conditional_brief_enabled = False
            self.assertEqual(_protected(logic), before)

    def test_preverbal_serializer_has_v3_surface_keys(self):
        for key in (
            "conditional_context",
            "expression_policy",
            "protected_fields",
            "tone",
            "energy",
            "brevity",
            "operations",
            "avoid",
        ):
            self.assertIn(key, KEY_TRANSLATIONS)

    def test_runner_uses_identical_seed_and_model_for_both_conditions(self):
        preregistration = json.loads(
            (ROOT / "configs/public_persona_contract_v3_preregistration.json").read_text(
                encoding="utf-8"
            )
        )
        row = self.dataset["cases"][0]
        requests = []
        for condition in CONDITIONS:
            _, payload_text, _ = build_payload(self.right_brain, row, condition)
            requests.append(build_request(preregistration, payload_text, 0))
        self.assertEqual(requests[0]["model"], requests[1]["model"])
        self.assertEqual(requests[0]["options"], requests[1]["options"])
        self.assertEqual(requests[0]["messages"][0], requests[1]["messages"][0])
        self.assertNotEqual(requests[0]["messages"][1], requests[1]["messages"][1])

    def test_persona_scorer_checks_order_and_forbidden_content(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_delay_01")
        base = {
            "condition": CONDITIONS[1],
            "contract_active": True,
            "transport_error": "",
            "tool_calls": [],
            "elapsed_seconds": 1.0,
            "peak_ollama_rss_bytes": 1,
        }
        good_reply = "遅れた。動画、楽しんで。"
        good = analyzer.score_row(
            self.right_brain,
            {**base, "raw_reply": good_reply, "raw_reply_sha256": hashlib.sha256(good_reply.encode()).hexdigest()},
            case,
        )
        bad_reply = "動画を楽しんで。遅れたし全部うちが悪い。"
        bad = analyzer.score_row(
            self.right_brain,
            {**base, "raw_reply": bad_reply, "raw_reply_sha256": hashlib.sha256(bad_reply.encode()).hexdigest()},
            case,
        )
        self.assertTrue(good["persona_policy_pass"])
        self.assertFalse(bad["persona_policy_pass"])
        self.assertFalse(bad["ordering_pass"])
        self.assertTrue(bad["persona_forbidden_hits"])

    def test_null_context_is_not_persona_scored(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_null_02")
        reply = "一週間は七日。"
        scored = analyzer.score_row(
            self.right_brain,
            {
                "condition": CONDITIONS[1],
                "contract_active": False,
                "transport_error": "",
                "tool_calls": [],
                "elapsed_seconds": 1.0,
                "peak_ollama_rss_bytes": 1,
                "raw_reply": reply,
                "raw_reply_sha256": hashlib.sha256(reply.encode()).hexdigest(),
            },
            case,
        )
        self.assertFalse(scored["persona_policy_scored"])
        self.assertIsNone(scored["persona_policy_pass"])

    def test_preregistration_forbids_runtime_training_and_holdout_unsealing(self):
        preregistration = json.loads(
            (ROOT / "configs/public_persona_contract_v3_preregistration.json").read_text(
                encoding="utf-8"
            )
        )
        decision = preregistration["decision_policy"]
        self.assertFalse(decision["runtime_default_enable"])
        self.assertFalse(decision["training"])
        self.assertFalse(decision["holdout_unsealing"])
        self.assertFalse(decision["public_persona_fidelity_claim"])

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        history = subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                str(LOCK_PATH.relative_to(ROOT)),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertTrue(history)
        frozen_commit = history[-1]
        for artifact in lock["frozen_artifacts"].values():
            frozen = subprocess.run(
                ["git", "show", f"{frozen_commit}:{artifact['path']}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            self.assertEqual(hashlib.sha256(frozen).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
