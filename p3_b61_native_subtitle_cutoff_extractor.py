"""B61 final native-subtitle transport correction with B60 cutoff projection."""

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

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56
import p3_b60_private_caption_cutoff_extractor as b60


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b61_native_subtitle_cutoff_extractor_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b61_native_subtitle_cutoff_extractor_implementation_freeze_2026-09-20.json"


class B61ContractError(ValueError):
    pass


class B61ExecutionError(RuntimeError):
    def __init__(self, stage: str, category: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.category = category


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


def _source_locator(contract: dict[str, Any]) -> str:
    source = contract["source"]
    return source["locator_template"].replace("<video_id>", source["video_id"])


def build_native_downloader_command(
    private_root: Path, contract: dict[str, Any] | None = None
) -> list[str]:
    contract = contract or load_contract()
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise B61ContractError("yt-dlp unavailable")
    native = contract["native_downloader"]
    return [
        executable,
        "--ignore-config",
        "--quiet",
        "--no-warnings",
        "--no-playlist",
        "--skip-download",
        "--write-auto-subs",
        "--sub-langs",
        ",".join(native["subtitle_languages"]),
        "--sub-format",
        native["subtitle_format"],
        "--no-write-info-json",
        "--no-write-thumbnail",
        "--no-write-comments",
        "--no-cache-dir",
        "--retries",
        "0",
        "--fragment-retries",
        "0",
        "--extractor-retries",
        "0",
        "--socket-timeout",
        "30",
        "-o",
        str(private_root / "caption.%(ext)s"),
        _source_locator(contract),
    ]


def read_single_private_caption(
    private_root: Path, contract: dict[str, Any] | None = None
) -> tuple[Path, bytes]:
    contract = contract or load_contract()
    candidates = [
        path
        for path in private_root.iterdir()
        if path.is_file() and not path.is_symlink() and path.suffix == ".json3"
    ]
    if len(candidates) != contract["native_downloader"]["required_private_caption_file_count"]:
        raise B61ExecutionError("private_caption", "caption_file_contract", "caption file count")
    path = candidates[0]
    if path.stat().st_nlink != 1:
        raise B61ExecutionError("private_caption", "caption_file_contract", "caption hardlink")
    limit = contract["native_downloader"]["maximum_private_caption_bytes"]
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    if not payload:
        raise B61ExecutionError("private_caption", "empty_response", "caption file empty")
    if len(payload) > limit:
        raise B61ExecutionError("private_caption", "response_too_large", "caption file too large")
    return path, payload


def validate_contract(
    contract: dict[str, Any] | None = None, *, root: Path = ROOT
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b61_native_subtitle_cutoff_extractor_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_frozen_final_caption_path_correction_before_native_download":
        errors.append("status")
    authorization = contract.get("authorization") or {}
    if authorization.get("native_downloader_process_invocation_count_max") != 1:
        errors.append("process_count")
    if authorization.get("retry_or_fallback_authorized") is not False:
        errors.append("retry_authorization")
    if authorization.get("paid_api_login_cookie_or_account_access_authorized") is not False:
        errors.append("account_authorization")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str((binding or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    review_binding = (contract.get("bindings") or {}).get("b60_review_required") or {}
    if review_binding:
        review = load_json(Path(root) / review_binding["path"])
        if review.get("status") != "caption_get_failed_before_private_raw_access":
            errors.append("review_status")
        next_stage = review.get("next_stage") or {}
        if next_stage.get("id") != "P3-B61" or next_stage.get("final_caption_path_correction") is not True:
            errors.append("review_next")
    source = contract.get("source") or {}
    if (
        source.get("source_id") != "youtube_4y5GiQpgJgo"
        or source.get("context_start_seconds") != 3000.0
        or source.get("context_end_seconds") != 3180.0
        or source.get("hidden_future_start_seconds") != 3181.0
        or source.get("hidden_future_end_seconds") != 3241.0
        or [source.get("selected_track_type"), source.get("selected_language_code"), source.get("selected_format")] != ["automatic", "ja", "json3"]
    ):
        errors.append("source_boundary")
    native = contract.get("native_downloader") or {}
    if native.get("required_version") != "2026.02.04":
        errors.append("tool_version")
    if native.get("skip_media_download") is not True or native.get("write_automatic_subtitles") is not True:
        errors.append("download_mode")
    if native.get("subtitle_languages") != ["ja"] or native.get("subtitle_format") != "json3":
        errors.append("track")
    if any(native.get(field) != 0 for field in ("network_retry_count", "fragment_retry_count", "extractor_retry_count")):
        errors.append("retries")
    for field in (
        "cookies_or_browser_session_allowed",
        "playlist_allowed",
        "media_file_download_allowed",
        "metadata_sidecar_allowed",
        "cache_allowed",
        "provider_http_request_count_observable",
    ):
        if native.get(field) is not False:
            errors.append(f"native_denial:{field}")
    if native.get("maximum_private_caption_bytes") != 10485760 or native.get("required_private_caption_file_count") != 1:
        errors.append("private_file")
    cutoff = contract.get("cutoff_and_publication") or {}
    if cutoff.get("reuse_b60_frozen_extraction_and_publication") is not True:
        errors.append("cutoff_reuse")
    if cutoff.get("context_start_milliseconds") != 3000000 or cutoff.get("context_end_milliseconds") != 3180000:
        errors.append("cutoff")
    if cutoff.get("fresh_reader") != "p3_b60_caption_context_reader.py" or cutoff.get("fresh_reader_count") != 1 or cutoff.get("fresh_reader_returns_caption_text") is not False:
        errors.append("reader")
    separation = contract.get("capability_separation") or {}
    if separation.get("private_acquisition_may_temporarily_observe_full_caption") is not True or separation.get("private_caption_file_deleted_before_fresh_reader") is not True:
        errors.append("private_scope")
    for field in (
        "private_caption_filename_or_hash_persistence_allowed",
        "raw_stdout_or_stderr_persistence_allowed",
        "post_cutoff_caption_persistence_allowed",
    ):
        if separation.get(field) is not False:
            errors.append(f"separation:{field}")
    if separation.get("prediction_side_future_access_required") != 0:
        errors.append("prediction_future")
    policy = contract.get("failure_policy") or {}
    if policy.get("caption_path_correction_batch_ordinal") != 2 or policy.get("final_caption_path_correction") is not True or policy.get("same_path_retry_after_failure_allowed") is not False:
        errors.append("failure_policy")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze = load_json(Path(root) / FREEZE_PATH.relative_to(ROOT))
    errors = []
    if freeze.get("status") != "frozen_before_b61_native_caption_download":
        errors.append("freeze_status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"missing:{name}")
        elif sha256_file(path) != artifact.get("sha256"):
            errors.append(f"hash:{name}")
    if errors:
        raise B61ContractError(";".join(errors))
    return {
        "valid": True,
        "native_downloader_process_invocation_count_at_freeze": freeze.get("native_downloader_process_invocation_count_at_freeze"),
        "prediction_side_future_access_count_at_freeze": freeze.get("prediction_side_future_access_count_at_freeze"),
    }


def _fresh_roots(contract: dict[str, Any]) -> tuple[Path, Path]:
    state_root = ROOT / contract["runtime_state"]["state_root"]
    public_root = ROOT / contract["cutoff_and_publication"]["public_root"]
    if state_root.exists():
        raise B61ExecutionError("preflight", "preflight", "B61 already consumed")
    if public_root.exists() and any(public_root.iterdir()):
        raise B61ExecutionError("preflight", "preflight", "B61 public root nonempty")
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    return state_root, public_root


def _intent(contract: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_p3_b61_native_caption_intent_v1",
        "version": "1.0.0",
        "status": "terminal_once_written_even_without_result",
        "source_id": contract["source"]["source_id"],
        "context_seconds": [3000.0, 3180.0],
        "contract_sha256": sha256_file(CONFIG_PATH),
        "native_downloader_process_max": 1,
        "prediction_side_future_access_authorized": False,
        "prediction_authorized": False,
    }
    value["intent_hash"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    return value


def _base_result(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_p3_b61_native_subtitle_cutoff_extractor_result_v1",
        "version": "1.0.0",
        "source_id": contract["source"]["source_id"],
        "context_seconds": [3000.0, 3180.0],
        "native_downloader_process_invocation_count": 0,
        "provider_http_request_count": "unavailable",
        "downloader_stdout_bytes_discarded": 0,
        "downloader_stderr_bytes_discarded": 0,
        "private_acquisition_full_caption_access_count": 0,
        "private_acquisition_may_include_post_cutoff_content": False,
        "prediction_side_future_access_count": 0,
        "private_caption_filename_persisted": False,
        "private_caption_hash_persisted": False,
        "raw_caption_persisted": False,
        "post_cutoff_caption_persisted": False,
        "private_caption_deleted_before_fresh_reader": False,
        "private_runtime_deleted_before_fresh_reader": False,
        "public_artifact_count": 0,
        "public_manifest_count": 0,
        "human_caption_display_count": 0,
        "semantic_inspection_count": 0,
        "prediction_execution_count": 0,
        "model_call_count": 0,
        "training_write_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
        "paid_api_or_account_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("schema") != "uruha_p3_b61_native_subtitle_cutoff_extractor_result_v1":
        errors.append("schema")
    if result.get("status") not in {"caption_context_published", "caption_context_failed"}:
        errors.append("status")
    if result.get("context_seconds") != [3000.0, 3180.0]:
        errors.append("context")
    if result.get("native_downloader_process_invocation_count") not in {0, 1}:
        errors.append("process_count")
    if result.get("provider_http_request_count") != "unavailable":
        errors.append("provider_http_claim")
    for field in (
        "private_caption_filename_persisted",
        "private_caption_hash_persisted",
        "raw_caption_persisted",
        "post_cutoff_caption_persisted",
    ):
        if result.get(field) is not False:
            errors.append(field)
    for field in (
        "prediction_side_future_access_count",
        "human_caption_display_count",
        "semantic_inspection_count",
        "prediction_execution_count",
        "model_call_count",
        "training_write_count",
        "formal_m56_write_count",
        "production_memory_write_count",
        "paid_api_or_account_access_count",
        "retry_count",
        "fallback_count",
    ):
        if result.get(field) != 0:
            errors.append(field)
    forbidden = {"private_caption_filename", "private_caption_hash", "raw_caption", "caption_text", "cues", "future", "outcome"}
    errors.extend(f"forbidden_key:{key}" for key in result if key in forbidden)
    if result.get("status") == "caption_context_published":
        if result.get("native_downloader_process_invocation_count") != 1 or result.get("downloader_returncode") != 0:
            errors.append("success_downloader")
        if result.get("private_acquisition_full_caption_access_count") != 1 or result.get("private_acquisition_may_include_post_cutoff_content") is not True:
            errors.append("success_private_scope")
        if result.get("private_caption_deleted_before_fresh_reader") is not True or result.get("private_runtime_deleted_before_fresh_reader") is not True:
            errors.append("success_private_delete")
        if result.get("public_artifact_count") != 1 or result.get("public_manifest_count") != 1:
            errors.append("success_public")
        if int(result.get("public_cue_count", 0)) < 1:
            errors.append("success_cues")
        if float(result.get("public_first_cue_start_seconds", 0)) < 3000.0 or float(result.get("public_last_cue_end_seconds", 999999)) > 3180.0:
            errors.append("success_cutoff")
        if result.get("fresh_public_reader_count") != 1 or result.get("fresh_public_reader_exit_code") != 0:
            errors.append("success_reader")
        if result.get("fresh_reader_caption_text_returned") is not False:
            errors.append("success_text_return")
        if result.get("fresh_reader_artifact_sha256") != result.get("public_artifact_sha256"):
            errors.append("success_hash")
    else:
        if not result.get("failure_stage") or not result.get("failure_category"):
            errors.append("failure_classification")
        if result.get("public_artifact_count") != 0 or result.get("public_manifest_count") != 0:
            errors.append("failure_public")
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def execute_native_caption_cutoff() -> dict[str, Any]:
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise B61ContractError("invalid B61 contract: " + ";".join(report["errors"]))
    contract = load_contract()
    state_root, public_root = _fresh_roots(contract)
    b55_v1._exclusive_json(state_root / contract["runtime_state"]["intent_filename"], _intent(contract))
    result = _base_result(contract)
    manifest = None
    private_runtime_path = None
    raw_caption = None
    artifact = None
    start_time = perf_counter()
    try:
        yt_dlp = shutil.which("yt-dlp")
        if yt_dlp is None:
            raise B61ExecutionError("tool_preflight", "tool_preflight", "yt-dlp unavailable")
        b55_contract = b55_v2.load_contract()
        version = b55_v2._tool_version(yt_dlp, b55_contract["transport"]["yt_dlp_version_command"])
        if version != contract["native_downloader"]["required_version"]:
            raise B61ExecutionError("tool_preflight", "tool_preflight", "yt-dlp version drift")
        result["yt_dlp_version"] = version
        with TemporaryDirectory(prefix="uruha-p3-b61-private-") as temporary:
            private_root = Path(temporary)
            private_runtime_path = private_root
            os.chmod(private_root, 0o700)
            result["native_downloader_process_invocation_count"] = 1
            downloader_start = perf_counter()
            try:
                completed = subprocess.run(
                    build_native_downloader_command(private_root, contract),
                    check=False,
                    capture_output=True,
                    timeout=contract["native_downloader"]["timeout_seconds"],
                )
            except subprocess.TimeoutExpired as exc:
                result["downloader_elapsed_seconds"] = round(perf_counter() - downloader_start, 6)
                result["downloader_stdout_bytes_discarded"] = len(exc.stdout or b"")
                result["downloader_stderr_bytes_discarded"] = len(exc.stderr or b"")
                raise B61ExecutionError("native_downloader", "timeout", "downloader timeout") from None
            result["downloader_elapsed_seconds"] = round(perf_counter() - downloader_start, 6)
            result["downloader_returncode"] = completed.returncode
            stdout = completed.stdout or b""
            stderr = completed.stderr or b""
            result["downloader_stdout_bytes_discarded"] = len(stdout)
            result["downloader_stderr_bytes_discarded"] = len(stderr)
            if completed.returncode != 0:
                category = b56.classify_private_stderr(stderr)
                stdout = stderr = b""
                completed = None
                raise B61ExecutionError("native_downloader", category, "downloader exit nonzero")
            stdout = stderr = b""
            completed = None
            caption_path, raw_caption = read_single_private_caption(private_root, contract)
            result["private_caption_bytes_discarded_after_projection"] = len(raw_caption)
            result["private_acquisition_full_caption_access_count"] = 1
            result["private_acquisition_may_include_post_cutoff_content"] = True
            artifact = b60.extract_context_artifact(raw_caption, b60.load_contract())
            manifest = b60.publish_context_artifact(artifact, public_root, b60.load_contract())
            result["public_artifact_count"] = 1
            result["public_manifest_count"] = 1
            result["public_artifact_id"] = manifest["artifact_id"]
            result["public_artifact_sha256"] = manifest["artifact_sha256"]
            result["public_manifest_hash"] = manifest["manifest_hash"]
            result["public_cue_count"] = manifest["cue_count"]
            result["public_first_cue_start_seconds"] = manifest["first_cue_start_seconds"]
            result["public_last_cue_end_seconds"] = manifest["last_cue_end_seconds"]
            caption_path.unlink()
            result["private_caption_deleted_before_fresh_reader"] = True
            raw_caption = None
            artifact = None
        result["private_runtime_deleted_before_fresh_reader"] = not private_runtime_path.exists()
        environment = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", b60.PUBLIC_ROOT_ENV: str(public_root)}
        child = subprocess.run(
            [sys.executable, str(ROOT / "p3_b60_caption_context_reader.py"), "--inspect", manifest["artifact_id"]],
            cwd=str(ROOT), env=environment, check=False, capture_output=True, text=True, timeout=60
        )
        result["fresh_public_reader_count"] = 1
        result["fresh_public_reader_exit_code"] = child.returncode
        if child.returncode != 0:
            raise B61ExecutionError("fresh_public_reader", "public_reader", "reader rejected artifact")
        summary = json.loads(child.stdout)["artifact_summary"]
        result["fresh_reader_artifact_sha256"] = summary["artifact_sha256"]
        result["fresh_reader_caption_text_returned"] = summary["caption_text_returned"]
        if summary["cue_count"] != manifest["cue_count"]:
            raise B61ExecutionError("fresh_public_reader", "public_reader", "cue count mismatch")
        result["status"] = "caption_context_published"
    except Exception as exc:
        raw_caption = None
        artifact = None
        if private_runtime_path is not None:
            result["private_runtime_deleted_before_fresh_reader"] = not private_runtime_path.exists()
        else:
            result["private_runtime_deleted_before_fresh_reader"] = True
        if public_root.exists():
            os.chmod(public_root, 0o700)
            for path in public_root.iterdir():
                os.chmod(path, 0o600)
                path.unlink(missing_ok=True)
        result["public_artifact_count"] = 0
        result["public_manifest_count"] = 0
        result["status"] = "caption_context_failed"
        if isinstance(exc, B61ExecutionError):
            result["failure_stage"] = exc.stage
            result["failure_category"] = exc.category
        else:
            result["failure_stage"] = "unexpected"
            result["failure_category"] = "unknown"
        result["failure_class"] = type(exc).__name__
    result["total_elapsed_seconds"] = round(perf_counter() - start_time, 6)
    _finalize_result(result)
    validation = validate_result(result)
    if not validation["valid"]:
        raise B61ContractError("invalid B61 result: " + ";".join(validation["errors"]))
    b55_v1._exclusive_json(state_root / contract["runtime_state"]["result_filename"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B61 native subtitle cutoff extractor")
    parser.add_argument("--execute-once", action="store_true")
    arguments = parser.parse_args()
    if not arguments.execute_once:
        parser.error("B61 supports only the frozen final one-shot caption correction")
    result = execute_native_caption_cutoff()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] != "caption_context_published":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
