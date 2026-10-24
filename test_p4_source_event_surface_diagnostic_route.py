"""Zero-provider P4 source-surface comparison under exact-input authority.

Historical pure-slot tests remain evidence about the old finite grammar; only
the prospective approved source may enter the current opt-in product route.
"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext, redirect_stdout
from copy import deepcopy
from dataclasses import asdict
from functools import wraps
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import pytest

from test_p4_source_event_surface_diagnostic import _canonical, _normalized_projection, _sha
from test_p4_source_event_core_utility_f7 import _handoff
from uruha_direct_reply_act_planner_handoff_p4 import route_receipt_p4
from uruha_source_event_core_utility_p4 import assess_candidate_coverage_p4
from uruha_source_event_surface_diagnostic_p4 import (
    admit_source_event_slot_p4,
    audit_final_source_event_p4,
    realize_source_event_p4,
)
import uruha_source_event_exact_input_capability_p4 as exact_cap


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_source_event_surface_diagnostic_probe_2026-10-24.json").read_text(encoding="utf-8")
)
CAP_DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_source_event_surface_exact_input_capability_probe_2026-10-24.json").read_text(encoding="utf-8")
)
APPROVED_P1 = next(row["source"] for row in CAP_DATA["positive_cases"] if row["id"] == "cap_fixed_envelope")
APPROVED_B = next(row["source"] for row in CAP_DATA["positive_cases"] if row["id"] == "cap_conditional_safari_soup")
PREIMPLEMENTATION_NORMALIZED_SHA = "a1759ae06069fc608d9ebc0826e7a7b98bd236babc5bf39a5030b0a064ba8335"
_ISOLATED_CHILD_ENV = "URUHA_P4_SURFACE_TEST_ISOLATED_CHILD"


def _private_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)


@contextmanager
def _synthetic_prepared_run(arm: str, *, attested: bool = True):
    """Fake controller metadata for no-provider capability contracts only."""
    with tempfile.TemporaryDirectory(
        prefix=f"uruha-product-source-surface-{arm}-",
        dir=Path(tempfile.gettempdir()).resolve(),
    ) as private_path:
        root = Path(private_path)
        root.chmod(0o700)
        (root / ".cache").mkdir(mode=0o700)
        schema = "uruha_p4_preference_fallback_detached_control_v1"
        entrypoint = str(Path(__file__).resolve().parent / "uruha_web_ui_product_p4_direct_reply_act_m29_priority.py")
        run_id = "a" * 16 if arm == "off" else "b" * 16
        _private_json(root / "uruha_product_launcher_manifest.json", {
            "schema": "uruha_p4_b_runtime_root_v1", "created_by_launcher": True,
        })
        _private_json(root / "p4_preference_fallback_detached.prepared.json", {
            "schema": schema, "kind": "prepared_first_start", "runtime_root": str(root),
            "uid": os.getuid(), "mode": "product", "entrypoint": entrypoint, "port": 7938,
        })
        _private_json(root / "p4_preference_fallback_detached.prepared-claim.json", {
            "schema": schema, "runtime_root": str(root), "uid": os.getuid(), "entrypoint": entrypoint,
        })
        _private_json(root / "p4_preference_fallback_detached.current.json", {
            "schema": schema, "run_id": run_id, "uid": os.getuid(),
        })
        child_flags = {
            "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
            "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
            "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
            "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM": arm,
            "URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT": str(root),
            "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "0",
        }
        _private_json(root / f"p4_preference_fallback_detached.{run_id}.json", {
            "schema": schema, "runtime_root": str(root), "run_id": run_id,
            "uid": os.getuid(), "mode": "product", "port": 7938,
            "pid": os.getpid(), "pre_main_command": f"/synthetic/python {entrypoint}",
            "env_keys": sorted(child_flags),
        })
        if attested:
            _private_json(root / ".cache" / f"p4_source_surface_child_flags.{run_id}.json", {
                "schema": "uruha_p4_source_surface_child_flags_v1",
                "runtime_root": str(root), "run_id": run_id,
                "pid": os.getpid(), "port": 7938,
                "flags": child_flags, "candidate_prompt_absent": True,
            })
        yield root


@contextmanager
def _approved_claim(monkeypatch, source: str, arm: str = "on"):
    assert source == APPROVED_P1
    with _synthetic_prepared_run(arm) as root, monkeypatch.context() as env:
        env.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", arm)
        env.setenv("URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT", str(root))
        exact_cap.issue_exact_input_permit(root, "cap_fixed_envelope", arm)
        claim = exact_cap.claim_exact_input_permit(root, source, arm)
        with exact_cap.scoped_exact_input_claim(claim):
            yield claim


def isolated_product_test(fn):
    """Contain product's irreversible process-global overlay installation."""
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
            timeout=45,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

    return run


