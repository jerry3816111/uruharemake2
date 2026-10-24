"""Execute one crash-safe B55 observable-context transport invocation."""

from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

import p3_b54_public_context_reader as public_reader
import p3_b54_unidirectional_context_extraction as b54


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b55_reserved_source_context_transport_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b55_reserved_source_context_transport_implementation_freeze_2026-09-18.json"
)


class B55ContractError(ValueError):
    pass


class B55ExecutionError(RuntimeError):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    return b54.sha256_file(path)


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B55ContractError(f"expected JSON object: {path}")
    return value


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def _tool_version(executable: str) -> str:
    completed = subprocess.run(
        [executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise B55ContractError(f"tool version probe failed: {Path(executable).name}")
    return completed.stdout.splitlines()[0].strip()


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b55_reserved_source_context_transport_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_before_any_reserved_source_media_request":
        errors.append("status")
    binding = (contract.get("binding") or {}).get("b54_release") or {}
    binding_path = Path(root) / str(binding.get("path") or "")
    if not binding_path.is_file():
        errors.append("b54_release_missing")
        release = {}
    else:
        if sha256_file(binding_path) != binding.get("sha256"):
            errors.append("b54_release_hash")
        release = load_json(binding_path)
    if release and release.get("boundary_receipt_hash") != binding.get("boundary_receipt_hash"):
        errors.append("boundary_receipt")
    source = contract.get("source") or {}
    if source.get("source_id") != "youtube_4y5GiQpgJgo" or source.get("video_id") != "4y5GiQpgJgo":
        errors.append("source_binding")
    if source.get("context_start_seconds") != 3000.0 or source.get("context_end_seconds") != 3180.0:
        errors.append("context_boundary")
    if source.get("hidden_future_start_seconds") != 3181.0 or source.get("hidden_future_end_seconds") != 3241.0:
        errors.append("future_boundary")
    transport = contract.get("transport") or {}
    if transport.get("maximum_attempts") != 1:
        errors.append("attempt_count")
    if transport.get("download_section") != "*3000-3180":
        errors.append("download_section")
    for field in (
        "cookies_or_browser_session_allowed",
        "playlist_allowed",
        "metadata_sidecars_allowed",
        "subtitles_allowed",
        "comments_allowed",
        "cache_allowed",
        "resume_allowed",
        "provider_transport_exact_byte_scope_claim_allowed",
        "stdout_or_stderr_content_persistence_allowed",
    ):
        if transport.get(field) is not False:
            errors.append(f"transport_denial:{field}")
    if any(transport.get(field) != 0 for field in (
        "network_retry_count", "fragment_retry_count", "extractor_retry_count"
    )):
        errors.append("transport_retries")
    private_gate = contract.get("local_private_gate") or {}
    if private_gate.get("expected_local_duration_seconds") != 180.0:
        errors.append("local_duration")
    if private_gate.get("duration_tolerance_seconds") != 0.05:
        errors.append("duration_tolerance")
    if private_gate.get("manual_playback_or_semantic_inspection_allowed") is not False:
        errors.append("manual_inspection")
    public_output = contract.get("public_output") or {}
    if public_output.get("profile") != "reserved_source_context":
        errors.append("public_profile")
    if public_output.get("fresh_public_reader_processes") != 1:
        errors.append("public_reader_processes")
    authorization = contract.get("execution_authorization") or {}
    if authorization.get("reserved_source_media_request_count_max") != 1:
        errors.append("media_authorization")
    for field in (
        "hidden_future_media_request_authorized",
        "title_description_transcript_comment_or_subtitle_storage_authorized",
        "manual_playback_authorized",
        "prediction_execution_authorized",
        "model_call_authorized",
        "formal_m56_write_authorized",
        "production_memory_write_authorized",
        "external_deployment_authorized",
    ):
        if authorization.get(field) is not False:
            errors.append(f"authorization:{field}")
    failure = contract.get("failure_policy") or {}
    if failure.get("retry_count") != 0 or failure.get("fallback_count") != 0:
        errors.append("failure_retry")
    if failure.get("source_replacement_allowed") is not False or failure.get("cutoff_change_allowed") is not False:
        errors.append("failure_mutation")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_reserved_source_media_request":
        errors.append("freeze_status")
    for artifact_id, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{artifact_id}")
        elif sha256_file(path) != (artifact or {}).get("sha256"):
            errors.append(f"hash:{artifact_id}")
    if errors:
        raise B55ContractError(";".join(errors))
    return {
        "valid": True,
        "reserved_source_media_request_count_at_freeze": freeze.get(
            "reserved_source_media_request_count_at_freeze"
        ),
        "hidden_future_media_request_count_at_freeze": freeze.get(
            "hidden_future_media_request_count_at_freeze"
        ),
    }


def _source_locator(contract: dict[str, Any]) -> str:
    source = contract["source"]
    return source["locator_template"].replace("<video_id>", source["video_id"])


def build_transport_command(private_root: Path, contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_contract()
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise B55ContractError("yt-dlp unavailable")
    template = private_root / contract["transport"]["private_output_template"]
    return [
        executable,
        "--ignore-config",
        "--quiet",
        "--no-warnings",
        "--no-progress",
        "--no-playlist",
        "--no-write-info-json",
        "--no-write-thumbnail",
        "--no-write-subs",
        "--no-write-auto-subs",
        "--no-write-comments",
        "--no-cache-dir",
        "--no-continue",
        "--no-part",
        "--retries",
        "0",
        "--fragment-retries",
        "0",
        "--extractor-retries",
        "0",
        "--socket-timeout",
        "30",
        "--download-sections",
        contract["transport"]["download_section"],
        "--force-keyframes-at-cuts",
        "-f",
        "bestaudio/best",
        "-x",
        "--audio-format",
        "wav",
        "--audio-quality",
        "0",
        "-o",
        str(template),
        _source_locator(contract),
    ]


def _exclusive_json(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json(value).encode("utf-8")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fresh_runtime_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    state_root = ROOT / contract["crash_safe_state"]["root"]
    public_root = ROOT / contract["public_output"]["root"]
    if state_root.exists():
        raise B55ExecutionError("preflight", "B55 invocation already consumed or started")
    if public_root.exists() and any(public_root.iterdir()):
        raise B55ExecutionError("preflight", "B55 public root is already nonempty")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    material = {
        "schema": "uruha_p3_b55_transport_invocation_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "source_id": contract["source"]["source_id"],
        "download_section": contract["transport"]["download_section"],
        "contract_sha256": sha256_file(CONFIG_PATH),
        "maximum_attempts": 1,
        "hidden_future_authorized": False,
        "prediction_authorized": False,
    }
    material["intent_hash"] = sha256_bytes(canonical_json(material).encode("utf-8"))
    return material


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b55_reserved_source_context_transport_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "requested_context_seconds": [3000.0, 3180.0],
        "network_attempt_count": 0,
        "transport_returncode": None,
        "transport_stdout_bytes_discarded": 0,
        "transport_stderr_bytes_discarded": 0,
        "provider_transport_exact_byte_scope_provable": False,
        "provider_metadata_may_have_been_received_privately": True,
        "private_transport_deleted_before_fresh_public_reader": False,
        "public_artifact_count": 0,
        "public_manifest_count": 0,
        "fresh_public_reader_count": 0,
        "hidden_future_media_request_count": 0,
        "manual_playback_count": 0,
        "semantic_inspection_count": 0,
        "prediction_execution_count": 0,
        "model_call_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if result.get("schema") != "uruha_p3_b55_reserved_source_context_transport_result_v1":
        errors.append("schema")
    if result.get("status") not in {"reserved_source_context_transport_passed", "reserved_source_context_transport_failed"}:
        errors.append("status")
    if result.get("requested_context_seconds") != [3000.0, 3180.0]:
        errors.append("context")
    if result.get("network_attempt_count") not in {0, 1}:
        errors.append("network_attempt_count")
    for field in (
        "hidden_future_media_request_count",
        "manual_playback_count",
        "semantic_inspection_count",
        "prediction_execution_count",
        "model_call_count",
        "formal_m56_write_count",
        "production_memory_write_count",
        "retry_count",
        "fallback_count",
    ):
        if result.get(field) != 0:
            errors.append(field)
    if result.get("provider_transport_exact_byte_scope_provable") is not False:
        errors.append("transport_scope_claim")
    if result.get("status") == "reserved_source_context_transport_passed":
        if result.get("network_attempt_count") != 1 or result.get("transport_returncode") != 0:
            errors.append("success_transport")
        if result.get("private_transport_deleted_before_fresh_public_reader") is not True:
            errors.append("success_private_delete")
        if result.get("public_artifact_count") != 1 or result.get("public_manifest_count") != 1:
            errors.append("success_public_counts")
        if result.get("fresh_public_reader_count") != 1 or result.get("fresh_public_reader_exit_code") != 0:
            errors.append("success_reader")
        if abs(float(result.get("public_artifact_duration_seconds", 0)) - 180.0) > 0.05:
            errors.append("success_duration")
        if result.get("fresh_reader_artifact_sha256") != result.get("public_artifact_sha256"):
            errors.append("success_hash")
    else:
        if result.get("public_artifact_count") != 0 or result.get("public_manifest_count") != 0:
            errors.append("failure_public_counts")
        if not result.get("failure_stage") or not result.get("failure_class"):
            errors.append("failure_classification")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_reserved_source_context_transport() -> dict[str, Any]:
    validate_implementation_freeze()
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise B55ContractError("invalid B55 contract: " + ";".join(contract_report["errors"]))
    contract = load_contract()
    state_root, public_root = _fresh_runtime_roots(contract)
    intent = _intent(contract)
    _exclusive_json(state_root / contract["crash_safe_state"]["intent_filename"], intent)
    result = _base_result(contract)
    public_receipt = None
    start_time = perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        ffmpeg = shutil.which("ffmpeg")
        if yt_dlp is None or ffmpeg is None:
            raise B55ExecutionError("tool_preflight", "required transport tool unavailable")
        yt_dlp_version = _tool_version(yt_dlp)
        ffmpeg_version = _tool_version(ffmpeg)
        if yt_dlp_version != contract["transport"]["required_version"]:
            raise B55ExecutionError("tool_preflight", "yt-dlp version drift")
        if not ffmpeg_version.startswith(
            "ffmpeg version " + contract["transport"]["ffmpeg_required_version_prefix"]
        ):
            raise B55ExecutionError("tool_preflight", "ffmpeg version drift")
        result["yt_dlp_version"] = yt_dlp_version
        result["ffmpeg_version"] = ffmpeg_version
        with TemporaryDirectory(prefix="uruha-p3-b55-private-") as temporary:
            private_root = Path(temporary)
            os.chmod(private_root, 0o700)
            command = build_transport_command(private_root, contract)
            result["network_attempt_count"] = 1
            network_start = perf_counter()
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    timeout=contract["transport"]["timeout_seconds"],
                )
            except subprocess.TimeoutExpired as exc:
                result["transport_stdout_bytes_discarded"] = len(exc.stdout or b"")
                result["transport_stderr_bytes_discarded"] = len(exc.stderr or b"")
                raise B55ExecutionError("network_transport", "transport timeout") from exc
            result["network_elapsed_seconds"] = round(perf_counter() - network_start, 6)
            result["transport_returncode"] = completed.returncode
            result["transport_stdout_bytes_discarded"] = len(completed.stdout)
            result["transport_stderr_bytes_discarded"] = len(completed.stderr)
            if completed.returncode != 0:
                raise B55ExecutionError("network_transport", "transport exit nonzero")
            candidates = [path for path in private_root.iterdir() if path.is_file()]
            wav_candidates = [path for path in candidates if path.suffix.lower() == ".wav"]
            if len(wav_candidates) != 1 or len(candidates) != 1:
                raise B55ExecutionError("local_transport", "unexpected private transport outputs")
            raw_path = wav_candidates[0]
            os.chmod(raw_path, 0o600)
            raw_probe = public_reader._ffprobe_audio(raw_path)
            result["private_transport_bytes"] = raw_path.stat().st_size
            result["private_transport_duration_seconds"] = round(raw_probe["duration_seconds"], 6)
            expected_duration = contract["local_private_gate"]["expected_local_duration_seconds"]
            tolerance = contract["local_private_gate"]["duration_tolerance_seconds"]
            if abs(raw_probe["duration_seconds"] - expected_duration) > tolerance:
                raise B55ExecutionError("local_transport", "private transport duration outside frozen tolerance")
            staged_path = private_root / "p3-b55-normalized-observable-context.wav"
            b54._run_ffmpeg_extract(
                raw_path,
                staged_path,
                contract["local_private_gate"]["normalization_input_start_seconds"],
                contract["local_private_gate"]["normalization_input_end_seconds"],
            )
            profile = b54.load_contract()["profiles"]["reserved_source_context"]
            public_receipt = b54._publish_artifact(staged_path, public_root, profile)
            result["public_artifact_id"] = public_receipt["artifact_id"]
            result["public_artifact_sha256"] = public_receipt["artifact_sha256"]
            result["public_manifest_hash"] = public_receipt["manifest_hash"]
            result["public_artifact_duration_seconds"] = public_receipt["observed_duration_seconds"]
            result["public_artifact_count"] = 1
            result["public_manifest_count"] = 1
            raw_path.unlink()
            staged_path.unlink()
        result["private_transport_deleted_before_fresh_public_reader"] = True
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            public_reader.PUBLIC_ROOT_ENV: str(public_root),
        }
        child = subprocess.run(
            [
                sys.executable,
                str(ROOT / "p3_b54_public_context_reader.py"),
                "--inspect",
                public_receipt["artifact_id"],
            ],
            cwd=str(ROOT),
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        result["fresh_public_reader_count"] = 1
        result["fresh_public_reader_exit_code"] = child.returncode
        if child.returncode != 0:
            raise B55ExecutionError("fresh_public_reader", "public reader rejected artifact")
        child_payload = json.loads(child.stdout)
        manifest = child_payload["manifest"]
        result["fresh_reader_artifact_sha256"] = manifest["artifact_sha256"]
        result["manifest_forbidden_field_count"] = len(
            public_reader._forbidden_field_paths(manifest)
        )
        if result["manifest_forbidden_field_count"] != 0:
            raise B55ExecutionError("fresh_public_reader", "forbidden manifest field")
        result["status"] = "reserved_source_context_transport_passed"
    except Exception as exc:
        if public_receipt is not None:
            (public_root / f"{public_receipt['artifact_id']}.json").unlink(missing_ok=True)
            (public_root / f"{public_receipt['artifact_id']}.wav").unlink(missing_ok=True)
        result["public_artifact_count"] = 0
        result["public_manifest_count"] = 0
        result["status"] = "reserved_source_context_transport_failed"
        result["failure_stage"] = exc.stage if isinstance(exc, B55ExecutionError) else "unexpected"
        result["failure_class"] = type(exc).__name__
    result["total_elapsed_seconds"] = round(perf_counter() - start_time, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B55ContractError("invalid B55 result: " + ";".join(validation["errors"]))
    _exclusive_json(state_root / contract["crash_safe_state"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B55 reserved-source context transport")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B55 only supports the frozen one-shot execution")
    result = execute_reserved_source_context_transport()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "reserved_source_context_transport_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
