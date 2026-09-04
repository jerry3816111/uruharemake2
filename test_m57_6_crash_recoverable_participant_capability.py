import inspect
import json
import os
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import m56_7_mac_full_sync_generation as durable_m56
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_6_crash_recoverable_participant_capability as recovery
from test_m56_10_crash_safe_outcome_join import m5610_private_roots
from test_m56_9_single_writer_formal_scoring import materialize_scoring_run


ROOT = Path(__file__).resolve().parent


def prepare(root: Path, run_id: str):
    materialize_scoring_run(root, run_id)
    commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
    delivery = root.resolve() / f"{run_id}-delivery"
    recovery.capability_m57._initialize_separated(
        run_id, recovery.capability_m57._synthetic_roster(), str(delivery), synthetic=True
    )
    return delivery / "coder_a" / "capability-envelope.json", secrets.token_urlsafe(30)


def durable_hashes(run_id: str, envelope: Path):
    paths = recovery._paths(run_id, "coder_a")
    candidates = {
        "intent": paths["m57_6_intent"],
        "vault": recovery._vault_path(envelope),
        "claim": paths["m57_5_claim_coder_a"],
        "activation": paths["m57_6_activation"],
        "envelope": envelope,
    }
    return {name: recovery.sha256_file(path) for name, path in candidates.items() if path.exists()}


