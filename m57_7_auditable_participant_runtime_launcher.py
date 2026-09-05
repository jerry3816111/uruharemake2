#!/usr/bin/env python3
"""M57.7 project-local attested runtime preparation and participant launch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "m57_7_auditable_participant_runtime_launcher_v1.json"
REQUIREMENTS_PATH = ROOT / "configs" / "m57_7_participant_runtime_requirements.txt"
GAP_PATH = ROOT / "analysis" / "m57_7_prechange_participant_runtime_gap_probe_2026-09-05.json"
RESULT_PATH = ROOT / "analysis" / "m57_7_auditable_participant_runtime_launcher_rehearsal_2026-09-05.json"
LIVE_AUDIT_PATH = ROOT / "analysis" / "m57_7_auditable_participant_runtime_launcher_live_audit_2026-09-05.json"
COST_PATH = ROOT / "analysis" / "m57_7_auditable_participant_runtime_launcher_fixture_cost_2026-09-05.json"
M57_6_AUDIT_PATH = ROOT / "analysis" / "m57_6_crash_recoverable_participant_capability_live_audit_2026-09-05.json"
DEFAULT_RUNTIME_ROOT = ROOT / ".venv" / "m57_7_participant_runtime"
ATTESTATION_NAME = "uruha_m57_7_runtime_attestation.json"


CHILD_AUDIT = r"""
import hashlib
import json
import platform
import site
import sys
from importlib import metadata
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