def _plans_with_labels() -> list[dict]:
    return [
        {**deepcopy(plan), "candidate_label": label}
        for plan, label in zip(DATA["fixed_compact_plans"], ("default", "softer", "sharper"))
    ]


def _paired_initial_brain_state(brain) -> dict:
    """The serializable pre-turn state shared by the three fake-M21 arms."""
    return {
        "memory": {
            "runtime_snapshot": brain.memory.get_runtime_snapshot(),
            "saved_episodes": deepcopy(brain.memory.saved_episodes),
        },
        "psyche": brain.psyche.get_state(),
        "persona_policy_provider": brain.persona_policy_provider,
        "right_brain_persona_policy_provider": brain.right_brain.persona_policy_provider,
        "right_brain_model_blend_enabled": brain.right_brain.model_blend_enabled,
        "right_brain_history": deepcopy(brain.right_brain.history),
        "right_brain_reply_variant_counts": dict(brain.right_brain.reply_variant_counts),
        "right_brain_intent_variant_counts": dict(brain.right_brain.intent_variant_counts),
        "left_brain_state": deepcopy(brain.left_brain.__dict__),
        "runtime_config": asdict(brain.runtime_config),
        "runtime": asdict(brain.runtime),
        "last_external_input_at": brain._last_external_input_at,
        "last_background_tick_at": brain._last_background_tick_at,
        "last_timer_event_at": brain._last_timer_event_at,
        "event_queue": deepcopy(brain._event_queue),
        "event_seq": brain._event_seq,
    }


def _minimal_logic(source: str) -> tuple[dict | None, dict]:
    """Contract-only mutation fixture; the main paired test uses real cognitive_tick."""
    handoff = _handoff(source)
    plans = _plans_with_labels()
    coverage = assess_candidate_coverage_p4(source, handoff, plans)
    core = plans[0]["core_message_jp"]
    coverage.update(
        compact_completed=True,
        compact_candidate_count=3,
        m21_fallback_used=False,
        final_core_matches_winner=True,
        final_core_sha256=hashlib.sha256(core.encode()).hexdigest(),
    )
    route = route_receipt_p4(
        arm="control", source=source, handoff=handoff,
        route="full_planner", planner_prompt_injected=False,
    )
    return handoff, {
        "bounded_slow_path_m21": {
            "route": "full_planner", "status": "completed_within_budget",
            "fallback_used": False, "model_call_completed": True,
        },
        "direct_reply_act_planner_handoff_p4": route,
        "source_event_core_utility_p4": coverage,
        "core_message_jp": core,
    }


