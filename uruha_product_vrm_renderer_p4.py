"""Product-only offline VRM renderer head injection for P4-D."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "web_assets" / "uruha_vrm_viewer_p4.bundle.js"
MARKER = "uruha-product-vrm-renderer-p4-d"
MAX_BUNDLE_BYTES = 3 * 1024 * 1024


class ProductVrmRendererError(RuntimeError):
    pass


def read_validated_bundle(path: Path = BUNDLE) -> str:
    if not path.is_file():
        raise ProductVrmRendererError("vrm_renderer_bundle_missing")
    size = path.stat().st_size
    if size <= 0 or size > MAX_BUNDLE_BYTES:
        raise ProductVrmRendererError("vrm_renderer_bundle_size_invalid")
    source = path.read_text(encoding="utf-8")
    if "</script" in source.lower():
        raise ProductVrmRendererError("vrm_renderer_bundle_script_boundary_invalid")
    required = (
        "uruha-vrm-viewer-p4",
        "waiting_for_local_vrm",
        "rendering_vrm",
        "load_failed",
        "serverUploadCount",
        "actionExecutionCount",
    )
    if any(token not in source for token in required):
        raise ProductVrmRendererError("vrm_renderer_bundle_contract_marker_missing")
    return source


def build_product_vrm_head(existing_head: str, *, bundle_path: Path | None = None) -> str:
    if MARKER in existing_head:
        return existing_head
    bundle_path = bundle_path or BUNDLE
    source = read_validated_bundle(bundle_path)
    return (
        existing_head
        + f'\n<meta name="{MARKER}" content="offline-local-file-only">\n'
        + '<script data-uruha-product-vrm-p4-d="true">\n'
        + source
        + "\n</script>\n"
    )


def install_product_vrm_renderer_p4(base_module) -> None:
    base_module.WEB_HEAD = build_product_vrm_head(str(base_module.WEB_HEAD))
