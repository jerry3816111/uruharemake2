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
    canonical_sha256,
    freeze_common_source,
    load_design,
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
            results[condition] = run_condition(
                condition=condition,
                view=views[condition],
                design=design,
                transport=transport,
                checkpoint_root=root / "checkpoints",
                item_id="case-fixture-turn-1",
                token_counter=token_counter,
                product_worker=fake_product_worker if condition == "product_system" else None,
            )

        reuse_transport = FakeTransport()
        reused = run_condition(
            condition="full_history_direct",
            view=views["full_history_direct"],
            design=design,
            transport=reuse_transport,
            checkpoint_root=root / "checkpoints",
            item_id="case-fixture-turn-1",
            token_counter=token_counter,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("contract", "preflight", "run"), required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--implementation-release")
    parser.add_argument("--data-freeze")
    parser.add_argument("--review-release")
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
