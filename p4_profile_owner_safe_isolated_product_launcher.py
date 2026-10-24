#!/usr/bin/env python3
"""Run the additive profile-owner product in the existing local write sandbox."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

import p4_past_source_safe_isolated_product_launcher as prior
import p4_b_safe_isolated_product_launcher as base_launcher
import p4_b_safe_isolated_product_launcher_v2 as sandbox


ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_profile_owner.py"


def preflight_profile_owner(**kwargs):
    summary, env, layout, created, profile = prior.preflight_past_source(**kwargs)
    probe = (
        "import json, gradio; import uruha_web_ui_product_p4_profile_owner as entry; "
        "import uruha_profile_owner_admission_p4 as overlay; "
        "print(json.dumps({'ok': True, 'entry': entry.__name__, "
        "'runtime_reused': entry.RUNTIME is entry._prior.RUNTIME, "
        "'overlay_installed': overlay._INSTALLED, "
        "'demo_builder': callable(entry._base.build_demo)}))"
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
                f"sandboxed_profile_owner_probe_failed:returncode={completed.returncode}"
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
        if not payload or not all(payload.get(key) is True for key in (
            "runtime_reused", "overlay_installed", "demo_builder"
        )):
            raise base_launcher.LauncherError("sandboxed_profile_owner_probe_invalid_output")
    except Exception:
        if created:
            shutil.rmtree(layout["runtime_root"], ignore_errors=True)
        raise
    summary.update({
        "schema": "uruha_p4_profile_owner_product_launch_preflight_v1",
        "entrypoint": str(ENTRYPOINT),
        "sandboxed_profile_owner_probe": payload,
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
    summary, env, layout, created, profile = preflight_profile_owner(
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
