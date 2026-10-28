"""One-shot B56 transport with private stderr-to-category projection."""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

import p3_b54_public_context_reader as public_reader
import p3_b54_unidirectional_context_extraction as b54
import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b56_allowlisted_diagnostic_transport_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b56_allowlisted_diagnostic_transport_implementation_freeze_2026-09-19.json"
)

CLASSIFIER_VERSION = "p3_b56_stderr_classifier_v1"
CLASSIFIER_RULES = (
    (
        "command_or_option",
        re.compile(
            r"(?:no such option|unrecognized (?:option|argument)|unknown option|invalid option|usage:)"
        ),
    ),
    (
        "provider_challenge_or_authentication",
        re.compile(
            r"(?:sign[ -]?in|log[ -]?in|cookies?|not a bot|captcha|authentication|age.restrict|members.only|account required)"
        ),
    ),
    (
        "source_unavailable_or_private",
        re.compile(
            r"(?:video unavailable|video is not available|source is not available|private video|has been removed|does not exist|this video is private|premieres in)"
        ),
    ),
    (
        "tls_or_network",
        re.compile(
            r"(?:ssl|tls|certificate|connection|network|timed? out|timeout|unable to download|http error|temporary failure|name or service not known|remote end closed)"
        ),
    ),
    (
        "ffmpeg_or_postprocessing",
        re.compile(r"(?:ffmpeg|ffprobe|post.?process|conversion failed|mux|demux)"),
    ),
    (
        "extractor_or_format",
        re.compile(
            r"(?:extractor|requested format|no video formats|format is not available|unsupported url|unable to extract|signature extraction|player response)"
        ),
    ),
)


class B56ContractError(ValueError):
    pass


class B56ExecutionError(RuntimeError):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage


def canonical_json(value: Any) -> str:
    return b55_v1.canonical_json(value)


def sha256_bytes(payload: bytes) -> str:
    return b55_v1.sha256_bytes(payload)


def sha256_file(path: str | Path) -> str:
    return b55_v1.sha256_file(path)


def load_json(path: str | Path) -> dict[str, Any]:
    return b55_v1.load_json(path)


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def classify_private_stderr(stderr_bytes: bytes) -> str:
    """Return one category while retaining no decoded source in the result."""

    if not isinstance(stderr_bytes, bytes):
        raise TypeError("stderr_bytes must be bytes")
    private_text = stderr_bytes.decode("utf-8", errors="replace").lower()
    for category, pattern in CLASSIFIER_RULES:
        if pattern.search(private_text):
            return category
    return "unknown"


