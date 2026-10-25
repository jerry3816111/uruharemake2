"""Zero-provider contracts for the prospective B-only local-source manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

import p4_b_product_source_manifest as manifest


def _clone_sources(tmp_path: Path) -> Path:
    root = tmp_path.resolve()
    for name in manifest.product_source_paths():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(manifest.ROOT / name, target)
    return root


def test_frozen_230_python_names_and_232_path_contract():
    paths = manifest.product_source_paths()
    python = sorted(name for name in paths if name.endswith(".py"))
    assert len(paths) == 232
    assert len(python) == 230
    assert len(set(paths)) == len(paths)
    assert tuple(sorted(paths)) == paths
    assert hashlib.sha256("\n".join(python).encode()).hexdigest() == (
        manifest.EXPECTED_PYTHON_NAMES_SHA256
    )
    assert "p4_b_product_source_manifest.py" in paths
    assert "longitudinal_human_model/__init__.py" in paths
    assert "uruha_brain_mac.py" in paths
    assert "uruha_product_function_calling_p4.py" in paths
    assert set(manifest.ASSETS).issubset(paths)


def test_canonical_digest_binds_helper_and_every_named_byte():
    names = manifest.product_source_paths()
    expected_files = [
        [name, hashlib.sha256((manifest.ROOT / name).read_bytes()).hexdigest()]
        for name in names
    ]
    canonical = json.dumps(
        {"schema": "p4_b_product_sources_v1", "files": expected_files},
        ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")
    digests = manifest.product_source_digests()
    assert digests == {
        "product_source_manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "product_manifest_module_sha256": dict(expected_files)[manifest.HELPER],
    }


@pytest.mark.parametrize("name", [
    "uruha_web_ui_product_p4_question_evidence.py",
    "uruha_brain_mac.py",
    "uruha_product_function_calling_p4.py",
    "longitudinal_human_model/metrics.py",
    "web_assets/uruha_vrm_viewer_p4.bundle.js",
    "configs/p4_c_read_only_function_calling_contract_v1.json",
    "p4_b_product_source_manifest.py",
])
def test_named_source_byte_drift_changes_digest(tmp_path, name):
    root = _clone_sources(tmp_path)
    original = manifest.product_source_digests(root)
    with (root / name).open("ab") as target:
        target.write(b"\n")
    updated = manifest.product_source_digests(root)
    assert updated["product_source_manifest_sha256"] != original[
        "product_source_manifest_sha256"
    ]
    assert (updated["product_manifest_module_sha256"] != original[
        "product_manifest_module_sha256"
    ]) is (name == manifest.HELPER)


def test_added_or_removed_package_file_rejected(tmp_path):
    root = _clone_sources(tmp_path)
    (root / "longitudinal_human_model/new_local.py").write_text("x = 1\n")
    with pytest.raises(manifest.ProductSourceManifestError, match="package_set_drift"):
        manifest.product_source_paths(root)
    (root / "longitudinal_human_model/new_local.py").unlink()
    (root / "longitudinal_human_model/metrics.py").unlink()
    with pytest.raises(manifest.ProductSourceManifestError, match="package_set_drift"):
        manifest.product_source_paths(root)


def test_new_local_namespace_package_import_rejected(tmp_path):
    root = _clone_sources(tmp_path)
    entry = root / manifest.ENTRY
    entry.write_text(entry.read_text() + "\nimport unreviewed_local_package\n")
    namespace = root / "unreviewed_local_package"
    namespace.mkdir()
    (namespace / "module.py").write_text("x = 1\n")
    with pytest.raises(manifest.ProductSourceManifestError, match="unreviewed_package"):
        manifest.product_source_paths(root)


def test_new_root_module_import_changes_frozen_name_set(tmp_path):
    root = _clone_sources(tmp_path)
    entry = root / manifest.ENTRY
    entry.write_text(entry.read_text() + "\nimport new_local_module\n")
    (root / "new_local_module.py").write_text("x = 1\n")
    with pytest.raises(manifest.ProductSourceManifestError, match="python_set_drift"):
        manifest.product_source_paths(root)


@pytest.mark.parametrize("line,reason", [
    ("from .metrics import x", "relative_import_unreviewed"),
    ("importlib.import_module('new_local')", "dynamic_import_or_eval"),
])
def test_new_unsupported_root_source_form_rejected(tmp_path, line, reason):
    root = _clone_sources(tmp_path)
    entry = root / manifest.ENTRY
    entry.write_text(entry.read_text() + "\n" + line + "\n")
    with pytest.raises(manifest.ProductSourceManifestError, match=reason):
        manifest.product_source_paths(root)


def test_symlinked_asset_parent_rejected(tmp_path):
    root = _clone_sources(tmp_path)
    parent = root / "web_assets"
    parent.rename(root / "relocated_assets")
    parent.symlink_to(root / "relocated_assets", target_is_directory=True)
    with pytest.raises(manifest.ProductSourceManifestError, match="parent_invalid"):
        manifest.product_source_paths(root)


def test_symlinked_python_file_rejected(tmp_path):
    root = _clone_sources(tmp_path)
    source = root / "uruha_brain_mac.py"
    source.unlink()
    source.symlink_to(manifest.ROOT / "uruha_brain_mac.py")
    with pytest.raises(manifest.ProductSourceManifestError):
        manifest.product_source_paths(root)


def test_package_relative_parent_escape_rejected(tmp_path):
    root = _clone_sources(tmp_path)
    source = root / "longitudinal_human_model/metrics.py"
    source.write_text(source.read_text() + "\nfrom ..external import value\n")
    with pytest.raises(manifest.ProductSourceManifestError, match="relative_import_unreviewed"):
        manifest.product_source_paths(root)