site_root = Path(metadata.distribution("cryptography").locate_file(""))
cryptography_binary = site_root / "cryptography/hazmat/bindings/_rust.abi3.so"
cffi_binary = site_root / "_cffi_backend.cpython-312-darwin.so"
salt = b"m57.7-audit-salt"
key = Scrypt(salt=salt, length=32, n=32768, r=8, p=1).derive(b"m57.7-audit-input")
nonce = b"m57.7nonce!"
ciphertext = AESGCM(key).encrypt(nonce, b"runtime-audit", b"m57.7")
primitive_smoke = AESGCM(key).decrypt(nonce, ciphertext, b"m57.7") == b"runtime-audit"
print(json.dumps({
    "python_version": platform.python_version(),
    "python_executable_sha256": sha(sys.executable),
    "system": platform.system(),
    "machine": platform.machine(),
    "macos_version": platform.mac_ver()[0],
    "isolated_user_site_disabled": site.ENABLE_USER_SITE is False,
    "distributions": {
        "cryptography": metadata.version("cryptography"),
        "cffi": metadata.version("cffi"),
        "pycparser": metadata.version("pycparser"),
    },
    "critical_binary_sha256": {
        "cryptography/hazmat/bindings/_rust.abi3.so": sha(cryptography_binary),
        "_cffi_backend.cpython-312-darwin.so": sha(cffi_binary),
    },
    "scrypt_aesgcm_smoke": primitive_smoke,
}, sort_keys=True))
"""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(path: Path, value: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, mode)
        payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, mode)
        _fsync_directory(path.parent)
    except BaseException:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _mode_bits(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _hashless(value: dict[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result.pop(field, None)
    return result


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    value = contract or load_contract()
    errors: list[str] = []
    expected_top = {
        "schema", "version", "status", "single_changed_variable", "frozen_dependencies",
        "accepted_platform", "base_interpreter", "project_runtime", "locked_distributions",
        "preparation", "launch", "preserved_boundaries", "claim_boundary",
    }
    if set(value) != expected_top:
        errors.append("contract.fields")
    if value.get("schema") != "uruha_m57_7_auditable_participant_runtime_launcher_contract_v1":
        errors.append("contract.schema")
    if value.get("version") != "1.0.0":
        errors.append("contract.version")
    if value.get("single_changed_variable") != "project_owned_attested_participant_runtime_launcher":
        errors.append("contract.single_changed_variable")
    for relative, expected_hash in value.get("frozen_dependencies", {}).items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"frozen_dependency:{relative}")
    if value.get("accepted_platform") != {
        "system": "Darwin", "machine": "arm64", "macos_major": 15,
        "general_cross_platform_support_claimed": False,
    }:
        errors.append("contract.accepted_platform")
    if value.get("base_interpreter") != {
        "executable": "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "exact_python_version": "3.12.10",
        "executable_sha256": "d4f152f2a753c94e0e7935c8ebbe6b2609979e1df7898422b577d0076383d08b",
        "venv_uses_copied_launcher": True,
        "missing_or_drift_fails_closed": True,
    }:
        errors.append("contract.base_interpreter")
    if value.get("project_runtime") != {
        "relative_root": ".venv/m57_7_participant_runtime",
        "directory_mode": "0700",
        "attestation_relative_path": ATTESTATION_NAME,
        "attestation_mode": "0600",
        "existing_runtime_automatically_overwritten_or_repaired": False,
        "atomically_published_after_audit": True,
        "tracked_in_git": False,
    }:
        errors.append("contract.project_runtime")
    expected_versions = {"cryptography": "50.0.1", "cffi": "2.1.1", "pycparser": "3.0"}
    locked = value.get("locked_distributions", {})
    if set(locked) != set(expected_versions):
        errors.append("contract.locked_distributions.names")
    for name, version in expected_versions.items():
        if locked.get(name, {}).get("version") != version:
            errors.append(f"contract.locked_distributions.{name}.version")
        wheel_hash = locked.get(name, {}).get("wheel_sha256")
        if not isinstance(wheel_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", wheel_hash):
            errors.append(f"contract.locked_distributions.{name}.wheel_hash")
    if value.get("preparation") != {
        "explicit_separate_operation_before_collection": True,
        "accepts_run_role_token_or_recovery_secret": False,
        "pip_require_hashes": True,
        "binary_wheels_only": True,
        "network_may_be_used_during_preparation": True,
        "staging_directory_then_atomic_publish": True,
        "failed_preparation_publishes_ready_runtime": False,
    }:
        errors.append("contract.preparation")
    if value.get("launch") != {
        "public_arguments": ["run_id", "role_slot", "envelope_path", "port"],
        "full_attestation_audit_precedes_secret_prompt": True,
        "executes_unchanged_m57_6_serve_recoverable": True,
        "downloads_installs_or_repairs_at_collection_time": False,
        "accepts_role_token_or_recovery_secret_argument": False,
        "role_token_or_recovery_secret_in_environment": False,
        "removes_pythonpath_pythonhome_and_user_site_injection": True,
    }:
        errors.append("contract.launch")
    if value.get("preserved_boundaries") != {
        "m57_4_m57_5_or_m57_6_semantics_changed": False,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "production_memory_write": False,
        "external_deployment": False,
        "synthetic_fixture_may_become_formal": False,
        "m58_authorized": False,
    }:
        errors.append("contract.preserved_boundaries")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(value),
        "binding_count": len(value.get("frozen_dependencies", {})),
    }


def validate_requirements_lock() -> dict[str, Any]:
    contract = load_contract()
    text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    errors: list[str] = []
    if "--only-binary=:all:" not in text:
        errors.append("requirements.binary_only")
    for name, details in contract["locked_distributions"].items():
        if f"{name}=={details['version']}" not in text:
            errors.append(f"requirements.version:{name}")
        if f"--hash=sha256:{details['wheel_sha256']}" not in text:
            errors.append(f"requirements.hash:{name}")
    if text.count("--hash=sha256:") != 3:
        errors.append("requirements.hash_count")
    expected_hash = contract["frozen_dependencies"]["configs/m57_7_participant_runtime_requirements.txt"]
    actual_hash = sha256_file(REQUIREMENTS_PATH)
    if actual_hash != expected_hash:
        errors.append("requirements.file_hash")
    return {"valid": not errors, "errors": errors, "requirements_hash": actual_hash, "locked_count": 3}


def _minimal_runtime_environment() -> dict[str, str]:
    environment = {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for key in ("HOME", "LC_ALL", "TERM", "TMPDIR"):
        if os.environ.get(key):
            environment[key] = os.environ[key]
    return environment


def audit_base_interpreter() -> dict[str, Any]:
    contract = load_contract()
    accepted = contract["base_interpreter"]
    executable = Path(accepted["executable"])
    report: dict[str, Any] = {
        "available": False,
        "executable": str(executable),
        "python_version": None,
        "executable_sha256": None,
        "system": None,
        "machine": None,
        "macos_version": None,
        "errors": [],
    }
    if not executable.is_file():
        report["errors"].append("base.missing")
        return report
    report["executable_sha256"] = sha256_file(executable)
    code = (
        "import json,platform;"
        "print(json.dumps({'python_version':platform.python_version(),"
        "'system':platform.system(),'machine':platform.machine(),'macos_version':platform.mac_ver()[0]}))"
    )
    done = subprocess.run(
        [str(executable), "-I", "-c", code], capture_output=True, text=True,
        timeout=30, env=_minimal_runtime_environment(), check=False,
    )
    if done.returncode != 0:
        report["errors"].append("base.probe_failed")
        return report
    try:
        observed = json.loads(done.stdout)
    except json.JSONDecodeError:
        report["errors"].append("base.probe_invalid_json")
        return report
    for key in ("python_version", "system", "machine", "macos_version"):
        report[key] = observed.get(key)
    if report["python_version"] != accepted["exact_python_version"]:
        report["errors"].append("base.python_version")
    if report["executable_sha256"] != accepted["executable_sha256"]:
        report["errors"].append("base.executable_hash")
    platform_lock = contract["accepted_platform"]
    if report["system"] != platform_lock["system"]:
        report["errors"].append("base.system")
    if report["machine"] != platform_lock["machine"]:
        report["errors"].append("base.machine")
    try:
        macos_major = int(str(report["macos_version"]).split(".", 1)[0])
    except (TypeError, ValueError):
        macos_major = -1
    if macos_major != platform_lock["macos_major"]:
        report["errors"].append("base.macos_major")
    report["available"] = not report["errors"]
    return report


def _run_child_audit(runtime_python: Path) -> dict[str, Any]:
    if not runtime_python.is_file() or runtime_python.is_symlink():
        raise RuntimeError("M57.7 runtime Python must be a copied regular file")
    done = subprocess.run(
        [str(runtime_python), "-I", "-c", CHILD_AUDIT], capture_output=True, text=True,
        timeout=60, env=_minimal_runtime_environment(), check=False,
    )
    if done.returncode != 0:
        raise RuntimeError("M57.7 isolated runtime audit failed")
    try:
        value = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("M57.7 isolated runtime audit returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("M57.7 isolated runtime audit returned invalid payload")
    return value


def _runtime_report_errors(report: dict[str, Any]) -> list[str]:
    contract = load_contract()
    errors: list[str] = []
    base = contract["base_interpreter"]
    platform_lock = contract["accepted_platform"]
    if report.get("python_version") != base["exact_python_version"]:
        errors.append("runtime.python_version")
    if report.get("python_executable_sha256") != base["executable_sha256"]:
        errors.append("runtime.python_executable_hash")
    if report.get("system") != platform_lock["system"]:
        errors.append("runtime.system")
    if report.get("machine") != platform_lock["machine"]:
        errors.append("runtime.machine")
    try:
        observed_major = int(str(report.get("macos_version", "")).split(".", 1)[0])
    except ValueError:
        observed_major = -1
    if observed_major != platform_lock["macos_major"]:
        errors.append("runtime.macos_major")
    if report.get("isolated_user_site_disabled") is not True:
        errors.append("runtime.user_site")
    expected_versions = {name: item["version"] for name, item in contract["locked_distributions"].items()}
    if report.get("distributions") != expected_versions:
        errors.append("runtime.distributions")
    expected_binaries = {
        item["critical_binary"]: item["critical_binary_sha256"]
        for item in contract["locked_distributions"].values()
        if item["critical_binary"] is not None
    }
    if report.get("critical_binary_sha256") != expected_binaries:
        errors.append("runtime.critical_binaries")
    if report.get("scrypt_aesgcm_smoke") is not True:
        errors.append("runtime.crypto_smoke")
    return errors


def _runtime_relative(runtime_root: Path) -> str:
    return runtime_root.resolve(strict=False).relative_to(ROOT.resolve()).as_posix()


def _validate_runtime_location(runtime_root: Path, *, allow_test_root: bool = False) -> list[str]:
    errors: list[str] = []
    resolved = runtime_root.resolve(strict=False)
    allowed_parent = (ROOT / ".venv").resolve(strict=False)
    try:
        resolved.relative_to(allowed_parent)
    except ValueError:
        errors.append("runtime.path_outside_project_venv")
    if not allow_test_root and resolved != DEFAULT_RUNTIME_ROOT.resolve(strict=False):
        errors.append("runtime.path_not_frozen_default")
    if runtime_root.exists() and runtime_root.is_symlink():
        errors.append("runtime.root_symlink")
    return errors


def _attestation_payload(
    runtime_root: Path,
    base_report: dict[str, Any],
    runtime_report: dict[str, Any],
    *,
    package_source: str,
    preparation_seconds: float,
) -> dict[str, Any]:
    contract = load_contract()
    value: dict[str, Any] = {
        "schema": "uruha_m57_7_project_runtime_attestation_v1",
        "version": "1.0.0",
        "status": "prepared_before_participant_collection",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_relative_root": _runtime_relative(runtime_root),
        "contract_hash": digest(contract),
        "requirements_hash": sha256_file(REQUIREMENTS_PATH),
        "base_interpreter": base_report,
        "runtime_report": runtime_report,
        "frozen_dependency_hashes": {
            relative: sha256_file(ROOT / relative) for relative in contract["frozen_dependencies"]
        },
        "preparation": {
            "separate_from_collection": True,
            "package_source": package_source,
            "require_hashes": True,
            "binary_only": True,
            "preparation_seconds": preparation_seconds,
            "run_role_token_or_secret_inputs": 0,
        },
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "real_participant_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    value["attestation_hash"] = digest(value)
    return value


def _attestation_errors(
    value: dict[str, Any],
    runtime_root: Path,
    base_report: dict[str, Any],
    runtime_report: dict[str, Any],
) -> list[str]:
    contract = load_contract()
    errors: list[str] = []
    if value.get("schema") != "uruha_m57_7_project_runtime_attestation_v1":
        errors.append("attestation.schema")
    if value.get("version") != "1.0.0" or value.get("status") != "prepared_before_participant_collection":
        errors.append("attestation.version_or_status")
    if value.get("runtime_relative_root") != _runtime_relative(runtime_root):
        errors.append("attestation.runtime_root")
    if value.get("contract_hash") != digest(contract):
        errors.append("attestation.contract_hash")
    if value.get("requirements_hash") != sha256_file(REQUIREMENTS_PATH):
        errors.append("attestation.requirements_hash")
    if value.get("base_interpreter") != base_report:
        errors.append("attestation.base_interpreter")
    if value.get("runtime_report") != runtime_report:
        errors.append("attestation.runtime_report")
    expected_frozen = {relative: sha256_file(ROOT / relative) for relative in contract["frozen_dependencies"]}
    if value.get("frozen_dependency_hashes") != expected_frozen:
        errors.append("attestation.frozen_dependencies")
    preparation = value.get("preparation", {})
    if preparation.get("separate_from_collection") is not True:
        errors.append("attestation.preparation_boundary")
    if preparation.get("require_hashes") is not True or preparation.get("binary_only") is not True:
        errors.append("attestation.package_lock")
    if preparation.get("run_role_token_or_secret_inputs") != 0:
        errors.append("attestation.secret_inputs")
    for key, expected in {
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "real_participant_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }.items():
        if value.get(key) != expected:
            errors.append(f"attestation.{key}")
    if value.get("attestation_hash") != digest(_hashless(value, "attestation_hash")):
        errors.append("attestation.hash")
    return errors


def audit_runtime(runtime_root: Path = DEFAULT_RUNTIME_ROOT, *, allow_test_root: bool = False) -> dict[str, Any]:
    errors = list(_validate_runtime_location(runtime_root, allow_test_root=allow_test_root))
    contract_report = validate_contract()
    requirements_report = validate_requirements_lock()
    if not contract_report["valid"]:
        errors.extend(contract_report["errors"])
    if not requirements_report["valid"]:
        errors.extend(requirements_report["errors"])
    base_report = audit_base_interpreter()
    if not base_report["available"]:
        errors.extend(base_report["errors"])
    attestation_path = runtime_root / ATTESTATION_NAME
    runtime_python = runtime_root / "bin" / "python"
    if not runtime_root.is_dir():
        errors.append("runtime.missing")
    elif _mode_bits(runtime_root) != 0o700:
        errors.append("runtime.mode")
    if not attestation_path.is_file():
        errors.append("attestation.missing")
    elif _mode_bits(attestation_path) != 0o600:
        errors.append("attestation.mode")
    runtime_report: dict[str, Any] | None = None
    if runtime_python.is_file():
        try:
            runtime_report = _run_child_audit(runtime_python)
            errors.extend(_runtime_report_errors(runtime_report))
        except RuntimeError as exc:
            errors.append(str(exc))
    else:
        errors.append("runtime.python_missing")
    attestation: dict[str, Any] | None = None
    if attestation_path.is_file():
        try:
            attestation = load_json(attestation_path)
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("attestation.invalid_json")
    if attestation is not None and runtime_report is not None:
        errors.extend(_attestation_errors(attestation, runtime_root, base_report, runtime_report))
    return {
        "ready": not errors,
        "errors": sorted(set(errors)),
        "runtime_relative_root": _runtime_relative(runtime_root) if not _validate_runtime_location(runtime_root, allow_test_root=True) else None,
        "contract_hash": contract_report["contract_hash"],
        "requirements_hash": requirements_report["requirements_hash"],
        "base_interpreter": base_report,
        "runtime_report": runtime_report,
        "attestation_hash": attestation.get("attestation_hash") if attestation else None,
        "collection_time_download_install_calls": 0,
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "real_participant_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }


def prepare_runtime(
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    *,
    package_source: Path | None = None,
    allow_test_root: bool = False,
) -> dict[str, Any]:
    location_errors = _validate_runtime_location(runtime_root, allow_test_root=allow_test_root)
    if location_errors:
        raise PermissionError("invalid M57.7 runtime location: " + "; ".join(location_errors))
    contract_report = validate_contract()
    requirements_report = validate_requirements_lock()
    base_report = audit_base_interpreter()
    if not contract_report["valid"]:
        raise PermissionError("invalid M57.7 contract: " + "; ".join(contract_report["errors"]))
    if not requirements_report["valid"]:
        raise PermissionError("invalid M57.7 requirements lock: " + "; ".join(requirements_report["errors"]))
    if not base_report["available"]:
        raise RuntimeError("M57.7 base interpreter drift: " + "; ".join(base_report["errors"]))
    if runtime_root.exists():
        raise FileExistsError("M57.7 runtime already exists; automatic overwrite or repair is forbidden")
    runtime_root.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(runtime_root.parent, 0o700)
    staging = Path(tempfile.mkdtemp(prefix=".m57_7_stage_", dir=runtime_root.parent))
    started = time.perf_counter()
    published = False
    try:
        base_python = load_contract()["base_interpreter"]["executable"]
        created = subprocess.run(
            [base_python, "-m", "venv", "--copies", str(staging)],
            capture_output=True, text=True, timeout=180, check=False,
        )
        if created.returncode != 0:
            raise RuntimeError("M57.7 copied venv creation failed")
        runtime_python = staging / "bin" / "python"
        install_command = [
            str(runtime_python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
            "--require-hashes", "-r", str(REQUIREMENTS_PATH),
        ]
        package_source_label = "hash_locked_package_index"
        if package_source is not None:
            install_command[6:6] = ["--no-index", "--find-links", str(package_source)]
            package_source_label = "hash_locked_local_wheel_fixture"
        installed = subprocess.run(
            install_command, capture_output=True, text=True, timeout=300, check=False,
        )
        if installed.returncode != 0:
            raise RuntimeError("M57.7 hash-locked runtime dependency installation failed")
        runtime_report = _run_child_audit(runtime_python)
        runtime_errors = _runtime_report_errors(runtime_report)
        if runtime_errors:
            raise RuntimeError("M57.7 prepared runtime audit failed: " + "; ".join(runtime_errors))
        elapsed = time.perf_counter() - started
        attestation = _attestation_payload(
            runtime_root, base_report, runtime_report,
            package_source=package_source_label, preparation_seconds=elapsed,
        )
        atomic_write_json(staging / ATTESTATION_NAME, attestation, 0o600)
        os.chmod(staging, 0o700)
        _fsync_directory(staging)
        if runtime_root.exists():
            raise FileExistsError("M57.7 runtime appeared during preparation; refusing overwrite")
        os.rename(staging, runtime_root)
        published = True
        _fsync_directory(runtime_root.parent)
        final = audit_runtime(runtime_root, allow_test_root=allow_test_root)
        if not final["ready"]:
            raise RuntimeError("M57.7 published runtime failed final attestation")
        return {
            "prepared": True,
            "runtime_relative_root": final["runtime_relative_root"],
            "preparation_seconds": elapsed,
            "package_source": package_source_label,
            "locked_distribution_count": 3,
            "attestation_hash": final["attestation_hash"],
            "runtime_ready": True,
            "run_role_token_or_secret_inputs": 0,
            "target_outcome_access_count": 0,
            "model_call_count": 0,
            "real_participant_count": 0,
            "formal_evidence_created": False,
            "m58_authorized": False,
        }
    finally:
        if not published and staging.exists():
            shutil.rmtree(staging)


def build_launch_spec(
    run_id: str,
    role_slot: str,
    envelope_path: str | Path,
    port: int,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    *,
    allow_test_root: bool = False,
) -> dict[str, Any]:
    if not isinstance(port, int) or isinstance(port, bool) or not (0 <= port <= 65535):
        raise ValueError("M57.7 port must be between 0 and 65535")
    audit = audit_runtime(runtime_root, allow_test_root=allow_test_root)
    if not audit["ready"]:
        raise PermissionError("M57.7 runtime attestation failed: " + "; ".join(audit["errors"]))
    runtime_python = runtime_root / "bin" / "python"
    command = [
        str(runtime_python), "-E", "-s", str(ROOT / "m57_6_crash_recoverable_participant_capability.py"),
        "--serve-recoverable", run_id, role_slot, str(Path(envelope_path)), str(port),
    ]
    environment = _minimal_runtime_environment()
    return {
        "executable": str(runtime_python),
        "argv": command,
        "environment": environment,
        "audit": audit,
        "downloads_installs_or_repairs": 0,
        "role_token_or_recovery_secret_arguments": 0,
    }


def launch_runtime(run_id: str, role_slot: str, envelope_path: str | Path, port: int) -> None:
    spec = build_launch_spec(run_id, role_slot, envelope_path, port)
    os.execve(spec["executable"], spec["argv"], spec["environment"])


def _directory_bytes(path: Path) -> int:
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def build_engineering_rehearsal() -> dict[str, Any]:
    audit = audit_runtime()
    if not audit["ready"]:
        raise PermissionError("M57.7 default runtime is not ready: " + "; ".join(audit["errors"]))
    spec = build_launch_spec(
        "forged-runner-no-human", "coder_a",
        ROOT / "analysis" / "local_m57_4_component_collection" / "forged-runner-no-human" / "capabilities" / "coder_a" / "role_envelope.json",
        7932,
    )
    serialized_surface = canonical_json({"argv": spec["argv"], "environment": spec["environment"]})
    drifted = dict(audit["runtime_report"] or {})
    drifted_binaries = dict(drifted.get("critical_binary_sha256", {}))
    drifted_binaries["cryptography/hazmat/bindings/_rust.abi3.so"] = "0" * 64
    drifted["critical_binary_sha256"] = drifted_binaries
    value: dict[str, Any] = {
        "schema": "uruha_m57_7_auditable_participant_runtime_launcher_rehearsal_v1",
        "version": "1.0.0",
        "status": "author_constructed_runtime_mechanics_only_not_formal_evidence",
        "runtime": {
            "ready": audit["ready"],
            "runtime_relative_root": audit["runtime_relative_root"],
            "python_version": audit["runtime_report"]["python_version"],
            "cryptography_version": audit["runtime_report"]["distributions"]["cryptography"],
            "attestation_hash": audit["attestation_hash"],
            "runtime_bytes": _directory_bytes(DEFAULT_RUNTIME_ROOT),
            "codex_runtime_required_at_collection": False,
        },
        "launch": {
            "audit_ready_before_exec": spec["audit"]["ready"],
            "argv_count": len(spec["argv"]),
            "downloads_installs_or_repairs": spec["downloads_installs_or_repairs"],
            "role_token_or_recovery_secret_arguments": spec["role_token_or_recovery_secret_arguments"],
            "pythonpath_present": "PYTHONPATH" in spec["environment"],
            "pythonhome_present": "PYTHONHOME" in spec["environment"],
            "synthetic_secret_marker_occurrences": serialized_surface.count("m57.7 synthetic secret marker"),
            "synthetic_role_token_marker_occurrences": serialized_surface.count("m57.7 synthetic role token marker"),
            "unchanged_m57_6_entrypoint": spec["argv"][3].endswith("m57_6_crash_recoverable_participant_capability.py"),
            "unchanged_m57_6_action": spec["argv"][4] == "--serve-recoverable",
        },
        "negative_paths": {
            "critical_binary_drift_errors": _runtime_report_errors(drifted),
            "missing_runtime_ready": audit_runtime(ROOT / ".venv" / "m57_7_missing_runtime", allow_test_root=True)["ready"],
            "existing_runtime_auto_repair_allowed": False,
        },
        "frozen_m57_6_implementation_hash": sha256_file(ROOT / "m57_6_crash_recoverable_participant_capability.py"),
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "real_participant_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }
    value["rehearsal_hash"] = digest(value)
    return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != "uruha_m57_7_auditable_participant_runtime_launcher_rehearsal_v1":
        errors.append("rehearsal.schema")
    expected = {
        ("runtime", "ready"): True,
        ("runtime", "codex_runtime_required_at_collection"): False,
        ("launch", "audit_ready_before_exec"): True,
        ("launch", "downloads_installs_or_repairs"): 0,
        ("launch", "role_token_or_recovery_secret_arguments"): 0,
        ("launch", "pythonpath_present"): False,
        ("launch", "pythonhome_present"): False,
        ("launch", "synthetic_secret_marker_occurrences"): 0,
        ("launch", "synthetic_role_token_marker_occurrences"): 0,
        ("launch", "unchanged_m57_6_entrypoint"): True,
        ("launch", "unchanged_m57_6_action"): True,
        ("negative_paths", "missing_runtime_ready"): False,
        ("negative_paths", "existing_runtime_auto_repair_allowed"): False,
    }
    for keys, expected_value in expected.items():
        current: Any = value
        for key in keys:
            current = current.get(key) if isinstance(current, dict) else None
        if current != expected_value:
            errors.append("rehearsal." + ".".join(keys))
    if "runtime.critical_binaries" not in value.get("negative_paths", {}).get("critical_binary_drift_errors", []):
        errors.append("rehearsal.negative_paths.critical_binary_drift")
    if not isinstance(value.get("runtime", {}).get("runtime_bytes"), int) or value["runtime"]["runtime_bytes"] <= 0:
        errors.append("rehearsal.runtime.bytes")
    if value.get("frozen_m57_6_implementation_hash") != load_contract()["frozen_dependencies"]["m57_6_crash_recoverable_participant_capability.py"]:
        errors.append("rehearsal.m57_6_hash")
    for key, expected_value in {
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "real_participant_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }.items():
        if value.get(key) != expected_value:
            errors.append(f"rehearsal.{key}")
    if value.get("rehearsal_hash") != digest(_hashless(value, "rehearsal_hash")):
        errors.append("rehearsal.hash")
    return {"valid": not errors, "errors": errors}


def load_saved_rehearsal(path: Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise PermissionError("invalid saved M57.7 rehearsal: " + "; ".join(report["errors"]))
    return value


def build_live_audit() -> dict[str, Any]:
    upstream = load_json(M57_6_AUDIT_PATH)
    runtime = audit_runtime()
    return {
        "schema": "uruha_m57_7_participant_runtime_live_audit_v1",
        "version": "1.0.0",
        "status": "live_external_evidence_unchanged_after_m57_7_engineering",
        "project_runtime_ready": runtime["ready"],
        "project_runtime_attestation_hash": runtime["attestation_hash"],
        "collection_time_download_install_calls": runtime["collection_time_download_install_calls"],
        "v7_actual_qualified_coder_slots": upstream["v7_actual_qualified_coder_slots"],
        "v7_required_coder_slots": upstream["v7_required_coder_slots"],
        "v7_actual_qualified_evaluator_slots": upstream["v7_actual_qualified_evaluator_slots"],
        "v7_required_evaluator_slots": upstream["v7_required_evaluator_slots"],
        "real_temporal_rows_available": upstream["real_temporal_rows_available"],
        "real_temporal_rows_required": upstream["real_temporal_rows_required"],
        "real_component_rows_available": upstream["real_component_rows_available"],
        "real_component_rows_required": upstream["real_component_rows_required"],
        "real_participant_runtime_launches": 0,
        "formal_m56_results": upstream["formal_m56_results"],
        "formal_m57_results": upstream["formal_m57_results"],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "m58_authorized": False,
        "boundary": "M57.7 runtime preparation and launch attestation create no humans, component labels, outcomes, model calls, formal M57 result or M58 authority.",
    }


def measure_fixture_cost(iterations: int = 7) -> dict[str, Any]:
    if iterations != 7:
        raise ValueError("M57.7 frozen fixture cost requires seven iterations")
    values: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        report = audit_runtime()
        if not report["ready"]:
            raise PermissionError("M57.7 cost audit found invalid runtime")
        values.append(time.perf_counter() - started)
    ordered = sorted(values)
    attestation = load_json(DEFAULT_RUNTIME_ROOT / ATTESTATION_NAME)
    return {
        "schema": "uruha_m57_7_participant_runtime_fixture_cost_v1",
        "version": "1.0.0",
        "status": "local_runtime_fixture_cost_not_human_model_or_production_cost",
        "iterations": iterations,
        "audit_seconds": values,
        "audit_seconds_min": ordered[0],
        "audit_seconds_median": ordered[len(ordered) // 2],
        "audit_seconds_max": ordered[-1],
        "one_time_preparation_seconds": attestation["preparation"]["preparation_seconds"],
        "one_time_locked_wheel_bytes": load_json(GAP_PATH)["locked_wheel_feasibility_probe"]["wheel_bytes_total"],
        "project_runtime_bytes": _directory_bytes(DEFAULT_RUNTIME_ROOT),
        "collection_time_download_install_calls": 0,
        "excludes": [
            "human labor and 90 real component entries", "model execution", "target outcomes",
            "energy", "offline wheel mirroring", "cross-platform packaging", "code signing and notarization",
            "TLS", "same-account adversarial testing", "production throughput",
        ],
        "target_outcome_access_count": 0,
        "model_call_count": 0,
        "real_participant_count": 0,
        "formal_evidence_created": False,
        "m58_authorized": False,
    }


def render_dashboard(
    rehearsal: dict[str, Any] | None = None,
    audit: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
) -> str:
    rehearsal = rehearsal or load_saved_rehearsal()
    audit = audit or (load_json(LIVE_AUDIT_PATH) if LIVE_AUDIT_PATH.exists() else build_live_audit())
    cost = cost or load_json(COST_PATH)
    runtime = rehearsal["runtime"]
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M57.7 Attested Runtime</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#08121e;color:#eff8ff;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}main{{max-width:1240px;margin:auto;padding:24px}}h1{{font-size:38px;margin:8px 0}}.sub{{color:#a9bfd6}}.status{{display:inline-block;background:#642e45;color:#ffe0eb;padding:8px 12px;border-radius:999px;font-weight:800}}.flow{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:22px 0}}.node,.card{{background:#12243a;border:1px solid #3c6083;border-radius:16px;padding:16px}}.node b{{display:block;color:#79e1bd;margin-bottom:8px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.metric{{font-size:29px;font-weight:850}}.ok{{color:#79e1bd}}.bad{{color:#ff9ab0}}.wide{{grid-column:span 2}}code{{color:#ffe590}}@media(max-width:900px){{.flow,.grid{{grid-template-columns:1fr}}.wide{{grid-column:auto}}}}</style></head><body><main>
<span class="status">REAL PARTICIPANT LAUNCHES {audit['real_participant_runtime_launches']} · FORMAL M57 DENIED</span><h1>M57.7 · 不再靠 Codex 內藏 Python 才能啟動</h1><p class="sub">單一變因：事前準備且可稽核的 project-local runtime。M57.4–M57.6 的證據與加密語意完全不變。</p>
<div class="flow"><div class="node"><b>1 · PREPARE</b>收集前獨立執行<br>不收 run/role/secret</div><div class="node"><b>2 · HASH LOCK</b>3 個 binary wheels<br>SHA-256 固定</div><div class="node"><b>3 · ATTEST</b>Python＋套件＋compiled binary<br>0600 commitment</div><div class="node"><b>4 · AUDIT</b>每次 launch 先重驗<br>drift 即拒絕</div><div class="node"><b>5 · HIDDEN PROMPT</b>通過後才交給 M57.6<br>secret 不進 argv/env</div><div class="node"><b>6 · COLLECT</b>原 M57.4 ledger<br>原 recovery 不變</div></div>
<section class="grid"><div class="card"><div class="metric ok">{str(runtime['ready']).upper()}</div><b>project runtime ready</b><p>Python {runtime['python_version']} · cryptography {runtime['cryptography_version']}</p></div><div class="card"><div class="metric ok">0</div><b>collection-time installs</b><p>真正啟動只 audit＋exec；不下載、不安裝、不修復。</p></div><div class="card"><div class="metric ok">0 / 0</div><b>secret surfaces</b><p>argv/env secret marker與role-token marker皆0。</p></div><div class="card"><div class="metric">{cost['audit_seconds_median']:.3f}s</div><b>median launch audit</b><p>七次本機attestation檢查中位數。</p></div><div class="card"><div class="metric">{runtime['runtime_bytes'] / 1048576:.1f} MiB</div><b>local runtime</b><p>一次準備；locked wheel下載約{cost['one_time_locked_wheel_bytes'] / 1048576:.1f} MiB。</p></div><div class="card"><div class="metric bad">{audit['real_component_rows_available']}/{audit['real_component_rows_required']}</div><b>real component rows</b><p>runtime完成不會自動產生真人標註。</p></div><div class="card wide"><h2>能主張</h2><p>在這台macOS 15 arm64與凍結Python上，repo可事前建立自己的hash-locked runtime；正式收集每次先驗證，drift在hidden secret輸入前拒絕，且不再依賴Codex runtime。</p></div><div class="card"><h2>不能主張</h2><p>不是離線／跨平台套件、供應鏈稽核、簽章、公證、身份證明、真人evidence、Equation V1或M58授權。</p></div></section>
</main></body></html>"""


