#!/usr/bin/env python3
"""Launch the first-step product overlay inside the existing private sandbox."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time

import p4_status_truth_safe_isolated_product_launcher as prior


ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_first_step_route.py"


def _probe_first_step(python: Path, env: dict[str, str], profile: Path) -> dict:
    probe = (
        "import json, gradio; import uruha_web_ui_product_p4_first_step_route as entry; "
        "import uruha_explicit_first_step_route_p4 as overlay; "
        "import uruha_source_bound_candidate_prompt_p4 as candidate; "
        "import uruha_crosslingual_help_routing_m47 as m47; "
        "print(json.dumps({'ok': True, 'entry': entry.__name__, "
        "'runtime_reused': entry.RUNTIME is entry._prior.RUNTIME, "
        "'overlay_installed': m47.classify_help_route_m47 is overlay.classify_first_step_route_p4, "
        "'candidate_prompt_installed': candidate.installed_source_bound_candidate_prompt_p4(), "
        "'demo_builder': callable(entry._base.build_demo)}))"
    )
    completed = subprocess.run(
        prior.sandbox.sandbox_command(profile, [str(python), "-c", probe]),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if completed.returncode != 0:
        raise prior.base_launcher.LauncherError(
            f"sandboxed_first_step_probe_failed:returncode={completed.returncode}"
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
    if not payload or not all(
        payload.get(key) is True for key in (
            "runtime_reused", "overlay_installed", "candidate_prompt_installed", "demo_builder"
        )
    ):
        raise prior.base_launcher.LauncherError("sandboxed_first_step_probe_invalid_output")
    return payload


def preflight_first_step(**kwargs):
    summary, env, layout, created, profile = prior.preflight_status_truth(**kwargs)
    try:
        probe = _probe_first_step(Path(summary["python"]), env, profile)
    except Exception:
        if created:
            shutil.rmtree(layout["runtime_root"], ignore_errors=True)
        raise
    summary.update(
        {
            "schema": "uruha_p4_first_step_route_product_launch_preflight_v1",
            "entrypoint": str(ENTRYPOINT),
            "sandboxed_first_step_probe": probe,
        }
    )
    return summary, env, layout, created, profile


def main(argv=None):
    args = prior._parser().parse_args(argv)
    summary, env, layout, created, profile = preflight_first_step(
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
    command = prior.sandbox.sandbox_command(profile, [summary["python"], str(ENTRYPOINT)])
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    summary.update(
        {
            "status": "running",
            "server_started": True,
            "pid": process.pid,
            "url": f"http://{prior.base_launcher.HOST}:{summary['port']}/",
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
