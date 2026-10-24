"""No-provider contracts for the frozen exact-input surface A diagnostic.

The live A trial is one new M21 generation total, followed by zero-provider
off/on replay of the same complete post-M21 boundary. These tests never send
the approved A source to a real provider or Safari.
"""

from __future__ import annotations

import hashlib
from functools import wraps
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import pytest

import p4_source_event_surface_exact_input_fresh_a as probe
from test_p4_source_event_surface_diagnostic_route import APPROVED_P1


_ISOLATED_CHILD_ENV = "P4_SOURCE_SURFACE_A_TEST_ISOLATED_CHILD"


def isolated_product_test(fn):
    """Contain process-global product overlay installation in this test file."""
    @wraps(fn)
    def run(*args, **kwargs):
        if os.getenv(_ISOLATED_CHILD_ENV) == "1":
            return fn(*args, **kwargs)
        env = dict(os.environ)
        env[_ISOLATED_CHILD_ENV] = "1"
        env.pop("PYTEST_CURRENT_TEST", None)
        env.pop("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", None)
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", f"{Path(__file__).name}::{fn.__name__}"],
            cwd=Path(__file__).parent,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

    return run


def test_frozen_a_source_is_the_only_preflight_source():
    source = probe._verify_frozen_sources()
    assert source == APPROVED_P1
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == (
        "6f2a1c58e7063fcbd245621bebf4b23559bc85f96617e10678d245010d3d4ac4"
    )


def test_cli_default_does_not_start_a_trial(monkeypatch):
    monkeypatch.setattr(probe, "_model_digest", lambda: (_ for _ in ()).throw(AssertionError("network")))
    with pytest.raises(SystemExit) as denied:
        probe.main([])
    assert denied.value.code == 2


def test_ambient_runtime_flag_and_preflight_request_drift_fail_closed(monkeypatch):
    monkeypatch.setenv("URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED", "1")
    with pytest.raises(RuntimeError, match="runner_ambient_uruha_configuration_not_isolated"):
        probe._require_clean_runner_ambient()
    monkeypatch.delenv("URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED")
    with pytest.raises(RuntimeError, match="fresh_m21_request_drift_from_fake_preflight"):
        probe._require_request_parity({"model": probe.MODEL}, {"request_sha256": "0" * 64})
    request = {"model": probe.MODEL}
    digest = probe._sha(probe._canonical(request))
    assert probe._require_request_parity(request, {"request_sha256": digest}) == digest


def test_global_once_marker_is_private_and_exclusive(monkeypatch):
    with tempfile.TemporaryDirectory(
        prefix=".uruha-p4-a-once-test-", dir=Path(tempfile.gettempdir()).resolve(),
    ) as private_path:
        directory = Path(private_path)
        directory.chmod(0o700)
        monkeypatch.setattr(probe, "GLOBAL_ATTEMPT_DIR", directory)
        marker = probe._global_once_marker(APPROVED_P1)
        probe._write_private(marker, {"attempted": True})
        assert stat.S_IMODE(marker.stat().st_mode) == 0o600
        with pytest.raises(FileExistsError):
            probe._write_private(probe._global_once_marker(APPROVED_P1), {"attempted": True})


@isolated_product_test
def test_preflight_uses_fake_m21_and_zero_real_provider(monkeypatch, capsys):
    import openai

    digest_reads = []

    monkeypatch.setattr(
        openai, "OpenAI",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("real_provider_forbidden")),
    )
    monkeypatch.setattr(
        probe, "_model_digest",
        lambda: digest_reads.append(True) or probe.MODEL_DIGEST,
    )
    assert probe.main(["--preflight-only"]) == 0
    output = capsys.readouterr().out
    assert '"status": "fake_m21_preflight_only_no_provider"' in output
    assert '"provider_generations": 0' in output
    assert len(digest_reads) == 1


def test_execute_requires_explicit_private_roots_and_evidence_parent():
    with pytest.raises(SystemExit) as denied:
        probe.main(["--execute"])
    assert denied.value.code == 2


