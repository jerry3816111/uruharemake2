#!/usr/bin/env python3
"""Run the source-bound preference fallback product in the local write sandbox."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

import p4_question_evidence_safe_isolated_product_launcher as prior
import p4_b_safe_isolated_product_launcher as base_launcher
import p4_b_safe_isolated_product_launcher_v2 as sandbox


ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_preference_fallback.py"
REQUIRED_CONTRACT = (
    "installed",
    "owner_postposed",
    "positive_route",
    "negative_route",
    "original_priority",
    "raw_free_trace",
)


def preflight_preference_fallback(**kwargs):
    summary, env, layout, created, profile = prior.preflight_question_evidence(**kwargs)
    probe = (
        "import json, gradio\n"
        "import uruha_web_ui_product_p4_preference_fallback as entry\n"
        "from uruha_source_bound_preference_fallback_p4 import preference_fallback_preflight_p4\n"
        "contract = preference_fallback_preflight_p4()\n"
        "print(json.dumps({'ok': True, 'entry': entry.__name__, "
        "'runtime_reused': entry.RUNTIME is entry._prior.RUNTIME, "
        "'demo_builder': callable(entry._base.build_demo), "
        "'contract': contract}))\n"
    )
    try:
        completed = subprocess.run(
            sandbox.sandbox_command(profile, [str(summary["python"]), "-c", probe]),
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if completed.returncode != 0:
            raise base_launcher.LauncherError(
                f"sandboxed_preference_fallback_probe_failed:returncode={completed.returncode}"
            )
        payload = None
        for line in reversed(completed.stdout.splitlines()):
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and candidate.get("ok") is True:
                payload = candidate
                break
        contract = payload.get("contract") if isinstance(payload, dict) else None
        if (
            not payload
            or payload.get("runtime_reused") is not True
            or payload.get("demo_builder") is not True
            or not isinstance(contract, dict)
            or not all(contract.get(key) is True for key in REQUIRED_CONTRACT)
            or not all(value is True for value in contract.values())
        ):
            raise base_launcher.LauncherError("sandboxed_preference_fallback_probe_invalid_output")
    except Exception:
        if created:
            shutil.rmtree(layout["runtime_root"], ignore_errors=True)
        raise
    summary.update({
        "schema": "uruha_p4_preference_fallback_product_launch_preflight_v1",
        "entrypoint": str(ENTRYPOINT),
        "sandboxed_preference_fallback_probe": payload,
    })
    return summary, env, layout, created, profile


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--python", dest="python_arg")
    parser.add_argument("--port", type=int, default=7892)
    parser.add_argument("--runtime-root")
    parser.add_argument("--reuse-runtime", action="store_true")
    parser.add_argument("--preserve-runtime", action="store_true")
    parser.add_argument("--prewarm", action="store_true")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    summary, env, layout, created, profile = preflight_preference_fallback(
        python_arg=args.python_arg,
        runtime_root_arg=args.runtime_root,
        reuse_runtime=args.reuse_runtime,
        port=args.port,
        prewarm=args.prewarm,
    )
    runtime_root = layout["runtime_root"]
    if args.mode == "check":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if created and not args.preserve_runtime:
            shutil.rmtree(runtime_root, ignore_errors=True)
        return 0
    command = sandbox.sandbox_command(profile, [summary["python"], str(ENTRYPOINT)])
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    summary.update({
        "status": "running",
        "server_started": True,
        "pid": process.pid,
        "url": f"http://{base_launcher.HOST}:{summary['port']}/",
        "started_at_unix": time.time(),
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            return process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            return process.wait()
    finally:
        if created and not args.preserve_runtime:
            shutil.rmtree(runtime_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
