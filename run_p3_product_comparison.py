#!/usr/bin/env python3
"""CLI for the bounded P3-A comparison contract.

`contract` uses deterministic fake transports only.  `preflight` performs
read-only local readiness checks.  `run` remains fail-closed until separately
hashed implementation, data, and review releases exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from p3_product_comparison import (
    CONDITIONS,
    CaseWorkspaceRegistry,
    FakeExactTokenCounter,
    FakeTransport,
    MANIFEST_SCHEMA,
    P3ContractError,
    build_balanced_condition_schedule,
    build_generation_view,
    build_smoke_generation_view,
    canonical_sha256,
    freeze_common_source,
    load_design,
    load_developer_smoke_manifests,
    run_condition,
    validate_common_views,
    validate_run_manifest,
    write_new_json,
)


def _fixture_source() -> tuple[list[dict[str, str]], dict[str, str]]:
    # Wiring-only synthetic data.  It is not a P3 smoke/confirmation case and
    # deliberately contains no gold answer or expected winning condition.
    prefix = [
        {
            "turn_id": "s1-u1",
            "session_id": "session-1",
            "role": "user",
            "content": "最近、答えを急がないでほしい。",
        },
        {
            "turn_id": "s1-a1",
            "session_id": "session-1",
            "role": "assistant",
            "content": "分かった。急かさないよ。",
        },
        {
            "turn_id": "s2-u1",
            "session_id": "session-2",
            "role": "user",
            "content": "前の話はまだ考えてる。",
        },
        {
            "turn_id": "s2-a1",
            "session_id": "session-2",
            "role": "assistant",
            "content": "うん、決まってからでいい。",
        },
    ]
    current = {
        "turn_id": "s2-u2",
        "session_id": "session-2",
        "content": "まだ決められない。",
    }
    return prefix, current


def build_contract_manifest(design_path: str | Path) -> dict[str, Any]:
    design = load_design(design_path)
    prefix, current = _fixture_source()
    commitment = freeze_common_source(prefix, current)
    views = {
        condition: build_generation_view(prefix, current, condition)
        for condition in CONDITIONS
    }
    validate_common_views(views, commitment)
    token_counter = FakeExactTokenCounter()
    transport = FakeTransport()
    registry = CaseWorkspaceRegistry()

    with tempfile.TemporaryDirectory(prefix="uruha-p3a-") as temporary:
        root = Path(temporary)
        state_path = root / "case-fixture" / "state"
        registry.claim("case-fixture", state_path)

        def fake_product_worker(**kwargs: Any) -> Mapping[str, Any]:
            worker_design = kwargs["design"]
            final = kwargs["execute"](
                "product",
                "Use the injected product worker contract and return only the final reply.",
                [],
                min(256, worker_design["budget"]["system_per_call_completion_max"]),
            )
            return {
                "final": final,
                "private_scratch_count": 0,
                "evidence": {
                    "worker_kind": "deterministic_fake_product_worker",
                    "case_state_isolated": True,
                    "product_imported": False,
                    "database_opened": False,
                },
            }

        order = build_balanced_condition_schedule(
            ["case-fixture"], design["model"]["seed"]
        )["case-fixture"]
        results: dict[str, Any] = {}
        for condition in order:
            ticks = iter([0.0, 0.005])
            results[condition] = run_condition(
                condition=condition,
                view=views[condition],
                design=design,
                transport=transport,
                checkpoint_root=root / "checkpoints",
                item_id="case-fixture-turn-1",
                token_counter=token_counter,
                product_worker=fake_product_worker if condition == "product_system" else None,
                clock=lambda ticks=ticks: next(ticks),
            )

        reuse_transport = FakeTransport()
        reuse_ticks = iter([0.0, 0.005])
        reused = run_condition(
            condition="full_history_direct",
            view=views["full_history_direct"],
            design=design,
            transport=reuse_transport,
            checkpoint_root=root / "checkpoints",
            item_id="case-fixture-turn-1",
            token_counter=token_counter,
            clock=lambda: next(reuse_ticks),
        )

    calls = [call for result in results.values() for call in result["calls"]]
    implementation_files = [
        Path(__file__).resolve().parent / "p3_product_comparison.py",
        Path(__file__).resolve(),
        Path(__file__).resolve().parent / "test_p3_product_comparison.py",
    ]
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "phase": "P3-A",
        "status": "contract_pass",
        "evidence_scope": "offline_fake_contract_only",
        "design_sha256": design["_design_sha256"],
        "implementation_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in implementation_files
        },
        "persona_contract_sha256": canonical_sha256(
            design["persona"]["shared_contract"]
        ),
        "source_commitment": commitment,
        "condition_schedule": order,
        "results": results,
        "fake_transport_attempts": transport.attempts,
        "network_calls": sum(call["network_calls"] for call in calls),
        "real_model_calls": sum(call["real_model_calls"] for call in calls),
        "paid_calls": 0,
        "token_evidence_kind": token_counter.evidence_kind,
        "contract_checks": {
            "allowlisted_common_source_equal": True,
            "all_prior_sessions_retained": commitment["session_ids"]
            == ["session-1", "session-2"],
            "three_conditions_executed": set(results) == set(CONDITIONS),
            "private_scratch_not_visible": all(
                result["private_scratch_written_to_visible_history"] is False
                for result in results.values()
            ),
            "case_state_isolated": results["product_system"]["worker_evidence"][
                "case_state_isolated"
            ],
            "completed_checkpoint_reused_without_transport": (
                reused["final"]["reused"] is True and reuse_transport.attempts == 0
            ),
            "zero_network_calls": all(call["network_calls"] == 0 for call in calls),
            "zero_real_model_calls": all(
                call["real_model_calls"] == 0 for call in calls
            ),
        },
        "claim_boundary": (
            "This proves P3-A wiring and fail-closed contracts only; it is not "
            "model-generation, product-quality, human-preference, or superiority evidence."
        ),
    }
    validate_run_manifest(manifest)
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def build_preflight(design_path: str | Path) -> dict[str, Any]:
    design = load_design(design_path)
    repo = Path(__file__).resolve().parent
    product_entry = repo / design["product_entry"]
    accounting = repo / design["accounting_freeze"]
    ollama = shutil.which("ollama")
    model_metadata: dict[str, Any] = {
        "command_available": ollama is not None,
        "model": design["model"]["generation_model"],
        "metadata_read": False,
        "digest": None,
    }
    if ollama:
        try:
            completed = subprocess.run(
                [ollama, "show", design["model"]["generation_model"], "--modelfile"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if completed.returncode == 0:
                from_line = next(
                    (line for line in completed.stdout.splitlines() if line.startswith("FROM ")),
                    "",
                )
                digest = from_line.rsplit("sha256-", 1)[-1] if "sha256-" in from_line else None
                model_metadata.update(
                    {
                        "metadata_read": True,
                        "digest": digest,
                        "template_present": "TEMPLATE " in completed.stdout,
                        "template_sha256": canonical_sha256(completed.stdout),
                    }
                )
            else:
                model_metadata["error"] = "ollama_show_failed"
        except (OSError, subprocess.TimeoutExpired):
            model_metadata["error"] = "ollama_metadata_unavailable"
    checks = {
        "design_valid": True,
        "product_entry_exists": product_entry.is_file(),
        "accounting_freeze_exists": accounting.is_file(),
        "ollama_command_available": model_metadata["command_available"],
        "model_metadata_read": model_metadata["metadata_read"],
        # P3 requires a tokenizer/template binding proven against provider usage.
        # The adapter is deliberately not released in P3-A.
        "verified_tokenizer_template_binding": False,
        "implementation_release_present": False,
        "data_freeze_present": False,
        "review_release_present": False,
    }
    return {
        "schema": "uruha_p3_preflight_v1",
        "phase": "P3-A",
        "status": "not_ready_for_real_generation",
        "python": platform.python_version(),
        "design_sha256": design["_design_sha256"],
        "paths": {
            "product_entry": str(product_entry),
            "accounting_freeze": str(accounting),
        },
        "model_metadata": model_metadata,
        "checks": checks,
        "network_calls": 0,
        "real_model_calls": 0,
        "transport_attempts": 0,
    }


def build_run_refusal(design_path: str | Path, args: argparse.Namespace) -> dict[str, Any]:
    design = load_design(design_path)
    artifacts = {
        "implementation_release": args.implementation_release,
        "data_freeze": args.data_freeze,
        "review_release": args.review_release,
    }
    reasons = []
    for name, raw_path in artifacts.items():
        if not raw_path or not Path(raw_path).is_file():
            reasons.append(f"{name}_missing")
    # Even if arbitrary paths are supplied, P3-A itself never grants generation.
    if design["implementation_release"]["real_generation_authorized"] is not False:
        reasons.append("p3a_design_authorization_invalid")
    reasons.append("p3a_implementation_not_review_released")
    return {
        "schema": "uruha_p3_run_refusal_v1",
        "phase": "P3-A",
        "status": "refused_before_transport",
        "design_sha256": design["_design_sha256"],
        "reasons": sorted(set(reasons)),
        "artifact_paths": artifacts,
        "transport_attempts": 0,
        "network_calls": 0,
        "real_model_calls": 0,
        "paid_calls": 0,
    }


def _read_worker_output(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("invalid_product_worker_output", path.name) from exc
    if not isinstance(value, dict):
        raise P3ContractError("invalid_product_worker_output", path.name)
    return value


def build_product_worker_preflight(
    design_path: str | Path,
    product_python: str | Path | None = None,
) -> dict[str, Any]:
    """Run the P3-B1 worker/import contract without any model generation."""

    design = load_design(design_path)
    repo = Path(__file__).resolve().parent
    worker = repo / "p3_product_worker.py"
    interpreter = Path(product_python or repo / ".venv/product_checks/bin/python")
    if not worker.is_file():
        raise P3ContractError("product_worker_missing")
    if not interpreter.is_file():
        raise P3ContractError("product_python_missing", str(interpreter))

    def invoke(
        mode: str,
        output: Path,
        *,
        workspace_root: Path | None = None,
        case_id: str | None = None,
        state_slot: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        command = [
            str(interpreter),
            str(worker),
            "--mode",
            mode,
            "--design",
            str(Path(design_path).resolve()),
            "--output",
            str(output),
        ]
        if workspace_root is not None:
            command.extend(["--workspace-root", str(workspace_root)])
        if case_id is not None:
            command.extend(["--case-id", case_id])
        if state_slot is not None:
            command.extend(["--state-slot", state_slot])
        completed = subprocess.run(
            command,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1"},
        )
        return completed.returncode, _read_worker_output(output)

    with tempfile.TemporaryDirectory(prefix="uruha-p3b1-") as temporary:
        temp_root = Path(temporary)
        workspace_root = temp_root / "worker-root"
        adapter_rc, adapter = invoke(
            "adapter-contract", temp_root / "adapter.json"
        )
        first_rc, first = invoke(
            "dry-run",
            temp_root / "dry-first.json",
            workspace_root=workspace_root,
            case_id="p3-b1-fixture",
            state_slot="restart-probe",
        )
        second_rc, second = invoke(
            "dry-run",
            temp_root / "dry-second.json",
            workspace_root=workspace_root,
            case_id="p3-b1-fixture",
            state_slot="restart-probe",
        )
        cross_rc, cross = invoke(
            "dry-run",
            temp_root / "dry-cross-case.json",
            workspace_root=workspace_root,
            case_id="p3-b1-other-case",
            state_slot="restart-probe",
        )
        checks = {
            "adapter_contract_passed": adapter_rc == 0
            and adapter.get("status") == "offline_transport_contract_pass",
            "openai_compatible_intercepted": bool(
                adapter.get("checks", {}).get("openai_compatible_intercepted")
            ),
            "native_ollama_intercepted": bool(
                adapter.get("checks", {}).get("native_ollama_intercepted")
            ),
            "first_isolated_import_passed": first_rc == 0
            and first.get("status") == "isolated_import_pass",
            "same_case_restart_passed": second_rc == 0
            and second.get("restart") is True
            and first.get("case_sha256") == second.get("case_sha256"),
            "same_case_state_path_retained": first.get("environment", {}).get(
                "state_paths_sha256"
            )
            == second.get("environment", {}).get("state_paths_sha256"),
            "cross_case_state_reuse_rejected": cross_rc != 0
            and cross.get("contract_code") == "cross_case_state_reuse",
            "product_brain_never_instantiated": first.get("brain_instances") == 0
            and second.get("brain_instances") == 0,
            "production_db_unreachable": bool(
                first.get("checks", {}).get("production_db_unreachable")
            )
            and bool(second.get("checks", {}).get("production_db_unreachable")),
            "no_generation_or_network": all(
                int(payload.get(key, 0)) == 0
                for payload in (adapter, first, second, cross)
                for key in (
                    "network_calls",
                    "real_model_calls",
                    "paid_calls",
                )
            ),
            "no_blocked_network_attempts": all(
                (
                    len(payload.get("network_attempts", []))
                    if isinstance(payload.get("network_attempts", []), list)
                    else int(payload.get("network_attempts", 0))
                )
                == 0
                for payload in (adapter, first, second, cross)
            ),
            "tokenizer_candidate_not_overclaimed": first.get(
                "tokenizer_candidate", {}
            ).get("provider_usage_equivalence_validated")
            is False,
        }
        result = {
            "schema": "uruha_p3_product_worker_preflight_v1",
            "phase": "P3-B1",
            "status": "p3_b1_contract_pass" if all(checks.values()) else "p3_b1_contract_failed",
            "design_sha256": design["_design_sha256"],
            "implementation_sha256": {
                worker.name: hashlib.sha256(worker.read_bytes()).hexdigest(),
                Path(__file__).name: hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            },
            "checks": checks,
            "adapter_contract": adapter,
            "first_import": first,
            "restart_import": second,
            "cross_case_refusal": cross,
            "network_calls": 0,
            "real_model_calls": 0,
            "paid_calls": 0,
            "formal_cases_accessed": 0,
            "claim_boundary": (
                "P3-B1 proves a zero-generation isolated product import and guarded fake "
                "transport seam. It does not prove provider token binding, product output "
                "quality, or comparative advantage."
            ),
        }
    result["ephemeral_workspace_removed_after_probe"] = not temp_root.exists()
    return result


def build_smoke_data_validation(
    design_path: str | Path,
    source_path: str | Path,
    annotation_path: str | Path,
) -> dict[str, Any]:
    """Validate all P3-B2 data and build all 72 zero-generation views."""

    design = load_design(design_path)
    loaded = load_developer_smoke_manifests(
        source_path,
        annotation_path,
        design,
    )
    view_digests: list[str] = []
    source_digests: list[str] = []
    input_digests: list[str] = []
    prefix_turn_counts: list[int] = []
    for case in loaded["source"]["cases"]:
        prior_system_replies: dict[str, str] = {}
        for turn_number, turn in enumerate(case["turns"], 1):
            views = {
                condition: build_smoke_generation_view(
                    case,
                    turn_number,
                    condition,
                    prior_system_replies,
                )
                for condition in CONDITIONS
            }
            commitment = freeze_common_source(
                views["product_system"]["visible_prefix"],
                views["product_system"]["current_input"],
            )
            validate_common_views(views, commitment)
            for view in views.values():
                view_digests.append(view["view_sha256"])
                source_digests.append(view["source_sha256"])
                input_digests.append(view["input_sha256"])
                prefix_turn_counts.append(len(view["visible_prefix"]))
                if set(view) != {
                    "schema",
                    "condition",
                    "visible_prefix",
                    "current_input",
                    "source_history_sha256",
                    "input_sha256",
                    "source_sha256",
                    "view_sha256",
                }:
                    raise P3ContractError("smoke_generation_view_allowlist_mismatch")
            prior_system_replies[turn["turn_id"]] = (
                f"P3-B2 source isolation fixture reply {turn_number}."
            )
    case_ids = [case["case_id"] for case in loaded["source"]["cases"]]
    schedule = build_balanced_condition_schedule(case_ids, design["model"]["seed"])
    position_counts = []
    for position in range(len(CONDITIONS)):
        counts = {condition: 0 for condition in CONDITIONS}
        for order in schedule.values():
            counts[order[position]] += 1
        position_counts.append(counts)
    summary = loaded["summary"]
    checks = {
        "six_cases": summary["case_count"] == 6,
        "twenty_four_user_turns": summary["turn_count"] == 24,
        "twelve_sessions": summary["session_count"] == 12,
        "one_case_per_family": set(summary["family_counts"].values()) == {1},
        "two_cases_per_language": set(summary["language_counts"].values()) == {2},
        "all_cases_have_verification_event": summary["verification_case_count"] == 6,
        "all_turn_hashes_unique": summary["content_hash_count"] == 24,
        "all_scenario_concepts_unique": summary["scenario_concept_count"] == 6,
        "seventy_two_views_built": len(view_digests) == 72
        and len(set(view_digests)) == 72,
        "three_conditions_share_each_source": all(
            len(set(source_digests[index : index + 3])) == 1
            for index in range(0, len(source_digests), 3)
        ),
        "three_conditions_share_each_input": all(
            len(set(input_digests[index : index + 3])) == 1
            for index in range(0, len(input_digests), 3)
        ),
        "system_anchored_prefix_shape": set(prefix_turn_counts) == {0, 2, 4, 6},
        "balanced_condition_order": all(
            set(counts.values()) == {2} for counts in position_counts
        ),
        "annotations_separate_from_source_hash": summary["source_sha256"]
        != summary["annotation_sha256"],
    }
    return {
        "schema": "uruha_p3_developer_smoke_data_validation_v1",
        "phase": "P3-B2",
        "status": "p3_b2_data_contract_pass" if all(checks.values()) else "p3_b2_data_contract_failed",
        "design_sha256": design["_design_sha256"],
        "source_manifest": {
            "path": str(Path(source_path)),
            "sha256": summary["source_sha256"],
        },
        "annotation_manifest": {
            "path": str(Path(annotation_path)),
            "sha256": summary["annotation_sha256"],
        },
        "summary": summary,
        "condition_schedule": schedule,
        "position_counts": position_counts,
        "generation_view_count": len(view_digests),
        "checks": checks,
        "network_calls": 0,
        "real_model_calls": 0,
        "paid_calls": 0,
        "formal_cases_accessed": 0,
        "claim_boundary": (
            "This validates developer-smoke provenance, quotas, annotation separation, "
            "and generation views only. It is not generated output, scoring, holdout, "
            "human preference, or product advantage evidence."
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "contract",
            "preflight",
            "product-dry-run",
            "smoke-data-validate",
            "run",
        ),
        required=True,
    )
    parser.add_argument("--design", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--implementation-release")
    parser.add_argument("--data-freeze")
    parser.add_argument("--review-release")
    parser.add_argument("--product-python")
    parser.add_argument("--smoke-source")
    parser.add_argument("--smoke-annotations")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        output = Path(args.output)
        if output.exists():
            raise P3ContractError("artifact_exists_no_overwrite", str(output))
        if args.mode == "contract":
            payload = build_contract_manifest(args.design)
            exit_code = 0
        elif args.mode == "preflight":
            payload = build_preflight(args.design)
            exit_code = 0
        elif args.mode == "product-dry-run":
            payload = build_product_worker_preflight(
                args.design,
                args.product_python,
            )
            exit_code = 0 if payload["status"] == "p3_b1_contract_pass" else 2
        elif args.mode == "smoke-data-validate":
            if not args.smoke_source or not args.smoke_annotations:
                raise P3ContractError("smoke_data_paths_required")
            payload = build_smoke_data_validation(
                args.design,
                args.smoke_source,
                args.smoke_annotations,
            )
            exit_code = 0 if payload["status"] == "p3_b2_data_contract_pass" else 2
        else:
            payload = build_run_refusal(args.design, args)
            exit_code = 2
        write_new_json(output, payload)
        print(json.dumps({"status": payload["status"], "output": str(output)}))
        return exit_code
    except P3ContractError as exc:
        print(json.dumps({"status": "error", "code": exc.code, "detail": exc.detail}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
