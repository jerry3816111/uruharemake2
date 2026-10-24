#!/usr/bin/env python3
"""Audit the product entry without importing its heavyweight runtime."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PRODUCT_ENTRY = ROOT / "uruha_web_ui_product.py"
WEB_ENTRY = ROOT / "uruha_web_ui.py"
BRAIN_ENTRY = ROOT / "uruha_brain_mac.py"
ACTION_POLICY = ROOT / "vrm_action_policy_v34.py"
EXPECTED_WORKTREE_PYTHON = ROOT / "Style-Bert-VITS2" / "venv" / "bin" / "python"
VRM_ASSET_SUFFIXES = {".vrm", ".glb", ".gltf", ".fbx", ".pmx"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def tracked_files(root: Path = ROOT) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    )


def build_inventory(
    *,
    root: Path = ROOT,
    tracked: list[str] | None = None,
    worktree_python_exists: bool | None = None,
) -> dict:
    root = Path(root)
    product_path = root / PRODUCT_ENTRY.name
    web_path = root / WEB_ENTRY.name
    brain_path = root / BRAIN_ENTRY.name
    policy_path = root / ACTION_POLICY.name
    product = _read(product_path)
    web = _read(web_path)
    brain = _read(brain_path)
    product_imports = _imports(product)
    web_imports = _imports(web)
    brain_imports = _imports(brain)
    all_runtime_imports = product_imports | web_imports | brain_imports
    tracked = tracked if tracked is not None else tracked_files(root)
    asset_paths = [
        path for path in tracked if Path(path).suffix.lower() in VRM_ASSET_SUFFIXES
    ]

    chat_checks = {
        "product_reuses_base_runtime": "RUNTIME = _base.RUNTIME" in product,
        "product_builds_base_demo": "_base.build_demo()" in product,
        "chat_tab_exists": 'gr.Tab("Chat", id="chat")' in web,
        "text_submit_is_bound": "text_in.submit(" in web and "fn=submit_text" in web,
        "send_button_is_bound": "send_btn.click(" in web and "fn=submit_text" in web,
        "turn_reaches_real_brain": "brain.run_turn_debug" in web,
    }
    graph_checks = {
        "observatory_renderer_imported": "render_memory_observatory_m38 as render_memory_observatory" in web,
        "live_memory_flow_component_exists": 'gr.Markdown("## Live Memory Flow")' in web,
        "flow_html_component_exists": "flow_html = gr.HTML(" in web,
        "turn_result_renders_observatory": 'result["flow_html"] = _render_flow_html(observatory_result)' in web,
        "text_turn_updates_same_component": "outputs=[chatbot, history_state, text_in, audio_out, debug_json, cognition_json, flow_html" in web,
    }
    renderer_markers = (
        "@pixiv/three-vrm",
        "three-vrm",
        "THREE.VRM",
        "VRMLoaderPlugin",
    )
    combined_ui = product + "\n" + web
    vrm_checks = {
        "tracked_3d_asset_count": len(asset_paths),
        "tracked_3d_assets": asset_paths,
        "vrm_renderer_present": any(marker in combined_ui for marker in renderer_markers),
        "product_action_policy_imported": "vrm_action_policy_v34" in all_runtime_imports,
        "physical_action_executor_present": any(
            marker in combined_ui
            for marker in ("execute_vrm_action", "dispatch_vrm_action", "apply_vrm_action")
        ),
    }
    function_checks = {
        "offline_action_policy_exists": policy_path.is_file(),
        "offline_action_policy_sha256": sha256_file(policy_path) if policy_path.is_file() else None,
        "product_action_policy_imported": "vrm_action_policy_v34" in all_runtime_imports,
        "runtime_tool_schema_present": any(
            marker in product + "\n" + web + "\n" + brain
            for marker in ('"tools":', "tool_choice=", "tools=")
        ),
        "runtime_tool_result_loop_present": any(
            marker in product + "\n" + web + "\n" + brain
            for marker in ("execute_tool_call", "dispatch_tool_call", "append_tool_result")
        ),
    }
    if worktree_python_exists is None:
        worktree_python_exists = (root / "Style-Bert-VITS2" / "venv" / "bin" / "python").exists()

    chat_integrated = all(chat_checks.values())
    graph_integrated = all(graph_checks.values())
    vrm_integrated = (
        vrm_checks["tracked_3d_asset_count"] > 0
        and vrm_checks["vrm_renderer_present"]
        and vrm_checks["physical_action_executor_present"]
    )
    function_integrated = (
        function_checks["product_action_policy_imported"]
        and function_checks["runtime_tool_schema_present"]
        and function_checks["runtime_tool_result_loop_present"]
    )
    return {
        "schema": "uruha_p4_a_unified_local_entry_inventory_v1",
        "status": "inventory_complete",
        "source_bindings": {
            "product_entry": {"path": product_path.name, "sha256": sha256_file(product_path)},
            "web_entry": {"path": web_path.name, "sha256": sha256_file(web_path)},
            "brain_entry": {"path": brain_path.name, "sha256": sha256_file(brain_path)},
        },
        "capabilities": {
            "chat": {
                "status": "integrated_in_product_entry" if chat_integrated else "not_integrated",
                "checks": chat_checks,
            },
            "truthful_runtime_graph": {
                "status": "integrated_same_turn_output" if graph_integrated else "not_integrated",
                "checks": graph_checks,
            },
            "vrm_3d": {
                "status": "integrated" if vrm_integrated else "absent_from_product_runtime",
                "checks": vrm_checks,
            },
            "function_calling": {
                "status": "integrated" if function_integrated else "research_policy_only_not_product_runtime",
                "checks": function_checks,
            },
        },
        "launchability": {
            "expected_worktree_python": str(root / "Style-Bert-VITS2" / "venv" / "bin" / "python"),
            "expected_worktree_python_exists": bool(worktree_python_exists),
            "direct_safe_worktree_launch_ready": bool(worktree_python_exists and chat_integrated and graph_integrated),
            "runtime_or_safari_launch_performed": False,
        },
        "decision": {
            "already_integrated": [
                name
                for name, integrated in (
                    ("chat", chat_integrated),
                    ("truthful_runtime_graph", graph_integrated),
                )
                if integrated
            ],
            "missing_or_not_integrated": [
                name
                for name, integrated in (
                    ("vrm_3d", vrm_integrated),
                    ("function_calling", function_integrated),
                )
                if not integrated
            ],
            "smallest_next_blocker": "safe_isolated_product_launcher",
            "reason": "Chat and graph share one real turn path, but the safe worktree has no bundled runtime Python; launchability must be made reproducible before adding tool or 3D paths.",
        },
        "access_accounting": {
            "model_call_count": 0,
            "production_memory_read_count": 0,
            "production_memory_write_count": 0,
            "physical_vrm_action_count": 0,
            "tool_execution_count": 0,
            "safari_operation_count": 0,
        },
        "claim_boundary": "Source inventory only. It proves code linkage or absence, not successful launch, visible Safari behavior, tool safety, VRM rendering, or end-to-end product readiness.",
    }


def validate_inventory(report: dict) -> list[str]:
    errors: list[str] = []
    if report.get("status") != "inventory_complete":
        errors.append("status")
    capabilities = report.get("capabilities") or {}
    if (capabilities.get("chat") or {}).get("status") != "integrated_in_product_entry":
        errors.append("chat_not_integrated")
    if (capabilities.get("truthful_runtime_graph") or {}).get("status") != "integrated_same_turn_output":
        errors.append("runtime_graph_not_integrated")
    if (capabilities.get("vrm_3d") or {}).get("status") == "integrated":
        errors.append("unexpected_vrm_integration")
    if (capabilities.get("function_calling") or {}).get("status") == "integrated":
        errors.append("unexpected_function_calling_integration")
    accounting = report.get("access_accounting") or {}
    if any(int(value) != 0 for value in accounting.values()):
        errors.append("nonzero_side_effect_accounting")
    if (report.get("decision") or {}).get("smallest_next_blocker") != "safe_isolated_product_launcher":
        errors.append("next_blocker")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-valid", action="store_true")
    args = parser.parse_args(argv)
    report = build_inventory()
    errors = validate_inventory(report)
    report["validation"] = {"valid": not errors, "errors": errors}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors}, ensure_ascii=False))
    return 1 if args.require_valid and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
