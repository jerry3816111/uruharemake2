from __future__ import annotations

import inspect
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import m57_7_auditable_participant_runtime_launcher as launcher


class M57_7AuditableParticipantRuntimeLauncherTests(unittest.TestCase):
    def test_contract_and_requirements_are_exact_and_frozen(self) -> None:
        contract = launcher.validate_contract()
        requirements = launcher.validate_requirements_lock()
        self.assertTrue(contract["valid"], contract)
        self.assertEqual(contract["binding_count"], 4)
        self.assertTrue(requirements["valid"], requirements)
        self.assertEqual(requirements["locked_count"], 3)

    def test_prechange_probe_preserves_real_runtime_gap_and_no_evidence(self) -> None:
        probe = launcher.load_json(launcher.GAP_PATH)
        self.assertFalse(probe["repository_runtime_inventory"]["project_owned_runtime_ready"])
        audits = {item["label"]: item for item in probe["interpreter_audit"]}
        self.assertFalse(audits["default_python"]["m57_6_crypto_available"])
        self.assertFalse(audits["project_test_python"]["m57_6_crypto_available"])
        self.assertTrue(audits["codex_bundled_python"]["m57_6_crypto_available"])
        self.assertFalse(audits["codex_bundled_python"]["project_owned"])
        self.assertTrue(probe["locked_wheel_feasibility_probe"]["scrypt_and_aesgcm_imported"])
        self.assertEqual(probe["target_outcome_access_count"], 0)
        self.assertEqual(probe["model_call_count"], 0)
        self.assertFalse(probe["formal_evidence_created"])
        self.assertFalse(probe["m58_authorized"])

    def test_exact_base_interpreter_is_available(self) -> None:
        report = launcher.audit_base_interpreter()
        self.assertTrue(report["available"], report)
        self.assertEqual(report["python_version"], "3.12.10")
        self.assertEqual(
            report["executable_sha256"],
            launcher.load_contract()["base_interpreter"]["executable_sha256"],
        )

    def test_prepared_project_runtime_passes_fresh_child_audit(self) -> None:
        report = launcher.audit_runtime()
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["runtime_report"]["distributions"]["cryptography"], "50.0.1")
        self.assertTrue(report["runtime_report"]["scrypt_aesgcm_smoke"])
        self.assertEqual(report["collection_time_download_install_calls"], 0)

    def test_runtime_report_rejects_critical_binary_and_version_drift(self) -> None:
        report = launcher._run_child_audit(launcher.DEFAULT_RUNTIME_ROOT / "bin" / "python")
        self.assertEqual(launcher._runtime_report_errors(report), [])
        drifted = json.loads(json.dumps(report))
        drifted["critical_binary_sha256"]["cryptography/hazmat/bindings/_rust.abi3.so"] = "0" * 64
        self.assertIn("runtime.critical_binaries", launcher._runtime_report_errors(drifted))
        drifted = json.loads(json.dumps(report))
        drifted["distributions"]["cryptography"] = "50.0.2"
        self.assertIn("runtime.distributions", launcher._runtime_report_errors(drifted))

    def test_attestation_tamper_is_detected(self) -> None:
        runtime_root = launcher.DEFAULT_RUNTIME_ROOT
        base = launcher.audit_base_interpreter()
        runtime = launcher._run_child_audit(runtime_root / "bin" / "python")
        attestation = launcher.load_json(runtime_root / launcher.ATTESTATION_NAME)
        self.assertEqual(launcher._attestation_errors(attestation, runtime_root, base, runtime), [])
        tampered = json.loads(json.dumps(attestation))
        tampered["requirements_hash"] = "0" * 64
        errors = launcher._attestation_errors(tampered, runtime_root, base, runtime)
        self.assertIn("attestation.requirements_hash", errors)
        self.assertIn("attestation.hash", errors)

    def test_missing_runtime_fails_closed(self) -> None:
        missing = launcher.ROOT / ".venv" / f"m57_7_missing_{uuid.uuid4().hex}"
        report = launcher.audit_runtime(missing, allow_test_root=True)
        self.assertFalse(report["ready"])
        self.assertIn("runtime.missing", report["errors"])
        self.assertIn("attestation.missing", report["errors"])

    def test_runtime_path_escape_and_symlink_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="m57_7_outside_") as external:
            report = launcher.audit_runtime(Path(external), allow_test_root=True)
            self.assertFalse(report["ready"])
            self.assertIn("runtime.path_outside_project_venv", report["errors"])
            self.assertIsNone(report["runtime_relative_root"])

        with tempfile.TemporaryDirectory(
            dir=launcher.ROOT / ".venv", prefix="m57_7_link_target_"
        ) as target:
            link = launcher.ROOT / ".venv" / f"m57_7_link_{uuid.uuid4().hex}"
            link.symlink_to(Path(target), target_is_directory=True)
            try:
                report = launcher.audit_runtime(link, allow_test_root=True)
                self.assertFalse(report["ready"])
                self.assertIn("runtime.root_symlink", report["errors"])
            finally:
                link.unlink(missing_ok=True)

    def test_public_launch_spec_has_no_secret_token_or_install_path(self) -> None:
        spec = launcher.build_launch_spec(
            "forged-runner-no-human", "coder_a", "/tmp/role_envelope.json", 7932,
        )
        joined = json.dumps({"argv": spec["argv"], "environment": spec["environment"]})
        self.assertEqual(spec["downloads_installs_or_repairs"], 0)
        self.assertEqual(spec["role_token_or_recovery_secret_arguments"], 0)
        self.assertNotIn("PYTHONPATH", spec["environment"])
        self.assertNotIn("PYTHONHOME", spec["environment"])
        self.assertIn("/opt/homebrew/bin", spec["environment"]["PATH"])
        self.assertIn("/usr/sbin", spec["environment"]["PATH"])
        self.assertEqual(spec["environment"].get("HOME"), launcher.os.environ.get("HOME"))
        self.assertNotIn("--token", joined)
        self.assertNotIn("--secret", joined)
        self.assertIn("--serve-recoverable", spec["argv"])
        self.assertIn("-E", spec["argv"])
        self.assertIn("-s", spec["argv"])

    def test_launch_execve_receives_only_prevalidated_spec(self) -> None:
        expected = {
            "executable": "/safe/runtime/python",
            "argv": ["/safe/runtime/python", "-E", "-s", "m57_6.py", "--serve-recoverable", "run", "coder_a", "envelope", "7932"],
            "environment": {"PATH": "/usr/bin:/bin"},
        }
        with patch.object(launcher, "build_launch_spec", return_value=expected) as built, patch.object(launcher.os, "execve") as executed:
            launcher.launch_runtime("run", "coder_a", "envelope", 7932)
        built.assert_called_once_with("run", "coder_a", "envelope", 7932)
        executed.assert_called_once_with(expected["executable"], expected["argv"], expected["environment"])

    def test_invalid_runtime_blocks_before_execve(self) -> None:
        with patch.object(launcher, "audit_runtime", return_value={"ready": False, "errors": ["runtime.critical_binaries"]}), patch.object(launcher.os, "execve") as executed:
            with self.assertRaises(PermissionError):
                launcher.build_launch_spec("run", "coder_a", "envelope", 7932)
        executed.assert_not_called()

    def test_existing_runtime_is_not_overwritten_or_repaired(self) -> None:
        with self.assertRaises(FileExistsError):
            launcher.prepare_runtime()

    def test_failed_preparation_does_not_publish_ready_runtime(self) -> None:
        runtime_root = launcher.ROOT / ".venv" / f"m57_7_failed_{uuid.uuid4().hex}"
        base_report = launcher.audit_base_interpreter()
        with patch.object(launcher, "audit_base_interpreter", return_value=base_report), patch.object(
            launcher.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=1, stdout="", stderr="fixture failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "venv creation failed"):
                launcher.prepare_runtime(runtime_root, allow_test_root=True)
        self.assertFalse(runtime_root.exists())

    def test_collection_launch_code_contains_no_pip_or_installer(self) -> None:
        source = inspect.getsource(launcher.build_launch_spec) + inspect.getsource(launcher.launch_runtime)
        self.assertNotIn('"pip"', source)
        self.assertNotIn("prepare_runtime", source)
        self.assertNotIn("subprocess.run", source)

    def test_saved_rehearsal_cost_and_live_audit_are_bounded(self) -> None:
        rehearsal = launcher.load_saved_rehearsal()
        self.assertTrue(launcher.validate_rehearsal(rehearsal)["valid"])
        cost = launcher.load_json(launcher.COST_PATH)
        live = launcher.load_json(launcher.LIVE_AUDIT_PATH)
        self.assertEqual(cost["iterations"], 7)
        self.assertEqual(cost["collection_time_download_install_calls"], 0)
        self.assertTrue(live["project_runtime_ready"])
        self.assertEqual(live["real_component_rows_available"], 0)
        self.assertEqual(live["formal_m57_results"], 0)
        self.assertFalse(live["m58_authorized"])

    def test_dashboard_explains_flow_and_boundaries(self) -> None:
        html = launcher.render_dashboard()
        for marker in ("PREPARE", "HASH LOCK", "ATTEST", "AUDIT", "HIDDEN PROMPT", "COLLECT"):
            self.assertIn(marker, html)
        self.assertIn("collection-time installs", html)
        self.assertIn("FORMAL M57 DENIED", html)
        self.assertNotIn("m57.7 synthetic secret marker", html)

    def test_implementation_freeze_hashes(self) -> None:
        freeze = launcher.load_json(
            launcher.ROOT
            / "research"
            / "m57_7_auditable_participant_runtime_launcher_implementation_freeze_2026-09-05.json"
        )
        self.assertEqual(
            freeze["schema"],
            "uruha_m57_7_auditable_participant_runtime_launcher_implementation_freeze_v1",
        )
        self.assertEqual(
            freeze["single_changed_variable"],
            "project_owned_attested_participant_runtime_launcher",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(launcher.sha256_file(launcher.ROOT / relative), expected_hash, relative)
        self.assertEqual(freeze["preserved_boundaries"]["real_participant_count"], 0)
        self.assertEqual(freeze["preserved_boundaries"]["formal_m57_results"], 0)
        self.assertFalse(freeze["preserved_boundaries"]["m58_authorized"])

    def test_cli_help_has_no_secret_or_role_token_option(self) -> None:
        done = subprocess.run(
            [sys.executable, str(launcher.ROOT / "m57_7_auditable_participant_runtime_launcher.py"), "--help"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("--secret", done.stdout)
        self.assertNotIn("--token", done.stdout)
        self.assertIn("--launch", done.stdout)


if __name__ == "__main__":
    unittest.main()