def serve_dashboard(port: int) -> None:
    payload = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if urllib.parse.urlparse(self.path).path != "/dashboard":
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare", action="store_true")
    actions.add_argument("--audit", action="store_true")
    actions.add_argument("--write-rehearsal", action="store_true")
    actions.add_argument("--write-live-audit", action="store_true")
    actions.add_argument("--measure-cost", action="store_true")
    actions.add_argument("--dashboard", type=int, metavar="PORT")
    actions.add_argument("--launch", nargs=4, metavar=("RUN_ID", "ROLE", "ENVELOPE_PATH", "PORT"))
    args = parser.parse_args()
    if args.prepare:
        print(json.dumps(prepare_runtime(), ensure_ascii=False, indent=2))
    elif args.audit:
        report = audit_runtime()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report["ready"]:
            raise SystemExit(1)
    elif args.write_rehearsal:
        value = build_engineering_rehearsal()
        atomic_write_json(RESULT_PATH, value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.write_live_audit:
        value = build_live_audit()
        atomic_write_json(LIVE_AUDIT_PATH, value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.measure_cost:
        value = measure_fixture_cost()
        atomic_write_json(COST_PATH, value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.dashboard is not None:
        serve_dashboard(args.dashboard)
    else:
        run_id, role_slot, envelope_path, port_text = args.launch
        if not re.fullmatch(r"\d{1,5}", port_text) or not (0 <= int(port_text) <= 65535):
            parser.error("PORT must be between 0 and 65535")
        launch_runtime(run_id, role_slot, envelope_path, int(port_text))


if __name__ == "__main__":
    main()