def test_real_controller_reader_requires_matching_run_bound_child_values(monkeypatch):
    import p4_direct_reply_act_m29_priority_detached_control as controller
    import uruha_source_event_exact_input_capability_p4 as cap
    from test_p4_source_event_surface_diagnostic_route import _private_json, _synthetic_prepared_run

    with _synthetic_prepared_run("off", attested=False) as root:
        run_id = cap.current_exact_input_run_id(root)
        metadata_path = root / f"p4_preference_fallback_detached.{run_id}.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        flags = {
            "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
            "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
            "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
            "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM": "off",
            "URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT": str(root),
            "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "0",
        }
        metadata["env_keys"] = sorted(flags)
        _private_json(metadata_path, metadata)
        controller._record_source_surface_child_flags(str(root), "off", flags)
        ready = {
            "ok": True, "ready": True, "http_ready_verified": True,
            "listener_same_pid_before_after": True, "runtime_root": str(root),
            "run_id": run_id, "pid": metadata["pid"], "port": metadata["port"],
        }
        monkeypatch.setattr(
            probe.subprocess, "run",
            lambda *_args, **_kwargs: SimpleNamespace(
                returncode=0, stdout=json.dumps(ready), stderr="",
            ),
        )
        assert probe._real_controller_ready(root, "off")["attested_arm"] == "off"
        with pytest.raises(RuntimeError, match="controller_exact_child_arm_values_not_attested"):
            probe._real_controller_ready(root, "on")
        receipt_path = root / ".cache" / f"p4_source_surface_child_flags.{run_id}.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["pid"] += 1
        _private_json(receipt_path, receipt)
        with pytest.raises(RuntimeError, match="controller_exact_child_arm_values_not_attested"):
            probe._real_controller_ready(root, "off")


def test_evidence_parent_cannot_overlap_controller_root(monkeypatch, tmp_path):
    from test_p4_source_event_surface_diagnostic_route import _synthetic_prepared_run

    with _synthetic_prepared_run("off") as off, _synthetic_prepared_run("on") as on:
        monkeypatch.setattr(
            probe, "_run_preflight",
            lambda _source: (_ for _ in ()).throw(AssertionError("preflight_after_overlap")),
        )
        with pytest.raises(RuntimeError, match="evidence_parent_overlaps_controller_root"):
            probe._run_execute(APPROVED_P1, off, on, off, tmp_path / "unused")


@isolated_product_test
def test_capture_rejects_missing_same_turn_scope_before_ingest_or_provider(monkeypatch):
    import uruha_source_event_exact_input_capability_p4 as cap
    from test_p4_source_event_surface_diagnostic_route import _synthetic_prepared_run
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    calls = []

    def forbidden_ingest(_self, _source):
        raise AssertionError("cognition_before_claim_scope")

    monkeypatch.setattr(_IsolatedContractBrain, "ingest_event", forbidden_ingest)
    with _synthetic_prepared_run("off") as root:
        cap.issue_exact_input_permit(root, probe.CASE_ID, "off")
        claim = cap.claim_exact_input_permit(root, APPROVED_P1, "off")
        with pytest.raises(cap.ExactInputCapabilityError) as denied:
            probe._capture_one_m21(
                APPROVED_P1,
                lambda **kwargs: calls.append(kwargs),
                root,
                claim,
            )
        assert denied.value.reason == "same_turn_claim_missing"
        assert calls == []
        cap.close_exact_input_claim(claim)


@isolated_product_test
def test_fake_preflight_generates_once_then_replays_identical_boundary(monkeypatch):
    from copy import deepcopy

    original_fake = probe._fake_response
    original_replay = probe._replay_arm
    provider_calls = []
    replay_inputs = []

    def counted_fake(source):
        create = original_fake(source)

        def counted_create(**kwargs):
            provider_calls.append(deepcopy(kwargs))
            return create(**kwargs)

        return counted_create

    def observed_replay(arm, root, source, raw, handoff, seed, post_seed, post_event,
                        claim=None, **kwargs):
        replay_inputs.append((arm, probe._sha(probe._canonical(raw)), root))
        if arm != "default":
            assert root is not None and claim is not None
            assert (root / ".cache" / "p4_source_event_exact_input_capability" / "spent.json").is_file()
        return original_replay(arm, root, source, raw, handoff, seed, post_seed, post_event,
                               claim, **kwargs)

    monkeypatch.setattr(probe, "_fake_response", counted_fake)
    monkeypatch.setattr(probe, "_replay_arm", observed_replay)
    report = probe._run_preflight(APPROVED_P1)
    assert len(provider_calls) == 1
    assert provider_calls[0]["model"] == probe.MODEL
    assert report["provider_generations"] == 0  # real provider calls, not fake create
    assert report["default_equals_off"] is True
    assert report["off_audit_status"] == "mismatch"
    assert report["on_audit_status"] == "matched"
    assert [row[0] for row in replay_inputs] == ["off", "default", "on"]
    assert len({row[1] for row in replay_inputs}) == 1
    assert replay_inputs[0][2] != replay_inputs[2][2]