def _fixed_product_boundary(monkeypatch, source: str | None = None, *, require_frozen_a: bool = True):
    import openai
    import uruha_brain_mac as runtime
    import uruha_compact_planner_p2 as compact
    import uruha_contextual_expression_commit_p2 as expression
    import uruha_web_ui_product_p4_direct_reply_act_m29_priority as product_entry
    from uruha_brain_mac import LeftBrain, RightBrain
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: (_ for _ in ()).throw(
        AssertionError("real_provider_client_forbidden")
    ))
    monkeypatch.setattr(runtime, "LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS", 20.0)
    for key, value in {
        "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
        "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT": "0",
        "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "0",
        "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM": "off",
    }.items():
        monkeypatch.setenv(key, value)
    compact.install_compact_planner_p2()
    expression.install_contextual_expression_commit_p2()
    product_entry.install_product_chain()
    plans = deepcopy(DATA["fixed_compact_plans"])
    calls = []

    def fake_create(**kwargs):
        calls.append(deepcopy(kwargs))
        if len(calls) != 1:
            raise AssertionError("one_fake_m21_call_only")
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
            finish_reason="stop",
        )])

    brain = _IsolatedContractBrain()
    left = LeftBrain(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))))

    def fit(plan, *_args):
        return 1.0 if plan.get("core_message_jp") == plans[0]["core_message_jp"] else 0.75

    for name in (
        "_persona_fit_score", "_psyche_fit_score", "_continuity_fit_score",
        "_human_fit_score", "_belief_gap_fit_score", "_procedural_fit_score",
    ):
        setattr(left, name, fit)
    left._critique_plan = lambda *_args: {"needs_revision": False, "issues": [], "internal_note": ""}
    brain.left_brain = left
    brain.right_brain = RightBrain(load_model=False)
    source = source or DATA["planner_comparison_source"]
    event = brain.ingest_event(source)
    logs = io.StringIO()
    with redirect_stdout(logs):
        tick = brain.cognitive_tick(event)
    assert "Ollama Left Brain Error" not in logs.getvalue()
    if require_frozen_a:
        assert len(calls) == 1
        assert calls[0]["response_format"]["type"] == "json_schema"
        assert tick["_source_event_surface_handoff_p4"] == _handoff(source)
    raw = {"logic": tick["logic"], "route_info": tick["route_info"]}
    if require_frozen_a:
        assert _sha(_canonical(_normalized_projection(raw))) == PREIMPLEMENTATION_NORMALIZED_SHA
        assert tick["logic"]["core_message_jp"] == "頑張ったね！"
        assert tick["logic"]["source_event_core_utility_p4"]["status"] == "no_grounded_candidate"
    return source, deepcopy(raw), deepcopy(tick["_source_event_surface_handoff_p4"]), calls


@isolated_product_test
def test_approved_p1_same_post_m21_off_on_final_visible_and_graph(monkeypatch):
    import uruha_brain_mac as runtime
    from uruha_brain_mac import RightBrain
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    source, raw, handoff, calls = _fixed_product_boundary(
        monkeypatch, source=APPROVED_P1, require_frozen_a=False,
    )
    raw_bytes = _canonical(raw)
    # This paired fake fixture has its own isolated starting state. The separate
    # preimplementation capture is not silently treated as byte-identical here.
    assert len(calls) == 1 and calls[0]["response_format"]["type"] == "json_schema"
    assert handoff == _handoff(source)
    seed_brain = _IsolatedContractBrain()
    seed_brain.right_brain = RightBrain(load_model=False)
    assert seed_brain.right_brain.model_blend_enabled is False
    initial_state_bytes = _canonical(_paired_initial_brain_state(seed_brain))
    initial_state_sha = _sha(initial_state_bytes)
    results = {}
    for arm in (None, "off", "on"):
        brain = _IsolatedContractBrain()
        brain.memory = deepcopy(seed_brain.memory)
        brain.psyche = deepcopy(seed_brain.psyche)
        brain.runtime = deepcopy(seed_brain.runtime)
        brain.runtime_config = brain.runtime.config
        brain.left_brain = deepcopy(seed_brain.left_brain)
        brain.right_brain = deepcopy(seed_brain.right_brain)
        brain._last_external_input_at = seed_brain._last_external_input_at
        brain._last_background_tick_at = seed_brain._last_background_tick_at
        brain._last_timer_event_at = seed_brain._last_timer_event_at
        brain._event_queue = deepcopy(seed_brain._event_queue)
        brain._event_seq = seed_brain._event_seq
        assert _sha(_canonical(_paired_initial_brain_state(brain))) == initial_state_sha
        brain.cognitive_tick = lambda _event: {
            **deepcopy(raw), "_source_event_surface_handoff_p4": deepcopy(handoff),
        }
        with monkeypatch.context() as arm_env:
            if arm is None:
                arm_env.delenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM")
                arm_env.delenv("URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT", raising=False)
                scope = nullcontext()
            else:
                arm_env.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", arm)
                scope = _synthetic_prepared_run(arm)
            if arm is None:
                with scope, redirect_stdout(io.StringIO()):
                    result = brain.run_turn_debug(source)
            else:
                with scope as root:
                    arm_env.setenv("URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT", str(root))
                    issued = exact_cap.issue_exact_input_permit(root, "cap_fixed_envelope", arm)
                    assert issued["input_sha256"] == hashlib.sha256(source.encode()).hexdigest()
                    claim = exact_cap.claim_exact_input_permit(root, source, arm)
                    assert exact_cap.validate_exact_input_claim(claim, root, source, arm) is claim
                    with exact_cap.scoped_exact_input_claim(claim), redirect_stdout(io.StringIO()):
                        result = brain.run_turn_debug(source)
        assert result["reply"] == brain.memory.saved_episodes[-1]["reply"]
        assert result["reply"] == brain.right_brain.history[-1]["content"]
        assert len(calls) == 1  # no RightBrain/provider/repair model call
        graph = result["runtime_trace"]["blackboard"]
        labels = (
            "source_event_certificate_p4", "source_event_ephemeral_slot_p4",
            "source_event_surface_p4", "source_event_final_visible_audit_p4",
        )
        assert sum(row.get("label") == "utterance" for row in graph) == 1
        if arm is None:
            assert "source_event_surface_diagnostic_p4" not in result["logic"]
            assert not any(row.get("label") in labels for row in graph)
            results["default"] = result
            continue
        assert sum(row.get("label") == "source_event_exact_input_capability_p4" for row in graph) == 1
        capability_node = next(row["payload"] for row in graph if row.get("label") == "source_event_exact_input_capability_p4")
        receipt = exact_cap.public_claim_receipt(claim)
        assert receipt == {
            "reason": "exact_input_permit_consumed",
            "input_sha256": hashlib.sha256(source.encode()).hexdigest(),
        }
        assert capability_node == receipt
        assert source not in repr(capability_node) and "slot" not in repr(capability_node)
        audit = result["logic"]["source_event_surface_diagnostic_p4"]
        for label in labels:
            assert sum(row.get("label") == label for row in graph) == 1
        prewrite = next(row["payload"] for row in graph if row.get("label") == "source_event_final_visible_audit_p4")
        assert prewrite["audit_stage"] == "after_last_guard_before_episode"
        assert sum(row.get("label") == "source_event_post_emit_audit_p4" for row in graph) == 1
        assert next(row["payload"] for row in graph if row.get("label") == "source_event_post_emit_audit_p4") == audit
        assert source not in repr(audit) and "和紙の封筒" not in repr(audit)
        for row in graph:
            if row.get("label") in labels:
                assert source not in repr(row["payload"])
                assert "和紙の封筒" not in repr(row["payload"])
        results[arm] = result
        assert runtime._P4_SOURCE_EVENT_SURFACE_SLOT.get() is None
    assert _canonical(raw) == raw_bytes
    assert results["default"]["reply"] == results["off"]["reply"]
    assert results["off"]["logic"]["source_event_surface_diagnostic_p4"]["status"] == "mismatch"
    assert results["on"]["logic"]["source_event_surface_diagnostic_p4"]["status"] == "matched"
    assert results["off"]["reply"] != results["on"]["reply"]
    assert "和紙の封筒を初めて自分で折った" in results["on"]["reply"]
    assert len(results["on"]["reply"]) <= 28
    assert _canonical(raw) == raw_bytes


