from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

import m56_10_crash_safe_outcome_join as crash_safe_m56
import m56_13_public_snapshot_reader as public_reader
import m56_13_unidirectional_public_snapshot as snapshot_m56
from test_m56_9_single_writer_formal_scoring import (
    materialize_scoring_run,
    m569_private_roots,
)


ROOT = Path(__file__).resolve().parent


@contextmanager
def m5613_roots(private_root: Path, public_root: Path):
    old_public_root = os.environ.get(snapshot_m56.PUBLIC_ROOT_ENV)
    os.environ[snapshot_m56.PUBLIC_ROOT_ENV] = str(public_root)
    try:
        with m569_private_roots(private_root):
            yield
    finally:
        if old_public_root is None:
            os.environ.pop(snapshot_m56.PUBLIC_ROOT_ENV, None)
        else:
            os.environ[snapshot_m56.PUBLIC_ROOT_ENV] = old_public_root


def materialize_completed_export(private_root: Path, public_root: Path, run_id: str) -> tuple[Path, dict, dict]:
    with m5613_roots(private_root, public_root):
        run_root = materialize_scoring_run(private_root, run_id)
        crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
        receipt = snapshot_m56.export_public_scoring_snapshot(run_id)
        snapshot_path = public_root / f"{receipt['snapshot_id']}.json"
        snapshot = snapshot_m56.load_json(snapshot_path)
    return run_root, receipt, snapshot


