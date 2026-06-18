#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

# Path constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF_CHECK_PATH = os.path.join(BASE_DIR, "analysis", "regression_panel_self_check.py")
CONTRACT_VALIDATOR_PATH = os.path.join(BASE_DIR, "analysis", "regression_panel_self_check_contract_validator.py")

# Metadata
SCHEMA_VERSION = "1"
RUNNER_VERSION = "1.0.0"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text):
    return ANSI_ESCAPE_RE.sub("", text)


def serialize_report(report):
    return json.dumps(report, indent=2)

def update_snapshot_index(snapshot_root, new_snapshot_id, report_path, manifest_path, generated_at, overall_status):
    """Maintains a machine-readable index.json in the snapshot root."""
    index_path = os.path.join(snapshot_root, "index.json")
    
    index = None
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load existing index.json: {e}\n")

    if not isinstance(index, dict) or "snapshots" not in index:
        index = {
            "schema_version": SCHEMA_VERSION,
            "runner_version": RUNNER_VERSION,
            "latest_snapshot": "",
            "snapshots": []
        }

    # Add or update new entry
    new_entry = {
        "id": new_snapshot_id,
        "generated_at": generated_at.isoformat(),
        "overall_status": overall_status,
        "report_path": os.path.relpath(report_path, snapshot_root),
        "manifest_path": os.path.relpath(manifest_path, snapshot_root)
    }
    
    # Filter out existing entry with same id if any (shouldn't happen with timestamp but for safety)
    snapshots = [s for s in index.get("snapshots", []) if s.get("id") != new_snapshot_id]
    snapshots.append(new_entry)
    
    # Sort snapshots by ID descending (timestamp-based sorting)
    snapshots.sort(key=lambda x: x.get("id", ""), reverse=True)
    
    # Calculate summary
    status_counts = {}
    latest_pass_snapshot = ""
    for s in snapshots:
        status = s.get("overall_status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "PASS" and not latest_pass_snapshot:
            latest_pass_snapshot = s["id"]

    index["snapshots"] = snapshots
    index["latest_snapshot"] = snapshots[0]["id"] if snapshots else ""
    index["summary"] = {
        "snapshot_count": len(snapshots),
        "status_counts": status_counts,
        "latest_pass_snapshot": latest_pass_snapshot
    }
    index["schema_version"] = SCHEMA_VERSION
    index["runner_version"] = RUNNER_VERSION

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(index, indent=2))
        f.write("\n")