@isolated_product_test
def test_historical_lamp_without_exact_input_claim_rejected_before_ingest(monkeypatch):
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    source = DATA["planner_comparison_source"]
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", "on")
    brain = _IsolatedContractBrain()
    brain.ingest_event = lambda _source: (_ for _ in ()).throw(AssertionError("ingest_must_not_run"))
    with pytest.raises(exact_cap.ExactInputCapabilityError) as denied:
        brain.run_turn_debug(source)
    assert denied.value.reason == "same_turn_claim_missing"
    assert not brain.memory.saved_episodes


@pytest.mark.parametrize("row", DATA["contract_sources"], ids=lambda row: row["id"])
def test_source_admission_contract_and_negative_controls(row, monkeypatch):
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "0")
    handoff, logic = _minimal_logic(row["source"])
    slot, receipt = admit_source_event_slot_p4(row["source"], handoff, logic)
    assert (slot is not None) is row["source_slot_expected"]
    if slot is not None:
        reply = realize_source_event_p4(slot)
        assert reply is not None and len(reply) <= 28
        assert audit_final_source_event_p4(row["source"], slot, reply)["status"] == "matched"
        if row["id"] == "no_first_time":
            assert slot.first_time == "not_stated" and "初めて" not in reply
    else:
        assert receipt["status"] == "not_authorized"
        if row["id"] in {"long_relation", "sensitive_medication"}:
            assert receipt["reason"] == row["reason"]


