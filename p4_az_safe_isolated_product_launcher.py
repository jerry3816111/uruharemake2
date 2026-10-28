#!/usr/bin/env python3
"""Launch P4-AZ with the released private-runtime sandbox."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

import p4_ay_safe_isolated_product_launcher as prior


ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_az.py"


def sandboxed_p4_az_probe(python: Path, env: dict[str, str], profile: Path) -> dict:
    probe = (
        "import json, gradio; import uruha_web_ui_product_p4_az as entry; "
        "import uruha_previous_turn_cjk_ellipsis_authority_p4 as authority; "
        "print(json.dumps({'ok': True, 'gradio': gradio.__version__, "
        "'entry': entry.__name__, 'demo_builder': callable(entry._base.build_demo), "
        "'runtime_reused': entry.RUNTIME is entry._p4_ay.RUNTIME, "
        "'authority_installed': authority._INSTALLED_P4_AZ}))"
    )
    completed = subprocess.run(
        prior.prior.v2.sandbox_command(profile, [str(python), "-c", probe]),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if completed.returncode != 0:
        raise prior.prior.v1.LauncherError(
            f"sandboxed_p4_az_probe_failed:returncode={completed.returncode}"
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
    required = ("demo_builder", "runtime_reused", "authority_installed")
    if not payload or not all(payload.get(field) is True for field in required):
        raise prior.prior.v1.LauncherError("sandboxed_p4_az_probe_invalid_output")
    return payload


def preflight_p4_az(**kwargs):
    summary, env, layout, created, profile = prior.prior.v2.preflight_v2(**kwargs)
    try:
        probe = sandboxed_p4_az_probe(Path(summary["python"]), env, profile)
    except Exception:
        if created:
            shutil.rmtree(layout["runtime_root"], ignore_errors=True)
        raise
    summary.update(
        {
            "schema": "uruha_p4_az_product_launch_preflight_v1",
            "entrypoint": str(ENTRYPOINT),
            "sandboxed_p4_az_probe": probe,
        }
    )
    return summary, env, layout, created, profile


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--python", dest="python_arg")
    parser.add_argument("--port", type=int, default=7891)
    parser.add_argument("--runtime-root")
    parser.add_argument("--reuse-runtime", action="store_true")
    parser.add_argument("--preserve-runtime", action="store_true")
    parser.add_argument("--prewarm", action="store_true")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    summary, env, layout, created, profile = preflight_p4_az(
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
    command = prior.prior.v2.sandbox_command(profile, [summary["python"], str(ENTRYPOINT)])
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    summary.update(
        {
            "status": "running",
            "server_started": True,
            "pid": process.pid,
            "url": f"http://{prior.prior.v1.HOST}:{summary['port']}/",
            "started_at_unix": time.time(),
        }
    )
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
