"""Fail-closed local source inventory for the prospective P4-B v5 receipt.

This is a cooperative, local source boundary, not a claim about third-party
packages, dynamic effects, or permission to send a model request.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parent
ENTRY = "uruha_web_ui_product_p4_preference_fallback.py"
PACKAGE = "longitudinal_human_model"
HELPER = "p4_b_product_source_manifest.py"
ASSETS = (
    "configs/p4_c_read_only_function_calling_contract_v1.json",
    "web_assets/uruha_vrm_viewer_p4.bundle.js",
)
EXPECTED_PYTHON_COUNT = 230
EXPECTED_PYTHON_NAMES_SHA256 = (
    "cd9f04bfcbc517b159aa19a4de2dc77982c161722760bed8f73b9fd97aee1053"
)
EXPECTED_PACKAGE_COUNT = 21
MAX_FILE_BYTES = 16 * 1024 * 1024


class ProductSourceManifestError(RuntimeError):
    """Fixed reason codes only; never expose source content or paths."""


def _fail(reason: str) -> None:
    raise ProductSourceManifestError(reason)


def _canonical_root(root: Path) -> Path:
    if not isinstance(root, Path):
        _fail("product_source_root_invalid")
    try:
        info = root.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or root.resolve(strict=True) != root):
            _fail("product_source_root_invalid")
    except OSError:
        _fail("product_source_root_invalid")
    return root


def _regular_bytes(root: Path, name: str) -> bytes:
    if (not name or name.startswith("/") or "\\" in name
            or any(part in ("", ".", "..") for part in name.split("/"))):
        _fail("product_source_name_invalid")
    path = root / name
    try:
        parent = root
        for part in name.split("/")[:-1]:
            parent = parent / part
            parent_info = parent.lstat()
            if (not stat.S_ISDIR(parent_info.st_mode)
                    or parent_info.st_uid != os.getuid()
                    or parent.resolve(strict=True) != parent):
                _fail("product_source_parent_invalid")
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or not (0 < before.st_size <= MAX_FILE_BYTES)):
            _fail("product_source_not_owned_regular_file")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as source:
            opened = os.fstat(source.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_uid != os.getuid()
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
                _fail("product_source_changed_during_read")
            raw = source.read(MAX_FILE_BYTES + 1)
            after = os.fstat(source.fileno())
        if (len(raw) != before.st_size or len(raw) > MAX_FILE_BYTES
                or (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)
                != (before.st_dev, before.st_ino, before.st_size,
                    before.st_mtime_ns, before.st_ctime_ns)):
            _fail("product_source_changed_during_read")
        return raw
    except OSError:
        _fail("product_source_unavailable")


def _tree(root: Path, name: str) -> ast.AST:
    try:
        return ast.parse(_regular_bytes(root, name).decode("utf-8"), filename=name)
    except (SyntaxError, UnicodeDecodeError, ValueError):
        _fail("product_source_ast_invalid")


def _local_top(root: Path, name: str) -> str | None:
    """Return root module/package kind, rejecting unresolved local packages."""
    if (not name or not name.isidentifier()
            or name in ("__pycache__",)):
        return None
    module = root / f"{name}.py"
    try:
        info = module.lstat()
    except FileNotFoundError:
        info = None
    except OSError:
        _fail("product_source_local_import_unavailable")
    if info is not None:
        if not stat.S_ISREG(info.st_mode):
            _fail("product_source_local_import_not_regular")
        return "root"
    directory = root / name
    try:
        info = directory.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        _fail("product_source_local_import_unavailable")
    if not stat.S_ISDIR(info.st_mode):
        _fail("product_source_local_import_not_directory")
    try:
        local_python = any(candidate.suffix == ".py" for candidate in directory.rglob("*.py"))
    except OSError:
        _fail("product_source_local_import_unavailable")
    if not local_python:
        return None
    if name != PACKAGE:
        _fail("product_source_unreviewed_package")
    return "package"


def _import_names(
    tree: ast.AST, *, package_stems: set[str], allow_relative: bool = False,
):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            method = node.func
            if ((isinstance(method, ast.Name)
                 and method.id in {"__import__", "eval", "exec", "import_module"})
                    or (isinstance(method, ast.Attribute)
                        and method.attr == "import_module")):
                _fail("product_source_dynamic_import_or_eval")
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if not allow_relative or node.level != 1:
                    _fail("product_source_relative_import_unreviewed")
                if node.module:
                    if ("." in node.module or node.module not in package_stems):
                        _fail("product_source_relative_import_unreviewed")
                elif any(alias.name not in package_stems for alias in node.names):
                    _fail("product_source_relative_import_unreviewed")
                continue
            modules = [node.module] if node.module else []
        else:
            continue
        for module in modules:
            parts = module.split(".")
            if parts[0] == PACKAGE:
                if (len(parts) > 2 or (len(parts) == 2
                                      and parts[1] not in package_stems)):
                    _fail("product_source_package_import_unreviewed")
            yield parts[0]


def _package_names(root: Path) -> tuple[str, ...]:
    directory = root / PACKAGE
    try:
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or directory.resolve(strict=True) != directory):
            _fail("product_source_package_invalid")
        entries = tuple(directory.iterdir())
    except OSError:
        _fail("product_source_package_invalid")
    for entry in entries:
        if entry.is_dir() and entry.name != "__pycache__":
            _fail("product_source_nested_package_unreviewed")
    names = tuple(sorted(f"{PACKAGE}/{entry.name}" for entry in entries
                         if entry.suffix == ".py"))
    if len(names) != EXPECTED_PACKAGE_COUNT or f"{PACKAGE}/__init__.py" not in names:
        _fail("product_source_package_set_drift")
    return names


def product_source_paths(root: Path = ROOT) -> tuple[str, ...]:
    """Return the frozen 230 Python + 2 asset paths, with no Web import."""
    root = _canonical_root(root)
    package = _package_names(root)
    stems = {Path(name).stem for name in package}
    todo = [ENTRY.removesuffix(".py")]
    root_names: set[str] = set()
    while todo:
        module = todo.pop(0)
        if module in root_names:
            continue
        name = f"{module}.py"
        root_names.add(module)
        tree = _tree(root, name)
        for imported in _import_names(tree, package_stems=stems):
            kind = _local_top(root, imported)
            if kind == "root" and imported not in root_names:
                todo.append(imported)
            elif kind == "package" and imported != PACKAGE:
                _fail("product_source_unreviewed_package")
    for name in package:
        for imported in _import_names(
            _tree(root, name), package_stems=stems, allow_relative=True,
        ):
            kind = _local_top(root, imported)
            if kind == "root" and imported not in root_names:
                _fail("product_source_package_root_dependency_drift")
            if kind == "package" and imported != PACKAGE:
                _fail("product_source_unreviewed_package")
    # The helper is safety-critical even before the binding module imports it
    # during the two-file implementation sequence.
    python_names = sorted({f"{name}.py" for name in root_names}
                          | set(package) | {HELPER})
    name_digest = hashlib.sha256("\n".join(python_names).encode("utf-8")).hexdigest()
    if (len(python_names) != EXPECTED_PYTHON_COUNT
            or name_digest != EXPECTED_PYTHON_NAMES_SHA256):
        _fail("product_source_python_set_drift")
    names = tuple(sorted((*python_names, *ASSETS)))
    if len(names) != EXPECTED_PYTHON_COUNT + len(ASSETS):
        _fail("product_source_duplicate_path")
    for name in names:
        _regular_bytes(root, name)
    return names


def product_source_digests(root: Path = ROOT) -> dict[str, str]:
    """Hash the frozen local source bytes using receipt-v5 canonical JSON."""
    names = product_source_paths(root)
    files = [[name, hashlib.sha256(_regular_bytes(root, name)).hexdigest()]
             for name in names]
    canonical = json.dumps(
        {"schema": "p4_b_product_sources_v1", "files": files},
        ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")
    return {
        "product_source_manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "product_manifest_module_sha256": dict(files)[HELPER],
    }
