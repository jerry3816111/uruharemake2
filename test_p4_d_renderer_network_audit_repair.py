import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPAIR = ROOT / "configs" / "p4_d_renderer_network_audit_repair_v1.json"
ENTRY = ROOT / "web_assets" / "uruha_vrm_viewer_p4_entry.js"
BUNDLE = ROOT / "web_assets" / "uruha_vrm_viewer_p4.bundle.js"


def test_first_literal_gate_failure_is_preserved():
    repair = json.loads(REPAIR.read_text(encoding="utf-8"))
    first = repair["preserved_first_attempt"]
    assert first["original_literal_gate_passed"] is False
    assert first["http_literal_count"] == 2
    assert first["https_literal_count"] == 1
    assert repair["authorized_repair_batch"]["dependency_version_change"] is False
    assert repair["unchanged_prohibition"]["runtime_cdn"] is False
    assert repair["unchanged_prohibition"]["external_model_or_texture_fetch"] is False


def test_entry_source_has_only_local_file_transport_and_explicit_url_allowlist():
    source = ENTRY.read_text(encoding="utf-8")
    assert "http://" not in source
    assert "https://" not in source
    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source
    assert 'url.startsWith("blob:") || url.startsWith("data:")' in source
    assert 'throw new Error("external_resource_blocked")' in source
    assert "URL.createObjectURL(file)" in source


def test_bundle_is_inline_iife_without_external_script_or_remote_dynamic_import():
    source = BUNDLE.read_text(encoding="utf-8")
    assert len(source.encode("utf-8")) < 3 * 1024 * 1024
    assert not re.search(r"<script[^>]+src=", source, flags=re.IGNORECASE)
    assert not re.search(r"import\s*\(\s*['\"]https?://", source)
    assert "uruha-vrm-viewer-p4" in source