def test_safari_source_slot_is_separate_developer_case(monkeypatch):
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "0")
    source = DATA["safari_confirmation_source"]
    handoff, logic = _minimal_logic(source)
    slot, receipt = admit_source_event_slot_p4(source, handoff, logic)
    assert receipt["status"] == "admitted" and slot is not None
    reply = realize_source_event_p4(slot)
    assert audit_final_source_event_p4(source, slot, reply)["status"] == "matched"
    assert "青い凧を初めて自分で揚げた" in reply


def test_stale_wrong_route_and_guard_mutations_fail_closed(monkeypatch):
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "0")
    source = DATA["planner_comparison_source"]
    handoff, logic = _minimal_logic(source)
    slot, receipt = admit_source_event_slot_p4(source, handoff, logic)
    assert receipt["status"] == "admitted" and slot is not None
    assert audit_final_source_event_p4(source, slot, "頑張ったね！")["status"] == "mismatch"
    assert audit_final_source_event_p4(source, slot, "初めて自分で古いランプの電球を交換したんだ。やるじゃん。")["status"] == "mismatch"
    assert audit_final_source_event_p4(source, slot, "古いランプの電球を初めて自分で替えたんだ。やるじゃん。")["status"] == "matched"
    for changed_handoff, changed_logic in (
        ({**handoff, "input_sha256": "0" * 64}, logic),
        (handoff, {**logic, "bounded_slow_path_m21": {**logic["bounded_slow_path_m21"], "route": "bounded_simple_presence"}}),
        (handoff, {**logic, "direct_reply_act_planner_handoff_p4": {**logic["direct_reply_act_planner_handoff_p4"], "m33_status": "applicable"}}),
        (handoff, {**logic, "core_message_jp": "別の話だよ。"}),
    ):
        denied, denied_receipt = admit_source_event_slot_p4(source, changed_handoff, changed_logic)
        assert denied is None and denied_receipt["status"] == "not_authorized"
    next_source = "今日は別の話をする。"
    denied, _ = admit_source_event_slot_p4(next_source, handoff, logic)
    assert denied is None


@isolated_product_test
def test_real_emit_guard_rewrite_is_audited_after_guard_and_slot_clears(monkeypatch):
    import uruha_brain_mac as runtime
    from uruha_brain_mac import RightBrain
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    source, raw, handoff, calls = _fixed_product_boundary(
        monkeypatch, source=APPROVED_P1, require_frozen_a=False,
    )
    brain = _IsolatedContractBrain()
    brain.right_brain = RightBrain(load_model=False)
    event = brain.ingest_event(source)
    tick = deepcopy(raw)
    tick["_source_event_surface_handoff_p4"] = deepcopy(handoff)
    monkeypatch.setattr(brain.right_brain, "enforce_user_visible_japanese", lambda *_args, **_kwargs: "頑張ったね！")
    with _approved_claim(monkeypatch, source), redirect_stdout(io.StringIO()):
        result = brain.emit_response_if_ready(event, tick)
    audit = result["logic"]["source_event_surface_diagnostic_p4"]
    assert audit["status"] == "mismatch"
    assert audit["treatment_applied_before_guards"] is True
    assert result["reply"] == brain.memory.saved_episodes[-1]["reply"] == "頑張ったね！"
    assert runtime._P4_SOURCE_EVENT_SURFACE_SLOT.get() is None
    assert len(calls) == 1