@isolated_product_test
def test_fake_preflight_rejects_divergent_arm_boundary(monkeypatch):
    original = probe._replay_arm

    def corrupted_on(arm, root, source, raw, handoff, seed, post_seed, post_event,
                     claim=None, **kwargs):
        if arm == "on":
            raw = {**raw, "test_only_mutation": True}
        return original(arm, root, source, raw, handoff, seed, post_seed, post_event,
                        claim, **kwargs)

    monkeypatch.setattr(probe, "_replay_arm", corrupted_on)
    with pytest.raises(RuntimeError, match="preflight_paired_parity_failed"):
        probe._run_preflight(APPROVED_P1)


def test_missing_human_author_review_rejects_before_ready_or_model(monkeypatch, tmp_path):
    import openai

    off = tmp_path / "off"
    on = tmp_path / "on"
    off.mkdir()
    on.mkdir()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir(mode=0o700)
    invalid_review = tmp_path / "invalid-review.json"
    invalid_review.write_text(json.dumps({"reviewer_kind": "synthetic_proxy", "verdict": "pass"}), encoding="utf-8")
    invalid_review.chmod(0o600)
    monkeypatch.setattr(probe, "_run_preflight", lambda _source: {"on_final_reply_sha256": "0" * 64})
    monkeypatch.setattr(
        probe, "_real_controller_ready",
        lambda _root, _arm: (_ for _ in ()).throw(AssertionError("ready_checked_before_review")),
    )
    monkeypatch.setattr(
        probe, "_model_digest",
        lambda: (_ for _ in ()).throw(AssertionError("model_checked_before_review")),
    )
    monkeypatch.setattr(
        openai, "OpenAI",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider_created_before_review")),
    )
    with pytest.raises(RuntimeError, match="fixed_gold_human_author_review_missing_or_mismatched"):
        probe._run_execute(APPROVED_P1, off, on, evidence_parent, invalid_review)


@pytest.mark.parametrize(("field", "wrong"), [
    ("source_sha256", "0" * 64),
    ("on_final_reply_sha256", "1" * 64),
    ("reviewer_kind", "synthetic_proxy"),
    ("natural_japanese", False),
    ("persona_consistent", False),
    ("not_overliteral_or_invented", False),
    ("verdict", "reject"),
])
def test_forged_or_negative_fixed_review_never_authorizes_trial(tmp_path, field, wrong):
    frozen = json.loads(probe.PROBE.read_text(encoding="utf-8"))
    case = next(row for row in frozen["positive_cases"] if row["id"] == probe.CASE_ID)
    expected = {
        "schema": "p4_source_event_surface_a_human_author_review_v1",
        "case_id": probe.CASE_ID,
        "source_sha256": probe._sha(APPROVED_P1.encode("utf-8")),
        "fixed_gold_sha256": probe._sha(probe._canonical(case["gold"])),
        "on_final_reply_sha256": "0" * 64,
        "reviewer_kind": "user_supplied_human_author",
        "natural_japanese": True,
        "persona_consistent": True,
        "not_overliteral_or_invented": True,
        "verdict": "pass",
    }
    expected[field] = wrong
    path = tmp_path / "synthetic-negative-review.json"
    path.write_text(json.dumps(expected), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(RuntimeError, match="fixed_gold_human_author_review_missing_or_mismatched"):
        probe._require_fixed_gold_review(
            path, APPROVED_P1, {"on_final_reply_sha256": "0" * 64}
        )


@isolated_product_test
def test_ambiguous_provider_failure_keeps_private_attempt_and_never_retries(monkeypatch, tmp_path):
    import openai
    from test_p4_source_event_surface_diagnostic_route import _synthetic_prepared_run

    parent = tmp_path / "private-evidence"
    parent.mkdir(mode=0o700)
    parent.chmod(0o700)
    monkeypatch.setattr(probe, "_global_once_marker", lambda _source: tmp_path / "global-once.json")
    attempts = []
    monkeypatch.setattr(
        probe, "_run_preflight",
        lambda _source: {"on_final_reply_sha256": "0" * 64},
    )
    # Synthetic fixture only: it cannot be used as a real human-review receipt.
    monkeypatch.setattr(
        probe, "_require_fixed_gold_review",
        lambda *_args: {"review_kind": "synthetic_test_stub_not_human"},
    )
    monkeypatch.setattr(probe, "_model_digest", lambda: probe.MODEL_DIGEST)
    monkeypatch.setattr(probe, "_require_request_parity", lambda _request, _preflight: "synthetic_unit_stub")

    def fake_create(**kwargs):
        attempts.append(kwargs)
        raise RuntimeError("synthetic_ambiguous_provider_failure")

    monkeypatch.setattr(
        openai, "OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
        ),
    )
    with _synthetic_prepared_run("off") as off_root, _synthetic_prepared_run("on") as on_root:
        monkeypatch.setattr(
            probe,
            "_real_controller_ready",
            lambda root, _arm: {
                "run_id": ("a" if root == off_root else "b") * 16,
                "pid": 111 if root == off_root else 222,
                "port": 7938 if root == off_root else 7939,
            },
        )
        with pytest.raises(RuntimeError):
            probe._run_execute(APPROVED_P1, off_root, on_root, parent, tmp_path / "stub")
        assert len(attempts) == 1
        roots = list(parent.glob("uruha-p4-source-surface-a-*"))
        assert len(roots) == 1
        evidence = roots[0]
        assert (parent / f".uruha-p4-source-surface-a-{probe._sha(APPROVED_P1.encode())}.attempted.json").is_file()
        assert (evidence / "m21_request_before_call.json").is_file()
        assert not (evidence / "m21_response_after_call.json").exists()
        receipt = json.loads((evidence / "terminal_receipt.json").read_text(encoding="utf-8"))
        assert receipt["status"] == "terminal_failure"
        assert receipt["provider_attempts"] == 1
        assert receipt["b_safari_authorized"] is False
        assert (off_root / ".cache" / "p4_source_event_exact_input_capability" / "spent.json").is_file()
        assert (on_root / ".cache" / "p4_source_event_exact_input_capability" / "spent.json").is_file()


