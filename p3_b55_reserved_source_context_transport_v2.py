"""One-change B55 V2 runner after the V1 pre-network version-probe failure."""

from __future__ import annotations

from copy import deepcopy
import argparse
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
import p3_b55_reserved_source_context_transport as b55_v1


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b55_reserved_source_context_transport_v2.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b55_reserved_source_context_transport_v2_implementation_freeze_2026-09-18.json"
)


class B55V2ContractError(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    return b55_v1.load_json(path)


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def sha256_file(path: str | Path) -> str:
    return b55_v1.sha256_file(path)


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b55_reserved_source_context_transport_contract_v2":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_after_v1_zero-network-tool-probe-failure_before_v2_media_request":
        errors.append("status")
    for binding_name, binding in (contract.get("binding") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{binding_name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{binding_name}")
    failure_binding = (contract.get("binding") or {}).get("v1_failure") or {}
    if failure_binding:
        failure = load_json(Path(root) / failure_binding["path"])
        if failure.get("result_hash") != failure_binding.get("result_hash"):
            errors.append("v1_failure_result_hash")
        if failure.get("network_attempt_count") != 0 or failure_binding.get("network_attempt_count") != 0:
            errors.append("v1_network_attempt_count")
        if failure.get("status") != "reserved_source_context_transport_failed":
            errors.append("v1_failure_status")
    source = contract.get("source") or {}
    if (
        source.get("source_id") != "youtube_4y5GiQpgJgo"
        or source.get("context_start_seconds") != 3000.0
        or source.get("context_end_seconds") != 3180.0
        or source.get("hidden_future_start_seconds") != 3181.0
        or source.get("hidden_future_end_seconds") != 3241.0
    ):
        errors.append("source_boundary")
    transport = contract.get("transport") or {}
    if transport.get("yt_dlp_version_command") != ["--version"]:
        errors.append("yt_dlp_version_command")
    if transport.get("ffmpeg_version_command") != ["-version"]:
        errors.append("ffmpeg_version_command")
    if transport.get("download_section") != "*3000-3180" or transport.get("maximum_attempts") != 1:
        errors.append("transport_scope")
    if any(transport.get(field) != 0 for field in (
        "network_retry_count", "fragment_retry_count", "extractor_retry_count"
    )):
        errors.append("transport_retries")
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
    authorization = contract.get("execution_authorization") or {}
    if authorization.get("v1_confirmed_network_attempt_count") != 0:
        errors.append("v1_authorization_basis")
    if authorization.get("v2_reserved_source_media_request_count_max") != 1:
        errors.append("v2_media_authorization")
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
    if failure.get("v2_retry_count") != 0 or failure.get("fallback_count") != 0:
        errors.append("failure_retry")
    if failure.get("additional_correction_after_v2_failure_allowed") is not False:
        errors.append("additional_correction")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_after_v1_zero-network-failure_before_v2_media_request":
        errors.append("freeze_status")
    for artifact_id, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{artifact_id}")
        elif sha256_file(path) != (artifact or {}).get("sha256"):
            errors.append(f"hash:{artifact_id}")
    if errors:
        raise B55V2ContractError(";".join(errors))
    return {
        "valid": True,
        "v1_network_attempt_count_at_freeze": freeze.get("v1_network_attempt_count_at_freeze"),
        "v2_network_attempt_count_at_freeze": freeze.get("v2_network_attempt_count_at_freeze"),
        "hidden_future_media_request_count_at_freeze": freeze.get(
            "hidden_future_media_request_count_at_freeze"
        ),
    }


def _tool_version(executable: str, arguments: list[str]) -> str:
    completed = subprocess.run(
        [executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise b55_v1.B55ExecutionError("tool_preflight", "tool version probe failed")
    output = completed.stdout or completed.stderr
    return output.splitlines()[0].strip()


def _fresh_runtime_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    state_root = ROOT / contract["crash_safe_state"]["root"]
    public_root = ROOT / contract["public_output"]["root"]
    if state_root.exists():
        raise b55_v1.B55ExecutionError("preflight", "B55 V2 invocation already consumed or started")
    if public_root.exists() and any(public_root.iterdir()):
        raise b55_v1.B55ExecutionError("preflight", "B55 public root is already nonempty")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    material = {
        "schema": "uruha_p3_b55_v2_transport_invocation_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "source_id": contract["source"]["source_id"],
        "download_section": contract["transport"]["download_section"],
        "contract_sha256": sha256_file(CONFIG_PATH),
        "maximum_v2_attempts": 1,
        "v1_network_attempt_count": 0,
        "hidden_future_authorized": False,
        "prediction_authorized": False,
    }
    material["intent_hash"] = b55_v1.sha256_bytes(
        b55_v1.canonical_json(material).encode("utf-8")
    )
    return material


def execute_reserved_source_context_transport_v2() -> dict[str, Any]:
    validate_implementation_freeze()
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise B55V2ContractError("invalid B55 V2 contract: " + ";".join(contract_report["errors"]))
    contract = load_contract()
    state_root, public_root = _fresh_runtime_roots(contract)
    b55_v1._exclusive_json(
        state_root / contract["crash_safe_state"]["intent_filename"], _intent(contract)
    )
    result = b55_v1._base_result(contract)
    result["version"] = "2.0.0"
    result["v1_network_attempt_count"] = 0
    public_receipt = None
    start_time = perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        ffmpeg = shutil.which("ffmpeg")
        if yt_dlp is None or ffmpeg is None:
            raise b55_v1.B55ExecutionError("tool_preflight", "required transport tool unavailable")
        yt_dlp_version = _tool_version(yt_dlp, contract["transport"]["yt_dlp_version_command"])
        ffmpeg_version = _tool_version(ffmpeg, contract["transport"]["ffmpeg_version_command"])
        if yt_dlp_version != contract["transport"]["required_version"]:
            raise b55_v1.B55ExecutionError("tool_preflight", "yt-dlp version drift")
        if not ffmpeg_version.startswith(contract["transport"]["ffmpeg_required_version_prefix"]):
            raise b55_v1.B55ExecutionError("tool_preflight", "ffmpeg version drift")
        result["yt_dlp_version"] = yt_dlp_version
        result["ffmpeg_version"] = ffmpeg_version
        with TemporaryDirectory(prefix="uruha-p3-b55-v2-private-") as temporary:
            private_root = Path(temporary)
            os.chmod(private_root, 0o700)
            command = b55_v1.build_transport_command(private_root, contract)
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
                raise b55_v1.B55ExecutionError("network_transport", "transport timeout") from exc
            result["network_elapsed_seconds"] = round(perf_counter() - network_start, 6)
            result["transport_returncode"] = completed.returncode
            result["transport_stdout_bytes_discarded"] = len(completed.stdout or b"")
            result["transport_stderr_bytes_discarded"] = len(completed.stderr or b"")
            if completed.returncode != 0:
                raise b55_v1.B55ExecutionError("network_transport", "transport exit nonzero")
            candidates = [path for path in private_root.iterdir() if path.is_file()]
            wav_candidates = [path for path in candidates if path.suffix.lower() == ".wav"]
            if len(wav_candidates) != 1 or len(candidates) != 1:
                raise b55_v1.B55ExecutionError("local_transport", "unexpected private transport outputs")
            raw_path = wav_candidates[0]
            os.chmod(raw_path, 0o600)
            raw_probe = public_reader._ffprobe_audio(raw_path)
            result["private_transport_bytes"] = raw_path.stat().st_size
            result["private_transport_duration_seconds"] = round(raw_probe["duration_seconds"], 6)
            expected = contract["local_private_gate"]["expected_local_duration_seconds"]
            tolerance = contract["local_private_gate"]["duration_tolerance_seconds"]
            if abs(raw_probe["duration_seconds"] - expected) > tolerance:
                raise b55_v1.B55ExecutionError(
                    "local_transport", "private transport duration outside frozen tolerance"
                )
            staged_path = private_root / "p3-b55-v2-normalized-observable-context.wav"
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
            raise b55_v1.B55ExecutionError("fresh_public_reader", "public reader rejected artifact")
        manifest = json.loads(child.stdout)["manifest"]
        result["fresh_reader_artifact_sha256"] = manifest["artifact_sha256"]
        result["manifest_forbidden_field_count"] = len(
            public_reader._forbidden_field_paths(manifest)
        )
        if result["manifest_forbidden_field_count"] != 0:
            raise b55_v1.B55ExecutionError("fresh_public_reader", "forbidden manifest field")
        result["status"] = "reserved_source_context_transport_passed"
    except Exception as exc:
        if public_receipt is not None:
            (public_root / f"{public_receipt['artifact_id']}.json").unlink(missing_ok=True)
            (public_root / f"{public_receipt['artifact_id']}.wav").unlink(missing_ok=True)
        result["public_artifact_count"] = 0
        result["public_manifest_count"] = 0
        result["status"] = "reserved_source_context_transport_failed"
        result["failure_stage"] = (
            exc.stage if isinstance(exc, b55_v1.B55ExecutionError) else "unexpected"
        )
        result["failure_class"] = type(exc).__name__
    result["total_elapsed_seconds"] = round(perf_counter() - start_time, 6)
    b55_v1._finalize_result(result)
    validation = b55_v1.validate_result(result)
    if not validation["valid"]:
        raise B55V2ContractError("invalid B55 V2 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(
        state_root / contract["crash_safe_state"]["result_filename"], result
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B55 V2 reserved-source context transport")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B55 V2 only supports the frozen one-shot execution")
    result = execute_reserved_source_context_transport_v2()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "reserved_source_context_transport_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