def run_check(name, check_id, cmd):
    """Runs a command and returns status and details."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )
        success = (result.returncode == 0)
        status = "PASS" if success else "FAIL"

        detail = result.stdout.strip()
        if not detail and result.stderr.strip():
            detail = result.stderr.strip()
        elif not detail and not success:
            detail = f"Command failed with exit code {result.returncode}"

        return {
            "name": name,
            "check_id": check_id,
            "status": status,
            "detail": strip_ansi(detail),
            "exit_code": result.returncode,
            "success": success,
        }
    except Exception as e:
        return {
            "name": name,
            "check_id": check_id,
            "status": "FAIL",
            "detail": str(e),
            "exit_code": 1,
            "success": False,
        }

def main():
    parser = argparse.ArgumentParser(description="Regression Panel Quality Gate Runner")
    parser.add_argument("--json", action="store_true", help="Output aggregate results in JSON format")
    parser.add_argument("--output-json", help="Path to export JSON artifact")
    parser.add_argument("--output-manifest", help="Path to export lightweight manifest JSON")
    parser.add_argument("--output-dir", help="Path to export bundle directory (report + manifest)")
    parser.add_argument("--snapshot-root", help="Root directory for timestamped snapshot exports")
    parser.add_argument("--self-check-path", help="Override path for self-check script")
    parser.add_argument("--contract-validator-path", help="Override path for contract validator script")
    args = parser.parse_args()

    self_check_path = args.self_check_path or SELF_CHECK_PATH
    contract_validator_path = args.contract_validator_path or CONTRACT_VALIDATOR_PATH

    checks = []
    
    # 1. Self-Check Runner
    check_self = run_check(
        "Regression Panel Self-Check",
        "regression_panel_self_check",
        [sys.executable, self_check_path, "--json"]
    )
    checks.append({
        "name": check_self["name"],
        "check_id": check_self["check_id"],
        "status": check_self["status"],
        "detail": check_self["detail"],
        "exit_code": check_self["exit_code"],
    })
    
    # 2. Contract Validator
    # Only run validator if self-check didn't crash (though it's independent enough to run anyway)
    check_contract = run_check(
        "Self-Check Contract Validator",
        "self_check_contract_validator",
        [sys.executable, contract_validator_path]
    )
    checks.append({
        "name": check_contract["name"],
        "check_id": check_contract["check_id"],
        "status": check_contract["status"],
        "detail": check_contract["detail"],
        "exit_code": check_contract["exit_code"],
    })

    overall_success = check_self["success"] and check_contract["success"]
    overall_status = "PASS" if overall_success else "FAIL"
    generated_at = datetime.now()

    report = {
        "schema_version": SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "overall_status": overall_status,
        "generated_at": generated_at.isoformat(),
        "checks": checks,
    }
    serialized_report = serialize_report(report)

    if args.json:
        print(serialized_report)
    else:
        print(f"{BOLD}=== Regression Panel Quality Gate v1 ==={RESET}")
        print(f"Generated at: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")

        for check in checks:
            status_color = GREEN if check["status"] == "PASS" else RED
            print(f"[{status_color}{check['status']}{RESET}] {check['name']}")
            if check["status"] == "FAIL":
                print(f"      Detail: {check['detail'].splitlines()[0]}...")

        print(f"\n{BOLD}Overall Status: {GREEN if overall_success else RED}{overall_status}{RESET}")

    # Artifact Export
    if args.output_json:
        try:
            output_path = os.path.abspath(args.output_json)
            parent_dir = os.path.dirname(output_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(serialized_report)
                f.write("\n")
        except Exception as e:
            sys.stderr.write(f"Error writing artifact to {args.output_json}: {e}\n")
            sys.exit(1)

    # Manifest Export
    if args.output_manifest:
        try:
            manifest_path = os.path.abspath(args.output_manifest)
            parent_dir = os.path.dirname(manifest_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            manifest = {
                "schema_version": SCHEMA_VERSION,
                "runner_version": RUNNER_VERSION,
                "generated_at": generated_at.isoformat(),
                "overall_status": overall_status,
                "artifact_path": os.path.abspath(args.output_json) if args.output_json else None,
                "check_ids": [c["check_id"] for c in checks],
            }

            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(manifest, indent=2))
                f.write("\n")
        except Exception as e:
            sys.stderr.write(f"Error writing manifest to {args.output_manifest}: {e}\n")
            sys.exit(1)

    # Bundle Export
    if args.output_dir:
        try:
            bundle_dir = os.path.abspath(args.output_dir)
            os.makedirs(bundle_dir, exist_ok=True)

            bundle_report_path = os.path.join(bundle_dir, "quality_gate_report.json")
            bundle_manifest_path = os.path.join(bundle_dir, "quality_gate_manifest.json")

            # Write bundle report
            with open(bundle_report_path, "w", encoding="utf-8") as f:
                f.write(serialized_report)
                f.write("\n")

            # Write bundle manifest (pointing to the report in the same bundle)
            bundle_manifest = {
                "schema_version": SCHEMA_VERSION,
                "runner_version": RUNNER_VERSION,
                "generated_at": generated_at.isoformat(),
                "overall_status": overall_status,
                "artifact_path": bundle_report_path,
                "check_ids": [c["check_id"] for c in checks],
            }
            with open(bundle_manifest_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(bundle_manifest, indent=2))
                f.write("\n")

        except Exception as e:
            sys.stderr.write(f"Error writing bundle to {args.output_dir}: {e}\n")
            sys.exit(1)

    # Snapshot Export
    if args.snapshot_root:
        try:
            timestamp = generated_at.strftime("%Y%m%d_%H%M%S_%f")
            snapshot_dir = os.path.join(os.path.abspath(args.snapshot_root), timestamp)
            os.makedirs(snapshot_dir, exist_ok=True)

            snapshot_report_path = os.path.join(snapshot_dir, "quality_gate_report.json")
            snapshot_manifest_path = os.path.join(snapshot_dir, "quality_gate_manifest.json")

            # Write snapshot report
            with open(snapshot_report_path, "w", encoding="utf-8") as f:
                f.write(serialized_report)
                f.write("\n")

            # Write snapshot manifest
            snapshot_manifest = {
                "schema_version": SCHEMA_VERSION,
                "runner_version": RUNNER_VERSION,
                "generated_at": generated_at.isoformat(),
                "overall_status": overall_status,
                "artifact_path": snapshot_report_path,
                "check_ids": [c["check_id"] for c in checks],
            }
            with open(snapshot_manifest_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(snapshot_manifest, indent=2))
                f.write("\n")

            # Update index
            update_snapshot_index(
                os.path.abspath(args.snapshot_root),
                timestamp,
                snapshot_report_path,
                snapshot_manifest_path,
                generated_at,
                overall_status
            )

        except Exception as e:
            sys.stderr.write(f"Error writing snapshot to {args.snapshot_root}: {e}\n")
            sys.exit(1)

    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    main()
