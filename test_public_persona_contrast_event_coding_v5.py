import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from public_persona_contrast_event_coding_v5 import (
    DEFAULT_CONTRAST_MANIFEST,
    DEFAULT_EVENT_SCHEMA,
    DEFAULT_FRAME,
    DEFAULT_GITIGNORE,
    DEFAULT_METHOD_REGISTRY,
    DEFAULT_PREREGISTRATION,
    DEFAULT_READINESS,
    DEFAULT_RIGHTS_V1,
    DEFAULT_RIGHTS_V2,
    DEFAULT_V4_RESULT,
    EXPECTED_METHOD_SOURCE_IDS,
    FAIL_DECISION,
    PASS_DECISION,
    PRIVATE_EVENT_DIRECTORY,
    ROOT,
    _find_prohibited_keys,
    audit,
    build_audit_from_paths,
    build_sampling_frame,
    load_json,
)


SCRIPT = ROOT / "public_persona_contrast_event_coding_v5.py"


class PublicPersonaContrastEventCodingV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)
        cls.method_registry = load_json(DEFAULT_METHOD_REGISTRY)
        cls.v4_result = load_json(DEFAULT_V4_RESULT)
        cls.contrast_manifest = load_json(DEFAULT_CONTRAST_MANIFEST)
        cls.event_schema = load_json(DEFAULT_EVENT_SCHEMA)
        cls.rights_v1 = load_json(DEFAULT_RIGHTS_V1)
        cls.rights_v2 = load_json(DEFAULT_RIGHTS_V2)
        cls.readiness = load_json(DEFAULT_READINESS)
        cls.frame = load_json(DEFAULT_FRAME)
        cls.gitignore_text = DEFAULT_GITIGNORE.read_text(encoding="utf-8")

    def run_audit(self, **overrides):
        names = (
            "preregistration",
            "method_registry",
            "v4_result",
            "contrast_manifest",
            "event_schema",
            "rights_v1",
            "rights_v2",
            "readiness",
            "frame",
            "gitignore_text",
        )
        values = [
            copy.deepcopy(overrides.get(name, getattr(self, name))) for name in names
        ]
        return audit(*values, root=ROOT)

    def test_protocol_passes_but_formal_execution_remains_blocked(self):
        report = self.run_audit()
        self.assertTrue(report["protocol_passed"])
        self.assertFalse(report["formal_execution_ready"])
        self.assertFalse(report["persona_score_computed"])
        self.assertEqual(report["decision"], PASS_DECISION)
        self.assertEqual(report["summary"]["protocol_check_pass_count"], 15)
        self.assertEqual(report["summary"]["protocol_check_count"], 15)
        self.assertEqual(report["summary"]["formal_readiness_pass_count"], 4)
        self.assertEqual(report["summary"]["formal_readiness_check_count"], 19)
        self.assertEqual(report["violations"], {})

    def test_frozen_frame_rebuilds_byte_equivalent_data(self):
        rebuilt = build_sampling_frame(
            self.preregistration, self.contrast_manifest, root=ROOT
        )
        self.assertEqual(rebuilt, self.frame)
        self.assertEqual(
            build_sampling_frame(
                self.preregistration, self.contrast_manifest, root=ROOT
            ),
            rebuilt,
        )

    def test_nine_sources_have_exactly_ten_slots(self):
        slots = self.frame["sampling_slots"]
        counts = Counter(row["source_id"] for row in slots)
        self.assertEqual(len(slots), 90)
        self.assertEqual(len(counts), 9)
        self.assertEqual(set(counts.values()), {10})
        self.assertEqual({row["slot_index"] for row in slots}, set(range(1, 11)))

    def test_every_search_start_is_inside_its_stratum(self):
        for row in self.frame["sampling_slots"]:
            self.assertLess(row["stratum_start_seconds"], row["stratum_end_exclusive_seconds"])
            self.assertLessEqual(
                row["stratum_start_seconds"], row["search_start_seconds"]
            )
            self.assertLess(
                row["search_start_seconds"], row["stratum_end_exclusive_seconds"]
            )
            self.assertLessEqual(
                row["stratum_end_exclusive_seconds"], row["source_duration_seconds"]
            )

    def test_global_review_order_is_complete_and_hash_derived(self):
        slots = self.frame["sampling_slots"]
        self.assertEqual(
            [row["global_review_order"] for row in slots], list(range(1, 91))
        )
        self.assertEqual(
            slots,
            sorted(slots, key=lambda row: row["review_order_sha256"]),
        )

    def test_exact_and_broad_slots_remain_separate(self):
        counts = Counter(
            row["match_granularity"] for row in self.frame["sampling_slots"]
        )
        self.assertEqual(counts, Counter({"exact_game": 60, "broad_family_only": 30}))
        report = self.run_audit()
        self.assertEqual(report["summary"]["exact_game_sampling_slot_count"], 60)
        self.assertEqual(report["summary"]["broad_family_sampling_slot_count"], 30)

    def test_frame_contains_no_event_or_language_content(self):
        self.assertEqual(_find_prohibited_keys(self.frame), [])
        self.assertTrue(
            all(
                row["slot_status"] == "unreviewed_no_content_access"
                for row in self.frame["sampling_slots"]
            )
        )
        self.assertTrue(
            all(value is False for value in self.frame["content_boundary"].values())
        )

    def test_method_registry_uses_only_official_or_primary_sources(self):
        sources = self.method_registry["sources"]
        self.assertEqual({row["source_id"] for row in sources}, EXPECTED_METHOD_SOURCE_IDS)
        self.assertEqual(len(sources), 7)
        self.assertTrue(
            all(
                row["authority"]
                in {"platform_official", "agency_official", "primary_research_paper"}
                for row in sources
            )
        )

    def test_rights_v2_is_conditional_and_not_a_license(self):
        policy = self.rights_v2["review_policy"]
        self.assertTrue(policy["in_service_manual_viewing_after_protocol_pass"])
        self.assertTrue(
            policy[
                "bounded_researcher_behavior_paraphrase_in_restricted_local_registry"
            ]
        )
        self.assertFalse(policy["public_event_level_paraphrase_or_quote_storage"])
        self.assertFalse(policy["automated_bulk_collection_or_download"])
        self.assertFalse(policy["model_training"])
        self.assertFalse(policy["rights_holder_permission_claimed"])
        self.assertFalse(policy["legal_opinion_claimed"])

    def test_private_event_directory_is_gitignored(self):
        self.assertIn(PRIVATE_EVENT_DIRECTORY, self.gitignore_text.splitlines())
        report = build_audit_from_paths()
        self.assertTrue(
            report["workspace_guards"]["private_event_directory_is_gitignored"]
        )

    def test_all_content_model_score_and_holdout_counts_remain_zero(self):
        report = self.run_audit()
        for field in (
            "content_reviewed_source_count",
            "selected_event_count",
            "coded_event_count",
            "independently_reviewed_event_count",
            "same_topic_reference_pair_count",
            "raw_or_verbatim_record_count",
            "model_output_count",
            "persona_score_count",
            "holdout_content_review_count",
            "model_call_count",
        ):
            self.assertEqual(report["summary"][field], 0, field)

    def test_pass_authorizes_only_bounded_manual_contrast_coding(self):
        auth = self.run_audit()["authorizations"]
        self.assertTrue(auth["bounded_manual_contrast_event_coding"])
        self.assertEqual(auth["maximum_source_count"], 9)
        self.assertEqual(auth["maximum_sampling_slot_count"], 90)
        self.assertEqual(auth["maximum_accepted_event_count"], 90)
        self.assertTrue(auth["restricted_local_researcher_paraphrase_storage"])
        for field in (
            "public_event_level_content_storage",
            "target_calibration_behavior_coding",
            "rater_recruitment",
            "rating_collection",
            "model_execution",
            "runtime_change",
            "prompt_change",
            "memory_change",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(auth[field], field)

    def test_mutation_search_start_fails(self):
        mutated = copy.deepcopy(self.frame)
        mutated["sampling_slots"][0]["search_start_seconds"] += 1
        report = self.run_audit(frame=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("sampling_frame", report["violations"])

    def test_mutation_global_order_fails(self):
        mutated = copy.deepcopy(self.frame)
        mutated["sampling_slots"][0]["global_review_order"] = 90
        report = self.run_audit(frame=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("sampling_frame", report["violations"])

    def test_mutation_convenience_sampling_fails(self):
        mutated = copy.deepcopy(self.preregistration)
        mutated["sampling_contract"]["convenience_sampling_forbidden"] = False
        report = self.run_audit(preregistration=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("sampling_contract", report["violations"])

    def test_mutation_first_eligible_event_rule_fails(self):
        mutated = copy.deepcopy(self.preregistration)
        mutated["sampling_contract"][
            "first_eligible_event_at_or_after_search_start_required"
        ] = False
        report = self.run_audit(preregistration=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("sampling_contract", report["violations"])

    def test_mutation_sampling_algorithm_fails(self):
        for field in (
            "stratum_boundary_algorithm",
            "search_start_algorithm",
            "global_review_order_algorithm",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.preregistration)
                mutated["sampling_contract"][field] = "posthoc_or_different_rule"
                report = self.run_audit(preregistration=mutated)
                self.assertFalse(report["protocol_passed"])
                self.assertIn("sampling_contract", report["violations"])

    def test_every_event_eligibility_rule_is_audited(self):
        for field in self.preregistration["event_eligibility_contract"]:
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.preregistration)
                mutated["event_eligibility_contract"][field] = False
                report = self.run_audit(preregistration=mutated)
                self.assertFalse(report["protocol_passed"])
                self.assertIn("eligibility", report["violations"])

    def test_custom_frame_bindings_follow_custom_input_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            preregistration_path = Path(temporary) / "preregistration.json"
            manifest_path = Path(temporary) / "manifest.json"
            preregistration_path.write_bytes(DEFAULT_PREREGISTRATION.read_bytes())
            manifest_path.write_bytes(DEFAULT_CONTRAST_MANIFEST.read_bytes())
            frame = build_sampling_frame(
                self.preregistration,
                self.contrast_manifest,
                root=ROOT,
                preregistration_path=preregistration_path,
                contrast_manifest_path=manifest_path,
            )
            self.assertEqual(
                frame["preregistration_binding"]["sha256"],
                hashlib.sha256(preregistration_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                frame["contrast_manifest_binding"]["sha256"],
                hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                frame["preregistration_binding"]["path"],
                str(preregistration_path.resolve()),
            )

    def test_mutation_copied_quote_or_system_visibility_fails(self):
        for field in (
            "copied_quote_allowed",
            "system_output_persona_score_and_target_hypothesis_visible_to_coders",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.preregistration)
                mutated["coding_contract"][field] = True
                report = self.run_audit(preregistration=mutated)
                self.assertFalse(report["protocol_passed"])
                self.assertIn("coding", report["violations"])

    def test_mutation_actor_blinding_claim_fails(self):
        mutated = copy.deepcopy(self.preregistration)
        mutated["coding_contract"]["actor_identity_blinding_feasible"] = True
        report = self.run_audit(preregistration=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("coding", report["violations"])

    def test_mutation_rights_training_or_publication_fails(self):
        for field in (
            "model_training",
            "public_event_level_paraphrase_or_quote_storage",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.rights_v2)
                mutated["review_policy"][field] = True
                report = self.run_audit(rights_v2=mutated)
                self.assertFalse(report["protocol_passed"])
                self.assertIn("rights", report["violations"])

    def test_mutation_nonzero_content_count_fails(self):
        mutated = copy.deepcopy(self.frame)
        mutated["current_counts"]["coded_event_count"] = 1
        report = self.run_audit(frame=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("count_honesty", report["violations"])

    def test_failed_frame_reports_observed_not_expected_slot_count(self):
        mutated = copy.deepcopy(self.frame)
        mutated["sampling_slots"].pop()
        report = self.run_audit(frame=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertEqual(report["summary"]["sampling_slot_count"], 89)

    def test_method_or_alpha_gate_mutation_fails(self):
        mutated_method = copy.deepcopy(self.method_registry)
        mutated_method["sources"].pop()
        report = self.run_audit(method_registry=mutated_method)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("method", report["violations"])
        mutated_prereg = copy.deepcopy(self.preregistration)
        mutated_prereg["reliability_contract"]["nominal_alpha_reliable_min"] = 0.5
        report = self.run_audit(preregistration=mutated_prereg)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("reliability", report["violations"])

    def test_report_inputs_are_hash_bound_without_freezing_whole_gitignore(self):
        report = build_audit_from_paths()
        self.assertEqual(len(report["inputs"]), 9)
        self.assertNotIn("gitignore", report["inputs"])
        for artifact in report["inputs"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                artifact["sha256"], hashlib.sha256(path.read_bytes()).hexdigest()
            )

    def test_cli_refuses_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_json = Path(temporary) / "audit.json"
            output_md = Path(temporary) / "audit.md"
            command = [
                sys.executable,
                str(SCRIPT),
                "--output-json",
                str(output_json),
                "--output-md",
                str(output_md),
            ]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)

    def test_require_execution_ready_exits_two_without_model_activity(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output-json",
                    str(Path(temporary) / "audit.json"),
                    "--output-md",
                    str(Path(temporary) / "audit.md"),
                    "--require-execution-ready",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["formal_execution_ready"])

    def test_markdown_explains_search_slots_are_not_events(self):
        markdown = (ROOT / "reports/public_persona_contrast_event_coding_v5_audit.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("搜尋層不是事件", markdown)
        self.assertIn("第一個合格的完整事件", markdown)
        self.assertIn("人物身分盲化", markdown)
        self.assertIn("內容仍是零", markdown)
        self.assertIn("不進 Git", markdown)


if __name__ == "__main__":
    unittest.main()
