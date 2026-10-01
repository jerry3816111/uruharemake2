from __future__ import annotations

from array import array
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import wave

import pytest

import p3_b54_public_context_reader as public_reader
import p3_b54_unidirectional_context_extraction as b54


def _write_tone(path: Path, duration_seconds: float, frequency_hz: float = 440.0) -> None:
    sample_rate = 16000
    samples = array(
        "h",
        (
            int(12000 * math.sin(2 * math.pi * frequency_hz * index / sample_rate))
            for index in range(int(duration_seconds * sample_rate))
        ),
    )
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(samples.tobytes())
    os.chmod(path, 0o600)


def _materialize_export(base: Path):
    private_root = base / "private"
    public_root = base / "public"
    private_root.mkdir(parents=True, mode=0o700)
    raw = private_root / "p3-b54-private-transport-test-canary.wav"
    b54._write_synthetic_transport(raw, b54.load_contract())
    receipt = b54.export_observable_context(
        str(raw), str(public_root), "synthetic_boundary_rehearsal"
    )
    return private_root, public_root, raw, receipt


def _with_public_root(public_root: Path):
    class PublicRootContext:
        def __enter__(self):
            self.previous = os.environ.get(public_reader.PUBLIC_ROOT_ENV)
            os.environ[public_reader.PUBLIC_ROOT_ENV] = str(public_root)

        def __exit__(self, *_):
            if self.previous is None:
                os.environ.pop(public_reader.PUBLIC_ROOT_ENV, None)
            else:
                os.environ[public_reader.PUBLIC_ROOT_ENV] = self.previous

    return PublicRootContext()


def _rewrite_manifest(path: Path, manifest: dict) -> None:
    unhashed = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    manifest["manifest_hash"] = public_reader.sha256_bytes(
        public_reader.canonical_json(unhashed).encode("utf-8")
    )
    path.write_text(public_reader.canonical_json(manifest), encoding="utf-8")
    os.chmod(path, 0o600)


def test_contract_is_bound_to_b53_and_public_reader_schema():
    assert b54.validate_contract() == {"valid": True, "errors": []}
    contract = b54.load_contract()
    assert set(contract["public_surface"]["allowed_manifest_fields"]) == public_reader.ALLOWED_MANIFEST_FIELDS
    assert set(contract["public_surface"]["forbidden_field_tokens"]) == public_reader.FORBIDDEN_FIELD_TOKENS


def test_public_reader_has_no_private_extractor_import_or_private_root_dependency():
    source = (b54.ROOT / "p3_b54_public_context_reader.py").read_text(encoding="utf-8")
    private_imports = [
        line
        for line in source.splitlines()
        if re.match(r"\s*(?:from|import)\s+p3_b54_unidirectional_context_extraction", line)
    ]
    assert private_imports == []
    assert "PRIVATE_ROOT" not in source
    assert "raw_media_path" not in source


def test_reserved_source_profile_is_fail_closed_before_media_access():
    with TemporaryDirectory(prefix="uruha-p3-b54-denied-") as temporary:
        with pytest.raises(b54.B54ContractError, match="not authorized"):
            b54.export_observable_context(
                str(Path(temporary) / "does-not-exist.wav"),
                str(Path(temporary) / "public"),
                "reserved_source_context",
            )
        assert not (Path(temporary) / "public").exists()


def test_synthetic_export_deletes_raw_and_round_trips_public_only():
    with TemporaryDirectory(prefix="uruha-p3-b54-export-") as temporary:
        private_root, public_root, raw, receipt = _materialize_export(Path(temporary))
        assert not raw.exists()
        assert len(list(private_root.iterdir())) == 0
        assert sorted(path.suffix for path in public_root.iterdir()) == [".json", ".wav"]
        with _with_public_root(public_root):
            loaded = public_reader.load_public_context(receipt["artifact_id"])
        manifest = loaded["manifest"]
        assert public_reader._forbidden_field_paths(manifest) == []
        assert manifest["artifact_sha256"] == receipt["artifact_sha256"]
        assert manifest["context_start_seconds"] == 1.0
        assert manifest["context_end_seconds"] == 3.0
        for path in public_root.iterdir():
            metadata = path.stat()
            assert metadata.st_nlink == 1
            assert metadata.st_mode & 0o777 == 0o600


