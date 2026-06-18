#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

# Contract Constants
EXPECTED_TOP_LEVEL_KEYS = {
    "schema_version",
    "runner_version",
    "overall_status",
    "generated_at",
    "checks"
}

EXPECTED_CHECK_KEYS = {
    "name",
    "check_id",
    "status",
    "detail",
    "exit_code"
}
EXPECTED_CHECK_NAMES = {
    "Regression Panel Self-Check",
    "Self-Check Contract Validator",
}

EXPECTED_CHECK_ID_MAPPING = {
    "Regression Panel Self-Check": "regression_panel_self_check",
    "Self-Check Contract Validator": "self_check_contract_validator",
}

ANSI_ESCAPE_MARKERS = ("\033[", "\x1b[")
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def ensure_no_ansi(raw_output, label):
    if any(marker in raw_output for marker in ANSI_ESCAPE_MARKERS):
        raise ValueError(f"ANSI escape code leaked in {label} raw output")


def load_file_text(path, label):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    ensure_no_ansi(text, label)
    return text


def parse_runner_json(result, label, expected_exit_code):
    ensure_no_ansi(result.stdout, label)
    if result.returncode != expected_exit_code:
        raise ValueError(
            f"{label} expected exit_code {expected_exit_code}, got {result.returncode}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} returned non-JSON output") from exc


def validate_contract(data, label, expected_status=None):
    print(f"  Validating {label}...")

    missing_keys = EXPECTED_TOP_LEVEL_KEYS - set(data.keys())
    if missing_keys:
        raise ValueError(f"Missing top-level keys: {missing_keys}")

    if expected_status and data["overall_status"] != expected_status:
        raise ValueError(f"Expected overall_status {expected_status}, got {data['overall_status']}")

    try:
        datetime.fromisoformat(data["generated_at"])
    except ValueError as exc:
        raise ValueError(f"Invalid generated_at format: {data['generated_at']}") from exc

    if not isinstance(data["checks"], list):
        raise ValueError("Checks must be a list")
    if len(data["checks"]) == 0:
        raise ValueError("Checks list is empty")

    seen_names = set()
    for check in data["checks"]:
        missing_check_keys = EXPECTED_CHECK_KEYS - set(check.keys())
        if missing_check_keys:
            raise ValueError(f"Check is missing keys: {missing_check_keys}")

        if check["status"] not in ("PASS", "FAIL"):
            raise ValueError(f"Invalid check status: {check['status']}")
        
        # Validate name -> check_id mapping
        expected_id = EXPECTED_CHECK_ID_MAPPING.get(check["name"])
        if expected_id and check["check_id"] != expected_id:
            raise ValueError(f"Check '{check['name']}' has invalid check_id: expected {expected_id}, got {check['check_id']}")
            
        seen_names.add(check["name"])

        for k, v in check.items():
            if isinstance(v, str) and any(marker in v for marker in ANSI_ESCAPE_MARKERS):
                raise ValueError(f"ANSI escape code leaked in field '{k}': {repr(v)}")

    missing_names = EXPECTED_CHECK_NAMES - seen_names
    if missing_names:
        raise ValueError(f"Missing expected check names: {missing_names}")

    print(f"  ✅ {label} passed contract validation.")

