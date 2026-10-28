import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import uruha_adaptive_person_model as uapm
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/m37_pragmatic_trigger_relation_reserve_v1_1.json"
PROTOCOL = ROOT / "research/m37_pragmatic_trigger_relation_protocol_v1_1.json"
EXPECTED_DATASET_SHA256 = (
    "0ef035f6f131191776c4d5eaceac58f91ddd30856804b22b731770ac97b150de"
)
EXPECTED_PROTOCOL_SHA256 = (
    "a14c1f567de8503fdb3a6ca7e114ddee6e857ceab2786a5cfa47d7d6d75d584f"
)


def _run_relation(case):
    brain = _IsolatedContractBrain()
    seed = brain.run_turn_debug(case["seed_input"])
    feedback = brain.run_turn_debug(case["seed_feedback"])
    current = brain.run_turn_debug(case["current_input"])
    return brain, seed, feedback, current


class PragmaticTriggerRelationM37Tests(unittest.TestCase):
    def test_sealed_reserve_hash_structure_and_pre_m37_labels(self):
        dataset_raw = DATASET.read_bytes()
        protocol_raw = PROTOCOL.read_bytes()
        dataset = json.loads(dataset_raw)

        self.assertEqual(hashlib.sha256(dataset_raw).hexdigest(), EXPECTED_DATASET_SHA256)
        self.assertEqual(hashlib.sha256(protocol_raw).hexdigest(), EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(len(dataset["cases"]), 12)
        self.assertEqual(
            {lang: sum(row["language"] == lang for row in dataset["cases"]) for lang in ("zh", "en", "ja")},
            {"zh": 4, "en": 4, "ja": 4},
        )
        pairs = {}
        for case in dataset["cases"]:
            classified = uapm.classify_explicit_desired_response_m25(case["seed_input"])
            self.assertEqual(classified["selected_policy"], case["expected_current_policy"])
            pairs.setdefault(case["pair_id"], []).append(case)
        self.assertEqual(len(pairs), 6)
        for pair in pairs.values():
            self.assertEqual(len(pair), 2)
            self.assertEqual(pair[0]["current_input"], pair[1]["current_input"])
            self.assertNotEqual(
                pair[0]["expected_current_policy"],
                pair[1]["expected_current_policy"],
            )

    def test_candidate_separates_observable_trigger_from_response_policy(self):
        candidate = uapm.classify_trigger_relation_candidate_m37(
            "Whenever ideas ricochet around my head after dark, tease me for it."
        )

        self.assertEqual(candidate["status"], "candidate_ready")
        self.assertEqual(candidate["trigger_predicate"], "cognitive_overactivity")
        self.assertEqual(candidate["response_policy"], "playful_tease")
        self.assertTrue(candidate["verification_required"])
        self.assertNotIn("ricochet", json.dumps(candidate, ensure_ascii=False).lower())

    def test_all_sealed_cases_persist_match_and_select_the_typed_relation(self):
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            with self.subTest(case_id=case["case_id"]):
                brain, seed, feedback, current = _run_relation(case)
                seed_trace = seed["runtime_trace"]["pragmatic_trigger_relation_m37"]
                feedback_trace = feedback["runtime_trace"]["pragmatic_trigger_relation_m37"]
                current_trace = current["runtime_trace"]["pragmatic_trigger_relation_m37"]
                decision_trace = current["logic"]["pragmatic_trigger_relation_m37"]

                self.assertEqual(seed_trace["candidate"]["status"], "candidate_ready")
                self.assertEqual(
                    seed_trace["candidate"]["trigger_predicate"],
                    case["expected_trigger_predicate"],
                )
                self.assertEqual(
                    seed_trace["candidate"]["response_policy"],
                    case["expected_current_policy"],
                )
                self.assertEqual(
                    feedback_trace["verification_update"]["status"],
                    "verified_relation_persisted",
                )
                self.assertEqual(
                    current_trace["match"]["status"],
                    "matched_verified_trigger_relation",
                )
                self.assertEqual(
                    current_trace["match"]["trigger_predicate"],
                    case["expected_trigger_predicate"],
                )
                self.assertEqual(
                    decision_trace["selected_policy"],
                    case["expected_current_policy"],
                )
                self.assertTrue(decision_trace["authoritative"])
                stored = json.dumps(
                    brain.runtime.adaptive_person_model,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                for raw_text in (
                    case["seed_input"],
                    case["seed_feedback"],
                    case["current_input"],
                ):
                    self.assertNotIn(raw_text, stored)

    def test_current_only_and_multiple_triggers_fail_closed(self):
        current_only = uapm.classify_trigger_relation_candidate_m37(
            "My thoughts are ricocheting around my head tonight."
        )
        multiple = uapm.classify_trigger_relation_candidate_m37(
            "Whenever my thoughts race and my report is stuck, tease me."
        )

        self.assertEqual(current_only["status"], "current_only_not_relation")
        self.assertEqual(multiple["status"], "ambiguous_multiple_triggers")
        self.assertFalse(current_only["verification_required"])
        self.assertFalse(multiple["verification_required"])

    def test_unsupported_candidate_is_not_persisted_or_reused(self):
        brain = _IsolatedContractBrain()
        brain.run_turn_debug(
            "Whenever ideas ricochet around my head after dark, tease me for it."
        )
        rejected = brain.run_turn_debug("No, that was not what I wanted.")
        current = brain.run_turn_debug(
            "Tonight those ideas are ricocheting back and forth in my head."
        )

        update = rejected["runtime_trace"]["pragmatic_trigger_relation_m37"][
            "verification_update"
        ]
        match = current["runtime_trace"]["pragmatic_trigger_relation_m37"]["match"]
        self.assertEqual(update["status"], "candidate_not_verified")
        self.assertEqual(match["status"], "no_verified_relation")
        self.assertEqual(
            brain.runtime.adaptive_person_model.get("trigger_policy_relations_m37"),
            [],
        )

    def test_relation_survives_save_load_but_expires_by_revision(self):
        case = json.loads(DATASET.read_text(encoding="utf-8"))["cases"][4]
        brain, _seed, _feedback, _current = _run_relation(case)
        model = brain.runtime.adaptive_person_model
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "adaptive.json"
            uapm.save_model(path, model)
            loaded, load_trace = uapm.load_model(path)
        self.assertEqual(load_trace["status"], "loaded")
        matched = uapm.match_verified_trigger_relation_m37(
            loaded,
            case["current_input"],
        )
        self.assertEqual(matched["status"], "matched_verified_trigger_relation")
        loaded["revision_count"] = (
            int(loaded["trigger_policy_relations_m37"][0]["updated_revision"])
            + uapm.M37_TRIGGER_RELATION_TTL_REVISIONS
            + 1
        )
        expired = uapm.match_verified_trigger_relation_m37(
            loaded,
            case["current_input"],
        )
        self.assertEqual(expired["status"], "no_verified_relation")
        self.assertTrue(expired["expired_relation_ids"])

    def test_runtime_graph_shows_the_verified_trigger_relation(self):
        case = json.loads(DATASET.read_text(encoding="utf-8"))["cases"][4]
        _brain, _seed, _feedback, current = _run_relation(case)
        graph = collect_cognitive_graph(current)
        labels = {node["label"] for node in graph["nodes"]}
        html = render_memory_observatory(current)

        self.assertIn("pragmatic_trigger_relation_m37", labels)
        self.assertIn("PRAGMATIC TRIGGER-RELATION NORMALIZATION · M37", html)
        self.assertIn("cognitive_overactivity → playful_tease", html)
        relation_node = next(
            node
            for node in graph["nodes"]
            if node["label"] == "pragmatic_trigger_relation_m37"
        )
        self.assertIn("cognitive_overactivity", relation_node["signal"])


if __name__ == "__main__":
    unittest.main()