@isolated_product_test
def test_fake_execute_uses_one_provider_boundary_for_both_arms(monkeypatch, tmp_path):
    import openai
    from test_p4_source_event_surface_diagnostic_route import _synthetic_prepared_run

    parent = tmp_path / "private-evidence"
    parent.mkdir(mode=0o700)
    parent.chmod(0o700)
    monkeypatch.setattr(probe, "_global_once_marker", lambda _source: tmp_path / "global-once.json")
    attempts = []
    monkeypatch.setattr(
        probe, "_run_preflight",
        lambda _source: {"on_final_reply_sha256": "0" * 64},
    )
    # A unit-test bypass of an external human dependency, never evidence of it.
    monkeypatch.setattr(
        probe, "_require_fixed_gold_review",
        lambda *_args: {"review_kind": "synthetic_test_stub_not_human"},
    )
    monkeypatch.setattr(probe, "_model_digest", lambda: probe.MODEL_DIGEST)
    monkeypatch.setattr(probe, "_require_request_parity", lambda _request, _preflight: "synthetic_unit_stub")
    plans = json.loads(probe.FIXED.read_text(encoding="utf-8"))["fixed_compact_plans"]

    def fake_create(**kwargs):
        attempts.append(kwargs)
        usage = SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            model_dump=lambda: {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                finish_reason="stop",
            )],
            usage=usage,
        )

    monkeypatch.setattr(
        openai, "OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
        ),
    )
    with _synthetic_prepared_run("off") as off_root, _synthetic_prepared_run("on") as on_root:
        monkeypatch.setattr(
            probe,
            "_real_controller_ready",
            lambda _root, arm: {
                "run_id": ("a" if arm == "off" else "b") * 16,
                "pid": 111 if arm == "off" else 222,
                "port": 7938 if arm == "off" else 7939,
            },
        )
        report = probe._run_execute(APPROVED_P1, off_root, on_root, parent, tmp_path / "stub")
    assert len(attempts) == 1
    assert attempts[0]["model"] == probe.MODEL
    assert report["provider_attempts"] == 1
    assert report["provider_total_tokens"] == 120
    assert report["status"] == "surface_structural_pass_author_naturalness_pending"
    assert report["b_safari_authorized"] is False
    assert [row["arm"] for row in report["arms"]] == ["default", "off", "on"]
    assert [row["audit_status"] for row in report["arms"][1:]] == ["mismatch", "matched"]
    assert len({row["initial_state_sha256"] for row in report["arms"]}) == 1
    assert len({row["raw_boundary_sha256"] for row in report["arms"]}) == 1
    assert all(row["provider_attempts_during_replay"] == 0 for row in report["arms"])
    evidence = next(parent.glob("uruha-p4-source-surface-a-*"))
    assert (evidence / "m21_request_before_call.json").is_file()
    assert (evidence / "m21_response_after_call.json").is_file()
    assert (evidence / "post_m21_boundary.json").is_file()
    assert (evidence / "terminal_receipt.json").is_file()
    other_parent = tmp_path / "other-private-evidence"
    other_parent.mkdir(mode=0o700)
    other_parent.chmod(0o700)
    with _synthetic_prepared_run("off") as next_off, _synthetic_prepared_run("on") as next_on:
        with pytest.raises(probe.TrialTerminal):
            probe._run_execute(APPROVED_P1, next_off, next_on, other_parent, tmp_path / "stub")
    assert len(attempts) == 1  # changing parent and controller roots cannot retry A
    assert not (other_parent / "m21_request_before_call.json").exists()