def main():
    print("=== Quality Gate Contract Validator v1 ===\n")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gate_path = os.path.join(base_dir, "analysis", "regression_panel_quality_gate.py")
    
    if not os.path.exists(gate_path):
        print(f"Error: Quality Gate script not found at {gate_path}")
        sys.exit(1)

    print("[SCENARIO 1] Success Path (Normal execution)")
    result = subprocess.run([sys.executable, gate_path, "--json"], capture_output=True, text=True)
    try:
        data = parse_runner_json(result, "Success Path Output", expected_exit_code=0)
        validate_contract(data, "Success Path Output", expected_status="PASS")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    print("\n[SCENARIO 2] Failure Path (Sub-check failure)")
    with tempfile.NamedTemporaryFile(suffix=".py", mode='w') as tmp:
        tmp.write("import sys; print('Simulated failure'); sys.exit(1)")
        tmp.flush()
        
        # Test failure of the first check (self-check)
        result = subprocess.run([
            sys.executable, gate_path, "--json",
            "--self-check-path", tmp.name
        ], capture_output=True, text=True)
        
        try:
            data = parse_runner_json(result, "Failure Path (Self-Check Fail)", expected_exit_code=1)
            validate_contract(data, "Failure Path (Self-Check Fail)", expected_status="FAIL")
            
            # Verify the specific check failed
            failed_check = next((c for c in data["checks"] if "Self-Check" in c["name"]), None)
            if not failed_check or failed_check["status"] != "FAIL":
                raise ValueError("Expected Regression Panel Self-Check to fail")
            if failed_check["exit_code"] != 1:
                raise ValueError(f"Expected exit_code 1, got {failed_check['exit_code']}")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n[SCENARIO 3] Text Mode Behavior")
    result = subprocess.run([sys.executable, gate_path], capture_output=True, text=True)
    if result.returncode != 0:
        print("FAILED: Text mode failed in success state")
        sys.exit(1)

    clean_stdout = ANSI_ESCAPE_RE.sub("", result.stdout)

    if "Overall Status: PASS" not in clean_stdout:
        print(f"FAILED: Text mode output missing 'Overall Status: PASS'. Got: {repr(clean_stdout)}")
        sys.exit(1)
    for expected_name in EXPECTED_CHECK_NAMES:
        if expected_name not in clean_stdout:
            print(f"FAILED: Text mode output missing check name '{expected_name}'")
            sys.exit(1)
    print("  ✅ Text mode output verified.")

    print("\n[SCENARIO 4] Artifact Export Equality")
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = os.path.join(tmpdir, "artifact.json")
        result = subprocess.run([
            sys.executable, gate_path, "--json", "--output-json", artifact_path
        ], capture_output=True, text=True)
        
        try:
            data_stdout = parse_runner_json(result, "Artifact Export (Stdout)", expected_exit_code=0)
            if not os.path.exists(artifact_path):
                raise ValueError("Artifact file was not created")

            artifact_text = load_file_text(artifact_path, "Artifact Export (File)")
            if result.stdout != artifact_text:
                raise ValueError("Stdout JSON text and artifact file text are not identical")

            data_file = json.loads(artifact_text)
            if data_stdout != data_file:
                raise ValueError("Stdout JSON object and artifact JSON object are not identical")

            print("  ✅ Stdout/File equality verified.")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n[SCENARIO 5] Nested Directory Artifact Export")
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_path = os.path.join(tmpdir, "deeply", "nested", "dir", "artifact.json")
        result = subprocess.run([
            sys.executable, gate_path, "--json", "--output-json", nested_path
        ], capture_output=True, text=True)

        try:
            parse_runner_json(result, "Nested Artifact Export (Stdout)", expected_exit_code=0)
            if not os.path.exists(nested_path):
                raise ValueError("Nested artifact file was not created")
            artifact_text = load_file_text(nested_path, "Nested Artifact Export (File)")
            json.loads(artifact_text)
            print("  ✅ Nested directory creation verified.")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n[SCENARIO 6] Artifact Write Failure Behavior")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Attempting to write to a path that is actually a directory
        invalid_path = os.path.join(tmpdir, "already_a_dir")
        os.makedirs(invalid_path)

        result = subprocess.run([
            sys.executable, gate_path, "--json", "--output-json", invalid_path
        ], capture_output=True, text=True)

        if result.returncode != 1:
            print(f"FAILED: Expected exit code 1 for write failure, got {result.returncode}")
            sys.exit(1)

        ensure_no_ansi(result.stderr, "Artifact Write Failure Stderr")
        if "Error writing artifact" not in result.stderr:
            print(f"FAILED: Stderr missing expected error message. Got: {repr(result.stderr)}")
            sys.exit(1)
        print("  ✅ Artifact write failure behavior verified.")

    print("\n[SCENARIO 7] Invalid check_id Mapping Detection")
    # Mock output with correct keys but wrong mapping for 'Regression Panel Self-Check'
    invalid_mapping_data = {
        "schema_version": "1",
        "runner_version": "1.0.0",
        "overall_status": "PASS",
        "generated_at": datetime.now().isoformat(),
        "checks": [
            {
                "name": "Regression Panel Self-Check",
                "check_id": "WRONG_ID",
                "status": "PASS",
                "detail": "ok",
                "exit_code": 0
            },
            {
                "name": "Self-Check Contract Validator",
                "check_id": "self_check_contract_validator",
                "status": "PASS",
                "detail": "ok",
                "exit_code": 0
            }
        ]
    }
    try:
        validate_contract(invalid_mapping_data, "Invalid Mapping Data")
        print("FAILED: Validator accepted an invalid check_id mapping")
        sys.exit(1)
    except ValueError as e:
        if "invalid check_id" in str(e).lower():
            print(f"  ✅ Correctly caught invalid mapping: {e}")
        else:
            print(f"FAILED: Caught unexpected error: {e}")
            sys.exit(1)

    print("\n[SCENARIO 8] Manifest Export and Artifact Consistency")
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = os.path.join(tmpdir, "artifact.json")
        manifest_path = os.path.join(tmpdir, "manifest.json")
        
        result = subprocess.run([
            sys.executable, gate_path, "--json", 
            "--output-json", artifact_path,
            "--output-manifest", manifest_path
        ], capture_output=True, text=True)
        
        try:
            parse_runner_json(result, "Manifest Export (Stdout)", expected_exit_code=0)
            
            if not os.path.exists(artifact_path):
                raise ValueError("Artifact file was not created")
            if not os.path.exists(manifest_path):
                raise ValueError("Manifest file was not created")
                
            artifact_data = json.loads(load_file_text(artifact_path, "Artifact File"))
            manifest_data = json.loads(load_file_text(manifest_path, "Manifest File"))
            
            print("    Checking manifest schema...")
            required_manifest_keys = {
                "schema_version", "runner_version", "generated_at", 
                "overall_status", "artifact_path", "check_ids"
            }
            missing_manifest_keys = required_manifest_keys - set(manifest_data.keys())
            if missing_manifest_keys:
                raise ValueError(f"Manifest missing keys: {missing_manifest_keys}")
                
            print("    Verifying consistency...")
            if manifest_data["schema_version"] != artifact_data["schema_version"]:
                raise ValueError("schema_version mismatch")
            if manifest_data["overall_status"] != artifact_data["overall_status"]:
                raise ValueError("overall_status mismatch")
            if manifest_data["generated_at"] != artifact_data["generated_at"]:
                raise ValueError("generated_at mismatch")
            if manifest_data["artifact_path"] != os.path.abspath(artifact_path):
                raise ValueError(f"artifact_path mismatch: expected {os.path.abspath(artifact_path)}, got {manifest_data['artifact_path']}")
                
            artifact_check_ids = [c["check_id"] for c in artifact_data["checks"]]
            if manifest_data["check_ids"] != artifact_check_ids:
                raise ValueError(f"check_ids mismatch: expected {artifact_check_ids}, got {manifest_data['check_ids']}")
                
            print("  ✅ Manifest/Artifact consistency verified.")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n[SCENARIO 9] Bundle Export (--output-dir)")
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = os.path.join(tmpdir, "quality_gate_bundle")
        result = subprocess.run([
            sys.executable, gate_path, "--json", 
            "--output-dir", bundle_dir
        ], capture_output=True, text=True)
        
        try:
            parse_runner_json(result, "Bundle Export (Stdout)", expected_exit_code=0)
            
            if not os.path.exists(bundle_dir):
                raise ValueError("Bundle directory was not created")
                
            report_path = os.path.join(bundle_dir, "quality_gate_report.json")
            manifest_path = os.path.join(bundle_dir, "quality_gate_manifest.json")
            
            if not os.path.exists(report_path):
                raise ValueError("Bundle report file missing")
            if not os.path.exists(manifest_path):
                raise ValueError("Bundle manifest file missing")
                
            report_data = json.loads(load_file_text(report_path, "Bundle Report File"))
            manifest_data = json.loads(load_file_text(manifest_path, "Bundle Manifest File"))
            
            print("    Verifying bundle manifest consistency...")
            if manifest_data["artifact_path"] != os.path.abspath(report_path):
                raise ValueError(f"Bundle manifest artifact_path mismatch: expected {os.path.abspath(report_path)}, got {manifest_data['artifact_path']}")
            
            if manifest_data["overall_status"] != report_data["overall_status"]:
                raise ValueError("Bundle manifest/report status mismatch")
                
            print("  ✅ Bundle export verified.")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n[SCENARIO 10] Snapshot Export (--snapshot-root)")
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_root = os.path.join(tmpdir, "quality_gate_snapshots")
        result = subprocess.run([
            sys.executable, gate_path, "--json", 
            "--snapshot-root", snapshot_root
        ], capture_output=True, text=True)
        
        try:
            parse_runner_json(result, "Snapshot Export (Stdout)", expected_exit_code=0)
            
            if not os.path.exists(snapshot_root):
                raise ValueError("Snapshot root directory was not created")
            
            snapshot_dirs = sorted(
                name for name in os.listdir(snapshot_root)
                if os.path.isdir(os.path.join(snapshot_root, name))
            )
            if not snapshot_dirs:
                raise ValueError("No timestamped subdirectory created in snapshot root")
            
            snapshot_id = snapshot_dirs[0]
            snapshot_dir = os.path.join(snapshot_root, snapshot_id)
            if not os.path.isdir(snapshot_dir):
                raise ValueError(f"Expected directory at {snapshot_dir}")
                
            # Verify naming pattern YYYYMMDD_HHMMSS_microseconds
            if not re.match(r"^\d{8}_\d{6}_\d{6}$", snapshot_id):
                raise ValueError(f"Invalid snapshot subdirectory naming: {snapshot_id}")

            report_path = os.path.join(snapshot_dir, "quality_gate_report.json")
            manifest_path = os.path.join(snapshot_dir, "quality_gate_manifest.json")
            
            if not os.path.exists(report_path):
                raise ValueError("Snapshot report file missing")
            if not os.path.exists(manifest_path):
                raise ValueError("Snapshot manifest file missing")
                
            report_data = json.loads(load_file_text(report_path, "Snapshot Report File"))
            manifest_data = json.loads(load_file_text(manifest_path, "Snapshot Manifest File"))
            
            print("    Verifying snapshot manifest consistency...")
            if manifest_data["artifact_path"] != os.path.abspath(report_path):
                raise ValueError(f"Snapshot manifest artifact_path mismatch: expected {os.path.abspath(report_path)}, got {manifest_data['artifact_path']}")
            
            if manifest_data["overall_status"] != report_data["overall_status"]:
                raise ValueError("Snapshot manifest/report status mismatch")
                
            # Verify index.json
            print("    Verifying snapshot index.json...")
            index_path = os.path.join(snapshot_root, "index.json")
            if not os.path.exists(index_path):
                raise ValueError("Snapshot index.json missing")
            
            index_data = json.loads(load_file_text(index_path, "Snapshot Index File"))
            for key in ("schema_version", "runner_version", "latest_snapshot", "snapshots", "summary"):
                if key not in index_data:
                    raise ValueError(f"Index missing key: {key}")
            
            if not isinstance(index_data["snapshots"], list):
                raise ValueError("Index 'snapshots' must be a list")
            
            if index_data["latest_snapshot"] != snapshot_id:
                raise ValueError(f"Index latest_snapshot mismatch: expected {snapshot_id}, got {index_data['latest_snapshot']}")
            
            # Summary validation
            summary = index_data["summary"]
            for key in ("snapshot_count", "status_counts", "latest_pass_snapshot"):
                if key not in summary:
                    raise ValueError(f"Index summary missing key: {key}")
            
            if summary["snapshot_count"] != len(index_data["snapshots"]):
                raise ValueError("Index summary snapshot_count mismatch")
            
            if report_data["overall_status"] == "PASS":
                if summary["latest_pass_snapshot"] != snapshot_id:
                    raise ValueError(f"Index summary latest_pass_snapshot mismatch: expected {snapshot_id}, got {summary['latest_pass_snapshot']}")
                if summary["status_counts"].get("PASS", 0) < 1:
                    raise ValueError("Index summary status_counts missing PASS count")
            
            found_current = False
            for snap in index_data["snapshots"]:
                if snap["id"] == snapshot_id:
                    found_current = True
                    if snap["report_path"] != os.path.join(snapshot_id, "quality_gate_report.json"):
                        raise ValueError(f"Index report_path mismatch for {snapshot_id}")
                    if snap["manifest_path"] != os.path.join(snapshot_id, "quality_gate_manifest.json"):
                        raise ValueError(f"Index manifest_path mismatch for {snapshot_id}")
                    break
            
            if not found_current:
                raise ValueError(f"Current snapshot {snapshot_id} not found in index")

            print("  ✅ Snapshot export and index verified.")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n" + "="*40)
    print("ALL QUALITY GATE CONTRACT VALIDATIONS PASSED.")
    print("="*40)

if __name__ == "__main__":
    main()
