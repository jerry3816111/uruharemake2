import json
import unittest

import uruha_source_semantic_atoms_m33 as m33
from test_generalized_literal_topic_projection_m29 import _IsolatedContractBrain


def candidate(required=True):
    return {
        "schema": "uruha_generalized_literal_topic_projection_m29",
        "projection_required": required,
        "surface_authority": False,
    }


class SourceSemanticAtomsM33Tests(unittest.TestCase):
    def test_chinese_source_atoms_preserve_fine_object_quantity_and_negation(self):
        text = "盒子裡沒有三支鉛筆。"
        ledger = m33.extract_source_semantic_atoms_m33(text, candidate())

        self.assertEqual(ledger["status"], "source_atoms_extracted")
        values = {atom["type"]: atom["value_jp"] for atom in ledger["atoms"]}
        self.assertEqual(values["container"], "箱")
        self.assertEqual(values["object"], "鉛筆")
        self.assertEqual(values["quantity"], "三本")
        self.assertEqual(values["negation"], "ない")
        self.assertNotIn(text, json.dumps(ledger, ensure_ascii=False))

    def test_canonical_object_loss_is_visible_and_repaired_from_source_atoms(self):
        text = "盒子裡沒有三支鉛筆。"
        ledger = m33.extract_source_semantic_atoms_m33(text, candidate())
        plan, verification, contract = m33.build_source_anchored_semantic_commit_m33(
            text,
            ledger,
            {
                "status": "semantically_authorized",
                "surface_authority": True,
                "subject_jp": "箱の中",
                "predicate_jp": "3本のペンがない",
                "literal_summary_jp": "箱の中には3本のペンがない",
            },
        )

        self.assertEqual(verification["status"], "source_canonical_conflict")
        self.assertTrue(verification["source_conflict_detected"])
        self.assertEqual(contract["repair_kind"], "source_atom_bounded_reconstruction")
        self.assertEqual(contract["response_jp"], "箱には三本の鉛筆がないんだね。")
        self.assertEqual(contract["polarity"], "negated")
        self.assertTrue(contract["surface_authority"])
        self.assertEqual(plan["core_message_jp"], contract["response_jp"])

    def test_change_operator_and_target_weekday_are_separate_atoms(self):
        text = "巴士改到下週三出發。"
        ledger = m33.extract_source_semantic_atoms_m33(text, candidate())
        _plan, verification, contract = m33.build_source_anchored_semantic_commit_m33(
            text,
            ledger,
            {
                "status": "semantically_authorized",
                "surface_authority": True,
                "subject_jp": "バス",
                "predicate_jp": "出発する",
                "time_jp": "来週の火曜日",
                "literal_summary_jp": "バスは来週の火曜日に出発する",
            },
        )

        self.assertIn("change", ledger["atom_types"])
        self.assertIn("weekday", ledger["atom_types"])
        self.assertTrue(verification["source_conflict_detected"])
        self.assertEqual(
            contract["response_jp"],
            "バスの出発は来週の水曜日に変更されたんだね。",
        )

    def test_direct_japanese_uses_identity_commit_without_model_canonical(self):
        text = "この棚にはノートが三冊しかない。"
        ledger = m33.extract_source_semantic_atoms_m33(text, candidate())
        plan, verification, contract = m33.build_source_anchored_semantic_commit_m33(
            text,
            ledger,
        )

        self.assertTrue(ledger["direct_japanese_identity"])
        self.assertEqual(verification["status"], "source_atoms_verified")
        self.assertEqual(contract["repair_kind"], "direct_japanese_identity_commit")
        self.assertEqual(contract["polarity"], "negated")
        self.assertEqual(contract["response_jp"], "この棚にはノートが三冊しかないんだね。")
        self.assertEqual(plan["intent"], "source_anchored_semantic_commit_m33")

    def test_incomplete_and_unknown_sources_fail_closed(self):
        incomplete = m33.extract_source_semantic_atoms_m33(
            "Maybe the folder near...",
            candidate(),
        )
        unknown = m33.extract_source_semantic_atoms_m33(
            "A completely unrelated bounded-looking sentence.",
            candidate(),
        )

        self.assertEqual(incomplete["status"], "incomplete_source_abstained")
        self.assertEqual(unknown["status"], "source_pattern_unavailable")
        for ledger in (incomplete, unknown):
            plan, verification, contract = m33.build_source_anchored_semantic_commit_m33(
                "ignored",
                ledger,
            )
            self.assertIsNone(plan)
            self.assertFalse(contract["surface_authority"])
            self.assertEqual(verification["status"], "not_applicable")

    def test_apply_and_final_surface_commit_preserve_authority(self):
        text = "The workshop was moved from Tuesday to Friday."
        ledger = m33.extract_source_semantic_atoms_m33(text, candidate())
        seed, _verification, commitment = m33.build_source_anchored_semantic_commit_m33(
            text,
            ledger,
        )
        plan, applied = m33.apply_source_anchored_semantic_commit_m33(
            {"intent": "chat", "scene": "casual", **seed},
            commitment,
        )
        visible, audited = m33.ensure_source_anchored_semantic_commit_m33_reaches_surface(
            "古い下書き",
            plan,
        )

        self.assertTrue(applied["plan_applied"])
        self.assertEqual(visible, commitment["response_jp"])
        self.assertEqual(audited["surface_status"], "matched")
        self.assertEqual(audited["surface_anchor_status"], "matched")

    def test_real_runtime_direct_japanese_bypasses_m31_and_reaches_trace(self):
        brain = _IsolatedContractBrain()

        result = brain.run_turn_debug("この棚にはノートが三冊しかない。")
        trace = result["runtime_trace"]

        self.assertEqual(result["reply"], "この棚にはノートが三冊しかないんだね。")
        self.assertEqual(
            trace["semantic_authorization_m31"]["reason"],
            "direct_japanese_identity_m33",
        )
        self.assertTrue(trace["source_semantic_atoms_m33"]["direct_japanese_identity"])
        self.assertEqual(
            trace["source_anchored_semantic_commit_m33"]["surface_status"],
            "matched",
        )


if __name__ == "__main__":
    unittest.main()
