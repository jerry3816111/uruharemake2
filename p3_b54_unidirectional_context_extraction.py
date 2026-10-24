"""B54 private worker for one-way observable-context audio extraction."""

from __future__ import annotations

from array import array
from copy import deepcopy
import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any
import wave

import p3_b54_public_context_reader as public_reader


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b54_unidirectional_context_extraction_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b54_unidirectional_context_extraction_implementation_freeze_2026-09-18.json"
)
PUBLIC_ROOT_ENV = public_reader.PUBLIC_ROOT_ENV


class B54ContractError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    with Path(path).open("rb") as handle:
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B54ContractError(f"expected JSON object: {path}")
    return value


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def _profile_tuple(profile: dict[str, Any]) -> tuple[str, str, float, float]:
    return (
        str(profile.get("source_id") or ""),
        str(profile.get("boundary_receipt_hash") or ""),
        float(profile.get("context_start_seconds")),
        float(profile.get("context_end_seconds")),
    )


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b54_unidirectional_context_extraction_contract_v1":
        errors.append("schema_mismatch")
    if contract.get("status") != "prospective_frozen_before_synthetic_rehearsal_or_reserved_source_media_access":
        errors.append("status_mismatch")
    binding = (contract.get("binding") or {}).get("boundary_release") or {}
    release_path = Path(root) / str(binding.get("path") or "")
    if not release_path.is_file():
        errors.append("boundary_release_missing")
        release = {}
    else:
        if sha256_file(release_path) != binding.get("sha256"):
            errors.append("boundary_release_hash_mismatch")
        release = load_json(release_path)
    if release and release.get("receipt_hash") != binding.get("receipt_hash"):
        errors.append("boundary_receipt_hash_mismatch")
    profiles = contract.get("profiles") or {}
    if set(profiles) != {"synthetic_boundary_rehearsal", "reserved_source_context"}:
        errors.append("profile_names")
    else:
        reserved = profiles["reserved_source_context"]
        boundary = release.get("boundary") or {}
        if reserved.get("source_id") != release.get("source_id"):
            errors.append("reserved_source_id_binding")
        if reserved.get("boundary_receipt_hash") != release.get("receipt_hash"):
            errors.append("reserved_receipt_binding")
        if reserved.get("context_start_seconds") != float(boundary.get("observable_input_start_seconds", -1)):
            errors.append("reserved_start_binding")
        if reserved.get("context_end_seconds") != float(boundary.get("prediction_cutoff_seconds", -1)):
            errors.append("reserved_end_binding")
        if {_profile_tuple(profile) for profile in profiles.values()} != public_reader.ALLOWED_PROFILES:
            errors.append("public_reader_profile_drift")
    worker = contract.get("private_worker_api") or {}
    if worker.get("function") != "export_observable_context":
        errors.append("worker_function")
    if worker.get("parameters") != list(inspect.signature(export_observable_context).parameters):
        errors.append("worker_signature")
    if worker.get("raw_transport_must_be_deleted_before_generation_reader") is not True:
        errors.append("raw_delete_policy")
    if worker.get("network_fetch_inside_extractor") is not False:
        errors.append("network_fetch_policy")
    if worker.get("retry_count") != 0 or worker.get("fallback_count") != 0:
        errors.append("retry_or_fallback")
    output = contract.get("output_audio") or {}
    if output.get("container") != "wav" or output.get("codec") != "pcm_s16le":
        errors.append("output_format")
    if output.get("sample_rate_hz") != 16000 or output.get("channels") != 1:
        errors.append("output_shape")
    if output.get("duration_tolerance_seconds") != 0.05:
        errors.append("duration_tolerance")
    public = contract.get("public_surface") or {}
    if public.get("root_environment_variable") != public_reader.PUBLIC_ROOT_ENV:
        errors.append("public_root_environment")
    if set(public.get("allowed_manifest_fields") or []) != public_reader.ALLOWED_MANIFEST_FIELDS:
        errors.append("manifest_field_drift")
    if set(public.get("forbidden_field_tokens") or []) != public_reader.FORBIDDEN_FIELD_TOKENS:
        errors.append("forbidden_field_drift")
    authorization = contract.get("execution_authorization") or {}
    expected_authorization = {
        "synthetic_boundary_rehearsal_authorized": True,
        "reserved_source_media_access_authorized": False,
        "hidden_future_access_authorized": False,
        "prediction_execution_authorized": False,
        "model_calls_authorized": False,
        "production_memory_write_authorized": False,
    }
    if authorization != expected_authorization:
        errors.append("authorization")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze_path = Path(root) / FREEZE_PATH.relative_to(ROOT)
    freeze = load_json(freeze_path)
    errors = []
    if freeze.get("status") != "frozen_before_synthetic_rehearsal_and_any_reserved_source_media_access":
        errors.append("freeze_status")
    for artifact_id, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"frozen_artifact_missing:{artifact_id}")
        elif sha256_file(path) != (artifact or {}).get("sha256"):
            errors.append(f"frozen_artifact_hash_mismatch:{artifact_id}")
    if errors:
        raise B54ContractError(";".join(errors))
    return {
        "valid": True,
        "synthetic_rehearsal_count_at_freeze": freeze.get("synthetic_rehearsal_count_at_freeze"),
        "reserved_source_media_access_count_at_freeze": freeze.get("reserved_source_media_access_count_at_freeze"),
        "hidden_future_access_count_at_freeze": freeze.get("hidden_future_access_count_at_freeze"),
    }


