#!/usr/bin/env python3
import os
import sys
import py_compile
import subprocess
import json
import argparse
from datetime import datetime

# Metadata constants
RUNNER_VERSION = "1.1"
SCHEMA_VERSION = "1"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_result(name, success, detail=""):
    status = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
    print(f"[{status}] {name}")
    if detail and not success:
        print(f"      {detail}")

def main():
    parser = argparse.ArgumentParser(description="Regression Panel Self-Check Runner")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--uruha-path", help="Override uruha_web_ui.py path (for testing)")
    parser.add_argument("--harness-path", help="Override harness path (for testing)")
    args = parser.parse_args()

    if not args.json:
        print(f"{BOLD}=== Regression Panel Self-Check Runner v1 ==={RESET}\n")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uruha_web_ui_path = args.uruha_path if args.uruha_path else os.path.join(base_dir, "uruha_web_ui.py")
    harness_path = args.harness_path if args.harness_path else os.path.join(base_dir, "analysis", "regression_panel_contract_harness.py")
    
    all_success = True
    steps = []
    
    # Step 1: Syntax Check
    if not args.json:
        print(f"{BOLD}Step 1: Syntax Check (py_compile){RESET}")
    
    for path in [uruha_web_ui_path, harness_path]:
        name = os.path.basename(path)
        step_name = f"Syntax: {name}"
        step_id = "syntax_uruha_web_ui" if name == "uruha_web_ui.py" else "syntax_contract_harness"
        try:
            py_compile.compile(path, doraise=True)
            if not args.json:
                print_result(step_name, True)
            steps.append({
                "step_id": step_id,
                "name": step_name, 
                "status": "PASS", 
                "detail": ""
            })
        except py_compile.PyCompileError as e:
            if not args.json:
                print_result(step_name, False, str(e))
            steps.append({
                "step_id": step_id,
                "name": step_name, 
                "status": "FAIL", 
                "detail": str(e)
            })
            all_success = False
        except Exception as e:
            if not args.json:
                print_result(step_name, False, str(e))
            steps.append({
                "step_id": step_id,
                "name": step_name, 
                "status": "FAIL", 
                "detail": str(e)
            })
            all_success = False
    
    if not args.json:
        print()

    # Step 2: Contract Harness Execution
    if all_success:
        if not args.json:
            print(f"{BOLD}Step 2: Contract Harness Execution{RESET}")
        
        step_name = "Contract Harness"
        step_id = "contract_harness"
        try:
            # Run the harness and capture output
            result = subprocess.run(
                [sys.executable, harness_path],
                capture_output=True,
                text=True,
                cwd=base_dir,
            )
            
            harness_success = (result.returncode == 0)
            if not args.json:
                print_result(step_name, harness_success)
            
            if not harness_success:
                detail = f"STDOUT: {result.stdout.strip()}\nSTDERR: {result.stderr.strip()}"
                steps.append({
                    "step_id": step_id,
                    "name": step_name, 
                    "status": "FAIL", 
                    "detail": detail
                })
                
                if not args.json:
                    if result.stdout.strip():
                        print(f"\n{RED}--- Harness STDOUT ---{RESET}")
                        print(result.stdout)
                    if result.stderr.strip():
                        print(f"\n{RED}--- Harness STDERR ---{RESET}")
                        print(result.stderr)
                all_success = False
            else:
                steps.append({
                    "step_id": step_id,
                    "name": step_name, 
                    "status": "PASS", 
                    "detail": ""
                })
        except Exception as e:
            if not args.json:
                print_result(step_name, False, str(e))
            steps.append({
                "step_id": step_id,
                "name": step_name, 
                "status": "FAIL", 
                "detail": str(e)
            })
            all_success = False
    else:
        if not args.json:
            print(f"{RED}Skipping Step 2 due to syntax errors.{RESET}")

    exit_code = 0 if all_success else 1

    if args.json:
        output = {
            "schema_version": SCHEMA_VERSION,
            "runner_version": RUNNER_VERSION,
            "generated_at": datetime.now().isoformat(),
            "overall_status": "PASS" if all_success else "FAIL",
            "steps": steps,
            "exit_code": exit_code
        }
        print(json.dumps(output, indent=2))
        sys.exit(exit_code)

    # Final Summary (Text Mode)
    print(f"\n{BOLD}=== Summary ==={RESET}")
    if all_success:
        print(f"{GREEN}{BOLD}ALL CHECKS PASSED{RESET}")
    else:
        print(f"{RED}{BOLD}SOME CHECKS FAILED{RESET}")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
