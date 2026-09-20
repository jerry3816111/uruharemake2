from pathlib import Path
from types import SimpleNamespace

import pytest

import uruha_product_vrm_renderer_p4 as viewer


ROOT = Path(__file__).resolve().parent
ENTRY_SOURCE = ROOT / "web_assets" / "uruha_vrm_viewer_p4_entry.js"


def _bundle(tmp_path: Path, source: str | None = None) -> Path:
    content = source if source is not None else "|".join(
        (
            "uruha-vrm-viewer-p4",
            "waiting_for_local_vrm",
            "rendering_vrm",
            "load_failed",
            "serverUploadCount",
            "actionExecutionCount",
        )
    )
    path = tmp_path / "viewer.js"
    path.write_text(content, encoding="utf-8")
    return path


def test_head_injection_is_product_only_self_contained_and_idempotent(tmp_path):
    path = _bundle(tmp_path)
    head = viewer.build_product_vrm_head("<meta name='base'>", bundle_path=path)
    assert viewer.MARKER in head
    assert "data-uruha-product-vrm-p4-d" in head
    assert path.read_text(encoding="utf-8") in head
    assert viewer.build_product_vrm_head(head, bundle_path=path) == head


def test_install_mutates_only_provided_product_base(tmp_path, monkeypatch):
    path = _bundle(tmp_path)
    monkeypatch.setattr(viewer, "BUNDLE", path)
    base = SimpleNamespace(WEB_HEAD="original")
    viewer.install_product_vrm_renderer_p4(base)
    assert base.WEB_HEAD.startswith("original")
    assert viewer.MARKER in base.WEB_HEAD


@pytest.mark.parametrize(
    "content,error",
    [
        ("", "vrm_renderer_bundle_size_invalid"),
        ("</script>", "vrm_renderer_bundle_script_boundary_invalid"),
        ("not-the-viewer", "vrm_renderer_bundle_contract_marker_missing"),
    ],
)
def test_bundle_validation_fails_closed(tmp_path, content, error):
    path = _bundle(tmp_path, content)
    with pytest.raises(viewer.ProductVrmRendererError, match=error):
        viewer.read_validated_bundle(path)


def test_client_source_uses_local_file_without_upload_or_action_policy():
    source = ENTRY_SOURCE.read_text(encoding="utf-8")
    assert 'accept=".vrm"' in source
    assert "URL.createObjectURL(file)" in source
    assert "URL.revokeObjectURL(currentObjectUrl)" in source
    assert "new VRMLoaderPlugin(parser)" in source
    assert 'url.startsWith("blob:") || url.startsWith("data:")' in source
    assert 'throw new Error("external_resource_blocked")' in source
    assert "serverUploadCount: 0" in source
    assert "actionExecutionCount: 0" in source
    assert "vrm_action_policy" not in source
    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source
    assert "http://" not in source
    assert "https://" not in source


def test_product_entry_installs_viewer_after_function_calling():
    source = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert "from uruha_product_vrm_renderer_p4 import install_product_vrm_renderer_p4" in source
    assert "install_product_vrm_renderer_p4(_base)" in source
    assert source.index("install_product_function_calling_p4(_base)") < source.index(
        "install_product_vrm_renderer_p4(_base)"
    )