@isolated_product_test
def test_full_run_wrapper_rechecks_visible_reply_after_emit_overlays(monkeypatch):
    from uruha_memory_observatory import collect_cognitive_graph
    from uruha_brain_mac import RightBrain
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    source, raw, handoff, calls = _fixed_product_boundary(
        monkeypatch, source=APPROVED_P1, require_frozen_a=False,
    )
    brain = _IsolatedContractBrain()
    brain.right_brain = RightBrain(load_model=False)
    monkeypatch.setattr(brain, "cognitive_tick", lambda _event: {
        **deepcopy(raw), "_source_event_surface_handoff_p4": deepcopy(handoff),
    })
    with _approved_claim(monkeypatch, source), redirect_stdout(io.StringIO()):
        result = brain.run_turn_debug(source)
    final = result["logic"]["source_event_surface_diagnostic_p4"]
    assert final["status"] == "matched"
    assert final["audit_stage"] == "after_emit_overlays_before_runtime_return"
    assert final["treatment_applied_before_guards"] is True
    assert final["matches_prewrite_reply"] is True
    assert final["right_brain_history_matches_visible"] is True
    assert final["reply_sha256"] == hashlib.sha256(result["reply"].encode()).hexdigest()
    assert result["reply"] == brain.memory.saved_episodes[-1]["reply"]
    assert result["runtime_trace"]["source_event_surface_diagnostic_p4"] == final
    graph = result["runtime_trace"]["blackboard"]
    assert sum(row.get("label") == "source_event_post_emit_audit_p4" for row in graph) == 1
    assert next(row["payload"] for row in graph if row.get("label") == "source_event_post_emit_audit_p4") == final
    visual = collect_cognitive_graph(result)
    visual_nodes = visual["nodes"]
    visual_labels = {node["label"] for node in visual_nodes}
    for label in (
        "source_event_certificate_p4", "source_event_ephemeral_slot_p4",
        "source_event_surface_p4", "source_event_final_visible_audit_p4",
        "source_event_post_emit_audit_p4", "UTTERANCE",
    ):
        assert label in visual_labels
    assert any(edge.get("class") == "is-main" for edge in visual["edges"])
    assert len(calls) == 1


@isolated_product_test
def test_post_emit_overlay_rewrite_is_failure_not_false_visible_success(monkeypatch):
    from uruha_brain_mac import RightBrain
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    source, raw, handoff, calls = _fixed_product_boundary(
        monkeypatch, source=APPROVED_P1, require_frozen_a=False,
    )
    brain = _IsolatedContractBrain()
    brain.right_brain = RightBrain(load_model=False)
    monkeypatch.setattr(brain, "cognitive_tick", lambda _event: {
        **deepcopy(raw), "_source_event_surface_handoff_p4": deepcopy(handoff),
    })
    normal_emit = brain.emit_response_if_ready

    def rewritten_after_emit(event, tick):
        result = normal_emit(event, tick)
        result["reply"] = "頑張ったね！"
        return result

    monkeypatch.setattr(brain, "emit_response_if_ready", rewritten_after_emit)
    with _approved_claim(monkeypatch, source), redirect_stdout(io.StringIO()):
        result = brain.run_turn_debug(source)
    final = result["logic"]["source_event_surface_diagnostic_p4"]
    assert result["reply"] == "頑張ったね！"
    assert final["status"] == "mismatch"
    assert final["matches_prewrite_reply"] is False
    assert final["reply_sha256"] == hashlib.sha256(result["reply"].encode()).hexdigest()
    assert brain.memory.saved_episodes[-1]["reply"] != result["reply"]
    assert len(calls) == 1


def test_medication_negative_final_audit_cannot_be_called_safe(monkeypatch):
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "0")
    source = next(row["source"] for row in DATA["contract_sources"] if row["id"] == "sensitive_medication")
    handoff, logic = _minimal_logic(source)
    slot, receipt = admit_source_event_slot_p4(source, handoff, logic)
    assert slot is None and receipt["reason"] == "medication_dose_safety_context"
    assert audit_final_source_event_p4(source, slot, "いいじゃん。")["status"] == "unsafe_endorsement_observed"


def test_harmful_completed_action_is_not_a_praiseworthy_slot(monkeypatch):
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "0")
    source = "初めて自分で友達の財布を盗んだ。今は一言だけ励まして。"
    handoff, logic = _minimal_logic(source)
    slot, receipt = admit_source_event_slot_p4(source, handoff, logic)
    assert slot is None
    assert receipt["reason"] == "unsafe_completed_action_context"
    assert audit_final_source_event_p4(source, slot, "やるじゃん。")["status"] == "unsafe_endorsement_observed"


@pytest.mark.parametrize("action", ("万引きした", "着服した"))
@pytest.mark.xfail(strict=True, reason="REVIEW_REQUIRED: finite harmful-action veto misses theft synonyms")
def test_unresolved_theft_synonyms_must_abstain_before_auto_praise(monkeypatch, action):
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "0")
    source = f"初めて自分で店の商品を{action}。今は一言だけ励まして。"
    handoff, logic = _minimal_logic(source)
    slot, _ = admit_source_event_slot_p4(source, handoff, logic)
    assert slot is None