def build_diagnostic_transport_command(private_root: Path) -> list[str]:
    """Reuse the frozen B55 V2 transport shape without widening capability."""

    return b55_v1.build_transport_command(private_root, b55_v2.load_contract())


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b56_allowlisted_diagnostic_transport_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_after_user_authorized_review_option_before_diagnostic_request":
        errors.append("status")
    authorization = contract.get("authorization") or {}
    if authorization.get("overrides_b55_next_execution_authorized_false") is not True:
        errors.append("review_override")
    if authorization.get("diagnostic_transport_request_count_max") != 1:
        errors.append("request_count")
    if authorization.get("additional_retry_or_correction_authorized") is not False:
        errors.append("additional_retry")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    review_binding = (contract.get("bindings") or {}).get("b55_review_required") or {}
    if review_binding:
        review = load_json(Path(root) / review_binding["path"])
        if review.get("status") != "review_required_after_two_evidence_bounded_batches":
            errors.append("review_status")
        if review.get("aggregate_counts", {}).get("network_attempt_count") != 1:
            errors.append("review_attempt_count")
        if review.get("aggregate_counts", {}).get("hidden_future_media_request_count") != 0:
            errors.append("review_future_count")
    unchanged = contract.get("unchanged_transport") or {}
    expected_transport = {
        "source_id": "youtube_4y5GiQpgJgo",
        "video_id": "4y5GiQpgJgo",
        "context_start_seconds": 3000.0,
        "context_end_seconds": 3180.0,
        "download_section": "*3000-3180",
        "yt_dlp_version": "2026.02.04",
        "ffmpeg_version_prefix": "ffmpeg version 8.0.1",
        "network_retry_count": 0,
        "fragment_retry_count": 0,
        "extractor_retry_count": 0,
        "cookies_or_browser_session_allowed": False,
        "source_replacement_allowed": False,
        "cutoff_change_allowed": False,
    }
    if unchanged != expected_transport:
        errors.append("transport_drift")
    classifier = contract.get("diagnostic_classifier") or {}
    expected_categories = {
        "command_or_option",
        "provider_challenge_or_authentication",
        "source_unavailable_or_private",
        "tls_or_network",
        "ffmpeg_or_postprocessing",
        "extractor_or_format",
        "timeout",
        "unknown",
        "not_applicable_success",
    }
    if set(classifier.get("allowlisted_categories") or []) != expected_categories:
        errors.append("classifier_categories")
    if classifier.get("priority") != [category for category, _ in CLASSIFIER_RULES] + ["unknown"]:
        errors.append("classifier_priority")
    for field in (
        "stderr_text_persistence_allowed",
        "stderr_hash_persistence_allowed",
        "stderr_token_or_excerpt_persistence_allowed",
        "stdout_text_persistence_allowed",
    ):
        if classifier.get(field) is not False:
            errors.append(f"classifier_denial:{field}")
    success = contract.get("success_gate") or {}
    if success.get("expected_private_duration_seconds") != 180.0:
        errors.append("success_duration")
    if success.get("duration_tolerance_seconds") != 0.05:
        errors.append("success_tolerance")
    if success.get("public_profile") != "reserved_source_context":
        errors.append("success_profile")
    if success.get("fresh_reader_count") != 1:
        errors.append("fresh_reader_count")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b56_diagnostic_request":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B56ContractError(";".join(errors))
    return {
        "valid": True,
        "b56_diagnostic_request_count_at_freeze": freeze.get(
            "b56_diagnostic_request_count_at_freeze"
        ),
        "hidden_future_media_request_count_at_freeze": freeze.get(
            "hidden_future_media_request_count_at_freeze"
        ),
    }