def test_synthetic_rehearsal_excludes_post_cutoff_sentinel_and_revalidates_hash():
    result = b54.run_synthetic_boundary_rehearsal()
    assert b54.validate_synthetic_rehearsal(result) == {"valid": True, "errors": []}
    assert result["raw_transport_scope_seconds"] == [0.0, 5.0]
    assert result["generation_visible_scope_seconds"] == [1.0, 3.0]
    assert result["post_cutoff_to_observable_spectral_energy_ratio"] <= 0.0001
    assert result["post_cutoff_sentinel_absent"] is True
    assert result["restart_outputs_identical"] is True
    assert len(set(result["restart_artifact_hashes"])) == 1


def test_ffprobe_rejects_overlong_artifact_even_when_manifest_claims_expected_duration():
    with TemporaryDirectory(prefix="uruha-p3-b54-overlong-") as temporary:
        _, public_root, _, receipt = _materialize_export(Path(temporary))
        artifact = public_root / f"{receipt['artifact_id']}.wav"
        manifest_path = public_root / f"{receipt['artifact_id']}.json"
        _write_tone(artifact, 2.25)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_bytes = artifact.read_bytes()
        manifest["artifact_bytes"] = len(artifact_bytes)
        manifest["artifact_sha256"] = public_reader.sha256_bytes(artifact_bytes)
        _rewrite_manifest(manifest_path, manifest)
        with _with_public_root(public_root):
            with pytest.raises(public_reader.PublicContextError, match="ffprobe_duration_gate"):
                public_reader.load_public_context(receipt["artifact_id"])


def test_hash_tamper_and_forbidden_manifest_field_fail_closed():
    with TemporaryDirectory(prefix="uruha-p3-b54-tamper-") as temporary:
        _, public_root, _, receipt = _materialize_export(Path(temporary))
        artifact = public_root / f"{receipt['artifact_id']}.wav"
        manifest_path = public_root / f"{receipt['artifact_id']}.json"
        with artifact.open("ab") as handle:
            handle.write(b"tamper")
        with _with_public_root(public_root):
            with pytest.raises(public_reader.PublicContextError, match="artifact_(size|hash)"):
                public_reader.load_public_context(receipt["artifact_id"])

        # Restore a fresh export before testing an attacker who recomputes the
        # content hash but injects a prohibited source locator field.
        second = Path(temporary) / "second"
        _, second_public, _, second_receipt = _materialize_export(second)
        second_manifest_path = second_public / f"{second_receipt['artifact_id']}.json"
        injected = json.loads(second_manifest_path.read_text(encoding="utf-8"))
        injected["source_url"] = "https://forbidden.invalid/private"
        _rewrite_manifest(second_manifest_path, injected)
        with _with_public_root(second_public):
            with pytest.raises(public_reader.PublicContextError, match="manifest_fields"):
                public_reader.load_public_context(second_receipt["artifact_id"])


def test_symlink_hardlink_and_group_world_permissions_fail_closed():
    with TemporaryDirectory(prefix="uruha-p3-b54-files-") as temporary:
        _, public_root, _, receipt = _materialize_export(Path(temporary))
        manifest = public_root / f"{receipt['artifact_id']}.json"
        with _with_public_root(public_root):
            os.chmod(manifest, 0o644)
            with pytest.raises(public_reader.PublicContextError, match="permissions"):
                public_reader.load_public_context(receipt["artifact_id"])
            os.chmod(manifest, 0o600)
            hard_id = "b" * 32
            os.link(manifest, public_root / f"{hard_id}.json")
            with pytest.raises(public_reader.PublicContextError, match="link count"):
                public_reader.load_public_context(hard_id)
            os.unlink(public_root / f"{hard_id}.json")
            link_id = "c" * 32
            os.symlink(manifest, public_root / f"{link_id}.json")
            with pytest.raises(public_reader.PublicContextError, match="secure open"):
                public_reader.load_public_context(link_id)


def test_failed_extraction_deletes_valid_disposable_raw_input():
    with TemporaryDirectory(prefix="uruha-p3-b54-invalid-") as temporary:
        base = Path(temporary)
        private_root = base / "private"
        private_root.mkdir(mode=0o700)
        raw = private_root / "p3-b54-private-transport-invalid.wav"
        raw.write_bytes(b"not media")
        os.chmod(raw, 0o600)
        with pytest.raises(b54.B54ContractError, match="ffmpeg extraction failed"):
            b54.export_observable_context(
                str(raw), str(base / "public"), "synthetic_boundary_rehearsal"
            )
        assert not raw.exists()


def test_implementation_freeze_matches_all_frozen_files():
    assert b54.validate_implementation_freeze() == {
        "valid": True,
        "synthetic_rehearsal_count_at_freeze": 0,
        "reserved_source_media_access_count_at_freeze": 0,
        "hidden_future_access_count_at_freeze": 0,
    }
