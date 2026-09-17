"""Standalone reader for B54 observable-context audio artifacts.

This module intentionally has no import of the private extractor or any earlier
P3 module.  A generation process gets only the public root, one random artifact
identifier, the allowlisted manifest, and its bounded WAV artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
from typing import Any


PUBLIC_ROOT_ENV = "URUHA_P3_B54_PUBLIC_CONTEXT_ROOT"
MANIFEST_SCHEMA = "uruha_p3_b54_public_context_manifest_v1"
ARTIFACT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
ALLOWED_MANIFEST_FIELDS = {
    "schema",
    "version",
    "status",
    "artifact_id",
    "source_id",
    "boundary_receipt_hash",
    "context_start_seconds",
    "context_end_seconds",
    "requested_duration_seconds",
    "observed_duration_seconds",
    "duration_tolerance_seconds",
    "sample_rate_hz",
    "channels",
    "codec",
    "container",
    "artifact_name",
    "artifact_bytes",
    "artifact_sha256",
    "exposure_policy",
    "manifest_hash",
}
FORBIDDEN_FIELD_TOKENS = {
    "url",
    "uri",
    "title",
    "description",
    "transcript",
    "future",
    "behavior",
    "raw",
    "transport_path",
    "input_path",
    "source_duration",
}
ALLOWED_PROFILES = {
    (
        "synthetic_p3_b54_boundary_canary",
        "57b30468c5be05a06da7d1f2d5b423385be1f2d274a8de40f6c4cb90d80459e6",
        1.0,
        3.0,
    ),
    (
        "youtube_4y5GiQpgJgo",
        "0c190de102962657a1ed121fd8ff01853584ed8afdd3b4070ffdb25042f63f5a",
        3000.0,
        3180.0,
    ),
}
EXPECTED_EXPOSURE_POLICY = {
    "generation_visible_scope": "bounded_audio_artifact_and_allowlisted_manifest_only",
    "private_transport_visible": False,
    "post_cutoff_content_visible": False,
    "source_locator_visible": False,
    "immutable": True,
}


class PublicContextError(PermissionError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _public_root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    if not raw:
        raise PublicContextError(f"{PUBLIC_ROOT_ENV} is required")
    unresolved = Path(raw)
    if unresolved.is_symlink():
        raise PublicContextError("public root symlink rejected")
    root = unresolved.resolve()
    try:
        metadata = root.stat()
    except FileNotFoundError as exc:
        raise PublicContextError("public root missing") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise PublicContextError("public root must be a directory")
    if metadata.st_uid != os.getuid():
        raise PublicContextError("public root owner mismatch")
    if metadata.st_mode & 0o077:
        raise PublicContextError("public root group/world permissions rejected")
    return root


def _secure_read(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PublicContextError(f"secure open failed: {path.name}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise PublicContextError(f"non-regular public file: {path.name}")
        if metadata.st_uid != os.getuid():
            raise PublicContextError(f"public file owner mismatch: {path.name}")
        if metadata.st_nlink != 1:
            raise PublicContextError(f"public file link count rejected: {path.name}")
        if metadata.st_mode & 0o077:
            raise PublicContextError(f"public file group/world permissions rejected: {path.name}")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _ffprobe_audio(path: Path) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if executable is None:
        raise PublicContextError("ffprobe unavailable")
    completed = subprocess.run(
        [
            executable,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "format=duration:stream=codec_name,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise PublicContextError("ffprobe rejected public artifact")
    try:
        payload = json.loads(completed.stdout)
        stream = payload["streams"][0]
        duration = float(payload["format"]["duration"])
        return {
            "duration_seconds": duration,
            "codec": str(stream["codec_name"]),
            "sample_rate_hz": int(stream["sample_rate"]),
            "channels": int(stream["channels"]),
        }
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PublicContextError("ffprobe output invalid") from exc


def _forbidden_field_paths(value: Any, prefix: str = "") -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if any(token in lowered for token in FORBIDDEN_FIELD_TOKENS):
                found.append(path)
            found.extend(_forbidden_field_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_field_paths(child, f"{prefix}[{index}]"))
    return found


def validate_manifest(manifest: dict[str, Any], artifact_bytes: bytes, artifact_path: Path) -> dict[str, Any]:
    errors = []
    if not isinstance(manifest, dict) or set(manifest) != ALLOWED_MANIFEST_FIELDS:
        return {"valid": False, "errors": ["manifest_fields"]}
    unhashed = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != sha256_bytes(canonical_json(unhashed).encode("utf-8")):
        errors.append("manifest_hash")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("version") != "1.0.0":
        errors.append("manifest_schema")
    if manifest.get("status") != "immutable_bounded_observable_context":
        errors.append("manifest_status")
    artifact_id = str(manifest.get("artifact_id") or "")
    if ARTIFACT_ID_PATTERN.fullmatch(artifact_id) is None:
        errors.append("artifact_id")
    if manifest.get("artifact_name") != f"{artifact_id}.wav":
        errors.append("artifact_name")
    try:
        start = float(manifest.get("context_start_seconds"))
        end = float(manifest.get("context_end_seconds"))
        requested = float(manifest.get("requested_duration_seconds"))
        observed = float(manifest.get("observed_duration_seconds"))
        tolerance = float(manifest.get("duration_tolerance_seconds"))
    except (TypeError, ValueError):
        errors.append("duration_types")
        start = end = requested = observed = tolerance = 0.0
    if (manifest.get("source_id"), manifest.get("boundary_receipt_hash"), start, end) not in ALLOWED_PROFILES:
        errors.append("profile_binding")
    if start < 0 or end <= start or abs((end - start) - requested) > 1e-9:
        errors.append("requested_duration")
    if tolerance != 0.05 or observed > requested + tolerance or observed < requested - tolerance:
        errors.append("manifest_duration_gate")
    if manifest.get("sample_rate_hz") != 16000 or manifest.get("channels") != 1:
        errors.append("audio_shape")
    if manifest.get("codec") != "pcm_s16le" or manifest.get("container") != "wav":
        errors.append("audio_format")
    if manifest.get("artifact_bytes") != len(artifact_bytes):
        errors.append("artifact_size")
    if manifest.get("artifact_sha256") != sha256_bytes(artifact_bytes):
        errors.append("artifact_hash")
    if manifest.get("exposure_policy") != EXPECTED_EXPOSURE_POLICY:
        errors.append("exposure_policy")
    errors.extend(f"forbidden_field:{path}" for path in _forbidden_field_paths(manifest))
    if not errors:
        probed = _ffprobe_audio(artifact_path)
        if probed["duration_seconds"] > requested + tolerance or probed["duration_seconds"] < requested - tolerance:
            errors.append("ffprobe_duration_gate")
        if abs(probed["duration_seconds"] - observed) > 0.001:
            errors.append("ffprobe_manifest_duration_mismatch")
        if probed["sample_rate_hz"] != 16000 or probed["channels"] != 1 or probed["codec"] != "pcm_s16le":
            errors.append("ffprobe_audio_profile")
    return {"valid": not errors, "errors": errors}


def load_public_context(artifact_id: str) -> dict[str, Any]:
    """Return only the validated public manifest and bounded artifact path."""

    if ARTIFACT_ID_PATTERN.fullmatch(str(artifact_id)) is None:
        raise PublicContextError("invalid artifact id")
    root = _public_root()
    manifest_path = root / f"{artifact_id}.json"
    artifact_path = root / f"{artifact_id}.wav"
    manifest_bytes = _secure_read(manifest_path)
    artifact_bytes = _secure_read(artifact_path)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicContextError("manifest JSON invalid") from exc
    report = validate_manifest(manifest, artifact_bytes, artifact_path)
    if not report["valid"]:
        raise PublicContextError("invalid public context: " + ";".join(report["errors"]))
    return {
        "manifest": manifest,
        "artifact_path": str(artifact_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read one B54 public context artifact")
    parser.add_argument("--inspect", required=True, metavar="ARTIFACT_ID")
    arguments = parser.parse_args()
    print(json.dumps(load_public_context(arguments.inspect), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