@isolated_product_test
def test_fake_execute_resource_and_finish_failures_are_terminal(monkeypatch, tmp_path):
    import openai
    from test_p4_source_event_surface_diagnostic_route import _synthetic_prepared_run

    plans = json.loads(probe.FIXED.read_text(encoding="utf-8"))["fixed_compact_plans"]
    for scenario in ("over_tokens", "over_wall", "finish_length"):
        parent = tmp_path / scenario
        parent.mkdir(mode=0o700)
        parent.chmod(0o700)
        attempts = []
        with monkeypatch.context() as patch:
            patch.setattr(probe, "_global_once_marker", lambda _source: tmp_path / f"global-once-{scenario}.json")
            patch.setattr(
                probe, "_run_preflight",
                lambda _source: {"on_final_reply_sha256": "0" * 64},
            )
            # These are synthetic unit-test shims, not a human-author review.
            patch.setattr(
                probe, "_require_fixed_gold_review",
                lambda *_args: {"review_kind": "synthetic_test_stub_not_human"},
            )
            patch.setattr(probe, "_model_digest", lambda: probe.MODEL_DIGEST)
            patch.setattr(probe, "_require_request_parity", lambda _request, _preflight: "synthetic_unit_stub")
            if scenario == "over_wall":
                patch.setattr(probe, "_planner_elapsed_seconds", lambda _started: 20.001)

            def fake_create(**kwargs):
                attempts.append(kwargs)
                total = 2001 if scenario == "over_tokens" else 120
                prompt = total - 20
                usage = SimpleNamespace(
                    prompt_tokens=prompt,
                    completion_tokens=20,
                    total_tokens=total,
                    model_dump=lambda: {
                        "prompt_tokens": prompt,
                        "completion_tokens": 20,
                        "total_tokens": total,
                    },
                )
                return SimpleNamespace(
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                        finish_reason="length" if scenario == "finish_length" else "stop",
                    )],
                    usage=usage,
                )

            patch.setattr(
                openai, "OpenAI",
                lambda **_kwargs: SimpleNamespace(
                    chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
                ),
            )
            with _synthetic_prepared_run("off") as off_root, _synthetic_prepared_run("on") as on_root:
                patch.setattr(
                    probe,
                    "_real_controller_ready",
                    lambda root, _arm: {
                        "run_id": ("a" if root == off_root else "b") * 16,
                        "pid": 111 if root == off_root else 222,
                        "port": 7938 if root == off_root else 7939,
                    },
                )
                with pytest.raises(RuntimeError):
                    probe._run_execute(APPROVED_P1, off_root, on_root, parent, tmp_path / "stub")
        assert len(attempts) == 1, scenario
        evidence = next(parent.glob("uruha-p4-source-surface-a-*"))
        receipt = json.loads((evidence / "terminal_receipt.json").read_text(encoding="utf-8"))
        assert receipt["status"] == "terminal_failure", scenario
        assert receipt["provider_attempts"] == 1, scenario
        assert receipt["b_safari_authorized"] is False, scenario
        assert (evidence / "m21_request_before_call.json").is_file(), scenario
        assert (evidence / "m21_response_after_call.json").is_file(), scenario
        assert not (evidence / "off_replay_private.json").exists(), scenario
        assert not (evidence / "on_replay_private.json").exists(), scenario
        if scenario == "over_tokens":
            assert receipt["provider_total_tokens"] == 2001
        elif scenario == "over_wall":
            assert receipt["planner_seconds"] == 20.001
        else:
            raw_response = json.loads((evidence / "m21_response_after_call.json").read_text(encoding="utf-8"))
            assert raw_response["finish_reason"] == "length"
            assert "fresh_m21_route_resource_or_accounting_gate_failed" in receipt["terminal_error"]