class M5613UnidirectionalPublicSnapshotTests(unittest.TestCase):
    def test_contract_dependencies_and_public_api_signatures_validate(self):
        report = snapshot_m56.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 4)
        self.assertEqual(
            report["contract_hash"],
            "61003d56527f9318994469fb0377e25fa2a746911293f4f225dfaa6ef2cd6fcf",
        )
        self.assertEqual(
            list(inspect.signature(snapshot_m56.export_public_scoring_snapshot).parameters),
            ["run_id"],
        )
        for name in (
            "load_public_projection", "build_public_log_record",
            "build_public_telemetry_record", "render_public_dashboard",
        ):
            self.assertEqual(list(inspect.signature(getattr(public_reader, name)).parameters), ["snapshot_id"])

    def test_standalone_reader_has_no_private_m56_import_or_root_dependency(self):
        source = (ROOT / "m56_13_public_snapshot_reader.py").read_text(encoding="utf-8")
        imports = [
            line for line in source.splitlines()
            if re.match(r"\s*(?:from|import)\s+m56_", line)
        ]
        self.assertEqual(imports, [])
        self.assertNotIn("URUHA_M56_PRIVATE_ROOT", source)
        self.assertNotIn("local_m56_formal_execution", source)
        self.assertEqual(snapshot_m56._reader_import_count(), 0)

    def test_export_is_random_immutable_public_only_and_round_trips(self):
        with TemporaryDirectory(prefix="uruha-m56-13-export-") as temp:
            base = Path(temp)
            private_root, public_root = base / "private", base / "public"
            run_id = "m56-13-private-run-canary"
            run_root, receipt, snapshot = materialize_completed_export(private_root, public_root, run_id)
            with m5613_roots(private_root, public_root):
                projection = public_reader.load_public_projection(receipt["snapshot_id"])
                log = public_reader.build_public_log_record(receipt["snapshot_id"])
                telemetry = public_reader.build_public_telemetry_record(receipt["snapshot_id"])
                page = public_reader.render_public_dashboard(receipt["snapshot_id"])
            self.assertRegex(receipt["snapshot_id"], r"^[0-9a-f]{32}$")
            self.assertNotIn(run_id, snapshot_m56.canonical({"receipt": receipt, "snapshot": snapshot, "page": page}))
            self.assertTrue(snapshot_m56._validate_export_receipt(receipt)["valid"])
            self.assertTrue(public_reader.validate_snapshot(snapshot, receipt["snapshot_id"])["valid"])
            self.assertEqual(public_reader.canonical(projection), public_reader.canonical(log))
            self.assertEqual(public_reader.canonical(projection), public_reader.canonical(telemetry))
            checkpoint = snapshot_m56.load_json(run_root / "scoring" / crash_safe_m56.CHECKPOINT_FILENAME)
            report = snapshot_m56.load_json(run_root / "scoring" / snapshot_m56.projection_m56.scorer_m56.SCORE_REPORT_FILENAME)
            combined = snapshot_m56.canonical({"receipt": receipt, "snapshot": snapshot, "page": page})
            for canary in snapshot_m56.projection_m56._private_canaries(checkpoint, report):
                self.assertNotIn(canary, combined)
            self.assertEqual(snapshot_m56.projection_m56._find_forbidden_public_keys(receipt), [])
            self.assertEqual(snapshot_m56.projection_m56._find_forbidden_public_keys(snapshot), [])
            snapshot_path = public_root / f"{receipt['snapshot_id']}.json"
            self.assertEqual(snapshot_path.stat().st_nlink, 1)
            self.assertEqual(snapshot_path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("<form", page)
            self.assertNotIn("overflow-x", page)

    def test_two_exports_use_distinct_ids_and_never_derive_id_from_run(self):
        with TemporaryDirectory(prefix="uruha-m56-13-random-") as temp:
            base = Path(temp)
            private_root, public_root = base / "private", base / "public"
            run_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            with m5613_roots(private_root, public_root):
                materialize_scoring_run(private_root, run_id)
                crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
                first = snapshot_m56.export_public_scoring_snapshot(run_id)
                second = snapshot_m56.export_public_scoring_snapshot(run_id)
            self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertNotEqual(first["snapshot_id"], run_id)
            self.assertNotEqual(second["snapshot_id"], run_id)
            self.assertEqual(len(list(public_root.glob("*.json"))), 2)

    def test_public_root_inside_private_run_is_rejected_before_private_validation(self):
        with TemporaryDirectory(prefix="uruha-m56-13-nesting-") as temp:
            private_root = Path(temp) / "private"
            run_id = "m56-13-nesting"
            with m5613_roots(private_root, private_root / run_id / "public"):
                materialize_scoring_run(private_root, run_id)
                with self.assertRaises(PermissionError):
                    snapshot_m56.export_public_scoring_snapshot(run_id)

    def test_actual_children_read_with_private_permissions_removed(self):
        result = snapshot_m56.build_synthetic_snapshot_rehearsal()
        validation = snapshot_m56.validate_rehearsal(result)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(result["private_validation_calls_during_export"], 1)
        self.assertEqual(result["private_root_permission_bits_during_children"], 0)
        self.assertEqual(result["public_child_process_count"], 4)
        self.assertEqual(set(result["public_child_exit_codes"].values()), {0})
        self.assertTrue(result["projection_log_telemetry_identical"])
        self.assertEqual(result["public_reader_m56_import_count"], 0)
        self.assertEqual(result["public_surface_private_canary_hit_count"], 0)

    def test_invalid_id_tamper_and_private_field_injection_fail_closed(self):
        for invalid in ("../private", "A" * 32, "a" * 31, "a" * 33, "g" * 32):
            with self.assertRaises(ValueError):
                public_reader.load_public_projection(invalid)
        with TemporaryDirectory(prefix="uruha-m56-13-tamper-") as temp:
            base = Path(temp)
            private_root, public_root = base / "private", base / "public"
            _, receipt, snapshot = materialize_completed_export(
                private_root, public_root, "m56-13-tamper"
            )
            snapshot_path = public_root / f"{receipt['snapshot_id']}.json"
            injected = deepcopy(snapshot)
            injected["projection"]["decision"] = "formal_gate_pass"
            injected["projection"]["projection_hash"] = public_reader.digest(
                {key: value for key, value in injected["projection"].items() if key != "projection_hash"}
            )
            injected["snapshot_hash"] = public_reader.digest(
                {key: value for key, value in injected.items() if key != "snapshot_hash"}
            )
            snapshot_path.write_text(json.dumps(injected, ensure_ascii=False), encoding="utf-8")
            os.chmod(snapshot_path, 0o600)
            with m5613_roots(private_root, public_root):
                with self.assertRaises(PermissionError):
                    public_reader.load_public_projection(receipt["snapshot_id"])

    def test_symlink_hardlink_and_group_world_permissions_fail_closed(self):
        with TemporaryDirectory(prefix="uruha-m56-13-file-guard-") as temp:
            base = Path(temp)
            private_root, public_root = base / "private", base / "public"
            _, receipt, _ = materialize_completed_export(private_root, public_root, "m56-13-file-guard")
            original = public_root / f"{receipt['snapshot_id']}.json"
            with m5613_roots(private_root, public_root):
                os.chmod(original, 0o644)
                with self.assertRaises(PermissionError):
                    public_reader.load_public_projection(receipt["snapshot_id"])
                os.chmod(original, 0o600)
                hard_id = "b" * 32
                os.link(original, public_root / f"{hard_id}.json")
                with self.assertRaises(PermissionError):
                    public_reader.load_public_projection(hard_id)
                os.unlink(public_root / f"{hard_id}.json")
                link_id = "c" * 32
                os.symlink(original, public_root / f"{link_id}.json")
                with self.assertRaises(OSError):
                    public_reader.load_public_projection(link_id)

    def test_live_audit_and_demo_retain_scientific_denial(self):
        audit = snapshot_m56.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_scoring_authorized"])
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["target_outcome_access_count"], 0)
        result = snapshot_m56.build_synthetic_snapshot_rehearsal()
        page = snapshot_m56.render_demo_dashboard(result)
        self.assertIn("0/3", page)
        self.assertIn("4/4", page)
        self.assertIn("private root mode 000", page)
        self.assertIn("0 REAL OUTCOME READS", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches_frozen_files(self):
        freeze_path = ROOT / "research/m56_13_unidirectional_public_snapshot_implementation_freeze_2026-09-04.json"
        if not freeze_path.exists():
            self.skipTest("implementation freeze is created after pre-freeze verification")
        freeze = snapshot_m56.load_json(freeze_path)
        self.assertEqual(freeze["schema"], "uruha_m56_unidirectional_public_snapshot_implementation_freeze_v1")
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_target_outcome_access")
        for row in freeze["files"]:
            self.assertEqual(snapshot_m56.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])


if __name__ == "__main__":
    unittest.main()
