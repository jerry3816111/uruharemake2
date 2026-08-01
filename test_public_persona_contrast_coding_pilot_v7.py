import copy
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path

from public_persona_contrast_coding_pilot_v7 import (
    DEFAULT_CODEBOOK,
    DEFAULT_CODER_MANUAL,
    DEFAULT_FULL_FRAME,
    DEFAULT_GITIGNORE,
    DEFAULT_PILOT_FRAME,
    DEFAULT_PREREGISTRATION,
    DEFAULT_SOURCE_MANIFEST,
    DEFAULT_V6_RESULT,
    EXPERIMENT_ID,
    FAIL_DECISION,
    PASS_DECISION,
    build_construction_audit,
    build_pilot_frame,
    build_pilot_reliability,
    make_pilot_handler,
    render_pilot_page,
    validate_coder_manual,
    validate_pilot_frame,
)
from public_persona_contrast_coding_tool_v6 import (
    initialize_ledger,
    load_json,
    normalize_entry,
    save_entry,
    sha256_file,
)


class PublicPersonaContrastCodingPilotV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)
        cls.v6_result = load_json(DEFAULT_V6_RESULT)
        cls.full_frame = load_json(DEFAULT_FULL_FRAME)
        cls.pilot_frame = load_json(DEFAULT_PILOT_FRAME)
        cls.codebook = load_json(DEFAULT_CODEBOOK)
        cls.coder_manual = load_json(DEFAULT_CODER_MANUAL)
        cls.source_manifest = load_json(DEFAULT_SOURCE_MANIFEST)

    def construction_audit(self, **overrides):
        return build_construction_audit(
            copy.deepcopy(overrides.get("preregistration", self.preregistration)),
            copy.deepcopy(overrides.get("v6_result", self.v6_result)),
            copy.deepcopy(overrides.get("full_frame", self.full_frame)),
            copy.deepcopy(overrides.get("pilot_frame", self.pilot_frame)),
            copy.deepcopy(overrides.get("codebook", self.codebook)),
            copy.deepcopy(overrides.get("coder_manual", self.coder_manual)),
            overrides.get(
                "gitignore_text", DEFAULT_GITIGNORE.read_text(encoding="utf-8")
            ),
        )

    def selected_payload(self, slot, offset=0):
        index = slot["pilot_review_order"] - 1
        dimensions = self.codebook["dimensions"]
        start = slot["search_start_seconds"] + offset
        return {
            "sampling_slot_id": slot["sampling_slot_id"],
            "slot_status": "selected_event",
            "timestamp_locator_start_seconds": start,
            "timestamp_locator_end_seconds": start + 2,
            "context_family": self.codebook["context_families"][
                index % len(self.codebook["context_families"])
            ],
            "observable_context_paraphrase": "合成測試情境，不是真實內容",
            "observable_behavior_paraphrase": "合成測試行為，不是真實內容",
            "primary_dimension": dimensions[index % len(dimensions)],
            "secondary_dimensions": [dimensions[(index + 1) % len(dimensions)]],
            "dialogue_act_or_action_label": self.codebook[
                "dialogue_act_or_action_labels"
            ][index % len(self.codebook["dialogue_act_or_action_labels"])],
            "observable_audience_relation": self.codebook["audience_relations"][
                index % len(self.codebook["audience_relations"])
            ],
            "evidence_strength": self.codebook["evidence_strengths"][
                index % len(self.codebook["evidence_strengths"])
            ],
            "ambiguity_notes": "",
            "alternative_interpretations": "",
            "first_eligible_event_attestation": True,
            "paraphrase_and_no_quote_attestation": True,
        }

    def complete_ledger(self, coder):
        ledger = {
            "schema": "uruha_public_persona_contrast_independent_coder_ledger_v6",
            "experiment_id": "public_persona_contrast_coding_tool_v6",
            "status": "private_independent_coding_ledger",
            "coder_pseudonym": coder,
            "created_at": "2026-08-01T00:00:00+00:00",
            "updated_at": "2026-08-01T00:00:00+00:00",
            "frame_binding": {
                "path": "datasets/public_persona_contrast_event_sampling_frame_v5.json",
                "sha256": sha256_file(DEFAULT_FULL_FRAME),
            },
            "codebook_binding": {
                "path": "configs/public_persona_contrast_coding_codebook_v6.json",
                "sha256": sha256_file(DEFAULT_CODEBOOK),
            },
            "entries": {},
            "data_boundary": {
                "private_gitignored_storage_required": True,
                "other_coder_ledger_visible": False,
                "model_output_or_persona_score_visible": False,
                "raw_or_verbatim_content_allowed": False,
                "prompt_memory_retrieval_training_or_model_selection_use": False,
            },
        }
        for slot in self.pilot_frame["sampling_slots"]:
            ledger["entries"][slot["sampling_slot_id"]] = normalize_entry(
                self.selected_payload(slot), slot, self.codebook, coder
            )
        return ledger

    def test_frozen_frame_is_byte_equivalent_to_deterministic_rebuild(self):
        rebuilt = build_pilot_frame(self.full_frame)
        serialized = json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(
            DEFAULT_PILOT_FRAME.read_text(encoding="utf-8"), serialized
        )
        self.assertEqual(validate_pilot_frame(rebuilt, self.full_frame), [])

    def test_frame_has_one_early_and_one_late_slot_for_each_source(self):
        slots = self.pilot_frame["sampling_slots"]
        self.assertEqual(len(slots), 18)
        self.assertEqual(len({row["source_id"] for row in slots}), 9)
        counts = Counter((row["source_id"], row["pilot_half"]) for row in slots)
        self.assertEqual(set(counts.values()), {1})
        self.assertEqual(len(counts), 18)
        for row in slots:
            allowed = range(1, 6) if row["pilot_half"] == "early" else range(6, 11)
            self.assertIn(row["slot_index"], allowed)

    def test_selected_rows_preserve_original_v5_source_and_search_metadata(self):
        originals = {
            row["sampling_slot_id"]: row
            for row in self.full_frame["sampling_slots"]
        }
        preserved = (
            "sampling_slot_id",
            "source_id",
            "source_partition_key",
            "source_duration_seconds",
            "slot_index",
            "stratum_start_seconds",
            "stratum_end_exclusive_seconds",
            "search_start_seconds",
            "actor_id",
            "topic_cell",
            "match_granularity",
        )
        for selected in self.pilot_frame["sampling_slots"]:
            original = originals[selected["sampling_slot_id"]]
            for field in preserved:
                self.assertEqual(selected[field], original[field], field)

    def test_frame_mutation_or_nonzero_data_count_fails_validation(self):
        mutated = copy.deepcopy(self.pilot_frame)
        mutated["sampling_slots"][0]["search_start_seconds"] += 1
        self.assertIn(
            "pilot_frame_does_not_match_rebuild",
            validate_pilot_frame(mutated, self.full_frame),
        )
        mutated = copy.deepcopy(self.pilot_frame)
        mutated["current_counts"]["selected_event_count"] = 1
        self.assertIn(
            "pilot_counts_nonzero", validate_pilot_frame(mutated, self.full_frame)
        )

    def test_construction_passes_with_zero_human_model_and_persona_data(self):
        report = self.construction_audit()
        self.assertTrue(report["construction_passed"])
        self.assertEqual(report["decision"], PASS_DECISION)
        self.assertEqual(report["summary"]["check_pass_count"], 9)
        self.assertEqual(report["summary"]["check_count"], 9)
        self.assertEqual(report["violations"], [])
        for field in (
            "private_ledger_count",
            "content_reviewed_source_count",
            "selected_event_count",
            "coded_event_count",
            "human_coder_count",
            "model_output_count",
            "persona_score_count",
            "holdout_content_review_count",
            "model_call_count",
        ):
            self.assertEqual(report["summary"][field], 0, field)

    def test_sampling_or_human_contract_mutation_blocks_pilot(self):
        mutated = copy.deepcopy(self.preregistration)
        mutated["pilot_sampling_contract"][
            "behavior_content_used_for_slot_selection"
        ] = True
        report = self.construction_audit(preregistration=mutated)
        self.assertFalse(report["construction_passed"])
        self.assertEqual(report["decision"], FAIL_DECISION)
        mutated = copy.deepcopy(self.preregistration)
        mutated["human_contract"]["distinct_consenting_human_coder_count_exact"] = 1
        self.assertFalse(
            self.construction_audit(preregistration=mutated)["construction_passed"]
        )

    def test_manual_defines_every_frozen_category_without_target_answers(self):
        self.assertEqual(validate_coder_manual(self.coder_manual, self.codebook), [])
        for field in (
            "categories_define_target_answers",
            "target_specific_examples_present",
            "real_source_quotes_present",
            "private_motive_inference_allowed",
        ):
            self.assertFalse(self.coder_manual[field], field)

    def test_manual_category_or_target_answer_mutation_blocks_pilot(self):
        mutated = copy.deepcopy(self.coder_manual)
        mutated["dimension_definitions"].pop(
            next(iter(mutated["dimension_definitions"]))
        )
        report = self.construction_audit(coder_manual=mutated)
        self.assertFalse(report["construction_passed"])
        mutated = copy.deepcopy(self.coder_manual)
        mutated["categories_define_target_answers"] = True
        report = self.construction_audit(coder_manual=mutated)
        self.assertFalse(report["construction_passed"])

    def test_pilot_page_shows_only_18_slots_and_clamps_last_navigation(self):
        ledger = self.complete_ledger("coder_a")
        page = render_pilot_page(
            ledger,
            self.pilot_frame,
            self.source_manifest,
            self.codebook,
            self.coder_manual,
            "secret-token",
            18,
        )
        self.assertIn("Contrast Coding Pilot V7", page)
        self.assertIn("Pilot progress: 18/18", page)
        self.assertIn("Pilot slot: 18/18", page)
        self.assertNotIn("/90", page)
        self.assertNotIn("slot=19", page)
        self.assertIn("V7 編碼手冊", page)
        self.assertIn("不是任何人物的標準答案", page)

    def test_nonpilot_full_frame_slot_cannot_be_saved(self):
        pilot_ids = {
            row["sampling_slot_id"] for row in self.pilot_frame["sampling_slots"]
        }
        outside = next(
            row
            for row in self.full_frame["sampling_slots"]
            if row["sampling_slot_id"] not in pilot_ids
        )
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            ledger_path, _ = initialize_ledger(
                "coder_a", "a.json", private_root=private_root
            )
            with self.assertRaisesRegex(ValueError, "unknown sampling slot"):
                save_entry(
                    ledger_path,
                    self.selected_payload(
                        {**outside, "pilot_review_order": 1}
                    ),
                    frame=self.pilot_frame,
                    codebook=self.codebook,
                    private_root=private_root,
                )

    def test_local_pilot_server_requires_token_and_serves_18_slot_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            ledger_path, _ = initialize_ledger(
                "coder_a", "a.json", private_root=private_root
            )
            token = "fixed-test-token"
            handler = make_pilot_handler(
                ledger_path,
                private_root,
                token,
                self.full_frame,
                self.pilot_frame,
                self.source_manifest,
                self.codebook,
                self.coder_manual,
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(base + "/", timeout=2)
                self.assertEqual(caught.exception.code, 403)
                with urllib.request.urlopen(
                    base + "/?token=fixed-test-token&slot=1", timeout=2
                ) as response:
                    page = response.read().decode("utf-8")
                    self.assertEqual(response.status, 200)
                    self.assertIn("Pilot progress: 0/18", page)
                    self.assertIn("Pilot slot: 1/18", page)
                    self.assertNotIn("/90", page)
                    self.assertIn("事件起點與終點", page)
                    self.assertIn(
                        "default-src 'none'",
                        response.headers["Content-Security-Policy"],
                    )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_perfect_synthetic_ledgers_authorize_only_full_manual_coding(self):
        report = build_pilot_reliability(
            self.complete_ledger("coder_a"), self.complete_ledger("coder_b")
        )
        self.assertTrue(report["gates"]["codebook_pilot_reliability_passed"])
        self.assertTrue(report["gates"]["full_v5_coding_authorized"])
        self.assertFalse(report["gates"]["aggregate_behavior_profile_authorized"])
        self.assertFalse(report["gates"]["persona_similarity_comparison_authorized"])
        self.assertFalse(report["persona_score_computed"])
        self.assertEqual(report["completion"]["expected_slot_count_per_coder"], 18)

    def test_incomplete_same_coder_or_low_temporal_overlap_blocks_pilot(self):
        ledger_a = self.complete_ledger("coder_a")
        incomplete = self.complete_ledger("coder_a")
        incomplete["entries"].pop(next(iter(incomplete["entries"])))
        report = build_pilot_reliability(ledger_a, incomplete)
        self.assertFalse(report["gates"]["codebook_pilot_reliability_passed"])
        self.assertFalse(report["gates"]["coder_pseudonyms_distinct"])
        self.assertFalse(report["gates"]["both_ledgers_complete_and_valid"])

        shifted = self.complete_ledger("coder_b")
        for entry in shifted["entries"].values():
            entry["timestamp_locator_start_seconds"] += 5
            entry["timestamp_locator_end_seconds"] += 5
        report = build_pilot_reliability(ledger_a, shifted)
        self.assertFalse(report["gates"]["temporal_iou_gate_passed"])
        self.assertFalse(report["gates"]["codebook_pilot_reliability_passed"])
        self.assertFalse(report["gates"]["full_v5_coding_authorized"])

    def test_reliability_report_contains_no_event_text_or_persona_score(self):
        report = build_pilot_reliability(
            self.complete_ledger("coder_a"), self.complete_ledger("coder_b")
        )
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("合成測試情境", serialized)
        self.assertNotIn("合成測試行為", serialized)
        self.assertFalse(report["contains_event_text"])
        self.assertFalse(report["contains_model_output"])
        self.assertFalse(report["persona_score_computed"])

    def test_experiment_id_is_stable(self):
        self.assertEqual(EXPERIMENT_ID, "public_persona_contrast_coding_pilot_v7")


if __name__ == "__main__":
    unittest.main()
