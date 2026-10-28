#!/usr/bin/env python3
"""Read-only P4-D local asset and renderer inventory."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT.parent.parent / "uruharemake2"
ASSET_SUFFIXES = {".vrm", ".glb", ".gltf"}
PACKAGE_NAMES = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def _relative_files(root: Path, *, predicate) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if path.is_file() and predicate(path, relative):
            found.append(relative.as_posix())
    return sorted(found)


def _version(executable: str) -> str | None:
    path = shutil.which(executable)
    if not path:
        return None
    completed = subprocess.run(
        [path, "--version"], check=False, capture_output=True, text=True, timeout=10
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def inspect_root(root: Path) -> dict:
    assets = _relative_files(root, predicate=lambda path, _: path.suffix.lower() in ASSET_SUFFIXES)
    package_files = _relative_files(root, predicate=lambda path, _: path.name in PACKAGE_NAMES)
    renderer_files = _relative_files(
        root,
        predicate=lambda path, relative: (
            path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".jsx", ".html"}
            and any(term in relative.as_posix().lower() for term in ("three-vrm", "model-viewer", "babylon"))
        ),
    )
    return {
        "asset_count": len(assets),
        "assets": assets,
        "package_manifest_count": len(package_files),
        "package_manifests": package_files,
        "renderer_file_count": len(renderer_files),
        "renderer_files": renderer_files,
    }


def build_inventory() -> dict:
    safe = inspect_root(ROOT)
    original = inspect_root(ORIGINAL)
    return {
        "schema": "uruha_p4_d_local_vrm_renderer_inventory_v1",
        "status": "no_local_asset_or_renderer_dependency_found",
        "roots": {"safe_worktree": safe, "original_checkout_read_only": original},
        "research_policy_only_files": [
            "vrm_action_policy_v34.py",
            "vrm_action_semantic_authorizer_v35.py",
        ],
        "research_policy_is_renderer": False,
        "local_tools": {"node": _version("node"), "npm": _version("npm")},
        "decision": "build_offline_renderer_for_user_supplied_vrm_without_bundled_character_asset",
        "write_count": 0,
    }


def validate_inventory(report: dict) -> list[str]:
    errors: list[str] = []
    for key in ("safe_worktree", "original_checkout_read_only"):
        row = report["roots"][key]
        if row["asset_count"] != 0:
            errors.append(f"unexpected_local_asset:{key}")
        if key == "original_checkout_read_only" and row["package_manifest_count"] != 0:
            errors.append("unexpected_original_package_manifest")
    if report["research_policy_is_renderer"] is not False:
        errors.append("research_policy_misclassified_as_renderer")
    if not report["local_tools"]["node"] or not report["local_tools"]["npm"]:
        errors.append("node_or_npm_unavailable")
    return errors


if __name__ == "__main__":
    payload = build_inventory()
    payload["validation_errors"] = validate_inventory(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
