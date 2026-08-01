import copy
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from public_persona_contrast_coding_tool_v6 import (
    DEFAULT_CODEBOOK,
    DEFAULT_FRAME,
    DEFAULT_GITIGNORE,
    DEFAULT_PREREGISTRATION,
    DEFAULT_SOURCE_MANIFEST,
    DEFAULT_V5_RESULT,
    FAIL_DECISION,
    PASS_DECISION,
    build_construction_audit,
    build_construction_audit_from_paths,
    build_official_watch_url,
    build_reliability_report,
    frame_slots_by_id,
    initialize_ledger,
    load_json,
    make_handler,
    nominal_krippendorff_alpha,
    normalize_entry,
    render_coding_page,
    resolve_private_path,
    save_entry,
    temporal_iou,
    validate_entry,
    validate_ledger,
)


class PublicPersonaContrastCodingToolV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)
        cls.codebook = load_json(DEFAULT_CODEBOOK)
        cls.v5_result = load_json(DEFAULT_V5_RESULT)
        cls.frame = load_json(DEFAULT_FRAME)
        cls.source_manifest = load_json(DEFAULT_SOURCE_MANIFEST)
        cls.slots = frame_slots_by_id(cls.frame)

    def construction_audit(self, **overrides):
        from public_persona_contrast_coding_tool_v6 import DEFAULT_EVENT_SCHEMA

        return build_construction_audit(
            copy.deepcopy(overrides.get("preregistration", self.preregistration)),
            copy.deepcopy(overrides.get("codebook", self.codebook)),
            copy.deepcopy(overrides.get("v5_result", self.v5_result)),
            copy.deepcopy(overrides.get("frame", self.frame)),
            load_json(DEFAULT_EVENT_SCHEMA),
            copy.deepcopy(overrides.get("source_manifest", self.source_manifest)),
            overrides.get(
                "gitignore_text", DEFAULT_GITIGNORE.read_text(encoding="utf-8")
            ),
        )

    def selected_payload(self, slot, offset=0):
        dimensions = self.codebook["dimensions"]
        index = slot["slot_index"] - 1
        primary = dimensions[index % len(dimensions)]
        secondary = dimensions[(index + 1) % len(dimensions)]
        start = slot["search_start_seconds"] + offset
        return {
            "sampling_slot_id": slot["sampling_slot_id"],
            "slot_status": "selected_event",
            "timestamp_locator_start_seconds": start,
            "timestamp_locator_end_seconds": start + 1,
            "context_family": self.codebook["context_families"][
                index % len(self.codebook["context_families"])
            ],
            "observable_context_paraphrase": "研究者改寫的可觀察情境",
            "observable_behavior_paraphrase": "研究者改寫的可觀察行為",
            "primary_dimension": primary,
            "secondary_dimensions": [secondary],
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
                "sha256": "79e183ff05fee7cbc361842d9064cb33ac00b27c28042ac23894e7b0605470a2",
            },
            "codebook_binding": {
                "path": "configs/public_persona_contrast_coding_codebook_v6.json",
                "sha256": "b7336503fdc18849e31ce6679e7897824193d237b0400c84500ebee6d51f84e1",
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
        for slot in self.frame["sampling_slots"]:
            ledger["entries"][slot["sampling_slot_id"]] = normalize_entry(
                self.selected_payload(slot), slot, self.codebook, coder
            )
        return ledger

    def test_construction_audit_passes_with_zero_data(self):
        report = build_construction_audit_from_paths()
        self.assertTrue(report["construction_passed"])
        self.assertEqual(report["decision"], PASS_DECISION)
        self.assertEqual(report["summary"]["check_pass_count"], 10)
        self.assertEqual(report["summary"]["check_count"], 10)
        for field in (
            "private_ledger_count",
            "content_reviewed_source_count",
            "selected_event_count",
            "coded_event_count",
            "model_output_count",
            "persona_score_count",
            "holdout_content_review_count",
            "model_call_count",
        ):
            self.assertEqual(report["summary"][field], 0, field)

    def test_construction_mutations_fail(self):
        mutated = copy.deepcopy(self.preregistration)
        mutated["ledger_contract"]["other_coder_ledger_visible_during_entry"] = True
        report = self.construction_audit(preregistration=mutated)
        self.assertFalse(report["construction_passed"])
        self.assertEqual(report["decision"], FAIL_DECISION)
        mutated = copy.deepcopy(self.codebook)
        mutated["text_contract"]["copied_quote_allowed"] = True
        report = self.construction_audit(codebook=mutated)
        self.assertFalse(report["construction_passed"])
        mutated = copy.deepcopy(self.preregistration)
        mutated["ui_contract"]["video_embedding_or_download"] = True
        report = self.construction_audit(preregistration=mutated)
        self.assertFalse(report["construction_passed"])

    def test_private_path_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            outside = Path(temporary) / "outside.json"
            with self.assertRaises(ValueError):
                resolve_private_path(outside, private_root)

    def test_initialize_ledger_is_private_empty_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            path, ledger = initialize_ledger(
                "coder_a", "a.json", private_root=private_root
            )
            self.assertEqual(ledger["entries"], {})
            self.assertEqual(ledger["coder_pseudonym"], "coder_a")
            self.assertEqual(os.stat(path.parent).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                initialize_ledger("coder_a", "a.json", private_root=private_root)

    def test_invalid_coder_pseudonym_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                initialize_ledger(
                    "real name with spaces",
                    "a.json",
                    private_root=Path(temporary),
                )

    def test_watch_url_uses_frozen_video_and_search_start(self):
        slot = self.frame["sampling_slots"][0]
        url = build_official_watch_url(slot)
        video_id = slot["source_partition_key"].removeprefix("youtube_archive_")
        self.assertEqual(
            url,
            f"https://www.youtube.com/watch?v={video_id}&t={slot['search_start_seconds']}s",
        )

    def test_selected_entry_requires_attestations_and_valid_time(self):
        slot = self.frame["sampling_slots"][0]
        payload = self.selected_payload(slot)
        payload["paraphrase_and_no_quote_attestation"] = False
        entry = normalize_entry(payload, slot, self.codebook, "coder_a")
        errors = validate_entry(entry, slot, self.codebook, "coder_a")
        self.assertIn("paraphrase_and_no_quote_attestation:required", errors)
        payload = self.selected_payload(slot)
        payload["timestamp_locator_start_seconds"] = slot["search_start_seconds"] - 1
        entry = normalize_entry(payload, slot, self.codebook, "coder_a")
        errors = validate_entry(entry, slot, self.codebook, "coder_a")
        self.assertIn("timestamp_locator_start_seconds:before_search_start", errors)

    def test_forbidden_or_unknown_entry_field_is_rejected(self):
        slot = self.frame["sampling_slots"][0]
        entry = normalize_entry(
            self.selected_payload(slot), slot, self.codebook, "coder_a"
        )
        entry["transcript"] = "forbidden"
        errors = validate_entry(entry, slot, self.codebook, "coder_a")
        self.assertIn("forbidden_payload_field", errors)
        self.assertTrue(any(error.startswith("unexpected_fields:") for error in errors))

    def test_nonselected_status_strips_event_payload(self):
        slot = self.frame["sampling_slots"][0]
        payload = self.selected_payload(slot)
        payload["slot_status"] = "no_eligible_event"
        entry = normalize_entry(payload, slot, self.codebook, "coder_a")
        self.assertEqual(set(entry), {
            "sampling_slot_id",
            "source_id",
            "source_partition_key",
            "coder_pseudonym",
            "slot_status",
            "first_eligible_event_attestation",
            "updated_at",
        })
        self.assertEqual(validate_entry(entry, slot, self.codebook, "coder_a"), [])

    def test_save_entry_is_atomic_and_validated(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            path, _ = initialize_ledger(
                "coder_a", "a.json", private_root=private_root
            )
            slot = self.frame["sampling_slots"][0]
            ledger = save_entry(
                path,
                self.selected_payload(slot),
                frame=self.frame,
                codebook=self.codebook,
                private_root=private_root,
            )
            self.assertIn(slot["sampling_slot_id"], ledger["entries"])
            self.assertEqual(
                validate_ledger(ledger, self.frame, self.codebook), []
            )

    def test_overlapping_selected_events_are_rejected(self):
        ledger = self.complete_ledger("coder_a")
        first_two = sorted(
            [
                slot
                for slot in self.frame["sampling_slots"]
                if slot["source_id"] == self.frame["sampling_slots"][0]["source_id"]
            ],
            key=lambda slot: slot["slot_index"],
        )[:2]
        first = ledger["entries"][first_two[0]["sampling_slot_id"]]
        second = ledger["entries"][first_two[1]["sampling_slot_id"]]
        first["timestamp_locator_end_seconds"] = second[
            "timestamp_locator_start_seconds"
        ] + 1
        errors = validate_ledger(ledger, self.frame, self.codebook)
        self.assertTrue(any(error.startswith("overlap:") for error in errors))

    def test_temporal_iou_examples(self):
        self.assertEqual(temporal_iou(10, 20, 10, 20), 1.0)
        self.assertEqual(temporal_iou(10, 20, 20, 30), 0.0)
        self.assertAlmostEqual(temporal_iou(10, 20, 15, 25), 5 / 15)

    def test_nominal_alpha_perfect_varied_labels_is_one(self):
        self.assertEqual(
            nominal_krippendorff_alpha([("a", "a"), ("b", "b"), ("a", "a")]),
            1.0,
        )
        self.assertIsNone(nominal_krippendorff_alpha([("a", "a"), ("a", "a")]))

    def test_perfect_complete_ledgers_pass_reliability_without_persona_score(self):
        ledger_a = self.complete_ledger("coder_a")
        ledger_b = self.complete_ledger("coder_b")
        report = build_reliability_report(
            ledger_a, ledger_b, self.frame, self.codebook
        )
        self.assertTrue(report["gates"]["reliability_passed"])
        self.assertTrue(report["gates"]["aggregate_behavior_profile_authorized"])
        self.assertFalse(report["gates"]["persona_similarity_comparison_authorized"])
        self.assertFalse(report["persona_score_computed"])
        self.assertEqual(
            report["unitizing_reliability"]["slot_status_percent_agreement"], 1.0
        )
        self.assertEqual(
            report["unitizing_reliability"]["joint_selected_temporal_iou_mean"],
            1.0,
        )
        self.assertTrue(
            all(
                value == 1.0
                for value in report["nominal_reliability"][
                    "krippendorff_alpha"
                ].values()
            )
        )

    def test_incomplete_or_same_coder_ledgers_block_reliability(self):
        ledger_a = self.complete_ledger("coder_a")
        ledger_b = self.complete_ledger("coder_a")
        ledger_b["entries"].pop(next(iter(ledger_b["entries"])))
        report = build_reliability_report(
            ledger_a, ledger_b, self.frame, self.codebook
        )
        self.assertFalse(report["gates"]["reliability_passed"])
        self.assertFalse(report["gates"]["coder_pseudonyms_distinct"])
        self.assertFalse(report["gates"]["both_ledgers_complete_and_valid"])

    def test_invalid_ledger_returns_errors_without_crashing_report(self):
        ledger_a = self.complete_ledger("coder_a")
        ledger_b = self.complete_ledger("coder_b")
        first = next(iter(ledger_b["entries"].values()))
        first.pop("timestamp_locator_end_seconds")
        report = build_reliability_report(
            ledger_a, ledger_b, self.frame, self.codebook
        )
        self.assertGreater(report["validation"]["coder_b_error_count"], 0)
        self.assertFalse(report["gates"]["reliability_passed"])

    def test_reliability_report_contains_no_event_text(self):
        report = build_reliability_report(
            self.complete_ledger("coder_a"),
            self.complete_ledger("coder_b"),
            self.frame,
            self.codebook,
        )
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("研究者改寫的可觀察情境", serialized)
        self.assertNotIn("研究者改寫的可觀察行為", serialized)
        self.assertTrue(report["contains_event_text"] is False)

    def test_rendered_page_contains_only_current_coder_and_official_link(self):
        ledger = self.complete_ledger("coder_a")
        page = render_coding_page(
            ledger,
            self.frame,
            self.source_manifest,
            self.codebook,
            "secret-token",
            1,
        )
        self.assertIn("coder_a", page)
        self.assertNotIn("coder_b", page)
        self.assertIn("https://www.youtube.com/watch?v=", page)
        self.assertIn("secret-token", page)
        self.assertIn("另一位編碼者答案", page)

    def test_local_server_requires_token_and_serves_no_external_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            ledger_path, _ = initialize_ledger(
                "coder_a", "a.json", private_root=private_root
            )
            token = "fixed-test-token"
            handler = make_handler(
                ledger_path,
                private_root,
                token,
                self.frame,
                self.source_manifest,
                self.codebook,
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
                    self.assertIn("在官方 YouTube 開啟時間點", page)
                    self.assertIn("找到合格事件", page)
                    self.assertNotIn("<script src=", page)
                    self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