class M576CrashRecoverableParticipantCapabilityTests(unittest.TestCase):
    def test_contract_public_signatures_frozen_hashes_and_crypto_backend(self):
        report = recovery.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 3)
        expected = recovery.load_contract()["public_functions"]
        functions = {
            "audit_crypto_backend": recovery.audit_crypto_backend,
            "validate_recoverable_capability": recovery.validate_recoverable_capability,
            "serve_recoverable_collection": recovery.serve_recoverable_collection,
        }
        for name, function in functions.items():
            self.assertEqual(list(inspect.signature(function).parameters), expected[name])
        for relative, expected_hash in recovery.load_contract()["frozen_dependencies"].items():
            self.assertEqual(recovery.sha256_file(ROOT / relative), expected_hash)
        backend = recovery.audit_crypto_backend()
        self.assertTrue(backend["available"], backend)
        self.assertEqual(backend["actual_cryptography_version"], "50.0.1")
        self.assertEqual(backend["kdf"], "Scrypt")
        self.assertEqual(backend["aead"], "AESGCM")

    def test_gap_probe_preserves_observed_restart_failure_and_runtime_boundary(self):
        probe = recovery.load_json(
            ROOT / "analysis/m57_6_prechange_post_claim_restart_gap_probe_2026-09-05.json"
        )
        self.assertTrue(probe["first_start"]["accepted"])
        self.assertFalse(probe["post_claim_restart"]["accepted"])
        self.assertEqual(probe["post_claim_restart"]["exception_type"], "PermissionError")
        self.assertIn("restart is unsupported", probe["post_claim_restart"]["message"])
        self.assertFalse(probe["crypto_environment_audit"]["project_python_cryptography_available"])
        self.assertTrue(probe["crypto_environment_audit"]["accepted_local_audit_scrypt_available"])
        self.assertTrue(probe["crypto_environment_audit"]["accepted_local_audit_aesgcm_available"])
        self.assertFalse(probe["crypto_environment_audit"]["dependency_was_installed_for_m57_6"])
        self.assertEqual(
            probe["frozen_m57_5_implementation_hash"],
            recovery.sha256_file(ROOT / "m57_5_participant_capability_issuance.py"),
        )

    def test_first_activation_encrypts_before_claim_and_same_secret_restarts(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-first-and-restart"
            envelope, secret = prepare(Path(temp), run_id)
            raw_token = recovery.load_json(envelope)["role_session_token"]
            first_token, first = recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            self.assertEqual(first_token, raw_token)
            self.assertTrue(first["vault_created"])
            self.assertTrue(first["claim_created"])
            self.assertTrue(first["activation_created"])
            first_hashes = durable_hashes(run_id, envelope)
            second_token, second = recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            self.assertEqual(second_token, raw_token)
            self.assertFalse(second["vault_created"])
            self.assertFalse(second["claim_created"])
            self.assertFalse(second["activation_created"])
            self.assertEqual(first_hashes, durable_hashes(run_id, envelope))
            report = recovery.validate_recoverable_capability(run_id, "coder_a")
            self.assertTrue(report["valid"], report["errors"])
            self.assertFalse(report["durable_state_contains_raw_role_token_field"])
            self.assertFalse(report["durable_state_contains_recovery_secret_field"])
            durable_text = json.dumps([
                recovery.load_json(path)
                for path in (
                    recovery._paths(run_id, "coder_a")["m57_6_intent"],
                    recovery._vault_path(envelope),
                    recovery._paths(run_id, "coder_a")["m57_5_claim_coder_a"],
                    recovery._paths(run_id, "coder_a")["m57_6_activation"],
                    envelope,
                )
            ])
            self.assertNotIn(raw_token, durable_text)
            self.assertNotIn(secret, durable_text)
            self.assertEqual(oct(recovery._mode_bits(recovery._vault_path(envelope))), "0o600")

    def test_wrong_secret_and_tampered_vault_fail_with_same_error_and_no_state_change(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-wrong-secret-tamper"
            envelope, secret = prepare(Path(temp), run_id)
            recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            before = durable_hashes(run_id, envelope)
            wrong = secrets.token_urlsafe(30)
            with self.assertRaisesRegex(PermissionError, "incorrect M57.6 recovery secret or tampered"):
                recovery._activate_or_recover(run_id, "coder_a", str(envelope), wrong)
            self.assertEqual(before, durable_hashes(run_id, envelope))
            vault_path = recovery._vault_path(envelope)
            vault = recovery.load_json(vault_path)
            ciphertext = bytearray(recovery._b64decode(vault["ciphertext_b64"]))
            ciphertext[0] ^= 1
            vault["ciphertext_b64"] = recovery._b64encode(bytes(ciphertext))
            vault["vault_hash"] = recovery.digest(recovery._hashless(vault, "vault_hash"))
            durable_m56._durable_atomic_write_json(vault_path, vault)
            with self.assertRaisesRegex(PermissionError, "incorrect M57.6 recovery secret or tampered"):
                recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)

    def test_structurally_malformed_vault_is_reported_not_crashed(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-malformed-vault"
            envelope, secret = prepare(Path(temp), run_id)
            recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            vault_path = recovery._vault_path(envelope)
            vault = recovery.load_json(vault_path)
            del vault["nonce_b64"]
            durable_m56._durable_atomic_write_json(vault_path, vault)
            report = recovery.validate_recoverable_capability(run_id, "coder_a")
            self.assertFalse(report["valid"])
            self.assertTrue(any("vault" in child for child in report["errors"]), report)
            with self.assertRaisesRegex(PermissionError, "invalid M57.6 encrypted vault"):
                recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)

    def test_role_path_and_missing_crypto_fail_closed(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-path-backend"
            envelope, secret = prepare(Path(temp), run_id)
            with self.assertRaisesRegex(PermissionError, "does not belong"):
                recovery._activate_or_recover(
                    run_id, "coder_b", str(envelope), secret
                )
            with patch.object(recovery, "audit_crypto_backend", return_value={
                "available": False, "error": "frozen crypto unavailable",
            }):
                with self.assertRaisesRegex(RuntimeError, "frozen crypto unavailable"):
                    recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            self.assertFalse(recovery._paths(run_id, "coder_a")["m57_6_intent"].exists())

    def test_vault_before_claim_interruption_resumes_without_reencrypting(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-vault-before-claim"
            envelope, secret = prepare(Path(temp), run_id)
            with patch.object(recovery.capability_m57, "_claim_capability", side_effect=RuntimeError("injected after vault")):
                with self.assertRaisesRegex(RuntimeError, "injected after vault"):
                    recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            paths = recovery._paths(run_id, "coder_a")
            vault_hash = recovery.sha256_file(recovery._vault_path(envelope))
            self.assertFalse(paths["m57_5_claim_coder_a"].exists())
            self.assertFalse(paths["m57_6_activation"].exists())
            _token, metadata = recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            self.assertFalse(metadata["vault_created"])
            self.assertEqual(vault_hash, recovery.sha256_file(recovery._vault_path(envelope)))
            self.assertTrue(recovery.validate_recoverable_capability(run_id, "coder_a")["valid"])

    def test_claim_before_activation_commit_interruption_resumes(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-claim-before-activation"
            envelope, secret = prepare(Path(temp), run_id)
            with patch.object(recovery, "_write_or_validate_activation", side_effect=RuntimeError("injected after claim")):
                with self.assertRaisesRegex(RuntimeError, "injected after claim"):
                    recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            paths = recovery._paths(run_id, "coder_a")
            self.assertTrue(paths["m57_5_claim_coder_a"].exists())
            self.assertFalse(paths["m57_6_activation"].exists())
            _token, metadata = recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            self.assertFalse(metadata["claim_created"])
            self.assertTrue(metadata["activation_created"])
            self.assertTrue(recovery.validate_recoverable_capability(run_id, "coder_a")["valid"])

    def test_claim_receipt_before_scrub_is_completed_exactly(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-claim-before-scrub"
            envelope, secret = prepare(Path(temp), run_id)
            with recovery.single_writer_m56._exclusive_scoring_lock(
                recovery.single_writer_m56._lock_path(run_id)
            ):
                mode, commitment, row, paths, expected = recovery._load_upstream(run_id, "coder_a")
                token, _intent, _vault, _vault_path, _created = recovery._encrypt_or_open_vault(
                    run_id, "coder_a", secret, mode, commitment, row, paths, expected
                )
            original_writer = recovery.capability_m57.durable_m56._durable_atomic_write_json

            def fail_scrub(path, value, *args, **kwargs):
                if Path(path) == envelope and value.get("status") == "claimed_and_raw_role_token_removed":
                    raise OSError("injected scrub interruption")
                return original_writer(path, value, *args, **kwargs)

            with patch.object(
                recovery.capability_m57.durable_m56, "_durable_atomic_write_json", side_effect=fail_scrub
            ):
                with self.assertRaisesRegex(OSError, "injected scrub interruption"):
                    recovery.capability_m57._claim_capability(run_id, "coder_a", str(envelope))
            self.assertTrue(paths["m57_5_claim_coder_a"].exists())
            self.assertEqual(recovery.load_json(envelope)["role_session_token"], token)
            recovered, _metadata = recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            self.assertEqual(recovered, token)
            self.assertFalse(recovery.capability_m57._contains_raw_role_token(recovery.load_json(envelope)))
            self.assertTrue(recovery.validate_recoverable_capability(run_id, "coder_a")["valid"])

    def test_outcome_state_blocks_recovery_after_vault(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-outcome-race"
            envelope, secret = prepare(Path(temp), run_id)
            with patch.object(recovery.capability_m57, "_claim_capability", side_effect=RuntimeError("stop after vault")):
                with self.assertRaises(RuntimeError):
                    recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            paths = recovery._paths(run_id, "coder_a")
            durable_m56._durable_atomic_write_json(
                paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
            )
            with self.assertRaisesRegex(PermissionError, "after outcome state"):
                recovery._activate_or_recover(run_id, "coder_a", str(envelope), secret)
            self.assertFalse(paths["m57_5_claim_coder_a"].exists())

    def test_restarted_http_round_trip_uses_cookie_csrf_and_saves_original_ledger(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-http-restart"
            envelope, secret = prepare(Path(temp), run_id)
            raw_token = recovery.load_json(envelope)["role_session_token"]
            first, first_meta = recovery._make_recoverable_collection_server(
                run_id, "coder_a", str(envelope), 0, secret
            )
            self.assertFalse(first_meta["restarted_from_encrypted_vault"])
            first.server_close()
            second, second_meta = recovery._make_recoverable_collection_server(
                run_id, "coder_a", str(envelope), 0, secret
            )
            self.assertTrue(second_meta["restarted_from_encrypted_vault"])
            self.assertNotIn(raw_token, json.dumps(second_meta))
            self.assertNotIn(secret, json.dumps(second_meta))
            exchange = recovery.capability_m57._http_exchange(second, raw_token)
            self.assertEqual(exchange["first_status"], 303)
            self.assertEqual(exchange["post_status"], 303)
            self.assertEqual(exchange["raw_role_token_surface_occurrences"], 0)
            self.assertFalse(exchange["role_token_equals_cookie_or_csrf"])
            self.assertIn("HttpOnly", exchange["set_cookie"])
            self.assertIn("SameSite=Strict", exchange["set_cookie"])
            self.assertNotIn("; Secure", exchange["set_cookie"])
            self.assertNotIn("token", exchange["location"].lower())
            self.assertNotIn("secret", exchange["body"].lower())
            ledger = recovery.load_json(recovery._paths(run_id, "coder_a")["ledger_coder_a"])
            self.assertEqual(ledger["revision_count"], 1)
            self.assertEqual(len(ledger["source_views"]), 1)
            self.assertEqual(ledger["target_outcome_access_count"], 0)
            self.assertEqual(ledger["model_call_count"], 0)

    def test_public_cli_has_no_secret_or_token_channel_and_non_tty_is_rejected(self):
        source = inspect.getsource(recovery.main)
        self.assertNotRegex(source, r"add_argument\([^\n]*(secret|token)")
        self.assertNotIn("os.environ", inspect.getsource(recovery))
        signature = inspect.signature(recovery.serve_recoverable_collection)
        self.assertNotIn("secret", signature.parameters)
        self.assertNotIn("token", signature.parameters)
        with patch.object(recovery.sys.stdin, "isatty", return_value=False), patch.object(
            recovery.getpass, "getpass"
        ) as prompt:
            with self.assertRaisesRegex(PermissionError, "interactive TTY"):
                recovery._interactive_recovery_secret("any-run", "coder_a")
            prompt.assert_not_called()

        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m576-interactive-confirmation"
            _envelope, secret = prepare(Path(temp), run_id)
            with patch.object(recovery.sys.stdin, "isatty", return_value=True), patch.object(
                recovery.getpass, "getpass", side_effect=[secret, secret]
            ) as prompt:
                self.assertEqual(
                    recovery._interactive_recovery_secret(run_id, "coder_a"), secret
                )
                self.assertEqual(prompt.call_count, 2)
            with patch.object(recovery.sys.stdin, "isatty", return_value=True), patch.object(
                recovery.getpass, "getpass", side_effect=[secret, secret + "-mismatch"]
            ):
                with self.assertRaisesRegex(PermissionError, "confirmation did not match"):
                    recovery._interactive_recovery_secret(run_id, "coder_a")

    def test_saved_rehearsal_contract_and_live_audit(self):
        if not recovery.RESULT_PATH.exists():
            self.skipTest("saved M57.6 rehearsal not generated yet")
        saved = recovery.load_saved_rehearsal()
        self.assertTrue(recovery.validate_rehearsal(saved)["valid"])
        self.assertEqual(saved["real_participant_count"], 0)
        self.assertEqual(saved["target_outcome_access_count"], 0)
        self.assertEqual(saved["model_call_count"], 0)
        self.assertFalse(saved["formal_evidence_created"])
        self.assertFalse(saved["m58_authorized"])
        audit = recovery.build_live_audit()
        self.assertEqual(audit["real_recovery_vaults_created"], 0)
        self.assertEqual(audit["real_component_rows_available"], 0)
        self.assertEqual(audit["formal_m57_results"], 0)
        self.assertFalse(audit["m58_authorized"])

    def test_implementation_freeze_hashes(self):
        freeze_path = ROOT / "research/m57_6_crash_recoverable_participant_capability_implementation_freeze_2026-09-05.json"
        if not freeze_path.exists():
            self.skipTest("M57.6 implementation freeze not generated yet")
        freeze = recovery.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"],
            "uruha_m57_6_crash_recoverable_participant_capability_implementation_freeze_v1",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(recovery.sha256_file(ROOT / relative), expected_hash, relative)
        self.assertFalse(freeze["verification"]["formal_m57_result_created"])
        self.assertFalse(freeze["verification"]["m58_authorized"])


if __name__ == "__main__":
    unittest.main()
