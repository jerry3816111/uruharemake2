from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import re
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request

import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m57_2_component_prediction_capsule as component_m57
import m57_4_component_evidence_collection as collection_m57
import m57_6_crash_recoverable_participant_capability as recovery_m57
import m57_8_participant_confirmed_ledger_completion as completion_m57
import m57_9_adjudicator_confirmed_manifest_export as export_m57
from test_m56_10_crash_safe_outcome_join import m5610_private_roots


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        del request, fp, code, msg, headers, newurl
        return None


class M579AdjudicatorConfirmedManifestExportTests(unittest.TestCase):
    @contextmanager
    def fixture(self, suffix: str, *, complete: bool = True):
        with tempfile.TemporaryDirectory(prefix="uruha-m579-test-") as temp, m5610_private_roots(Path(temp)):
            run_id = f"m579-{suffix}"
            first_envelope, secret = recovery_m57._synthetic_setup(Path(temp), run_id)
            delivery = first_envelope.parent.parent
            envelopes = {
                role: delivery / role / "capability-envelope.json" for role in collection_m57.ROLE_SLOTS
            }
            tokens = {
                role: export_m57.load_json(envelopes[role])["role_session_token"]
                for role in collection_m57.ROLE_SLOTS
            }
            if complete:
                self.complete_and_seal_all(run_id, tokens)
            yield Path(temp), run_id, delivery, envelopes, secret, tokens

    @staticmethod
    def confirm_ledger(run_id: str, role: str, token: str) -> dict:
        progress = completion_m57.inspect_participant_ledger_completion(run_id, role, token)
        return completion_m57.confirm_and_seal_participant_ledger(
            run_id, role, token, progress["displayed_expected_ledger_hash"], completion_m57.CONFIRMATION_VALUE
        )

    @staticmethod
    def fill_adjudicator(run_id: str, token: str) -> None:
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
                    collection_m57._synthetic_state_payload(collection_m57._context(run_id), sample_id, source),
                    ensure_ascii=False,
                )],
            }
            payload = collection_m57._entry_form_payload("adjudicator", form, view)
            collection_m57.save_component_evidence_entry(run_id, "adjudicator", token, sample_id, payload)

    def complete_and_seal_all(self, run_id: str, tokens: dict[str, str]) -> None:
        completion_m57._fill_synthetic_coder(run_id, "coder_a", tokens["coder_a"])
        completion_m57._fill_synthetic_coder(run_id, "coder_b", tokens["coder_b"])
        self.confirm_ledger(run_id, "coder_a", tokens["coder_a"])
        self.confirm_ledger(run_id, "coder_b", tokens["coder_b"])
        self.fill_adjudicator(run_id, tokens["adjudicator"])
        self.confirm_ledger(run_id, "adjudicator", tokens["adjudicator"])

    @staticmethod
    def confirm_export(run_id: str, token: str) -> dict:
        preview = export_m57.inspect_adjudicator_manifest_export(run_id, token)
        return export_m57.confirm_and_export_adjudicator_manifest(
            run_id, token, preview["displayed_expected_manifest_hash"], export_m57.CONFIRMATION_VALUE
        )

    def test_contract_gap_and_public_signatures(self):
        report = export_m57.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 7)
        gap = export_m57.load_json(
            export_m57.ROOT / "analysis/m57_9_prechange_adjudicator_manifest_export_gap_probe_2026-09-06.json"
        )
        self.assertEqual(gap["existing_participant_browser"]["m57_8_post_routes"], ["/save", "/seal"])
        self.assertFalse(gap["existing_participant_browser"]["token_free_export_route_present"])
        self.assertFalse(gap["existing_participant_browser"]["adjudicator_can_export_without_internal_api_or_raw_token"])
        self.assertEqual(gap["real_component_rows"], 0)
        self.assertFalse(gap["m58_authorized"])

    def test_requires_explicit_m57_8_adjudicator_completion_receipt(self):
        with self.fixture("receipt-required", complete=False) as (_root, run_id, _delivery, _envelopes, _secret, tokens):
            completion_m57._fill_synthetic_coder(run_id, "coder_a", tokens["coder_a"])
            completion_m57._fill_synthetic_coder(run_id, "coder_b", tokens["coder_b"])
            self.confirm_ledger(run_id, "coder_a", tokens["coder_a"])
            self.confirm_ledger(run_id, "coder_b", tokens["coder_b"])
            self.fill_adjudicator(run_id, tokens["adjudicator"])
            collection_m57.seal_component_evidence_ledger(run_id, "adjudicator", tokens["adjudicator"])
            with self.assertRaisesRegex(PermissionError, "M57.8 adjudicator completion receipt"):
                export_m57.inspect_adjudicator_manifest_export(run_id, tokens["adjudicator"])
            paths = export_m57._paths(run_id)
            self.assertFalse(paths["evidence"].exists())
            self.assertFalse(paths["m57_9_intent"].exists())

    def test_explicit_export_matches_unchanged_m57_4_and_replays_identically(self):
        with self.fixture("complete") as (_root, run_id, _delivery, _envelopes, _secret, tokens):
            token = tokens["adjudicator"]
            preview = export_m57.inspect_adjudicator_manifest_export(run_id, token)
            paths = export_m57._paths(run_id)
            self.assertTrue(preview["can_confirm_and_export"])
            self.assertFalse(preview["formal_manifest_exported"])
            self.assertFalse(paths["evidence"].exists())
            with self.assertRaisesRegex(PermissionError, "explicit adjudicator confirmation"):
                export_m57.confirm_and_export_adjudicator_manifest(
                    run_id, token, preview["displayed_expected_manifest_hash"], ""
                )
            with self.assertRaisesRegex(PermissionError, "stale"):
                export_m57.confirm_and_export_adjudicator_manifest(
                    run_id, token, "0" * 64, export_m57.CONFIRMATION_VALUE
                )
            first = export_m57.confirm_and_export_adjudicator_manifest(
                run_id, token, preview["displayed_expected_manifest_hash"], export_m57.CONFIRMATION_VALUE
            )
            replay = export_m57.confirm_and_export_adjudicator_manifest(
                run_id, token, preview["displayed_expected_manifest_hash"], export_m57.CONFIRMATION_VALUE
            )
            self.assertEqual(first["manifest_hash"], replay["manifest_hash"])
            self.assertEqual(first["m57_4_export_commitment_hash"], replay["m57_4_export_commitment_hash"])
            self.assertEqual(replay["intent_write"], "validated_existing_identical")
            self.assertEqual(replay["manifest_write"], "validated_existing_identical")
            self.assertEqual(replay["m57_4_export_write"], "validated_existing_identical")
            self.assertEqual(replay["receipt_write"], "validated_existing_identical")
            with self.assertRaisesRegex(PermissionError, "nonidentical"):
                export_m57.confirm_and_export_adjudicator_manifest(
                    run_id, token, "f" * 64, export_m57.CONFIRMATION_VALUE
                )
            manifest = export_m57.load_json(paths["evidence"])
            validation = component_m57.validate_evidence_manifest(
                manifest, run_id, collection_m57._context(run_id), allow_forged=True
            )
            self.assertTrue(validation["valid"], validation["errors"])
            done = export_m57.inspect_adjudicator_manifest_export(run_id, token)
            self.assertEqual(done["status"], "adjudicator_confirmed_manifest_export_completed")
            self.assertFalse(done["can_resume_identical_export"])
            self.assertEqual(paths["m57_9_intent"].stat().st_mode & 0o777, 0o600)
            self.assertEqual(paths["m57_9_receipt"].stat().st_mode & 0o777, 0o600)

    def test_intent_only_and_export_without_receipt_resume(self):
        with self.fixture("resume") as (_root, run_id, _delivery, _envelopes, _secret, tokens):
            token = tokens["adjudicator"]
            preview = export_m57.inspect_adjudicator_manifest_export(run_id, token)
            expected = preview["displayed_expected_manifest_hash"]
            paths = export_m57._paths(run_id)
            with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
                _context, mode, _paths, ledgers, seals, manifest = export_m57._validated_context_under_lock(run_id, token)
                intent = export_m57._new_intent(mode, ledgers, seals, manifest)
                durable_m56._durable_atomic_write_json(paths["m57_9_intent"], intent, exclusive=True)
            pending = export_m57.inspect_adjudicator_manifest_export(run_id, token)
            self.assertTrue(pending["can_resume_identical_export"])
            first = export_m57.confirm_and_export_adjudicator_manifest(
                run_id, token, expected, export_m57.CONFIRMATION_VALUE
            )
            paths["m57_9_receipt"].unlink()
            resumed = export_m57.confirm_and_export_adjudicator_manifest(
                run_id, token, expected, export_m57.CONFIRMATION_VALUE
            )
            self.assertEqual(first["manifest_hash"], resumed["manifest_hash"])
            self.assertEqual(resumed["manifest_write"], "validated_existing_identical")
            self.assertEqual(resumed["m57_4_export_write"], "validated_existing_identical")
            self.assertEqual(resumed["receipt_write"], "created_full_sync")

    def test_preexisting_unattributed_export_and_outcome_state_fail_closed(self):
        with self.fixture("unattributed") as (_root, run_id, _delivery, _envelopes, _secret, tokens):
            token = tokens["adjudicator"]
            collection_m57.export_component_evidence_manifest(run_id, token)
            preview = export_m57.inspect_adjudicator_manifest_export(run_id, token)
            self.assertTrue(preview["preexisting_unattributed_export"])
            with self.assertRaisesRegex(PermissionError, "cannot attribute a preexisting"):
                export_m57.confirm_and_export_adjudicator_manifest(
                    run_id, token, preview["displayed_expected_manifest_hash"], export_m57.CONFIRMATION_VALUE
                )
            self.assertFalse(export_m57._paths(run_id)["m57_9_intent"].exists())
        with self.fixture("outcome") as (_root, run_id, _delivery, _envelopes, _secret, tokens):
            token = tokens["adjudicator"]
            preview = export_m57.inspect_adjudicator_manifest_export(run_id, token)
            paths = export_m57._paths(run_id)
            durable_m56._durable_atomic_write_json(
                paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
            )
            with self.assertRaisesRegex(PermissionError, "denied after outcome"):
                export_m57.confirm_and_export_adjudicator_manifest(
                    run_id, token, preview["displayed_expected_manifest_hash"], export_m57.CONFIRMATION_VALUE
                )
            self.assertFalse(paths["m57_9_intent"].exists())

    def test_tampered_export_and_receipt_fail_validation(self):
        with self.fixture("tamper") as (_root, run_id, _delivery, _envelopes, _secret, tokens):
            token = tokens["adjudicator"]
            self.confirm_export(run_id, token)
            paths = export_m57._paths(run_id)
            export = export_m57.load_json(paths["m57_4_export"])
            export["source_view_count"] = 89
            durable_m56._durable_atomic_write_json(paths["m57_4_export"], export)
            with self.assertRaisesRegex(ValueError, "export commitment"):
                export_m57.inspect_adjudicator_manifest_export(run_id, token)

    def test_outcome_appearing_after_intent_before_upstream_export_leaves_no_manifest(self):
        with self.fixture("outcome-race") as (_root, run_id, _delivery, _envelopes, _secret, tokens):
            token = tokens["adjudicator"]
            preview = export_m57.inspect_adjudicator_manifest_export(run_id, token)
            paths = export_m57._paths(run_id)
            original = collection_m57.export_component_evidence_manifest

            def outcome_race(inner_run_id, inner_token):
                durable_m56._durable_atomic_write_json(
                    paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
                )
                return original(inner_run_id, inner_token)

            with patch.object(collection_m57, "export_component_evidence_manifest", side_effect=outcome_race):
                with self.assertRaisesRegex(PermissionError, "denied after outcome"):
                    export_m57.confirm_and_export_adjudicator_manifest(
                        run_id, token, preview["displayed_expected_manifest_hash"], export_m57.CONFIRMATION_VALUE
                    )
            self.assertTrue(paths["m57_9_intent"].exists())
            self.assertFalse(paths["evidence"].exists())
            self.assertFalse(paths["m57_4_export"].exists())
            self.assertFalse(paths["m57_9_receipt"].exists())

    def test_browser_hides_coder_export_and_requires_adjudicator_cookie_csrf_and_confirmation(self):
        with self.fixture("browser") as (_root, run_id, _delivery, envelopes, secret, tokens):
            coder_server, _coder_metadata = export_m57._make_export_server(
                run_id, "coder_a", str(envelopes["coder_a"]), 0, secret
            )
            coder_thread = Thread(target=coder_server.serve_forever, daemon=True)
            coder_thread.start()
            coder_opener = urllib.request.build_opener(NoRedirect())
            try:
                base = f"http://127.0.0.1:{coder_server.server_address[1]}"
                with self.assertRaises(urllib.error.HTTPError) as redirect:
                    coder_opener.open(urllib.request.Request(base + "/", method="GET"))
                cookie = redirect.exception.headers["Set-Cookie"].split(";", 1)[0]
                page = coder_opener.open(urllib.request.Request(
                    base + redirect.exception.headers["Location"], headers={"Cookie": cookie}, method="GET"
                )).read().decode("utf-8")
                self.assertNotIn('action="/export"', page)
            finally:
                coder_server.shutdown()
                coder_thread.join(timeout=5)
                coder_server.server_close()

            server, metadata = export_m57._make_export_server(
                run_id, "adjudicator", str(envelopes["adjudicator"]), 0, secret
            )
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            opener = urllib.request.build_opener(NoRedirect())
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with self.assertRaises(urllib.error.HTTPError) as first:
                    opener.open(urllib.request.Request(base + "/", method="GET"))
                self.assertEqual(first.exception.code, 303)
                cookie = first.exception.headers["Set-Cookie"].split(";", 1)[0]
                page = opener.open(urllib.request.Request(
                    base + first.exception.headers["Location"], headers={"Cookie": cookie}, method="GET"
                )).read().decode("utf-8")
                self.assertIn('action="/export"', page)
                self.assertIn("exact M57.2 manifest hash", page)
                csrf = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
                expected = re.search(r'name="expected_manifest_hash" value="([0-9a-f]{64})"', page).group(1)
                with self.assertRaises(urllib.error.HTTPError) as bad_csrf:
                    opener.open(urllib.request.Request(
                        base + "/export", data=b"csrf=wrong", headers={
                            "Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded",
                        }, method="POST",
                    ))
                self.assertEqual(bad_csrf.exception.code, 403)
                bad = urllib.parse.urlencode({
                    "csrf": csrf, "expected_manifest_hash": expected,
                    "confirmation": export_m57.CONFIRMATION_VALUE, "token": tokens["adjudicator"],
                }).encode()
                with self.assertRaises(urllib.error.HTTPError) as bad_token:
                    opener.open(urllib.request.Request(
                        base + "/export", data=bad, headers={
                            "Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded",
                        }, method="POST",
                    ))
                self.assertEqual(bad_token.exception.code, 400)
                good = urllib.parse.urlencode({
                    "csrf": csrf, "expected_manifest_hash": expected,
                    "confirmation": export_m57.CONFIRMATION_VALUE,
                }).encode()
                with self.assertRaises(urllib.error.HTTPError) as exported:
                    opener.open(urllib.request.Request(
                        base + "/export", data=good, headers={
                            "Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded",
                        }, method="POST",
                    ))
                self.assertEqual(exported.exception.code, 303)
                final = opener.open(urllib.request.Request(
                    base + exported.exception.headers["Location"], headers={"Cookie": cookie}, method="GET"
                )).read().decode("utf-8")
                self.assertIn("已由 adjudicator 確認並匯出", final)
                self.assertNotIn('action="/export"', final)
                surfaces = page + final + json.dumps(metadata)
                self.assertNotIn(tokens["adjudicator"], surfaces)
                self.assertNotIn(secret, surfaces)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

    def test_project_runtime_launch_spec_has_no_secret_token_or_install_path(self):
        spec = export_m57.build_launch_spec("fixture-run", "adjudicator", "/tmp/envelope.json", 7938)
        self.assertTrue(spec["m57_7_full_audit_ready_before_exec"])
        self.assertTrue(spec["m57_9_entrypoint"])
        self.assertEqual(spec["downloads_installs_or_repairs"], 0)
        self.assertEqual(spec["role_token_or_recovery_secret_arguments"], 0)
        joined = " ".join(spec["argv"]).lower()
        self.assertIn("m57_9_adjudicator_confirmed_manifest_export.py", joined)
        self.assertIn("--serve-exportable", joined)
        self.assertNotIn("--token", joined)
        self.assertNotIn("--secret", joined)
        self.assertNotIn("pip", joined)

    def test_saved_rehearsal_live_audit_dashboard_and_cli_boundaries(self):
        rehearsal = export_m57.load_saved_rehearsal()
        self.assertTrue(export_m57.validate_rehearsal(rehearsal)["valid"])
        live = export_m57.load_json(export_m57.LIVE_AUDIT_PATH)
        cost = export_m57.load_json(export_m57.COST_PATH)
        self.assertEqual(live["real_participant_manifest_export_receipts"], 0)
        self.assertEqual(live["real_component_rows_available"], 0)
        self.assertEqual(live["formal_m57_results"], 0)
        self.assertFalse(live["m58_authorized"])
        self.assertEqual(cost["iterations"], 3)
        self.assertGreater(cost["export_transaction_seconds_median"], 0)
        html_page = export_m57.render_dashboard(rehearsal, live, cost)
        for marker in ("3 SEALS", "MANIFEST PREVIEW", "CONFIRM", "INTENT", "M57.4 EXPORT", "RECEIPT"):
            self.assertIn(marker, html_page)
        self.assertIn("real component rows", html_page)
        self.assertNotIn("m579-forged-no-human-export", html_page)
        help_text = Path(export_m57.__file__).read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--token"', help_text)
        self.assertNotIn('add_argument("--secret"', help_text)


if __name__ == "__main__":
    unittest.main()
