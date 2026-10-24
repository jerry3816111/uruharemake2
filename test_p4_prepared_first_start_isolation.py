"""Product-free contracts for the one-use prepared first-start route."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile

import pytest

import p4_b_safe_isolated_product_launcher as base
import p4_b_safe_isolated_product_launcher_v2 as sandbox
import p4_preference_fallback_detached_control as control
import p4_preference_fallback_launchd_control as launchd
import p4_preference_fallback_safe_isolated_product_launcher as launcher


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    # The controller requires an immediate child of the resolved system temp.
    # Patch only the temp parent for these contract tests; no real model is used.
    monkeypatch.setattr(control.tempfile, "gettempdir", lambda: str(tmp_path))
    result = control.prepare()
    return Path(result["runtime_root"])


def _private_file(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


def _private_model(root: Path, monkeypatch) -> Path:
    model = root / ".cache/chroma/onnx_models/all-MiniLM-L6-v2"
    extracted = model / "onnx"
    extracted.mkdir(parents=True)
    for directory in (root / ".cache", root / ".cache/chroma",
                      root / ".cache/chroma/onnx_models", model, extracted):
        directory.chmod(0o700)
    data = {name: f"fixture:{name}".encode() for name in control.ONNX_FILES}
    archive = model / "onnx.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        directory = tarfile.TarInfo("onnx/")
        directory.type = tarfile.DIRTYPE
        stream.addfile(directory)
        for name in sorted(data):
            payload = data[name]
            member = tarfile.TarInfo(f"onnx/{name}")
            member.size = len(payload)
            stream.addfile(member, io.BytesIO(payload))
            _private_file(extracted / name, payload)
    archive.chmod(0o600)
    monkeypatch.setattr(control, "ONNX_ARCHIVE_SIZE", archive.stat().st_size)
    monkeypatch.setattr(control, "ONNX_ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    return archive


def test_prepare_is_private_and_does_not_start_or_open_model(prepared, monkeypatch):
    root = prepared
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert control._prepared_root(str(root)) == root
    receipt = root / control.PREPARED
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert json.loads(receipt.read_text())["entrypoint"] == str(control.ENTRYPOINT)
    assert not (root / control.CURRENT).exists()
    assert not (root / control.PREPARED_CLAIM).exists()
    assert not (root / ".cache").exists()
    assert all(not any((root / name).iterdir()) for name in
               ("memory_db", "session_db", "web_logs"))


def test_prepare_itself_never_spawns_a_process(tmp_path, monkeypatch):
    monkeypatch.setattr(control.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(control.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    result = control.prepare()
    assert result["prepared"] is True and result["started"] is False


@pytest.mark.parametrize("mutation,match", [
    ("receipt", "prepared_receipt_mismatch"),
    ("receipt_uid", "prepared_receipt_mismatch"),
    ("receipt_port", "prepared_receipt_mismatch"),
    ("current", "prepared_root_stale_artifacts"),
    ("prior_run", "prepared_root_stale_artifacts"),
    ("db", "prepared_root_nonempty"),
    ("claim", "prepared_root_already_claimed"),
    ("manifest_mode", "prepared_path_not_private"),
    ("manifest_link", "prepared_path_not_private"),
])
def test_invalid_prepared_roots_reject_before_spawn(prepared, monkeypatch, mutation, match):
    root = prepared
    if mutation in ("receipt", "receipt_uid", "receipt_port"):
        receipt = root / control.PREPARED
        data = json.loads(receipt.read_text())
        if mutation == "receipt":
            data["entrypoint"] = "/tmp/other-product.py"
        elif mutation == "receipt_uid":
            data["uid"] = os.getuid() + 1
        else:
            data["port"] = control.PORT + 1
        _private_file(receipt, json.dumps(data).encode())
    elif mutation == "current":
        _private_file(root / control.CURRENT, b"{}")
    elif mutation == "prior_run":
        _private_file(root / f"{control.PREFIX}0123456789abcdef.json", b"{}")
    elif mutation == "db":
        _private_file(root / "memory_db" / "stale.sqlite", b"x")
    elif mutation == "claim":
        _private_file(root / control.PREPARED_CLAIM, b"{}")
    elif mutation == "manifest_mode":
        (root / base.MANIFEST_NAME).chmod(0o644)
    elif mutation == "manifest_link":
        manifest = root / base.MANIFEST_NAME
        alias = root / "manifest-alias"
        os.link(manifest, alias)
    monkeypatch.setattr(control.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    with pytest.raises(control.ControllerError, match=match):
        control.start(mode="product", python="unused", prepared_runtime_root=str(root))


def test_path_and_mode_are_bounded(prepared, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(prepared, target_is_directory=True)
    with pytest.raises(control.ControllerError, match="prepared_root_symlink"):
        control._prepared_root(str(alias))
    with pytest.raises(control.ControllerError, match="product_only_and_exclusive"):
        control.start(mode="inert", python=None, prepared_runtime_root=str(prepared))
    with pytest.raises(control.ControllerError, match="product_only_and_exclusive"):
        control.start(mode="product", python="unused", prepared_runtime_root=str(prepared),
                      reuse_runtime_root=str(prepared))


@pytest.mark.parametrize("mutation,match", [
    ("missing_archive", "No such file|not_private"),
    ("bad_archive", "archive_size_or_sha"),
    ("missing_extracted", "extracted_file_set"),
    ("altered_extracted", "extracted_content"),
    ("symlink", "prepared_path_not_private"),
    ("hardlink", "prepared_path_not_private"),
    ("world_readable", "prepared_path_not_private"),
])
def test_unsafe_private_model_cache_rejects_without_spawn(
    prepared, monkeypatch, mutation, match,
):
    root = prepared
    archive = _private_model(root, monkeypatch)
    target = archive.parent / "onnx" / "config.json"
    if mutation == "missing_archive":
        archive.unlink()
    elif mutation == "bad_archive":
        archive.write_bytes(archive.read_bytes() + b"altered")
    elif mutation == "missing_extracted":
        target.unlink()
    elif mutation == "altered_extracted":
        _private_file(target, b"altered")
    elif mutation == "symlink":
        target.unlink()
        target.symlink_to(archive)
    elif mutation == "hardlink":
        os.link(target, target.parent / "extra-link")
    elif mutation == "world_readable":
        target.chmod(0o644)
    monkeypatch.setattr(control.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    with pytest.raises((control.ControllerError, OSError), match=match):
        control.start(mode="product", python="unused", prepared_runtime_root=str(root))
    assert (root / control.PREPARED_CLAIM).is_file()


def test_claim_is_atomic_and_one_use(prepared):
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: _try_claim(prepared), range(2)))
    assert sorted(results) == ["claimed", "rejected"]
    assert stat.S_IMODE((prepared / control.PREPARED_CLAIM).stat().st_mode) == 0o600
    with pytest.raises(control.ControllerError, match="already_claimed"):
        control._prepared_root(str(prepared))


def _try_claim(root: Path) -> str:
    try:
        control._claim_prepared_root(root)
    except control.ControllerError:
        return "rejected"
    return "claimed"


def test_valid_prepared_product_start_is_one_use_and_binds_entrypoint(
    prepared, monkeypatch,
):
    root = prepared
    _private_model(root, monkeypatch)
    python = str(Path(".venv/product_checks/bin/python").resolve())
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control.base, "resolve_python", lambda requested, env: Path(python))

    def preflight(**kwargs):
        assert kwargs["runtime_root_arg"] == str(root)
        assert kwargs["prewarm"] is False
        layout = base.build_runtime_layout(root)
        profile = sandbox.write_sandbox_profile(root)
        env = launchd._isolated_env(layout, port=control.PORT)
        return {"python": python}, env, layout, False, profile

    monkeypatch.setattr(launcher, "preflight_preference_fallback", preflight)
    monkeypatch.setattr(control, "_calibrate_python_command", lambda *args: {
        "python_ps_executable": "/bin/sleep", "identity": {"pid": 999},
    })
    final = {
        "pid": 4242, "uid": os.getuid(), "pgid": 4242,
        "lstart": "Wed Oct 21 01:02:03 2026",
        "command": f"/bin/sleep {control.ENTRYPOINT}",
    }
    monkeypatch.setattr(control, "_identity", lambda pid: final)

    class FakeProcess:
        pid = 4242

    calls = []
    monkeypatch.setattr(control.subprocess, "Popen", lambda *args, **kwargs:
                        calls.append(args[0]) or FakeProcess())
    def first_start():
        try:
            return control.start(mode="product", python=python,
                                 prepared_runtime_root=str(root))
        except control.ControllerError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(lambda _: first_start(), range(2)))
    successes = [item for item in outcomes if isinstance(item, dict)]
    failures = [item for item in outcomes if isinstance(item, str)]
    assert len(successes) == 1 and len(failures) == 1
    assert "already_claimed" in failures[0]
    result = successes[0]
    assert result["ready"] is False
    assert len(calls) == 1
    assert calls[0][-1] == str(control.ENTRYPOINT)
    assert (root / control.PREPARED_CLAIM).is_file()
    _, metadata = control._root(str(root))
    assert metadata["previous_run_id"] is None
    with pytest.raises(control.ControllerError, match="already_claimed"):
        control.start(mode="product", python=python, prepared_runtime_root=str(root))
    assert len(calls) == 1


@pytest.mark.parametrize("mutation_stage", ["preflight", "calibration"])
def test_cache_mutation_during_setup_cannot_launch_product(prepared, monkeypatch, mutation_stage):
    root = prepared
    archive = _private_model(root, monkeypatch)
    python = str(Path(".venv/product_checks/bin/python").resolve())
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control.base, "resolve_python", lambda requested, env: Path(python))
    monkeypatch.setattr(control.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))

    def mutate():
        archive.write_bytes(archive.read_bytes() + b"changed after first validation")

    def preflight(**kwargs):
        layout = base.build_runtime_layout(root)
        profile = sandbox.write_sandbox_profile(root)
        env = launchd._isolated_env(layout, port=control.PORT)
        if mutation_stage == "preflight":
            mutate()
        return {"python": python}, env, layout, False, profile

    def calibration(*args):
        if mutation_stage == "calibration":
            mutate()
        return {"python_ps_executable": "/bin/sleep", "identity": {"pid": 999}}

    monkeypatch.setattr(launcher, "preflight_preference_fallback", preflight)
    monkeypatch.setattr(control, "_calibrate_python_command", calibration)
    with pytest.raises(control.ControllerError, match="archive_size_or_sha"):
        control.start(mode="product", python=python, prepared_runtime_root=str(root))
    assert (root / control.PREPARED_CLAIM).is_file()
    assert not (root / control.CURRENT).exists()
