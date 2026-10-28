"""Non-B, zero-generation Ollama identity probe for the P4 B preflight.

This does not authorize a B Send or provide a production prompt-token bound. It
only checks an already-running private daemon/runner and a harmless fixed prompt.
No process is started or stopped and no raw prompt is written to a report.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import urllib.error
import urllib.request

from uruha_compact_planner_p2 import _REQUIRED_JSON_SCHEMA_FORMAT


MODEL = "qwen2.5:7b"
VERSION = "0.34.4"
FROZEN_MANIFEST_SHA256 = "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
FROZEN_DAEMON_SHA256 = "bba8b79eac84ab092b9568978c1116e6c950eda588961b14d8608ac683a2af0b"
FROZEN_RUNNER_SHA256 = "e1cf69803dac46fc5beb750ae77f3824cf4aa42bd8f636fc9d613039baf959e2"
FROZEN_BLOBS = (
    "2f15b3218f0552c60647ce60ada83632d2c09755b16259b13e3e4458e9ae419d",
    "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730",
    "66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e",
    "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
    "eb4402837c7829a690fa845de4d7f3fd842c2adee476d5341da8a46ea9255175",
)
GGUF_SHA256 = FROZEN_BLOBS[1]
TEMPLATE_SHA256 = FROZEN_BLOBS[4]
SYSTEM_SHA256 = FROZEN_BLOBS[2]
FIXTURE = "Tokenizer fixture only."


class ProbeError(RuntimeError):
    """A fixed, raw-free failure code; never interpolate HTTP/process text."""


@dataclass(frozen=True)
class ExpectedModel:
    manifest_sha256: str = FROZEN_MANIFEST_SHA256
    blob_sha256s: tuple[str, ...] = FROZEN_BLOBS
    daemon_sha256: str = FROZEN_DAEMON_SHA256
    runner_sha256: str = FROZEN_RUNNER_SHA256
    gguf_sha256: str = GGUF_SHA256
    template_sha256: str = TEMPLATE_SHA256
    system_sha256: str = SYSTEM_SHA256


FROZEN_MODEL = ExpectedModel()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_json(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _regular_single_link(path: Path, *, code: str) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ProbeError(code) from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ProbeError(code)
    return info


def _private_dir(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ProbeError("private_store_unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ProbeError("private_store_not_isolated")


def _model_store(private_root: Path, shared_models: Path, expected: ExpectedModel) -> tuple[Path, dict]:
    """Read-only byte identity; distinct inode is not proof of CoW allocation."""
    _private_dir(private_root)
    models = private_root / "models"
    _private_dir(models)
    for relative in ("blobs", "manifests", "manifests/registry.ollama.ai",
                     "manifests/registry.ollama.ai/library",
                     "manifests/registry.ollama.ai/library/qwen2.5"):
        _private_dir(models / relative)
    manifest_rel = Path("manifests/registry.ollama.ai/library/qwen2.5/7b")
    private_manifest = models / manifest_rel
    shared_manifest = shared_models / manifest_rel
    private_files = [private_manifest] + [models / "blobs" / f"sha256-{sha}" for sha in expected.blob_sha256s]
    shared_files = [shared_manifest] + [shared_models / "blobs" / f"sha256-{sha}" for sha in expected.blob_sha256s]
    recorded = []
    for private, shared in zip(private_files, shared_files, strict=True):
        private_stat = _regular_single_link(private, code="private_model_file_invalid")
        shared_stat = _regular_single_link(shared, code="shared_model_file_invalid")
        if (private_stat.st_dev, private_stat.st_ino) == (shared_stat.st_dev, shared_stat.st_ino):
            raise ProbeError("model_clone_not_distinct")
        recorded.append((private, private_stat))
    if {p.name for p in (models / "blobs").iterdir()} != {f"sha256-{sha}" for sha in expected.blob_sha256s}:
        raise ProbeError("private_model_has_extra_or_missing_blobs")
    if _sha256_file(private_manifest) != expected.manifest_sha256:
        raise ProbeError("manifest_digest_drift")
    try:
        manifest = json.loads(private_manifest.read_text(encoding="utf-8"))
        references = [manifest["config"]["digest"]] + [layer["digest"] for layer in manifest["layers"]]
        sizes = {entry["digest"].removeprefix("sha256:"): entry["size"]
                 for entry in [manifest["config"], *manifest["layers"]]}
    except (ValueError, KeyError, TypeError) as exc:
        raise ProbeError("manifest_shape_invalid") from exc
    if (len(references) != 5 or len(set(references)) != 5
            or {ref.removeprefix("sha256:") for ref in references} != set(expected.blob_sha256s)
            or any(not ref.startswith("sha256:") for ref in references)):
        raise ProbeError("manifest_references_drift")
    for sha in expected.blob_sha256s:
        blob = models / "blobs" / f"sha256-{sha}"
        if blob.stat().st_size != sizes[sha] or _sha256_file(blob) != sha:
            raise ProbeError("model_blob_digest_drift")
    return models, {str(p): (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                    for p, s in recorded}


def _process(pid: int) -> tuple[int, list[str]]:
    try:
        run = subprocess.run(["/bin/ps", "-ww", "-p", str(pid), "-o", "ppid=", "-o", "command="],
                             capture_output=True, text=True, timeout=3, check=True)
        parent, command = run.stdout.strip().split(maxsplit=1)
        return int(parent), shlex.split(command)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise ProbeError("process_identity_unavailable") from exc


def _owns_loopback_port(pid: int, port: int) -> bool:
    try:
        run = subprocess.run(["/usr/sbin/lsof", "-nP", "-a", "-p", str(pid),
                              f"-iTCP:{port}", "-sTCP:LISTEN"],
                             capture_output=True, text=True, timeout=3, check=True)
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(re.search(rf"\bTCP 127\.0\.0\.1:{port} \(LISTEN\)(?:\s|$)", run.stdout))


def _arg_value(args: list[str], key: str) -> str | None:
    try:
        return args[args.index(key) + 1]
    except (ValueError, IndexError):
        return None


def _process_identity(*, daemon_pid: int, runner_pid: int, daemon_port: int, runner_port: int,
                      daemon_binary: Path, runner_binary: Path, model_blob: Path,
                      expected: ExpectedModel) -> dict:
    daemon_parent, daemon_args = _process(daemon_pid)
    runner_parent, runner_args = _process(runner_pid)
    del daemon_parent  # Parent app identity is not an authority for this probe.
    try:
        daemon_stat = _regular_single_link(daemon_binary, code="daemon_binary_invalid")
        runner_stat = _regular_single_link(runner_binary, code="runner_binary_invalid")
        del daemon_stat, runner_stat
        binaries_match = (Path(daemon_args[0]).resolve(strict=True) == daemon_binary.resolve(strict=True)
                          and Path(runner_args[0]).resolve(strict=True) == runner_binary.resolve(strict=True))
        model_matches = Path(_arg_value(runner_args, "--model") or "").resolve(strict=True) == model_blob.resolve(strict=True)
    except (OSError, IndexError) as exc:
        raise ProbeError("process_path_unavailable") from exc
    if (not binaries_match or daemon_args[1:2] != ["serve"] or runner_parent != daemon_pid
            or not model_matches or _arg_value(runner_args, "--host") != "127.0.0.1"
            or _arg_value(runner_args, "--port") != str(runner_port)
            or "--offline" not in runner_args or "--no-jinja" not in runner_args
            or _arg_value(runner_args, "--chat-template") != "chatml"
            or not _owns_loopback_port(daemon_pid, daemon_port)
            or not _owns_loopback_port(runner_pid, runner_port)):
        raise ProbeError("process_endpoint_or_model_drift")
    daemon_sha = _sha256_file(daemon_binary)
    if daemon_sha != expected.daemon_sha256:
        raise ProbeError("daemon_binary_digest_drift")
    runner_sha = _sha256_file(runner_binary)
    if runner_sha != expected.runner_sha256:
        raise ProbeError("runner_binary_digest_drift")
    return {"daemon_binary_sha256": daemon_sha, "runner_binary_sha256": runner_sha}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ProbeError("diagnostic_redirect_forbidden")


def _http_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"} if data is not None else {},
                                     method="POST" if data is not None else "GET")
    try:
        # Never inherit the user's HTTP proxy for a loopback-only identity probe.
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect).open(request, timeout=5) as response:
            if response.geturl() != url or response.status != 200:
                raise ProbeError("diagnostic_http_identity_drift")
            body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise ProbeError("diagnostic_response_too_large")
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ProbeError("diagnostic_response_shape_invalid")
            return value
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise ProbeError("diagnostic_http_failed") from exc


def _fixed_request() -> dict:
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are the Left Brain Planner for a dual-brain character system."},
            {"role": "user", "content": f"User Input: {FIXTURE}"},
        ],
        "temperature": 0.1,
        "max_tokens": 256,
        "response_format": _REQUIRED_JSON_SCHEMA_FORMAT,
        "_debug_render_only": True,
    }


def probe(*, private_root: Path, shared_models: Path, daemon_pid: int, runner_pid: int,
          daemon_port: int, runner_port: int, daemon_binary: Path, runner_binary: Path,
          expected: ExpectedModel = FROZEN_MODEL) -> dict:
    if (min(daemon_pid, runner_pid, daemon_port, runner_port) <= 0
            or daemon_port == runner_port or 11434 in (daemon_port, runner_port)
            or max(daemon_port, runner_port) > 65535):
        raise ProbeError("private_endpoint_invalid")
    models, before = _model_store(private_root, shared_models, expected)
    binary_identity = _process_identity(
        daemon_pid=daemon_pid, runner_pid=runner_pid, daemon_port=daemon_port, runner_port=runner_port,
        daemon_binary=daemon_binary, runner_binary=runner_binary,
        model_blob=models / "blobs" / f"sha256-{expected.gguf_sha256}", expected=expected)
    daemon = f"http://127.0.0.1:{daemon_port}"
    runner = f"http://127.0.0.1:{runner_port}"
    version = _http_json(f"{daemon}/api/version")
    tags = _http_json(f"{daemon}/api/tags")
    show = _http_json(f"{daemon}/api/show", {"model": MODEL})
    if version.get("version") != VERSION:
        raise ProbeError("daemon_version_drift")
    rows = tags.get("models")
    if (not isinstance(rows, list) or len(rows) != 1 or rows[0].get("name") != MODEL
            or rows[0].get("digest") != expected.manifest_sha256):
        raise ProbeError("model_tag_digest_drift")
    try:
        template = (models / "blobs" / f"sha256-{expected.template_sha256}").read_text(encoding="utf-8")
        system = (models / "blobs" / f"sha256-{expected.system_sha256}").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProbeError("model_template_or_system_drift") from exc
    if show.get("template") != template or show.get("system") != system:
        raise ProbeError("model_template_or_system_drift")
    request = _fixed_request()
    rendered_result = _http_json(f"{daemon}/v1/chat/completions", request)
    try:
        rendered = rendered_result["_debug_info"]["rendered_template"]
        usage = rendered_result["usage"]
        choices = rendered_result["choices"]
        if (rendered_result.get("model") != MODEL or not isinstance(rendered, str)
                or not rendered or len(choices) != 1
                or choices[0]["message"]["content"] != ""
                or {key: usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
                   != {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}):
            raise ProbeError("render_only_contract_drift")
    except (KeyError, TypeError, IndexError) as exc:
        raise ProbeError("render_only_contract_drift") from exc
    if (f"User Input: {FIXTURE}" not in rendered or "<|im_start|>system" not in rendered
            or "<|im_start|>user" not in rendered):
        raise ProbeError("rendered_prompt_branch_unverified")
    tokens = _http_json(f"{runner}/tokenize", {
        "content": rendered, "add_special": False, "parse_special": True,
    }).get("tokens")
    if not isinstance(tokens, list) or not tokens or any(type(item) is not int or item < 0 for item in tokens):
        raise ProbeError("runner_tokenizer_contract_drift")
    if _model_store(private_root, shared_models, expected)[1] != before:
        raise ProbeError("private_model_store_changed_during_probe")
    _process_identity(
        daemon_pid=daemon_pid, runner_pid=runner_pid, daemon_port=daemon_port, runner_port=runner_port,
        daemon_binary=daemon_binary, runner_binary=runner_binary,
        model_blob=models / "blobs" / f"sha256-{expected.gguf_sha256}", expected=expected)
    return {
        "schema": "p4_b_non_b_private_ollama_zero_generation_identity_probe_v1",
        "status": "mechanical_identity_pass_not_b_authorization",
        "daemon_pid": daemon_pid, "runner_pid": runner_pid,
        "daemon_port": daemon_port, "runner_port": runner_port,
        "ollama_version": VERSION, "model_manifest_sha256": expected.manifest_sha256,
        "gguf_sha256": expected.gguf_sha256, "template_sha256": expected.template_sha256,
        "system_sha256": expected.system_sha256, **binary_identity,
        "request_sha256": _sha256_json(request),
        "rendered_prompt_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "rendered_prompt_chars": len(rendered), "runner_token_count": len(tokens),
        "diagnostic_http_calls": 5, "generated_completions": 0,
        "raw_rendered_prompt_or_reply_in_result": False, "copy_on_write_allocation_proven": False,
        "b_prompt_upper_bound_proven": False, "b_safari_send_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("private-root", "shared-models", "daemon-binary", "runner-binary"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("daemon-pid", "runner-pid", "daemon-port", "runner-port"):
        parser.add_argument(f"--{name}", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        result = probe(private_root=args.private_root, shared_models=args.shared_models,
                       daemon_pid=args.daemon_pid, runner_pid=args.runner_pid,
                       daemon_port=args.daemon_port, runner_port=args.runner_port,
                       daemon_binary=args.daemon_binary, runner_binary=args.runner_binary)
    except ProbeError as exc:
        print(json.dumps({"schema": "p4_b_non_b_private_ollama_zero_generation_identity_probe_v1",
                          "status": "fail_closed", "reason": str(exc), "b_safari_send_authorized": False}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
