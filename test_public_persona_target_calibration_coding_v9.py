import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path

import public_persona_target_calibration_coding_v9 as v9


class TargetCalibrationCodingV9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = v9.load_json(v9.DEFAULT_PREREGISTRATION)
        cls.metadata = v9.load_json(v9.DEFAULT_SOURCE_METADATA)
        cls.frame = v9.build_sampling_frame(cls.preregistration, cls.metadata)
        cls.codebook = v9.load_json(v9.DEFAULT_CODEBOOK)

    def test_sampling_frame_is_deterministic_and_balanced(self):
        rebuilt = v9.build_sampling_frame(self.preregistration, self.metadata)
        self.assertEqual(self.frame, rebuilt)
        self.assertEqual([], v9.validate_sampling_frame(
            self.frame, self.preregistration, self.metadata
        ))
        counts = Counter(row["source_id"] for row in self.frame["sampling_slots"])
        self.assertEqual(
            Counter({source_id: 10 for source_id in v9.AUTHORIZED_SOURCE_IDS}),
            counts,
        )

    def test_all_search_starts_are_inside_their_strata(self):
        self.assertEqual(
            set(range(1, 31)),
            {row["global_review_order"] for row in self.frame["sampling_slots"]},
        )
        for row in self.frame["sampling_slots"]:
            self.assertLessEqual(row["stratum_start_seconds"], row["search_start_seconds"])
            self.assertLess(row["search_start_seconds"], row["stratum_end_exclusive_seconds"])
            self.assertLessEqual(
                row["stratum_end_exclusive_seconds"], row["source_duration_seconds"]
            )

    def test_metadata_and_frame_exclude_holdout_and_behavior_payloads(self):
        source_ids = {row["source_id"] for row in self.metadata["sources"]}
        self.assertFalse(source_ids & v9.FORBIDDEN_HOLDOUT_SOURCE_IDS)
        self.assertEqual([], v9._find_prohibited_keys(self.metadata))
        self.assertEqual([], v9._find_prohibited_keys(self.frame))
        self.assertFalse(self.metadata["content_boundary"]["behavior_content_reviewed"])
        self.assertFalse(self.frame["content_boundary"]["final_holdout_source_included"])

    def test_human_use_is_blocked_without_v7_reliability_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            missing_lock = Path(temporary) / "missing.json"
            authorized, reason = v9.human_use_authorized(missing_lock)
            self.assertFalse(authorized)
            self.assertIn("absent", reason)
            with self.assertRaises(PermissionError):
                v9.initialize_target_ledger(
                    "coder_a", "coder_a.json", missing_lock, private_root
                )

    def _write_authorization_lock(self, root):
        path = Path(root) / "v7_reliability.json"
        path.write_text(
            json.dumps(
                {
                    "decision": v9.REQUIRED_V7_DECISION,
                    "reliability_passed": True,
                    "persona_score_computed": False,
                    "frozen_artifacts": {"codebook": v9._binding(v9.DEFAULT_CODEBOOK)},
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_authorized_ledger_is_private_bound_and_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            lock = self._write_authorization_lock(temporary)
            path, ledger = v9.initialize_target_ledger(
                "coder_a", "coder_a.json", lock, private_root
            )
            self.assertTrue(path.is_file())
            self.assertEqual(v9.LEDGER_SCHEMA, ledger["schema"])
            self.assertEqual([], v9.validate_target_ledger(
                ledger, self.frame, self.codebook, expected_coder="coder_a"
            ))
            outside = Path(temporary) / "outside.json"
            with self.assertRaises(ValueError):
                v9.initialize_target_ledger(
                    "coder_b", outside, lock, private_root
                )

    def test_entry_validation_rejects_posthoc_or_out_of_stratum_selection(self):
        slot = self.frame["sampling_slots"][0]
        entry = {
            "sampling_slot_id": slot["sampling_slot_id"],
            "source_id": slot["source_id"],
            "source_partition_key": slot["source_partition_key"],
            "coder_pseudonym": "coder_a",
            "slot_status": "selected_event",
            "first_eligible_event_attestation": True,
            "updated_at": "2026-08-01T00:00:00+00:00",
            "timestamp_locator_start_seconds": slot["search_start_seconds"] - 1,
            "timestamp_locator_end_seconds": slot["search_start_seconds"] + 1,
            "context_family": self.codebook["context_families"][0],
            "observable_context_paraphrase": "context paraphrase",
            "observable_behavior_paraphrase": "behavior paraphrase",
            "primary_dimension": self.codebook["dimensions"][0],
            "secondary_dimensions": [],
            "dialogue_act_or_action_label": self.codebook[
                "dialogue_act_or_action_labels"
            ][0],
            "observable_audience_relation": self.codebook["audience_relations"][0],
            "evidence_strength": self.codebook["evidence_strengths"][0],
            "ambiguity_notes": "",
            "alternative_interpretations": "",
            "paraphrase_and_no_quote_attestation": True,
        }
        errors = v9.validate_entry(entry, slot, self.codebook, "coder_a")
        self.assertIn("timestamp_locator_start_seconds:before_search_start", errors)
        entry["target_reply"] = "forbidden"
        self.assertIn("forbidden_payload_field", v9.validate_entry(
            entry, slot, self.codebook, "coder_a"
        ))

    def test_local_page_has_thirty_slots_and_only_official_watch_locator(self):
        ledger = {
            "coder_pseudonym": "coder_a",
            "entries": {},
        }
        page = v9.render_target_page(
            ledger, self.frame, self.codebook, "token", 1
        )
        self.assertIn("Progress: 0/30", page)
        self.assertIn("www.youtube.com/watch?v=", page)
        self.assertNotIn("iframe", page.lower())
        self.assertNotIn("transcript", page.lower())
        self.assertNotIn("model output", page.lower())

    def test_local_server_requires_session_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary) / "private"
            lock = self._write_authorization_lock(temporary)
            ledger_path, _ = v9.initialize_target_ledger(
                "coder_a", "coder_a.json", lock, private_root
            )
            token = "frozen-test-token"
            handler = v9.make_target_handler(
                ledger_path, private_root, token, self.frame, self.codebook
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urllib.request.urlopen(f"{base}/health") as response:
                    self.assertEqual(b"ok", response.read())
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    urllib.request.urlopen(f"{base}/?slot=1")
                self.assertEqual(403, denied.exception.code)
                with urllib.request.urlopen(
                    f"{base}/?token={token}&slot=1"
                ) as response:
                    body = response.read().decode("utf-8")
                self.assertIn("Progress: 0/30", body)
                self.assertEqual("no-store", response.headers["Cache-Control"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def _complete_ledger(self, coder, lock_path):
        ledger = {
            "schema": v9.LEDGER_SCHEMA,
            "experiment_id": v9.EXPERIMENT_ID,
            "status": "private_independent_target_calibration_ledger",
            "coder_pseudonym": coder,
            "created_at": "2026-08-01T00:00:00+00:00",
            "updated_at": "2026-08-01T00:00:00+00:00",
            **v9._target_ledger_binding(),
            "authorization_lock_binding": v9._binding(lock_path),
            "entries": {},
            "data_boundary": {
                "private_gitignored_storage_required": True,
                "other_coder_ledger_visible": False,
                "model_output_or_persona_score_visible": False,
                "raw_or_verbatim_content_allowed": False,
                "prompt_memory_retrieval_training_or_model_selection_use": False,
            },
        }
        for index, slot in enumerate(self.frame["sampling_slots"]):
            alternate = index % 2
            ledger["entries"][slot["sampling_slot_id"]] = {
                "sampling_slot_id": slot["sampling_slot_id"],
                "source_id": slot["source_id"],
                "source_partition_key": slot["source_partition_key"],
                "coder_pseudonym": coder,
                "slot_status": "selected_event",
                "first_eligible_event_attestation": True,
                "updated_at": "2026-08-01T00:00:00+00:00",
                "timestamp_locator_start_seconds": slot["search_start_seconds"],
                "timestamp_locator_end_seconds": slot["search_start_seconds"] + 1,
                "context_family": self.codebook["context_families"][alternate],
                "observable_context_paraphrase": "independent private paraphrase",
                "observable_behavior_paraphrase": "independent private paraphrase",
                "primary_dimension": self.codebook["dimensions"][alternate],
                "secondary_dimensions": [self.codebook["dimensions"][alternate + 2]],
                "dialogue_act_or_action_label": self.codebook[
                    "dialogue_act_or_action_labels"
                ][alternate],
                "observable_audience_relation": self.codebook["audience_relations"][
                    alternate
                ],
                "evidence_strength": self.codebook["evidence_strengths"][alternate],
                "ambiguity_notes": "",
                "alternative_interpretations": "",
                "paraphrase_and_no_quote_attestation": True,
            }
        return ledger

    def test_reliability_report_is_aggregate_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock = self._write_authorization_lock(temporary)
            ledger_a = self._complete_ledger("coder_a", lock)
            ledger_b = self._complete_ledger("coder_b", lock)
            report = v9.build_target_reliability_report(ledger_a, ledger_b)
            self.assertTrue(report["gates"]["target_calibration_reliability_passed"])
            self.assertFalse(report["contains_event_text"])
            self.assertFalse(report["persona_score_computed"])
            serialized = json.dumps(report)
            self.assertNotIn("independent private paraphrase", serialized)


if __name__ == "__main__":
    unittest.main()
