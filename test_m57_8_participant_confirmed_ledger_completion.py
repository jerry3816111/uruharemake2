from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
from threading import Thread
import unittest
import urllib.error
import urllib.parse
import urllib.request

import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m57_4_component_evidence_collection as collection_m57
import m57_6_crash_recoverable_participant_capability as recovery_m57
import m57_8_participant_confirmed_ledger_completion as completion_m57
from test_m56_10_crash_safe_outcome_join import m5610_private_roots


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        del request, fp, code, msg, headers, newurl
        return None


class M578ParticipantConfirmedLedgerCompletionTests(unittest.TestCase):
    @contextmanager
    def fixture(self, suffix: str):
        with tempfile.TemporaryDirectory(prefix="uruha-m578-test-") as temp, m5610_private_roots(Path(temp)):
            run_id = f"m578-{suffix}"
            envelope, secret = recovery_m57._synthetic_setup(Path(temp), run_id)
            delivery = envelope.parent.parent
            tokens = {
                role: completion_m57.load_json(delivery / role / "capability-envelope.json")["role_session_token"]
                for role in collection_m57.ROLE_SLOTS
            }
            yield Path(temp), run_id, delivery, envelope, secret, tokens

    def fill_coder(self, run_id: str, role: str, token: str, count: int = 30) -> None:
        completion_m57._fill_synthetic_coder(run_id, role, token, count)

    def fill_adjudicator(self, run_id: str, token: str) -> None:
        context = collection_m57._context(run_id)
        for sample_id in collection_m57._sample_order(context):
            view = collection_m57.record_component_source_view(run_id, "adjudicator", token, sample_id)
            source = view["source_information"]
            form = {
                "perception_choice": ["coder_a"],
                "perception_resolution_basis": ["Synthetic pre-outcome mechanics basis."],
                "retrieval_choice": ["coder_a"],
                "retrieval_resolution_basis": ["Synthetic pre-outcome mechanics basis."],
                "observable_state_proxy": [json.dumps(
                    collection_m57._synthetic_state_payload(context, sample_id, source), ensure_ascii=False
                )],
            }
            payload = collection_m57._entry_form_payload("adjudicator", form, view)
            collection_m57.save_component_evidence_entry(run_id, "adjudicator", token, sample_id, payload)

    @staticmethod
    def confirm(run_id: str, role: str, token: str) -> dict:
        progress = completion_m57.inspect_participant_ledger_completion(run_id, role, token)
        return completion_m57.confirm_and_seal_participant_ledger(
            run_id, role, token, progress["displayed_expected_ledger_hash"], completion_m57.CONFIRMATION_VALUE
        )

    def test_contract_gap_and_public_signatures(self):
        report = completion_m57.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 8)
        gap = completion_m57.load_json(
            completion_m57.ROOT / "analysis/m57_8_prechange_participant_ledger_completion_gap_probe_2026-09-05.json"
        )
        self.assertFalse(gap["existing_participant_browser"]["token_free_seal_route_present"])
        self.assertFalse(gap["existing_participant_browser"]["participant_can_finish_and_seal_without_internal_api_or_raw_token"])
        self.assertEqual(gap["real_component_rows"], 0)
        self.assertFalse(gap["m58_authorized"])

    def test_incomplete_ledger_cannot_confirm_or_seal(self):
        with self.fixture("incomplete") as (_root, run_id, _delivery, _envelope, _secret, tokens):
            self.fill_coder(run_id, "coder_a", tokens["coder_a"], 29)
            progress = completion_m57.inspect_participant_ledger_completion(run_id, "coder_a", tokens["coder_a"])
            self.assertEqual(progress["completed_unique_sample_count"], 29)
            self.assertFalse(progress["complete"])
            self.assertFalse(progress["can_confirm_and_seal"])
            with self.assertRaisesRegex(ValueError, "ledger.incomplete"):
                completion_m57.confirm_and_seal_participant_ledger(
                    run_id, "coder_a", tokens["coder_a"], progress["displayed_expected_ledger_hash"],
                    completion_m57.CONFIRMATION_VALUE,
                )
            paths = completion_m57._completion_paths(run_id, "coder_a")
            self.assertFalse(paths["m57_8_intent"].exists())
            self.assertFalse(paths["seal_coder_a"].exists())

    def test_complete_ledger_requires_explicit_confirmation_and_replays_identically(self):
        with self.fixture("complete") as (_root, run_id, _delivery, _envelope, _secret, tokens):
            token = tokens["coder_a"]
            self.fill_coder(run_id, "coder_a", token)
            progress = completion_m57.inspect_participant_ledger_completion(run_id, "coder_a", token)
            paths = completion_m57._completion_paths(run_id, "coder_a")
            self.assertEqual(progress["completed_unique_sample_count"], 30)
            self.assertEqual(progress["ledger_status"], "open_private_role_ledger")
            self.assertTrue(progress["can_confirm_and_seal"])
            self.assertFalse(paths["seal_coder_a"].exists())
            with self.assertRaisesRegex(PermissionError, "explicit participant confirmation"):
                completion_m57.confirm_and_seal_participant_ledger(
                    run_id, "coder_a", token, progress["displayed_expected_ledger_hash"], ""
                )
            with self.assertRaisesRegex(PermissionError, "stale"):
                completion_m57.confirm_and_seal_participant_ledger(
                    run_id, "coder_a", token, "0" * 64, completion_m57.CONFIRMATION_VALUE
                )
            self.assertFalse(paths["m57_8_intent"].exists())
            first = completion_m57.confirm_and_seal_participant_ledger(
                run_id, "coder_a", token, progress["displayed_expected_ledger_hash"], completion_m57.CONFIRMATION_VALUE
            )
            replay = completion_m57.confirm_and_seal_participant_ledger(
                run_id, "coder_a", token, progress["displayed_expected_ledger_hash"], completion_m57.CONFIRMATION_VALUE
            )
            self.assertEqual(first["m57_4_seal_hash"], replay["m57_4_seal_hash"])
            self.assertEqual(replay["intent_write"], "validated_existing_identical")
            self.assertEqual(replay["seal_write"], "validated_existing_identical")
            self.assertEqual(replay["receipt_write"], "validated_existing_identical")
            with self.assertRaisesRegex(PermissionError, "nonidentical"):
                completion_m57.confirm_and_seal_participant_ledger(
                    run_id, "coder_a", token, "f" * 64, completion_m57.CONFIRMATION_VALUE
                )
            ledger = completion_m57.load_json(paths["ledger_coder_a"])
            seal = completion_m57.load_json(paths["seal_coder_a"])
            receipt = completion_m57.load_json(paths["m57_8_receipt"])
            self.assertEqual(ledger["status"], "sealed_private_role_ledger")
            self.assertEqual(set(seal), {
                "schema", "version", "status", "run_id", "mode_hash", "role_slot",
                "participant_pseudonym", "ledger_hash", "entry_count", "source_view_count",
                "revision_count", "sealed_at_utc", "target_outcome_access_count", "model_call_count", "seal_hash",
            })
            self.assertEqual(receipt["m57_4_seal_hash"], seal["seal_hash"])
            with self.assertRaisesRegex(PermissionError, "sealed"):
                context = collection_m57._context(run_id)
                sample_id = collection_m57._sample_order(context)[0]
                view = collection_m57.record_component_source_view(run_id, "coder_a", token, sample_id)
                collection_m57.save_component_evidence_entry(
                    run_id, "coder_a", token, sample_id,
                    collection_m57._synthetic_coder_payload(view["source_information"], variant="a", index=1),
                )

    def test_tamper_and_outcome_state_fail_before_intent(self):
        with self.fixture("tamper") as (_root, run_id, _delivery, _envelope, _secret, tokens):
            token = tokens["coder_a"]
            self.fill_coder(run_id, "coder_a", token)
            progress = completion_m57.inspect_participant_ledger_completion(run_id, "coder_a", token)
            paths = completion_m57._completion_paths(run_id, "coder_a")
            ledger = completion_m57.load_json(paths["ledger_coder_a"])
            sample_id = next(iter(ledger["entries"]))
            ledger["entries"][sample_id]["revisions"][0]["payload"]["perception"]["representation_note"] = "tampered"
            durable_m56._durable_atomic_write_json(paths["ledger_coder_a"], ledger)
            with self.assertRaisesRegex(ValueError, "ledger.hash"):
                completion_m57.confirm_and_seal_participant_ledger(
                    run_id, "coder_a", token, progress["displayed_expected_ledger_hash"], completion_m57.CONFIRMATION_VALUE
                )
            self.assertFalse(paths["m57_8_intent"].exists())
        with self.fixture("outcome") as (_root, run_id, _delivery, _envelope, _secret, tokens):
            token = tokens["coder_a"]
            self.fill_coder(run_id, "coder_a", token)
            progress = completion_m57.inspect_participant_ledger_completion(run_id, "coder_a", token)
            paths = completion_m57._completion_paths(run_id, "coder_a")
            durable_m56._durable_atomic_write_json(
                paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
            )
            with self.assertRaisesRegex(PermissionError, "denied after outcome"):
                completion_m57.confirm_and_seal_participant_ledger(
                    run_id, "coder_a", token, progress["displayed_expected_ledger_hash"], completion_m57.CONFIRMATION_VALUE
                )
            self.assertFalse(paths["m57_8_intent"].exists())

    def test_interrupted_intent_and_post_seal_receipt_resume(self):
        with self.fixture("resume") as (_root, run_id, _delivery, _envelope, _secret, tokens):
            token = tokens["coder_a"]
            self.fill_coder(run_id, "coder_a", token)
            progress = completion_m57.inspect_participant_ledger_completion(run_id, "coder_a", token)
            expected_hash = progress["displayed_expected_ledger_hash"]
            paths = completion_m57._completion_paths(run_id, "coder_a")
            with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
                _context, mode, _paths, ledger, _cl, _cs = completion_m57._role_context_under_lock(
                    run_id, "coder_a", token, require_complete=True
                )
                intent = completion_m57._new_intent(mode, ledger, expected_hash)
                durable_m56._durable_atomic_write_json(paths["m57_8_intent"], intent, exclusive=True)
            pending = completion_m57.inspect_participant_ledger_completion(run_id, "coder_a", token)
            self.assertTrue(pending["can_resume_identical_confirmation"])
            completed = completion_m57.confirm_and_seal_participant_ledger(
                run_id, "coder_a", token, expected_hash, completion_m57.CONFIRMATION_VALUE
            )
            seal_hash = completed["m57_4_seal_hash"]
            paths["m57_8_receipt"].unlink()
            resumed = completion_m57.confirm_and_seal_participant_ledger(
                run_id, "coder_a", token, expected_hash, completion_m57.CONFIRMATION_VALUE
            )
            self.assertEqual(resumed["m57_4_seal_hash"], seal_hash)
            self.assertEqual(resumed["receipt_write"], "created_full_sync")

    def test_pending_confirmation_hides_save_and_later_valid_mutation_fails_closed(self):
        with self.fixture("pending-mutation") as (_root, run_id, _delivery, _envelope, _secret, tokens):
            token = tokens["coder_a"]
            self.fill_coder(run_id, "coder_a", token)
            progress = completion_m57.inspect_participant_ledger_completion(run_id, "coder_a", token)
            expected_hash = progress["displayed_expected_ledger_hash"]
            paths = completion_m57._completion_paths(run_id, "coder_a")
            with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
                _context, mode, _paths, ledger, _cl, _cs = completion_m57._role_context_under_lock(
                    run_id, "coder_a", token, require_complete=True
                )
                intent = completion_m57._new_intent(mode, ledger, expected_hash)
                durable_m56._durable_atomic_write_json(paths["m57_8_intent"], intent, exclusive=True)
            context = collection_m57._context(run_id)
            sample_id = collection_m57._sample_order(context)[0]
            pending_page = completion_m57._render_participant_page(
                run_id, "coder_a", token, sample_id, "fixture-csrf"
            )
            self.assertIn("確認已落盤，等待完成封存", pending_page)
            self.assertNotIn('action="/save"', pending_page)
            view = collection_m57.record_component_source_view(run_id, "coder_a", token, sample_id)
            collection_m57.save_component_evidence_entry(
                run_id, "coder_a", token, sample_id,
                collection_m57._synthetic_coder_payload(view["source_information"], variant="a", index=31),
            )
            with self.assertRaisesRegex(PermissionError, "changed after participant confirmation"):
                completion_m57.confirm_and_seal_participant_ledger(
                    run_id, "coder_a", token, expected_hash, completion_m57.CONFIRMATION_VALUE
                )
            self.assertFalse(paths["seal_coder_a"].exists())
            self.assertFalse(paths["m57_8_receipt"].exists())

    def test_two_coder_seals_release_adjudicator_and_adjudicator_can_confirm(self):
        with self.fixture("roles") as (_root, run_id, _delivery, _envelope, _secret, tokens):
            self.fill_coder(run_id, "coder_a", tokens["coder_a"])
            self.fill_coder(run_id, "coder_b", tokens["coder_b"])
            self.confirm(run_id, "coder_a", tokens["coder_a"])
            context = collection_m57._context(run_id)
            sample_id = collection_m57._sample_order(context)[0]
            with self.assertRaisesRegex(PermissionError, "coder_b ledger is not valid and sealed"):
                collection_m57.record_component_source_view(run_id, "adjudicator", tokens["adjudicator"], sample_id)
            self.confirm(run_id, "coder_b", tokens["coder_b"])
            self.fill_adjudicator(run_id, tokens["adjudicator"])
            progress = completion_m57.inspect_participant_ledger_completion(run_id, "adjudicator", tokens["adjudicator"])
            self.assertTrue(progress["can_confirm_and_seal"])
            sealed = self.confirm(run_id, "adjudicator", tokens["adjudicator"])
            self.assertEqual(sealed["role_slot"], "adjudicator")
            self.assertFalse(sealed["m58_authorized"])

    def test_browser_hides_incomplete_seal_then_requires_cookie_csrf_and_confirmation(self):
        with self.fixture("browser") as (_root, run_id, _delivery, envelope, secret, tokens):
            token = tokens["coder_a"]
            self.fill_coder(run_id, "coder_a", token, 29)
            server, metadata = completion_m57._make_completion_server(run_id, "coder_a", str(envelope), 0, secret)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            opener = urllib.request.build_opener(NoRedirect())
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with self.assertRaises(urllib.error.HTTPError) as first_error:
                    opener.open(urllib.request.Request(base + "/", method="GET"))
                self.assertEqual(first_error.exception.code, 303)
                cookie = first_error.exception.headers["Set-Cookie"].split(";", 1)[0]
                location = first_error.exception.headers["Location"]
                incomplete = opener.open(urllib.request.Request(
                    base + location, headers={"Cookie": cookie}, method="GET"
                )).read().decode("utf-8")
                self.assertIn("29/30", incomplete)
                self.assertNotIn('action="/seal"', incomplete)
                with self.assertRaises(urllib.error.HTTPError) as csrf_error:
                    opener.open(urllib.request.Request(
                        base + "/seal", data=b"csrf=wrong", headers={
                            "Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded"
                        }, method="POST"
                    ))
                self.assertEqual(csrf_error.exception.code, 403)
                context = collection_m57._context(run_id)
                final_sample = collection_m57._sample_order(context)[29]
                view = collection_m57.record_component_source_view(run_id, "coder_a", token, final_sample)
                collection_m57.save_component_evidence_entry(
                    run_id, "coder_a", token, final_sample,
                    collection_m57._synthetic_coder_payload(view["source_information"], variant="a", index=30),
                )
                complete = opener.open(urllib.request.Request(
                    base + location, headers={"Cookie": cookie}, method="GET"
                )).read().decode("utf-8")
                self.assertIn("30/30", complete)
                self.assertIn('action="/seal"', complete)
                self.assertLess(complete.index("PARTICIPANT CONFIRMATION"), complete.index('action="/save"'))
                csrf = re.search(r'name="csrf" value="([^"]+)"', complete).group(1)
                ledger_hash = re.search(r'name="expected_ledger_hash" value="([0-9a-f]{64})"', complete).group(1)
                bad = urllib.parse.urlencode({
                    "csrf": csrf,
                    "expected_ledger_hash": ledger_hash,
                    "confirmation": completion_m57.CONFIRMATION_VALUE,
                    "token": token,
                }).encode()
                with self.assertRaises(urllib.error.HTTPError) as token_error:
                    opener.open(urllib.request.Request(
                        base + "/seal", data=bad, headers={
                            "Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded"
                        }, method="POST"
                    ))
                self.assertEqual(token_error.exception.code, 400)
                good = urllib.parse.urlencode({
                    "csrf": csrf,
                    "expected_ledger_hash": ledger_hash,
                    "confirmation": completion_m57.CONFIRMATION_VALUE,
                }).encode()
                with self.assertRaises(urllib.error.HTTPError) as seal_redirect:
                    opener.open(urllib.request.Request(
                        base + "/seal", data=good, headers={
                            "Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded"
                        }, method="POST"
                    ))
                self.assertEqual(seal_redirect.exception.code, 303)
                final = opener.open(urllib.request.Request(
                    base + seal_redirect.exception.headers["Location"], headers={"Cookie": cookie}, method="GET"
                )).read().decode("utf-8")
                self.assertIn("已由參與者確認並封存", final)
                self.assertNotIn('<form method="post"', final.lower())
                self.assertNotIn(token, complete + final + json.dumps(metadata))
                self.assertNotIn(secret, complete + final + json.dumps(metadata))
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

    def test_project_runtime_launch_spec_has_no_secret_token_or_install_path(self):
        spec = completion_m57.build_launch_spec("fixture-run", "coder_a", "/tmp/envelope.json", 7934)
        self.assertTrue(spec["m57_7_full_audit_ready_before_exec"])
        self.assertTrue(spec["m57_8_entrypoint"])
        self.assertEqual(spec["downloads_installs_or_repairs"], 0)
        self.assertEqual(spec["role_token_or_recovery_secret_arguments"], 0)
        joined = " ".join(spec["argv"]).lower()
        self.assertIn("m57_8_participant_confirmed_ledger_completion.py", joined)
        self.assertIn("--serve-completable", joined)
        self.assertNotIn("--token", joined)
        self.assertNotIn("--secret", joined)
        self.assertNotIn("pip", joined)

    def test_saved_rehearsal_live_audit_and_cli_boundaries(self):
        rehearsal = completion_m57.load_saved_rehearsal()
        self.assertTrue(completion_m57.validate_rehearsal(rehearsal)["valid"])
        live = completion_m57.build_live_audit()
        self.assertEqual(live["real_participant_completion_receipts"], 0)
        self.assertEqual(live["real_component_rows_available"], 0)
        self.assertEqual(live["formal_m57_results"], 0)
        self.assertFalse(live["m58_authorized"])
        help_text = Path(completion_m57.__file__).read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--token"', help_text)
        self.assertNotIn('add_argument("--secret"', help_text)

    def test_implementation_freeze_hashes(self):
        freeze = completion_m57.load_json(
            completion_m57.ROOT
            / "research"
            / "m57_8_participant_confirmed_ledger_completion_implementation_freeze_2026-09-06.json"
        )
        self.assertEqual(
            freeze["schema"],
            "uruha_m57_8_participant_confirmed_ledger_completion_implementation_freeze_v1",
        )
        self.assertEqual(
            freeze["single_changed_variable"],
            "participant_confirmed_token_free_complete_ledger_seal",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(
                completion_m57.sha256_file(completion_m57.ROOT / relative),
                expected_hash,
                relative,
            )
        self.assertEqual(freeze["preserved_boundaries"]["real_participant_count"], 0)
        self.assertEqual(freeze["preserved_boundaries"]["formal_m57_results"], 0)
        self.assertFalse(freeze["preserved_boundaries"]["m58_authorized"])


if __name__ == "__main__":
    unittest.main()