def _validate_disposable_private_input(path: Path) -> None:
    if not path.name.startswith("p3-b54-private-transport-"):
        raise B54ContractError("raw media must be a disposable B54 private transport file")
    if path.is_symlink():
        raise B54ContractError("raw media symlink rejected")
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_nlink != 1:
        raise B54ContractError("raw media must be an owner-only regular single-link file")
    if metadata.st_mode & 0o077:
        raise B54ContractError("raw media group/world permissions rejected")


def _prepare_public_root(public_root: Path, private_root: Path) -> Path:
    unresolved = Path(public_root)
    if unresolved.exists() and unresolved.is_symlink():
        raise B54ContractError("public root symlink rejected")
    resolved = unresolved.resolve()
    private_resolved = private_root.resolve()
    if resolved == private_resolved or private_resolved in resolved.parents:
        raise B54ContractError("public root inside private root rejected")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(resolved, 0o700)
    metadata = resolved.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise B54ContractError("public root permissions invalid")
    return resolved


def _run_ffmpeg_extract(raw_path: Path, output_path: Path, start: float, end: float) -> None:
    executable = shutil.which("ffmpeg")
    if executable is None:
        raise B54ContractError("ffmpeg unavailable")
    filter_value = f"atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS"
    completed = subprocess.run(
        [
            executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            str(raw_path),
            "-map",
            "0:a:0",
            "-af",
            filter_value,
            "-map_metadata",
            "-1",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise B54ContractError("ffmpeg extraction failed")


def _exclusive_write(path: Path, payload: bytes) -> None:
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


def _publish_artifact(staged_path: Path, public_root: Path, profile: dict[str, Any]) -> dict[str, Any]:
    artifact_id = secrets.token_hex(16)
    artifact_name = f"{artifact_id}.wav"
    artifact_path = public_root / artifact_name
    manifest_path = public_root / f"{artifact_id}.json"
    audio_bytes = staged_path.read_bytes()
    staged_probe = public_reader._ffprobe_audio(staged_path)
    start = float(profile["context_start_seconds"])
    end = float(profile["context_end_seconds"])
    requested = end - start
    tolerance = 0.05
    if (
        staged_probe["duration_seconds"] > requested + tolerance
        or staged_probe["duration_seconds"] < requested - tolerance
    ):
        raise B54ContractError("staged artifact duration outside frozen tolerance")
    if (
        staged_probe["sample_rate_hz"] != 16000
        or staged_probe["channels"] != 1
        or staged_probe["codec"] != "pcm_s16le"
    ):
        raise B54ContractError("staged artifact audio profile mismatch")
    manifest = {
        "schema": public_reader.MANIFEST_SCHEMA,
        "version": "1.0.0",
        "status": "immutable_bounded_observable_context",
        "artifact_id": artifact_id,
        "source_id": profile["source_id"],
        "boundary_receipt_hash": profile["boundary_receipt_hash"],
        "context_start_seconds": start,
        "context_end_seconds": end,
        "requested_duration_seconds": requested,
        "observed_duration_seconds": round(staged_probe["duration_seconds"], 6),
        "duration_tolerance_seconds": tolerance,
        "sample_rate_hz": 16000,
        "channels": 1,
        "codec": "pcm_s16le",
        "container": "wav",
        "artifact_name": artifact_name,
        "artifact_bytes": len(audio_bytes),
        "artifact_sha256": sha256_bytes(audio_bytes),
        "exposure_policy": deepcopy(public_reader.EXPECTED_EXPOSURE_POLICY),
    }
    manifest["manifest_hash"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    try:
        _exclusive_write(artifact_path, audio_bytes)
        _exclusive_write(manifest_path, canonical_json(manifest).encode("utf-8"))
        directory_descriptor = os.open(public_root, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        old_root = os.environ.get(PUBLIC_ROOT_ENV)
        os.environ[PUBLIC_ROOT_ENV] = str(public_root)
        try:
            loaded = public_reader.load_public_context(artifact_id)
        finally:
            if old_root is None:
                os.environ.pop(PUBLIC_ROOT_ENV, None)
            else:
                os.environ[PUBLIC_ROOT_ENV] = old_root
        if loaded["manifest"] != manifest:
            raise B54ContractError("public artifact round trip changed manifest")
    except Exception:
        manifest_path.unlink(missing_ok=True)
        artifact_path.unlink(missing_ok=True)
        raise
    return {
        "artifact_id": artifact_id,
        "artifact_sha256": manifest["artifact_sha256"],
        "manifest_hash": manifest["manifest_hash"],
        "observed_duration_seconds": manifest["observed_duration_seconds"],
        "public_artifact_count": 1,
        "public_manifest_count": 1,
        "retry_count": 0,
        "fallback_count": 0,
    }


def export_observable_context(raw_media_path, public_root, profile_name):
    """Extract one frozen profile, delete its disposable raw input, and publish."""

    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise B54ContractError("invalid B54 contract: " + ";".join(contract_report["errors"]))
    contract = load_contract()
    profiles = contract["profiles"]
    if profile_name not in profiles:
        raise B54ContractError("profile not frozen")
    if (
        profile_name == "reserved_source_context"
        and contract["execution_authorization"]["reserved_source_media_access_authorized"] is not True
    ):
        raise B54ContractError("reserved source media access not authorized in B54")
    raw_path = Path(raw_media_path)
    public_path = Path(public_root)
    _validate_disposable_private_input(raw_path)
    try:
        prepared_public_root = _prepare_public_root(public_path, raw_path.parent)
        profile = profiles[profile_name]
        with TemporaryDirectory(prefix=".p3-b54-staging-", dir=raw_path.parent) as staging:
            staged_path = Path(staging) / "bounded-context.wav"
            _run_ffmpeg_extract(
                raw_path,
                staged_path,
                float(profile["context_start_seconds"]),
                float(profile["context_end_seconds"]),
            )
            return _publish_artifact(staged_path, prepared_public_root, profile)
    finally:
        raw_path.unlink(missing_ok=True)


def _write_synthetic_transport(path: Path, contract: dict[str, Any]) -> None:
    profile = contract["profiles"]["synthetic_boundary_rehearsal"]
    sample_rate = contract["output_audio"]["sample_rate_hz"]
    total_samples = int(profile["raw_transport_duration_seconds"] * sample_rate)
    cutoff_sample = int(profile["context_end_seconds"] * sample_rate)
    visible_frequency = profile["observable_tone_hz"]
    sentinel_frequency = profile["post_cutoff_sentinel_tone_hz"]
    samples = array("h")
    for index in range(total_samples):
        frequency = visible_frequency if index < cutoff_sample else sentinel_frequency
        sample = int(12000 * math.sin(2 * math.pi * frequency * index / sample_rate))
        samples.append(sample)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(samples.tobytes())
    os.chmod(path, 0o600)


def _spectral_power_ratio(path: Path, observable_frequency: float, sentinel_frequency: float) -> float:
    with wave.open(str(path), "rb") as reader:
        sample_rate = reader.getframerate()
        samples = array("h")
        samples.frombytes(reader.readframes(reader.getnframes()))
    def power(frequency: float) -> float:
        cosine = 0.0
        sine = 0.0
        for index, sample in enumerate(samples):
            angle = 2 * math.pi * frequency * index / sample_rate
            cosine += sample * math.cos(angle)
            sine += sample * math.sin(angle)
        return cosine * cosine + sine * sine
    observable_power = power(observable_frequency)
    if observable_power <= 0:
        raise B54ContractError("synthetic observable tone missing")
    return power(sentinel_frequency) / observable_power


def _reader_private_import_count() -> int:
    source = (ROOT / "p3_b54_public_context_reader.py").read_text(encoding="utf-8")
    return sum(
        bool(re.match(r"\s*(?:from|import)\s+p3_b54_unidirectional_context_extraction", line))
        for line in source.splitlines()
    )


def run_synthetic_boundary_rehearsal() -> dict[str, Any]:
    validate_implementation_freeze()
    contract = load_contract()
    acceptance = contract["synthetic_acceptance"]
    private_canary = "p3-b54-private-transport-future-sentinel"
    with TemporaryDirectory(prefix="uruha-p3-b54-") as temporary:
        base = Path(temporary)
        private_root = base / "private"
        public_root = base / "public"
        private_root.mkdir(mode=0o700)
        raw_path = private_root / f"p3-b54-private-transport-{private_canary}.wav"
        _write_synthetic_transport(raw_path, contract)
        receipt = export_observable_context(
            str(raw_path),
            str(public_root),
            "synthetic_boundary_rehearsal",
        )
        raw_deleted_before_generation_reader = not raw_path.exists()
        artifact_path = public_root / f"{receipt['artifact_id']}.wav"
        profile = contract["profiles"]["synthetic_boundary_rehearsal"]
        ratio = _spectral_power_ratio(
            artifact_path,
            profile["observable_tone_hz"],
            profile["post_cutoff_sentinel_tone_hz"],
        )
        private_mode_before = private_root.stat().st_mode & 0o777
        child_outputs = []
        child_exit_codes = []
        try:
            os.chmod(private_root, 0)
            for _ in range(int(acceptance["fresh_public_reader_processes"])):
                environment = {
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONIOENCODING": "utf-8",
                    PUBLIC_ROOT_ENV: str(public_root),
                }
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "p3_b54_public_context_reader.py"),
                        "--inspect",
                        receipt["artifact_id"],
                    ],
                    cwd=str(ROOT),
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                child_exit_codes.append(completed.returncode)
                child_outputs.append(completed.stdout)
        finally:
            os.chmod(private_root, private_mode_before)
        parsed_outputs = [json.loads(output) for output in child_outputs]
        combined_public_surface = canonical_json(parsed_outputs)
        manifests = [item["manifest"] for item in parsed_outputs]
        forbidden_paths = public_reader._forbidden_field_paths(manifests[0])
        result = {
            "schema": "uruha_p3_b54_synthetic_boundary_rehearsal_result_v1",
            "version": "1.0.0",
            "status": "synthetic_unidirectional_context_extraction_passed",
            "profile": "synthetic_boundary_rehearsal",
            "raw_transport_scope_seconds": [0.0, profile["raw_transport_duration_seconds"]],
            "generation_visible_scope_seconds": [
                profile["context_start_seconds"],
                profile["context_end_seconds"],
            ],
            "raw_deleted_before_generation_reader": raw_deleted_before_generation_reader,
            "private_root_mode_during_generation_readers": 0,
            "public_reader_process_count": len(child_exit_codes),
            "public_reader_exit_codes": child_exit_codes,
            "restart_outputs_identical": len(set(child_outputs)) == 1,
            "restart_artifact_hashes": [manifest["artifact_sha256"] for manifest in manifests],
            "artifact_sha256": receipt["artifact_sha256"],
            "manifest_hash": receipt["manifest_hash"],
            "observed_duration_seconds": receipt["observed_duration_seconds"],
            "post_cutoff_to_observable_spectral_energy_ratio": ratio,
            "post_cutoff_sentinel_absent": ratio <= acceptance["post_cutoff_to_observable_spectral_energy_ratio_max"],
            "manifest_forbidden_field_paths": forbidden_paths,
            "private_canary_hit_count": combined_public_surface.count(private_canary),
            "public_reader_private_import_count": _reader_private_import_count(),
            "reserved_source_media_access_count": 0,
            "hidden_future_access_count": 0,
            "prediction_execution_count": 0,
            "model_call_count": 0,
            "production_memory_write_count": 0,
            "claim_boundary": contract["claim_boundary"],
        }
        result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
        validate_synthetic_rehearsal(result)
        return result


def validate_synthetic_rehearsal(result: dict[str, Any]) -> dict[str, Any]:
    contract = load_contract()
    acceptance = contract["synthetic_acceptance"]
    errors = []
    if result.get("status") != "synthetic_unidirectional_context_extraction_passed":
        errors.append("status")
    if result.get("raw_transport_scope_seconds") != [0.0, 5.0]:
        errors.append("raw_transport_scope")
    if result.get("generation_visible_scope_seconds") != [1.0, 3.0]:
        errors.append("generation_visible_scope")
    if result.get("raw_deleted_before_generation_reader") is not True:
        errors.append("raw_not_deleted")
    if result.get("private_root_mode_during_generation_readers") != 0:
        errors.append("private_root_permissions")
    if result.get("public_reader_process_count") != acceptance["fresh_public_reader_processes"]:
        errors.append("reader_process_count")
    if set(result.get("public_reader_exit_codes") or []) != {0}:
        errors.append("reader_exit_codes")
    if result.get("restart_outputs_identical") is not True:
        errors.append("restart_output_drift")
    if len(set(result.get("restart_artifact_hashes") or [])) != 1:
        errors.append("restart_hash_drift")
    if result.get("post_cutoff_to_observable_spectral_energy_ratio", 1.0) > acceptance["post_cutoff_to_observable_spectral_energy_ratio_max"]:
        errors.append("post_cutoff_sentinel_leak")
    if result.get("post_cutoff_sentinel_absent") is not True:
        errors.append("post_cutoff_sentinel_present")
    if result.get("manifest_forbidden_field_paths") != []:
        errors.append("manifest_forbidden_fields")
    if result.get("private_canary_hit_count") != acceptance["private_canary_hits_allowed"]:
        errors.append("private_canary_exposed")
    if result.get("public_reader_private_import_count") != 0:
        errors.append("reader_private_import")
    for field in (
        "reserved_source_media_access_count",
        "hidden_future_access_count",
        "prediction_execution_count",
        "model_call_count",
        "production_memory_write_count",
    ):
        if result.get(field) != 0:
            errors.append(field)
    unhashed = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("result_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("result_hash")
    if errors:
        raise B54ContractError(";".join(errors))
    return {"valid": True, "errors": []}


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-B54 unidirectional context extraction")
    parser.add_argument("--synthetic-rehearsal", action="store_true")
    arguments = parser.parse_args()
    if not arguments.synthetic_rehearsal:
        parser.error("only the frozen synthetic rehearsal is authorized in B54")
    print(json.dumps(run_synthetic_boundary_rehearsal(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
