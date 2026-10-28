#!/usr/bin/env python3
"""Sandbox repair for the frozen P4-B isolated product launcher."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

import p4_b_safe_isolated_product_launcher as v1


ROOT = Path(__file__).resolve().parent
ORIGINAL_CHECKOUT = ROOT.parent.parent / "uruharemake2"
SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")
PROFILE_NAME = "product-write-isolation.sb"


def _sandbox_string(value: Path) -> str:
    return json.dumps(str(value.resolve()))


def sandbox_profile_text(protected_roots: list[Path]) -> str:
    unique = []
    seen = set()
    for root in protected_roots:
        resolved = root.resolve()
        if str(resolved) not in seen:
            unique.append(resolved)
            seen.add(str(resolved))
    lines = ["(version 1)", "(allow default)"]
    lines.extend(
        f"(deny file-write* (subpath {_sandbox_string(root)}))" for root in unique
    )
    return "\n".join(lines) + "\n"


def write_sandbox_profile(
    runtime_root: Path,
    *,
    protected_roots: list[Path] | None = None,
) -> Path:
    if not SANDBOX_EXEC.is_file() or not os.access(SANDBOX_EXEC, os.X_OK):
        raise v1.LauncherError("sandbox_exec_unavailable")
    protected_roots = protected_roots or [ROOT, ORIGINAL_CHECKOUT]
    profile = runtime_root / PROFILE_NAME
    profile.write_text(sandbox_profile_text(protected_roots), encoding="utf-8")
    os.chmod(profile, stat.S_IRUSR | stat.S_IWUSR)
    return profile


def sandbox_command(profile: Path, command: list[str]) -> list[str]:
    return [str(SANDBOX_EXEC), "-f", str(profile), *command]


def sandboxed_probe(
    python: Path,
    env: dict[str, str],
    profile: Path,
    *,
    root: Path = ROOT,
) -> dict:
    probe = (
        "import json, gradio; import uruha_web_ui_product as entry; "
        "print(json.dumps({'ok': True, 'gradio': gradio.__version__, "
        "'entry': entry.__name__, 'demo_builder': callable(entry._base.build_demo)}))"
    )
    completed = subprocess.run(
        sandbox_command(profile, [str(python), "-c", probe]),
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if completed.returncode != 0:
        raise v1.LauncherError(
            f"sandboxed_product_probe_failed:returncode={completed.returncode}"
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
    if not payload or payload.get("demo_builder") is not True:
        raise v1.LauncherError("sandboxed_product_probe_invalid_output")
    return payload


def preflight_v2(**kwargs):
    summary, env, layout, created = v1.preflight(**kwargs)
    runtime_root = layout["runtime_root"]
    try:
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["URUHA_PRODUCT_WRITE_SANDBOX"] = "1"
        profile = write_sandbox_profile(runtime_root)
        probe = sandboxed_probe(Path(summary["python"]), env, profile)
    except Exception:
        if created:
            shutil.rmtree(runtime_root, ignore_errors=True)
        raise
    summary.update(
        {
            "schema": "uruha_p4_b_product_launch_preflight_v2",
            "sandbox": {
                "enabled": True,
                "executor": str(SANDBOX_EXEC),
                "profile": str(profile),
                "profile_mode": oct(stat.S_IMODE(profile.stat().st_mode)),
                "protected_roots": [str(ROOT.resolve()), str(ORIGINAL_CHECKOUT.resolve())],
                "isolated_runtime_writable": True,
            },
            "sandboxed_probe": probe,
        }
    )
    return summary, env, layout, created, profile


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--python", dest="python_arg")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--runtime-root")
    parser.add_argument("--reuse-runtime", action="store_true")
    parser.add_argument("--preserve-runtime", action="store_true")
    parser.add_argument("--prewarm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    summary, env, layout, created, profile = preflight_v2(
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

    command = sandbox_command(profile, [summary["python"], str(v1.ENTRYPOINT)])
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    summary.update(
        {
            "status": "running",
            "server_started": True,
            "pid": process.pid,
            "url": f"http://{v1.HOST}:{summary['port']}/",
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