@isolated_product_test
def test_harmful_completed_action_does_not_use_auto_praise_surface(monkeypatch):
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    source = "初めて自分で友達の財布を盗んだ。今は一言だけ励まして。"
    brain = _IsolatedContractBrain()
    brain.ingest_event = lambda _source: (_ for _ in ()).throw(AssertionError("ingest_must_not_run"))
    with _synthetic_prepared_run("on") as root, monkeypatch.context() as env:
        env.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", "on")
        env.setenv("URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT", str(root))
        exact_cap.issue_exact_input_permit(root, "cap_fixed_envelope", "on")
        with pytest.raises(exact_cap.ExactInputCapabilityError) as denied:
            exact_cap.claim_exact_input_permit(root, source, "on")
        assert denied.value.reason == "permit_does_not_authorize_input"
        with pytest.raises(exact_cap.ExactInputCapabilityError) as no_claim:
            brain.run_turn_debug(source)
        assert no_claim.value.reason == "same_turn_claim_missing"
    assert not brain.memory.saved_episodes


@isolated_product_test
def test_sensitive_medication_is_not_visibly_praised_in_isolated_fake_route(monkeypatch):
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    source = next(row["source"] for row in DATA["contract_sources"] if row["id"] == "sensitive_medication")
    brain = _IsolatedContractBrain()
    brain.ingest_event = lambda _source: (_ for _ in ()).throw(AssertionError("ingest_must_not_run"))
    with _synthetic_prepared_run("on") as root, monkeypatch.context() as env:
        env.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", "on")
        env.setenv("URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT", str(root))
        exact_cap.issue_exact_input_permit(root, "cap_fixed_envelope", "on")
        with pytest.raises(exact_cap.ExactInputCapabilityError) as denied:
            exact_cap.claim_exact_input_permit(root, source, "on")
        assert denied.value.reason == "permit_does_not_authorize_input"
        with pytest.raises(exact_cap.ExactInputCapabilityError) as no_claim:
            brain.run_turn_debug(source)
        assert no_claim.value.reason == "same_turn_claim_missing"
    assert not brain.memory.saved_episodes


def test_child_only_surface_arm_controller_contract(monkeypatch, tmp_path):
    import p4_direct_reply_act_m29_priority_detached_control as controller

    layout = {
        "runtime_root": tmp_path / "runtime",
        "memory_db": tmp_path / "memory",
        "session_db": tmp_path / "session",
        "web_logs": tmp_path / "web_logs",
        "jsonl_log": tmp_path / "web_logs/conversation.jsonl",
        "text_log": tmp_path / "web_logs/conversation.txt",
    }
    observed = []
    attestations = []

    def preflight(**kwargs):
        return {}, dict(kwargs["environ"]), layout, False, None

    def no_launch(argv):
        base = controller.launchd._isolated_env(layout, port=None)
        child = controller.launchd._isolated_env(layout, port=7938)
        if argv[0] == "start" and "product" in argv:
            _, final, _, _, _ = controller.product_launcher.preflight_preference_fallback(
                environ=base, prewarm=False, port=7938,
            )
            observed.append((base, child, final))
        else:
            observed.append((base, child, None))
        return 0

    monkeypatch.setattr(controller.product_launcher, "preflight_preference_fallback", preflight)
    monkeypatch.setattr(controller.prior.base_controller, "main", no_launch)
    monkeypatch.setattr(
        controller, "_record_source_surface_child_flags",
        lambda root, arm, env: attestations.append((root, arm, dict(env))),
    )
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", "on")
    assert controller.main(["prepare"]) == 0
    assert "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM" not in observed[-1][1]
    for arm in ("off", "on"):
        assert controller.main([
            "--source-event-surface-arm", arm, "--source-event-core-utility",
            "--compact-json-schema", "--direct-act-arm", "control", "--product-port", "7938",
            "start", "--mode", "product", "--prepared-runtime-root", str(layout["runtime_root"]),
        ]) == 0
        base, child, final = observed[-1]
        assert "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM" not in base
        assert child["URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM"] == arm
        assert final["URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM"] == arm
        assert child["URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT"] == str(layout["runtime_root"])
        assert final["URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT"] == str(layout["runtime_root"])
        assert child["URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED"] == "0"
        assert final["URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED"] == "0"
        assert attestations[-1][0:2] == (str(layout["runtime_root"]), arm)
        assert attestations[-1][2]["URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM"] == arm
    assert len(attestations) == 2
    for rejected in (
        ["--source-event-surface-arm", "on", "prepare"],
        ["--source-event-surface-arm", "on", "start", "--mode", "inert"],
        ["--source-event-surface-arm", "on", "start", "--mode", "product"],
        ["--source-event-surface-arm", "on", "--compact-json-schema", "start", "--mode", "product"],
        ["--source-event-surface-arm", "on", "--source-event-core-utility", "--compact-json-schema",
         "--direct-act-arm", "treatment", "start", "--mode", "product"],
        ["--source-event-surface-arm", "on", "--source-event-candidate-prompt", "--source-event-core-utility",
         "--compact-json-schema", "start", "--mode", "product"],
    ):
        before = len(observed)
        with pytest.raises(SystemExit):
            controller.main(rejected)
        assert len(observed) == before


