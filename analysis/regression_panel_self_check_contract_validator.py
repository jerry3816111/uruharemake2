#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

# Contract Constants
EXPECTED_KEYS = {
    "schema_version",
    "runner_version",
    "generated_at",
    "overall_status",
    "steps",
    "exit_code"
}

EXPECTED_STEP_IDS = {
    "syntax_uruha_web_ui",
    "syntax_contract_harness",
    "contract_harness"
}

ANSI_ESCAPE_MARKERS = ("\033[", "\x1b[")


def ensure_no_ansi(raw_output, label):
    if any(marker in raw_output for marker in ANSI_ESCAPE_MARKERS):
        raise ValueError(f"ANSI escape code leaked in {label} raw output")


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

    missing_keys = EXPECTED_KEYS - set(data.keys())
    if missing_keys:
        raise ValueError(f"Missing top-level keys: {missing_keys}")

    if expected_status and data["overall_status"] != expected_status:
        raise ValueError(f"Expected overall_status {expected_status}, got {data['overall_status']}")

    try:
        datetime.fromisoformat(data["generated_at"])
    except ValueError as exc:
        raise ValueError(f"Invalid generated_at format: {data['generated_at']}") from exc

    if not isinstance(data["steps"], list):
        raise ValueError("Steps must be a list")
    if len(data["steps"]) == 0:
        raise ValueError("Steps list is empty")

    step_ids = set()
    for step in data["steps"]:
        missing_step_keys = {"step_id", "name", "status", "detail"} - set(step.keys())
        if missing_step_keys:
            raise ValueError(f"Step is missing keys: {missing_step_keys}")
        step_ids.add(step["step_id"])

    invalid_ids = step_ids - EXPECTED_STEP_IDS
    if invalid_ids:
        raise ValueError(f"Unknown step_ids found: {invalid_ids}")

    for step in data["steps"]:
        for k, v in step.items():
            if isinstance(v, str) and any(marker in v for marker in ANSI_ESCAPE_MARKERS):
                raise ValueError(f"ANSI escape code leaked in field '{k}': {repr(v)}")

    if not data["schema_version"] or not data["runner_version"]:
        raise ValueError("Missing version metadata")

    print(f"  ✅ {label} passed contract validation.")

def main():
    print("=== Regression Panel Self-Check Contract Validator v1 ===\n")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runner_path = os.path.join(base_dir, "analysis", "regression_panel_self_check.py")
    
    if not os.path.exists(runner_path):
        print(f"Error: Runner not found at {runner_path}")
        sys.exit(1)

    print("[SCENARIO] Success Path (Normal execution)")
    result = subprocess.run([sys.executable, runner_path, "--json"], capture_output=True, text=True)
    try:
        data = parse_runner_json(result, "Success Path Output", expected_exit_code=0)
        validate_contract(data, "Success Path Output", expected_status="PASS")
        if {step["step_id"] for step in data["steps"]} != EXPECTED_STEP_IDS:
            raise ValueError("Success path did not contain the expected full step_id set")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    print("\n[SCENARIO] Failure Path (Step 1: Syntax Error)")
    with tempfile.TemporaryDirectory() as tmp_dir:
        broken_file = os.path.join(tmp_dir, "uruha_web_ui.py")
        with open(broken_file, 'w') as f:
            f.write("def broken_syntax(:\n    pass")
        result = subprocess.run([
            sys.executable, runner_path, "--json",
            "--uruha-path", broken_file
        ], capture_output=True, text=True)
        try:
            data = parse_runner_json(result, "Failure Path (Syntax)", expected_exit_code=1)
            validate_contract(data, "Failure Path (Syntax)", expected_status="FAIL")
            syntax_step = next((s for s in data["steps"] if s["step_id"] == "syntax_uruha_web_ui"), None)
            if not syntax_step or syntax_step["status"] != "FAIL":
                raise ValueError("Step 'syntax_uruha_web_ui' should have failed")
            if any(step["step_id"] == "contract_harness" for step in data["steps"]):
                raise ValueError("Syntax failure path should not execute contract_harness")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n[SCENARIO] Failure Path (Step 2: Harness Runtime Error)")
    with tempfile.NamedTemporaryFile(suffix=".py", mode='w') as tmp:
        tmp.write("import sys; print('Simulated failure'); sys.exit(1)")
        tmp.flush()
        result = subprocess.run([
            sys.executable, runner_path, "--json",
            "--harness-path", tmp.name
        ], capture_output=True, text=True)
        try:
            data = parse_runner_json(result, "Failure Path (Harness)", expected_exit_code=1)
            validate_contract(data, "Failure Path (Harness)", expected_status="FAIL")
            harness_step = next((s for s in data["steps"] if s["step_id"] == "contract_harness"), None)
            if not harness_step or harness_step["status"] != "FAIL":
                raise ValueError("Step 'contract_harness' should have failed")
            if "Simulated failure" not in harness_step["detail"]:
                raise ValueError("Harness output should be captured in detail")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)

    print("\n" + "="*40)
    print("ALL CONTRACT VALIDATIONS PASSED SUCCESSFULLY.")
    print("="*40)

if __name__ == "__main__":
    main()