def _fresh_runtime_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    runtime = contract["runtime_state"]
    state_root = ROOT / runtime["state_root"]
    public_root = ROOT / runtime["public_root"]
    if state_root.exists():
        raise B56ExecutionError("preflight", "B56 invocation already consumed or started")
    if public_root.exists() and any(public_root.iterdir()):
        raise B56ExecutionError("preflight", "B56 public root already nonempty")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    material = {
        "schema": "uruha_p3_b56_diagnostic_transport_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "source_id": contract["unchanged_transport"]["source_id"],
        "download_section": contract["unchanged_transport"]["download_section"],
        "contract_sha256": sha256_file(CONFIG_PATH),
        "maximum_attempts": 1,
        "classifier_version": CLASSIFIER_VERSION,
        "stderr_persistence_allowed": False,
        "hidden_future_authorized": False,
        "prediction_authorized": False,
    }
    material["intent_hash"] = sha256_bytes(canonical_json(material).encode("utf-8"))
    return material


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b56_allowlisted_diagnostic_transport_result_v1",
        "version": "1.0.0",
        "source_id": contract["unchanged_transport"]["source_id"],
        "requested_context_seconds": [3000.0, 3180.0],
        "classifier_version": CLASSIFIER_VERSION,
        "network_attempt_count": 0,
        "transport_returncode": None,
        "transport_stdout_bytes_discarded": 0,
        "transport_stderr_bytes_discarded": 0,
        "stderr_text_persisted": False,
        "stderr_hash_persisted": False,
        "stderr_excerpt_or_token_persisted": False,
        "private_runtime_deleted_before_result": False,
        "public_artifact_count": 0,
        "public_manifest_count": 0,
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
    contract = load_contract()
    errors = []
    allowed_categories = set(contract["diagnostic_classifier"]["allowlisted_categories"])
    if result.get("schema") != "uruha_p3_b56_allowlisted_diagnostic_transport_result_v1":
        errors.append("schema")
    if result.get("status") not in {
        "diagnostic_transport_passed",
        "diagnostic_transport_failed",
    }:
        errors.append("status")
    if result.get("diagnostic_category") not in allowed_categories:
        errors.append("diagnostic_category")
    if result.get("requested_context_seconds") != [3000.0, 3180.0]:
        errors.append("context")
    if result.get("network_attempt_count") not in {0, 1}:
        errors.append("attempt_count")
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
    for field in (
        "stderr_text_persisted",
        "stderr_hash_persisted",
        "stderr_excerpt_or_token_persisted",
    ):
        if result.get(field) is not False:
            errors.append(field)
    forbidden_key_tokens = ("stderr_text", "stderr_hash", "stderr_excerpt", "stderr_token")
    allowed_denial_keys = {
        "stderr_text_persisted",
        "stderr_hash_persisted",
        "stderr_excerpt_or_token_persisted",
    }
    for key in result:
        if any(token in key.lower() for token in forbidden_key_tokens) and key not in allowed_denial_keys:
            errors.append(f"forbidden_result_key:{key}")
    if result.get("private_runtime_deleted_before_result") is not True:
        errors.append("private_runtime_delete")
    if result.get("status") == "diagnostic_transport_passed":
        if result.get("diagnostic_category") != "not_applicable_success":
            errors.append("success_category")
        if result.get("transport_returncode") != 0 or result.get("network_attempt_count") != 1:
            errors.append("success_transport")
        if result.get("public_artifact_count") != 1 or result.get("public_manifest_count") != 1:
            errors.append("success_public")
        if result.get("fresh_public_reader_count") != 1 or result.get("fresh_public_reader_exit_code") != 0:
            errors.append("success_reader")
        if abs(float(result.get("public_artifact_duration_seconds", 0)) - 180.0) > 0.05:
            errors.append("success_duration")
        if result.get("fresh_reader_artifact_sha256") != result.get("public_artifact_sha256"):
            errors.append("success_hash")
        if result.get("manifest_forbidden_field_count") != 0:
            errors.append("success_manifest")
    else:
        if result.get("diagnostic_category") == "not_applicable_success":
            errors.append("failure_category")
        if result.get("public_artifact_count") != 0 or result.get("public_manifest_count") != 0:
            errors.append("failure_public")
        if not result.get("failure_stage") or not result.get("failure_class"):
            errors.append("failure_classification")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_allowlisted_diagnostic_transport() -> dict[str, Any]:
    validate_implementation_freeze()
    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise B56ContractError("invalid B56 contract: " + ";".join(contract_report["errors"]))
    contract = load_contract()
    state_root, public_root = _fresh_runtime_roots(contract)
    b55_v1._exclusive_json(
        state_root / contract["runtime_state"]["intent_filename"], _intent(contract)
    )
    result = _base_result(contract)
    public_receipt = None
    private_root_path = None
    start_time = perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        ffmpeg = shutil.which("ffmpeg")
        if yt_dlp is None or ffmpeg is None:
            raise B56ExecutionError("tool_preflight", "required tool unavailable")
        b55_contract = b55_v2.load_contract()
        yt_dlp_version = b55_v2._tool_version(
            yt_dlp, b55_contract["transport"]["yt_dlp_version_command"]
        )
        ffmpeg_version = b55_v2._tool_version(
            ffmpeg, b55_contract["transport"]["ffmpeg_version_command"]
        )
        if yt_dlp_version != contract["unchanged_transport"]["yt_dlp_version"]:
            raise B56ExecutionError("tool_preflight", "yt-dlp version drift")
        if not ffmpeg_version.startswith(
            contract["unchanged_transport"]["ffmpeg_version_prefix"]
        ):
            raise B56ExecutionError("tool_preflight", "ffmpeg version drift")
        result["yt_dlp_version"] = yt_dlp_version
        result["ffmpeg_version"] = ffmpeg_version
        with TemporaryDirectory(prefix="uruha-p3-b56-private-") as temporary:
            private_root = Path(temporary)
            private_root_path = private_root
            os.chmod(private_root, 0o700)
            command = build_diagnostic_transport_command(private_root)
            result["network_attempt_count"] = 1
            network_start = perf_counter()
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    timeout=b55_contract["transport"]["timeout_seconds"],
                )
            except subprocess.TimeoutExpired as exc:
                result["network_elapsed_seconds"] = round(
                    perf_counter() - network_start, 6
                )
                result["transport_stdout_bytes_discarded"] = len(exc.stdout or b"")
                result["transport_stderr_bytes_discarded"] = len(exc.stderr or b"")
                result["diagnostic_category"] = "timeout"
                raise B56ExecutionError("network_transport", "transport timeout") from exc
            result["network_elapsed_seconds"] = round(perf_counter() - network_start, 6)
            result["transport_returncode"] = completed.returncode
            result["transport_stdout_bytes_discarded"] = len(completed.stdout or b"")
            result["transport_stderr_bytes_discarded"] = len(completed.stderr or b"")
            if completed.returncode != 0:
                result["diagnostic_category"] = classify_private_stderr(
                    completed.stderr or b""
                )
                raise B56ExecutionError("network_transport", "transport exit nonzero")
            result["diagnostic_category"] = "not_applicable_success"
            candidates = [path for path in private_root.iterdir() if path.is_file()]
            wav_candidates = [path for path in candidates if path.suffix.lower() == ".wav"]
            if len(candidates) != 1 or len(wav_candidates) != 1:
                raise B56ExecutionError("local_transport", "unexpected private outputs")
            raw_path = wav_candidates[0]
            os.chmod(raw_path, 0o600)
            raw_probe = public_reader._ffprobe_audio(raw_path)
            result["private_transport_bytes"] = raw_path.stat().st_size
            result["private_transport_duration_seconds"] = round(
                raw_probe["duration_seconds"], 6
            )
            expected = contract["success_gate"]["expected_private_duration_seconds"]
            tolerance = contract["success_gate"]["duration_tolerance_seconds"]
            if abs(raw_probe["duration_seconds"] - expected) > tolerance:
                raise B56ExecutionError(
                    "local_transport", "private duration outside frozen tolerance"
                )
            staged_path = private_root / "p3-b56-normalized-observable-context.wav"
            b54._run_ffmpeg_extract(raw_path, staged_path, 0.0, 180.0)
            profile = b54.load_contract()["profiles"]["reserved_source_context"]
            public_receipt = b54._publish_artifact(staged_path, public_root, profile)
            result["public_artifact_id"] = public_receipt["artifact_id"]
            result["public_artifact_sha256"] = public_receipt["artifact_sha256"]
            result["public_manifest_hash"] = public_receipt["manifest_hash"]
            result["public_artifact_duration_seconds"] = public_receipt[
                "observed_duration_seconds"
            ]
            result["public_artifact_count"] = 1
            result["public_manifest_count"] = 1
            raw_path.unlink()
            staged_path.unlink()
        result["private_runtime_deleted_before_result"] = not private_root_path.exists()
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
            raise B56ExecutionError("fresh_public_reader", "public reader rejected artifact")
        manifest = json.loads(child.stdout)["manifest"]
        result["fresh_reader_artifact_sha256"] = manifest["artifact_sha256"]
        result["manifest_forbidden_field_count"] = len(
            public_reader._forbidden_field_paths(manifest)
        )
        if result["manifest_forbidden_field_count"] != 0:
            raise B56ExecutionError("fresh_public_reader", "forbidden manifest field")
        result["status"] = "diagnostic_transport_passed"
    except Exception as exc:
        if private_root_path is not None:
            result["private_runtime_deleted_before_result"] = not private_root_path.exists()
        else:
            result["private_runtime_deleted_before_result"] = True
        if public_receipt is not None:
            (public_root / f"{public_receipt['artifact_id']}.json").unlink(missing_ok=True)
            (public_root / f"{public_receipt['artifact_id']}.wav").unlink(missing_ok=True)
        result["public_artifact_count"] = 0
        result["public_manifest_count"] = 0
        result["status"] = "diagnostic_transport_failed"
        result.setdefault("diagnostic_category", "unknown")
        result["failure_stage"] = (
            exc.stage if isinstance(exc, B56ExecutionError) else "unexpected"
        )
        result["failure_class"] = type(exc).__name__
    result["total_elapsed_seconds"] = round(perf_counter() - start_time, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B56ContractError("invalid B56 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(
        state_root / contract["runtime_state"]["result_filename"], result
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B56 allowlisted diagnostic transport")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B56 supports only the frozen one-shot diagnostic execution")
    result = execute_allowlisted_diagnostic_transport()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "diagnostic_transport_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