def test_controller_records_run_bound_private_child_arm_values():
    import p4_direct_reply_act_m29_priority_detached_control as controller

    with _synthetic_prepared_run("off", attested=False) as root:
        run_id = exact_cap.current_exact_input_run_id(root)
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
        receipt_path = root / ".cache" / f"p4_source_surface_child_flags.{run_id}.json"
        receipt = exact_cap._read_private_json(receipt_path)
        assert receipt == {
            "schema": controller.SOURCE_SURFACE_ATTESTATION_SCHEMA,
            "runtime_root": str(root), "run_id": run_id,
            "pid": metadata["pid"], "port": metadata["port"],
            "flags": flags, "candidate_prompt_absent": True,
        }
        assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
        with pytest.raises(exact_cap.ExactInputCapabilityError):
            controller._record_source_surface_child_flags(str(root), "off", flags)


@pytest.mark.parametrize("change", [
    {"URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM": "on"},
    {"URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "0"},
    {"URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "1"},
    {"URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT": "1"},
])
def test_controller_rejects_wrong_private_child_flags(change):
    import p4_direct_reply_act_m29_priority_detached_control as controller

    with _synthetic_prepared_run("off", attested=False) as root:
        run_id = exact_cap.current_exact_input_run_id(root)
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
        flags.update(change)
        metadata["env_keys"] = sorted(flags)
        _private_json(metadata_path, metadata)
        with pytest.raises(RuntimeError, match="source_surface_child_flags_not_attestable"):
            controller._record_source_surface_child_flags(str(root), "off", flags)
        assert not (root / ".cache" / f"p4_source_surface_child_flags.{run_id}.json").exists()


def test_controller_attestation_failure_hides_success_and_attempts_exact_stop(monkeypatch, tmp_path, capsys):
    import p4_direct_reply_act_m29_priority_detached_control as controller

    layout = {
        "runtime_root": tmp_path / "prepared",
        "memory_db": tmp_path / "memory",
        "session_db": tmp_path / "session",
        "web_logs": tmp_path / "web_logs",
        "jsonl_log": tmp_path / "web_logs/conversation.jsonl",
        "text_log": tmp_path / "web_logs/conversation.txt",
    }
    root = str(layout["runtime_root"])
    stops = []

    def preflight(**kwargs):
        return {}, dict(kwargs["environ"]), layout, False, None

    def started(argv):
        controller.product_launcher.preflight_preference_fallback(
            environ=controller.launchd._isolated_env(layout, port=None),
            port=7938, prewarm=False,
        )
        print(json.dumps({"ok": True, "runtime_root": root}))
        return 0

    monkeypatch.setattr(controller.product_launcher, "preflight_preference_fallback", preflight)
    monkeypatch.setattr(controller.prior.base_controller, "main", started)
    monkeypatch.setattr(
        controller, "_record_source_surface_child_flags",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("test_attestation_failure")),
    )
    monkeypatch.setattr(
        controller.prior.base_controller, "stop",
        lambda target: stops.append(target) or {"ok": True},
    )
    assert controller.main([
        "--source-event-surface-arm", "on", "--source-event-core-utility",
        "--compact-json-schema", "--direct-act-arm", "control", "--product-port", "7938",
        "start", "--mode", "product", "--prepared-runtime-root", root,
    ]) == 2
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    receipt = json.loads(lines[0])
    assert receipt == {
        "ok": False, "error": "source_surface_child_flags_attestation_failed",
        "runtime_root": root, "exact_stop": {"ok": True, "stop_attempt_file": None},
    }
    assert stops == [root]
