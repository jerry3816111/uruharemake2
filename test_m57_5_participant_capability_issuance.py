import http.client
import inspect
import json
import os
from copy import deepcopy
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
import urllib.parse

import m56_7_mac_full_sync_generation as durable_m56
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_5_participant_capability_issuance as capability
from test_m56_10_crash_safe_outcome_join import m5610_private_roots
from test_m56_9_single_writer_formal_scoring import materialize_scoring_run


ROOT = Path(__file__).resolve().parent


def prepare(root: Path, run_id: str):
    materialize_scoring_run(root, run_id)
    commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
    delivery = root.resolve() / f"{run_id}-delivery"
    receipt = capability._initialize_separated(
        run_id, capability._synthetic_roster(), str(delivery), synthetic=True
    )
    return receipt, delivery


def no_redirect_request(port: int, method: str, path: str, *, headers=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    payload = response.read()
    result = (response.status, dict(response.getheaders()), payload)
    connection.close()
    return result


class M575ParticipantCapabilityTests(unittest.TestCase):
    def test_contract_public_signatures_and_frozen_m574_hashes(self):
        report = capability.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 3)
        expected = capability.load_contract()["public_functions"]
        functions = {
            "initialize_separated_participant_capabilities": capability.initialize_separated_participant_capabilities,
            "validate_participant_capability_issuance": capability.validate_participant_capability_issuance,
            "serve_secure_collection": capability.serve_secure_collection,
        }
        for name, function in functions.items():
            self.assertEqual(list(inspect.signature(function).parameters), expected[name])
        for relative, expected_hash in capability.load_contract()["frozen_dependencies"].items():
            self.assertEqual(capability.sha256_file(ROOT / relative), expected_hash)

    def test_gap_probe_preserves_the_exact_prechange_exposure(self):
        probe = capability.load_json(
            ROOT / "analysis/m57_5_prechange_participant_capability_gap_probe_2026-09-04.json"
        )
        observations = probe["observations"]
        for name in (
            "initializer_returns_all_three_raw_role_tokens_to_one_caller",
            "collector_cli_requires_raw_token_argument",
            "collector_get_reads_token_from_query_string",
            "collector_form_embeds_raw_token_in_hidden_input",
            "collector_redirect_places_raw_token_in_url",
        ):
            self.assertTrue(observations[name])
        self.assertFalse(observations["separate_role_delivery_envelopes_present"])
        self.assertEqual(
            probe["frozen_m57_4_implementation_hash"],
            capability.sha256_file(ROOT / "m57_4_component_evidence_collection.py"),
        )

    def test_synthetic_issuance_returns_no_tokens_and_writes_private_envelopes(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            receipt, delivery = prepare(Path(temp), "m575-private-envelopes")
            receipt_text = json.dumps(receipt, ensure_ascii=False)
            self.assertFalse(capability._contains_raw_role_token(receipt))
            self.assertFalse(receipt["raw_role_tokens_returned"])
            self.assertEqual(oct(capability._mode_bits(delivery)), "0o700")
            raw_tokens = []
            for role in capability.ROLE_SLOTS:
                role_dir = delivery / role
                envelope_path = role_dir / "capability-envelope.json"
                self.assertEqual(oct(capability._mode_bits(role_dir)), "0o700")
                self.assertEqual(oct(capability._mode_bits(envelope_path)), "0o600")
                envelope = capability.load_json(envelope_path)
                raw_tokens.append(envelope["role_session_token"])
                self.assertNotIn(envelope["role_session_token"], receipt_text)
            self.assertEqual(len(set(raw_tokens)), 3)
            report = capability.validate_participant_capability_issuance("m575-private-envelopes")
            self.assertTrue(report["valid"], report["errors"])
            replay = capability._initialize_separated(
                "m575-private-envelopes", capability._synthetic_roster(), str(delivery), synthetic=True
            )
            self.assertEqual(replay["status"], "m57_5_existing_issuance_revalidated")

    def test_delivery_path_must_be_absolute_new_and_not_a_symlink(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            root = Path(temp)
            run_id = "m575-delivery-path"
            materialize_scoring_run(root, run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
            with self.assertRaisesRegex(ValueError, "absolute"):
                capability._initialize_separated(
                    run_id, capability._synthetic_roster(), "relative-delivery", synthetic=True
                )
            existing = root / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(FileExistsError, "must not already exist"):
                capability._initialize_separated(
                    run_id, capability._synthetic_roster(), str(existing.resolve()), synthetic=True
                )
            symlink = root / "delivery-link"
            symlink.symlink_to(existing, target_is_directory=True)
            with self.assertRaises((FileExistsError, PermissionError)):
                capability._initialize_separated(
                    run_id, capability._synthetic_roster(), str(symlink), synthetic=True
                )

    def test_intent_only_failure_is_terminal_and_does_not_retry_m574_initialization(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            root = Path(temp)
            run_id = "m575-intent-terminal"
            materialize_scoring_run(root, run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
            delivery = root.resolve() / "intent-terminal-delivery"
            with patch.object(capability.collection_m57, "_initialize", side_effect=RuntimeError("injected crash")):
                with self.assertRaisesRegex(RuntimeError, "injected crash"):
                    capability._initialize_separated(
                        run_id, capability._synthetic_roster(), str(delivery), synthetic=True
                    )
            paths = capability._paths(run_id)
            self.assertTrue(paths["m57_5_intent"].exists())
            self.assertFalse(paths["m57_5_commitment"].exists())
            with self.assertRaisesRegex(PermissionError, "terminal"):
                capability._initialize_separated(
                    run_id, capability._synthetic_roster(), str(delivery), synthetic=True
                )

    def test_wrong_role_or_tampered_envelope_cannot_claim(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            receipt, delivery = prepare(Path(temp), "m575-wrong-role")
            del receipt
            coder_a = delivery / "coder_a" / "capability-envelope.json"
            with self.assertRaisesRegex(PermissionError, "does not belong"):
                capability._claim_capability("m575-wrong-role", "coder_b", str(coder_a))
            envelope = capability.load_json(coder_a)
            envelope["participant_pseudonym"] = "tampered-person"
            durable_m56._durable_atomic_write_json(coder_a, envelope)
            report = capability.validate_participant_capability_issuance("m575-wrong-role")
            self.assertFalse(report["valid"])
            with self.assertRaisesRegex(PermissionError, "invalid M57.5 issuance"):
                capability._claim_capability("m575-wrong-role", "coder_a", str(coder_a))

    def test_claim_is_one_time_scrubs_token_and_preserves_valid_issuance(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            receipt, delivery = prepare(Path(temp), "m575-one-time")
            del receipt
            envelope_path = delivery / "coder_a" / "capability-envelope.json"
            raw_token = capability.load_json(envelope_path)["role_session_token"]
            claimed, claim = capability._claim_capability(
                "m575-one-time", "coder_a", str(envelope_path)
            )
            self.assertEqual(claimed, raw_token)
            self.assertNotIn(raw_token, envelope_path.read_text(encoding="utf-8"))
            self.assertFalse(capability._contains_raw_role_token(capability.load_json(envelope_path)))
            self.assertNotIn(raw_token, json.dumps(claim, ensure_ascii=False))
            report = capability.validate_participant_capability_issuance("m575-one-time")
            self.assertTrue(report["valid"], report["errors"])
            self.assertEqual(report["claimed_role_count"], 1)
            with self.assertRaisesRegex(PermissionError, "already claimed"):
                capability._claim_capability("m575-one-time", "coder_a", str(envelope_path))

    def test_outcome_state_blocks_initialization_and_claim(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            root = Path(temp)
            run_id = "m575-outcome-init"
            materialize_scoring_run(root, run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
            paths = capability._paths(run_id)
            durable_m56._durable_atomic_write_json(
                paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
            )
            with self.assertRaisesRegex(PermissionError, "after outcome state"):
                capability._initialize_separated(
                    run_id, capability._synthetic_roster(), str(root.resolve() / "late"), synthetic=True
                )
            self.assertFalse(paths["m57_5_intent"].exists())

        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            receipt, delivery = prepare(Path(temp), "m575-outcome-claim")
            del receipt
            paths = capability._paths("m575-outcome-claim")
            durable_m56._durable_atomic_write_json(
                paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
            )
            with self.assertRaisesRegex(PermissionError, "after outcome state"):
                capability._claim_capability(
                    "m575-outcome-claim", "coder_a",
                    str(delivery / "coder_a" / "capability-envelope.json"),
                )

    def test_secure_http_round_trip_omits_role_token_and_saves_m574_entry(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            receipt, delivery = prepare(Path(temp), "m575-http-round-trip")
            del receipt
            envelope = delivery / "coder_a" / "capability-envelope.json"
            raw_token = capability.load_json(envelope)["role_session_token"]
            server, metadata = capability._make_secure_collection_server(
                "m575-http-round-trip", "coder_a", str(envelope), 0
            )
            self.assertFalse(metadata["role_token_in_metadata"])
            self.assertNotIn(raw_token, json.dumps(metadata))
            exchange = capability._http_exchange(server, raw_token)
            self.assertEqual(exchange["first_status"], 303)
            self.assertEqual(exchange["post_status"], 303)
            self.assertEqual(exchange["raw_role_token_surface_occurrences"], 0)
            self.assertFalse(exchange["role_token_equals_cookie_or_csrf"])
            self.assertNotIn("token", exchange["location"].lower())
            self.assertNotIn("token", exchange["post_location"].lower())
            self.assertNotIn('name="token"', exchange["body"])
            self.assertIn("HttpOnly", exchange["set_cookie"])
            self.assertIn("SameSite=Strict", exchange["set_cookie"])
            self.assertNotIn("; Secure", exchange["set_cookie"])
            ledger = capability.load_json(capability._paths("m575-http-round-trip")["ledger_coder_a"])
            self.assertEqual(ledger["revision_count"], 1)
            self.assertEqual(len(ledger["source_views"]), 1)
            self.assertEqual(ledger["target_outcome_access_count"], 0)
            self.assertEqual(ledger["model_call_count"], 0)

    def test_post_requires_cookie_and_csrf_and_rejects_raw_token_field(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            receipt, delivery = prepare(Path(temp), "m575-http-guards")
            del receipt
            envelope = delivery / "coder_a" / "capability-envelope.json"
            raw_token = capability.load_json(envelope)["role_session_token"]
            server, metadata = capability._make_secure_collection_server(
                "m575-http-guards", "coder_a", str(envelope), 0
            )
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = metadata["port"]
            try:
                status, headers, _ = no_redirect_request(port, "GET", "/")
                self.assertEqual(status, 303)
                cookie = headers["Set-Cookie"].split(";", 1)[0]
                location = headers["Location"]
                status, _, body_bytes = no_redirect_request(
                    port, "GET", location, headers={"Cookie": cookie}
                )
                self.assertEqual(status, 200)
                body = body_bytes.decode("utf-8")
                csrf = re.search(r'name="csrf" value="([^"]+)"', body).group(1)
                sample = re.search(r'name="sample_id" value="([^"]+)"', body).group(1)
                base_form = {
                    "csrf": csrf,
                    "sample_id": sample,
                    "observable_features": "input_modality:text_paraphrase",
                    "representation_note": "Synthetic negative HTTP guard test.",
                    "selection_rule": "No history selected.",
                }
                encoded = urllib.parse.urlencode(base_form)
                status, _, _ = no_redirect_request(
                    port, "POST", "/save",
                    headers={"Content-Type": "application/x-www-form-urlencoded"}, body=encoded,
                )
                self.assertEqual(status, 403)
                wrong = deepcopy(base_form)
                wrong["csrf"] = "wrong-csrf"
                status, _, _ = no_redirect_request(
                    port, "POST", "/save",
                    headers={"Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded"},
                    body=urllib.parse.urlencode(wrong),
                )
                self.assertEqual(status, 403)
                forbidden = deepcopy(base_form)
                forbidden["token"] = raw_token
                status, _, _ = no_redirect_request(
                    port, "POST", "/save",
                    headers={"Cookie": cookie, "Content-Type": "application/x-www-form-urlencoded"},
                    body=urllib.parse.urlencode(forbidden),
                )
                self.assertEqual(status, 400)
                ledger = capability.load_json(capability._paths("m575-http-guards")["ledger_coder_a"])
                self.assertEqual(ledger["revision_count"], 0)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

    def test_cli_dashboard_saved_rehearsal_and_freeze(self):
        source = (ROOT / "m57_5_participant_capability_issuance.py").read_text(encoding="utf-8")
        self.assertIn('add_parser("collect-secure")', source)
        self.assertNotIn('add_argument("--token"', source)
        value = capability.load_saved_rehearsal()
        report = capability.validate_rehearsal(value)
        self.assertTrue(report["valid"], report["errors"])
        page = capability.render_dashboard(value, capability.build_live_audit())
        self.assertIn("三個角色，不共用一把鑰匙", page)
        self.assertIn("token surface hits", page)
        self.assertIn("FORMAL M57 DENIED", page)
        self.assertIn("M58 denied", page)
        freeze = capability.load_json(
            ROOT / "research/m57_5_participant_capability_issuance_implementation_freeze_2026-09-04.json"
        )
        self.assertEqual(
            freeze["status"],
            "implementation_frozen_after_engineering_acceptance_before_any_real_capability_issuance",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(capability.sha256_file(ROOT / relative), expected_hash)


if __name__ == "__main__":
    unittest.main()
