#!/usr/bin/env python3
"""Launch the existing product UI with fail-closed local data isolation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "uruha_web_ui_product.py"
MANIFEST_NAME = "uruha_product_launcher_manifest.json"
HOST = "127.0.0.1"


class LauncherError(RuntimeError):
    pass


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _absolute_without_resolving_symlink(path: Path) -> Path:
    """Keep a venv's python symlink path so Python can discover pyvenv.cfg."""
    return Path(os.path.abspath(os.fspath(path)))


def python_candidates(explicit: str | None, environ: dict[str, str], root: Path = ROOT) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if environ.get("URUHA_PRODUCT_PYTHON"):
        candidates.append(Path(environ["URUHA_PRODUCT_PYTHON"]).expanduser())
    candidates.append(root / "Style-Bert-VITS2" / "venv" / "bin" / "python")
    candidates.append(
        root.parent.parent / "uruharemake2" / "Style-Bert-VITS2" / "venv" / "bin" / "python"
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(_absolute_without_resolving_symlink(candidate))
        if key not in seen:
            unique.append(_absolute_without_resolving_symlink(candidate))
            seen.add(key)
    return unique


def resolve_python(explicit: str | None, environ: dict[str, str], root: Path = ROOT) -> Path:
    candidates = python_candidates(explicit, environ, root)
    for candidate in candidates:
        if _is_executable_file(candidate):
            return _absolute_without_resolving_symlink(candidate)
    raise LauncherError(
        "no_executable_product_python:" + ",".join(str(path) for path in candidates)
    )


def validate_port(port: int) -> int:
    port = int(port)
    if not 1024 <= port <= 65535:
        raise LauncherError(f"invalid_port:{port}")
    return port


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _write_manifest(runtime_root: Path, *, created_by_launcher: bool = True) -> Path:
    manifest = runtime_root / MANIFEST_NAME
    payload = {
        "schema": "uruha_p4_b_runtime_root_v1",
        "created_by_launcher": bool(created_by_launcher),
        "contains_secrets": False,
    }
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest, stat.S_IRUSR | stat.S_IWUSR)
    return manifest


def _valid_launcher_root(runtime_root: Path) -> bool:
    manifest = runtime_root / MANIFEST_NAME
    if not manifest.is_file():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("schema") == "uruha_p4_b_runtime_root_v1"
        and payload.get("created_by_launcher") is True
    )


def prepare_runtime_root(
    requested: str | None,
    *,
    reuse: bool,
    temporary_parent: Path | None = None,
) -> tuple[Path, bool]:
    temporary_parent = (temporary_parent or Path(tempfile.gettempdir())).resolve()
    if requested:
        runtime_root = Path(requested).expanduser().resolve(strict=False)
        if not _within(runtime_root, temporary_parent):
            raise LauncherError(f"runtime_root_outside_temporary_parent:{runtime_root}")
        if runtime_root.exists():
            if not reuse:
                raise LauncherError(f"existing_runtime_root_requires_reuse:{runtime_root}")
            if not _valid_launcher_root(runtime_root):
                raise LauncherError(f"existing_runtime_root_not_launcher_owned:{runtime_root}")
            created = False
        else:
            if reuse:
                raise LauncherError(f"reuse_runtime_root_missing:{runtime_root}")
            runtime_root.mkdir(parents=False, mode=0o700)
            _write_manifest(runtime_root)
            created = True
    else:
        runtime_root = Path(tempfile.mkdtemp(prefix="uruha-product-", dir=temporary_parent))
        os.chmod(runtime_root, 0o700)
        _write_manifest(runtime_root)
        created = True
    if stat.S_IMODE(runtime_root.stat().st_mode) != 0o700:
        os.chmod(runtime_root, 0o700)
    return runtime_root, created


def build_runtime_layout(runtime_root: Path) -> dict[str, Path]:
    layout = {
        "runtime_root": runtime_root,
        "memory_db": runtime_root / "memory_db",
        "session_db": runtime_root / "session_db",
        "web_logs": runtime_root / "web_logs",
        "jsonl_log": runtime_root / "web_logs" / "conversation.jsonl",
        "text_log": runtime_root / "web_logs" / "conversation.txt",
    }
    for key in ("memory_db", "session_db", "web_logs"):
        layout[key].mkdir(mode=0o700, exist_ok=True)
        os.chmod(layout[key], 0o700)
    return layout


def child_environment(
    base: dict[str, str], layout: dict[str, Path], *, port: int, prewarm: bool
) -> dict[str, str]:
    env = dict(base)
    env.update(
        {
            "URUHA_MEMORY_DB_PATH": str(layout["memory_db"]),
            "URUHA_WEB_SESSION_DB_PATH": str(layout["session_db"]),
            "URUHA_WEB_LOG_JSONL_PATH": str(layout["jsonl_log"]),
            "URUHA_WEB_LOG_TXT_PATH": str(layout["text_log"]),
            "URUHA_WEB_HOST": HOST,
            "URUHA_WEB_PORT": str(validate_port(port)),
            "URUHA_SKIP_AUTO_VENV": "1",
            "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
            "URUHA_WEB_PREWARM_BRAIN": "1" if prewarm else "0",
            "GRADIO_ANALYTICS_ENABLED": "False",
            "PYTHONUNBUFFERED": "1",
        }
    )
    for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
        env.pop(key, None)
    return env


def probe_python(python: Path, env: dict[str, str], *, root: Path = ROOT) -> dict:
    probe = (
        "import json, gradio; import uruha_web_ui_product as entry; "
        "print(json.dumps({'ok': True, 'gradio': gradio.__version__, "
        "'entry': entry.__name__, 'demo_builder': callable(entry._base.build_demo)}))"
    )
    completed = subprocess.run(
        [str(python), "-c", probe],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if completed.returncode != 0:
        raise LauncherError(f"product_python_probe_failed:returncode={completed.returncode}")
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
        raise LauncherError("product_python_probe_invalid_output")
    return payload


def preflight(
    *,
    python_arg: str | None,
    runtime_root_arg: str | None,
    reuse_runtime: bool,
    port: int,
    prewarm: bool,
    environ: dict[str, str] | None = None,
    temporary_parent: Path | None = None,
) -> tuple[dict, dict[str, str], dict[str, Path], bool]:
    environ = dict(environ if environ is not None else os.environ)
    python = resolve_python(python_arg, environ)
    runtime_root, created = prepare_runtime_root(
        runtime_root_arg, reuse=reuse_runtime, temporary_parent=temporary_parent
    )
    try:
        layout = build_runtime_layout(runtime_root)
        env = child_environment(environ, layout, port=port, prewarm=prewarm)
        probe = probe_python(python, env)
    except Exception:
        if created:
            shutil.rmtree(runtime_root, ignore_errors=True)
        raise
    summary = {
        "schema": "uruha_p4_b_product_launch_preflight_v1",
        "status": "ready",
        "python": str(python),
        "entrypoint": str(ENTRYPOINT),
        "host": HOST,
        "port": validate_port(port),
        "runtime_root": str(runtime_root),
        "runtime_root_created": created,
        "isolated_paths": {key: str(value) for key, value in layout.items() if key != "runtime_root"},
        "probe": probe,
        "server_started": False,
        "model_call_count": 0,
        "safari_operation_count": 0,
        "vrm_or_tool_execution_count": 0,
    }
    return summary, env, layout, created


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
    summary, env, layout, created = preflight(
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

    command = [summary["python"], str(ENTRYPOINT)]
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    summary.update(
        {
            "status": "running",
            "server_started": True,
            "pid": process.pid,
            "url": f"http://{HOST}:{summary['port']}/",
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
