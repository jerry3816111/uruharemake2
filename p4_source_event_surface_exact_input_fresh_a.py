#!/usr/bin/env python3
"""One fresh M21 boundary, then paired off/on surface replay for frozen P4 A.

This is a one-shot, developer-authored *research diagnostic*, not a Web turn,
general safety classifier, naturalness rating, or strong-LLM comparison.
``--preflight-only`` uses a fake provider and synthetic controller metadata;
only ``--execute`` may contact the real local model, and it requires two
already-running, distinct controller-prepared product roots.  Neither mode
uses the formal memory DB or sends a Safari message.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import urllib.request


HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent.resolve()
ORIGINAL_DIRTY = Path("/Users/jerrychang/Desktop/uruharemake2").resolve()
FREEZE = HERE / "research/p4_source_event_surface_exact_input_capability_source_freeze_2026-10-24.sha256"
PROBE = HERE / "datasets/p4_source_event_surface_exact_input_capability_probe_2026-10-24.json"
FIXED = HERE / "datasets/p4_source_event_surface_diagnostic_probe_2026-10-24.json"
CASE_ID = "cap_fixed_envelope"
MODEL = "qwen2.5:7b"
MODEL_DIGEST = "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
TAGS_URL = "http://127.0.0.1:11434/api/tags"
OPENAI_URL = "http://127.0.0.1:11434/v1"
MAX_PROVIDER_TOKENS = 2000
MAX_PLANNER_SECONDS = 20.0
SCHEMA = "p4_source_event_surface_exact_input_fresh_a_v1"
GLOBAL_ATTEMPT_DIR = Path(tempfile.gettempdir()).resolve() / ".uruha-p4-source-surface-a-once"


class TrialTerminal(RuntimeError):
    """A failed trial with a private artifact pointer, never raw model text."""

    def __init__(self, reason: str, evidence_root: Path) -> None:
        super().__init__(reason)
        self.evidence_root = evidence_root


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_private(path: Path, payload: object) -> str:
    raw = _canonical(payload) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise RuntimeError("private_artifact_mode_invalid")
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        # The partial file is evidence; a second attempt must not overwrite it.
        raise
    return _sha(raw)


def _verify_frozen_sources() -> str:
    expected = {}
    for line in FREEZE.read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        if separator:
            expected[relative] = digest
    if len(expected) != 6:
        raise RuntimeError("source_freeze_entry_count_invalid")
    for relative, digest in expected.items():
        if not relative.startswith(("research/", "datasets/", "analysis/")):
            raise RuntimeError("source_freeze_path_invalid")
        if _sha((HERE / relative).read_bytes()) != digest:
            raise RuntimeError("source_freeze_mismatch")
    import uruha_source_event_exact_input_capability_p4 as cap

    approved = cap._approved_inputs()  # Verifies both manifest and probe digests.
    data = json.loads(PROBE.read_text(encoding="utf-8"))
    matches = [row for row in data.get("positive_cases", []) if row.get("id") == CASE_ID]
    if len(matches) != 1:
        raise RuntimeError("frozen_a_case_missing")
    source = matches[0].get("source")
    gold = matches[0].get("gold")
    if not isinstance(source, str) or not isinstance(gold, dict):
        raise RuntimeError("frozen_a_case_invalid")
    if approved.get(CASE_ID) != _sha(source.encode("utf-8")):
        raise RuntimeError("approved_full_input_sha_mismatch")
    fixed = json.loads(FIXED.read_text(encoding="utf-8"))
    if len(fixed.get("fixed_compact_plans", [])) != 3:
        raise RuntimeError("fixed_three_plan_fixture_invalid")
    return source


def _model_digest() -> str:
    """Read-only localhost model identity; this is not a generation call."""
    with urllib.request.urlopen(TAGS_URL, timeout=5) as response:
        tags = json.load(response)
    rows = [row for row in tags.get("models", []) if row.get("name") == MODEL]
    if len(rows) != 1 or rows[0].get("digest") != MODEL_DIGEST:
        raise RuntimeError("frozen_model_digest_missing_or_changed")
    return MODEL_DIGEST


def _require_clean_runner_ambient() -> None:
    """No inherited Uruha import-time flags in this fresh in-process replay."""
    if any(key.startswith("URUHA_") for key in os.environ):
        raise RuntimeError("runner_ambient_uruha_configuration_not_isolated")


def _require_request_parity(request: dict, preflight: dict) -> str:
    expected = preflight.get("request_sha256")
    actual = _sha(_canonical(request))
    if not isinstance(expected, str) or len(expected) != 64 or expected != actual:
        raise RuntimeError("fresh_m21_request_drift_from_fake_preflight")
    return actual


def _require_pre_send_token_upper_bound(_request: dict) -> None:
    """Fail closed until exact Ollama prompt-token accounting is reviewed.

    ``max_tokens=256`` caps only completion; response usage can detect, but
    cannot prevent, a >2000 total-token spend. A local HF tokenizer proxy is
    not a verified upper bound for this frozen Ollama request.
    """
    raise RuntimeError("pre_send_provider_total_token_bound_unverified")


def _pre_send_bound_ready() -> bool:
    # A future reviewed exact-tokenizer implementation must replace this
    # together with _require_pre_send_token_upper_bound, not just flip a flag.
    return False


def _private_root(parent: Path) -> Path:
    if parent.is_symlink():
        raise ValueError("private_parent_symlink")
    parent = parent.resolve(strict=True)
    info = parent.stat()
    if (not parent.is_dir() or parent.is_symlink() or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
            or parent == COLLECTION or parent.is_relative_to(COLLECTION)
            or parent == ORIGINAL_DIRTY or parent.is_relative_to(ORIGINAL_DIRTY)):
        raise ValueError("private_parent_must_be_owned_0700_outside_checkouts")
    root = Path(tempfile.mkdtemp(prefix="uruha-p4-source-surface-a-", dir=parent))
    root.chmod(0o700)
    if stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise RuntimeError("private_root_mode_invalid")
    return root


def _global_once_marker(source: str) -> Path:
    """One A attempt across all evidence parents and prepared controller roots."""
    directory = GLOBAL_ATTEMPT_DIR
    if directory.is_symlink() or directory.parent != Path(tempfile.gettempdir()).resolve():
        raise RuntimeError("global_attempt_directory_invalid")
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = os.lstat(directory)
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise RuntimeError("global_attempt_directory_not_private")
    return directory / f"{_sha(source.encode('utf-8'))}.attempted.json"


def _real_controller_ready(root: Path, expected_arm: str) -> dict:
    """Reject synthetic metadata by requiring the live controller's PID/HTTP proof."""
    import uruha_source_event_exact_input_capability_p4 as cap

    if expected_arm not in {"off", "on"}:
        raise ValueError("invalid_expected_arm")
    root, run_id = cap._root_and_run(root)
    metadata = cap._read_private_json(root / f"p4_preference_fallback_detached.{run_id}.json")
    port = metadata.get("port")
    if not isinstance(port, int):
        raise RuntimeError("controller_port_missing")
    env_keys = metadata.get("env_keys")
    required = {
        "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM",
        "URUHA_P4_COMPACT_JSON_SCHEMA",
        "URUHA_P4_SOURCE_EVENT_CORE_UTILITY",
        "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM",
        "URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT",
        "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED",
    }
    if (not isinstance(env_keys, list) or not required.issubset(set(env_keys))
            or "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT" in env_keys):
        raise RuntimeError("controller_surface_child_flags_not_attested")
    child_flags = cap._read_private_json(
        root / ".cache" / f"p4_source_surface_child_flags.{run_id}.json"
    )
    expected_flags = {
        "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
        "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM": expected_arm,
        "URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT": str(root),
        "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "0",
    }
    if (set(child_flags) != {
        "schema", "runtime_root", "run_id", "pid", "port", "flags", "candidate_prompt_absent",
    } or child_flags.get("schema") != "uruha_p4_source_surface_child_flags_v1"
            or child_flags.get("runtime_root") != str(root)
            or child_flags.get("run_id") != run_id
            or child_flags.get("pid") != metadata.get("pid")
            or child_flags.get("port") != port
            or child_flags.get("flags") != expected_flags
            or child_flags.get("candidate_prompt_absent") is not True):
        raise RuntimeError("controller_exact_child_arm_values_not_attested")
    command = [
        sys.executable, str(HERE / "p4_direct_reply_act_m29_priority_detached_control.py"),
        "--product-port", str(port), "verify-ready", "--runtime-root", str(root),
    ]
    checked = subprocess.run(command, cwd=HERE, capture_output=True, text=True, timeout=15, check=False)
    try:
        receipt = json.loads(checked.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError("controller_ready_receipt_unreadable") from exc
    if any((
        checked.returncode != 0, receipt.get("ok") is not True,
        receipt.get("ready") is not True, receipt.get("http_ready_verified") is not True,
        receipt.get("listener_same_pid_before_after") is not True,
        receipt.get("runtime_root") != str(root), receipt.get("run_id") != run_id,
        receipt.get("pid") != metadata.get("pid"), receipt.get("port") != port,
    )):
        raise RuntimeError("controller_live_ready_not_verified")
    if cap._root_and_run(root)[1] != run_id:
        raise RuntimeError("controller_current_run_changed_during_ready_check")
    return {
        "root": str(root), "run_id": run_id, "pid": receipt["pid"], "port": port,
        "child_flags_sha256": _sha(_canonical(child_flags)), "attested_arm": expected_arm,
    }


@contextmanager
def _flags(arm: str | None, root: Path | None):
    import uruha_brain_mac as runtime

    flags = {
        "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": "control",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "URUHA_P4_SOURCE_EVENT_CORE_UTILITY": "1",
        "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT": None,
        "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "0",
        "URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM": arm,
        "URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT": str(root) if root is not None else None,
    }
    prior = {key: os.environ.get(key) for key in flags}
    prior_budget = runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS
    try:
        for key, value in flags.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = MAX_PLANNER_SECONDS
        yield
    finally:
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = prior_budget
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _initial_projection(brain) -> dict:
    return {
        "memory_runtime": brain.memory.get_runtime_snapshot(),
        "saved_episodes": deepcopy(brain.memory.saved_episodes),
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


def _clone_seed(seed, *, surface_only_left_brain: bool = False):
    from test_personhood_loop_v2_13 import _IsolatedContractBrain

    brain = _IsolatedContractBrain()
    brain.memory = deepcopy(seed.memory)
    brain.psyche = deepcopy(seed.psyche)
    brain.runtime = deepcopy(seed.runtime)
    brain.runtime_config = brain.runtime.config
    # The post-M21 surface must never retain or call the live provider client.
    # All cognition outputs used by the surface are already in the captured
    # tick; this no-provider stand-in is an explicit replay limitation.
    if not surface_only_left_brain:
        brain.left_brain = deepcopy(seed.left_brain)
    brain.right_brain = deepcopy(seed.right_brain)
    brain.persona_policy_provider = seed.persona_policy_provider
    brain._last_external_input_at = seed._last_external_input_at
    brain._last_background_tick_at = seed._last_background_tick_at
    brain._last_timer_event_at = seed._last_timer_event_at
    brain._event_queue = deepcopy(seed._event_queue)
    brain._event_seq = seed._event_seq
    return brain


def _surface_state_projection(brain) -> dict:
    projection = _initial_projection(brain)
    # OpenAI clients and closures have no canonical JSON representation and
    # are not read by this bounded no-repair surface replay.
    projection["left_brain_state"] = {"provider_available_during_replay": False}
    return projection


def _capture_one_m21(source: str, create, off_root: Path, off_claim):
    """Return one complete post-M21 boundary; ``create`` is fake or metered real."""
    import uruha_brain_mac as runtime
    import uruha_compact_planner_p2 as compact
    import uruha_contextual_expression_commit_p2 as expression
    import uruha_web_ui_product_p4_direct_reply_act_m29_priority as product
    import uruha_source_event_exact_input_capability_p4 as cap
    from test_personhood_loop_v2_13 import _IsolatedContractBrain
    from test_p4_source_event_core_utility_f7 import _handoff

    compact.install_compact_planner_p2()
    expression.install_contextual_expression_commit_p2()
    product.install_product_chain()
    seed = _IsolatedContractBrain()
    seed.right_brain = runtime.RightBrain(load_model=False)
    seed.right_brain.model_blend_enabled = False
    if seed.right_brain.model is not None or seed.right_brain.history:
        raise RuntimeError("nonempty_or_model_right_brain_seed")
    initial_sha = _sha(_canonical(_initial_projection(seed)))
    brain = _clone_seed(seed)
    requests: list[dict] = []

    def exactly_one_create(**kwargs):
        if requests:
            raise RuntimeError("second_m21_attempt_prohibited")
        requests.append(deepcopy(kwargs))
        if any((
            kwargs.get("model") != MODEL, kwargs.get("max_tokens") != 256,
            kwargs.get("timeout") != MAX_PLANNER_SECONDS,
            kwargs.get("temperature") != 0.1,
            (kwargs.get("response_format") or {}).get("type") != "json_schema",
        )):
            raise RuntimeError("frozen_m21_request_arguments_changed")
        return create(**kwargs)

    brain.left_brain = runtime.LeftBrain(SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=exactly_one_create))
    ))
    expected_handoff = _handoff(source)
    with _flags("off", off_root):
        # The caller owns one scope spanning this capture and the off replay.
        # A second scoped entry would consume the one-use handle twice.
        if cap.require_exact_input_claim(off_root, source, "off") is not off_claim:
            raise RuntimeError("capture_off_claim_not_current")
        event = brain.ingest_event(source)
        if brain.left_brain._rule_based_plan(
            source, deepcopy(event["psyche_before"]), deepcopy(event["memory_data"])
        ) is not None:
            raise RuntimeError("frozen_a_not_full_planner")
        with redirect_stdout(io.StringIO()):
            tick = brain.cognitive_tick(event)
    if len(requests) != 1:
        raise RuntimeError("m21_call_count_not_one")
    handoff = deepcopy(tick.get("_source_event_surface_handoff_p4"))
    if handoff != expected_handoff:
        raise RuntimeError("same_turn_handoff_mismatch")
    raw = {"logic": deepcopy(tick["logic"]), "route_info": deepcopy(tick["route_info"])}
    if brain.memory.saved_episodes or brain.right_brain.history:
        raise RuntimeError("capture_wrote_episode_or_history")
    if _sha(_canonical(_initial_projection(seed))) != initial_sha:
        raise RuntimeError("seed_mutated_during_generation")
    post_seed = _clone_seed(brain, surface_only_left_brain=True)
    post_event = deepcopy(event)
    _sha(_canonical(_surface_state_projection(post_seed)))
    _sha(_canonical(post_event))
    return raw, handoff, seed, post_seed, post_event, requests[0]


def _replay_arm(arm: str, root: Path | None, source: str, raw: dict,
                handoff: dict, seed, post_seed, post_event, claim=None,
                *, already_scoped: bool = False) -> dict:
    import uruha_source_event_exact_input_capability_p4 as cap
    from uruha_source_event_surface_diagnostic_p4 import (
        admit_source_event_slot_p4, audit_final_source_event_p4,
    )
    from contextlib import nullcontext

    if arm not in {"default", "off", "on"}:
        raise ValueError("invalid_replay_arm")
    if arm == "default" and (root is not None or claim is not None):
        raise ValueError("default_requires_no_capability")
    if arm != "default" and (root is None or claim is None):
        raise ValueError("diagnostic_arm_requires_capability")
    if already_scoped and arm != "off":
        raise ValueError("only_off_capture_scope_can_be_reused_for_replay")
    brain = _clone_seed(post_seed)
    initial_sha = _sha(_canonical(_initial_projection(seed)))
    post_sha = _sha(_canonical(_surface_state_projection(brain)))
    event_sha = _sha(_canonical(post_event))
    raw_sha = _sha(_canonical(raw))
    brain.ingest_event = lambda _source, input_context=None: deepcopy(post_event)
    brain.cognitive_tick = lambda _event: {
        **deepcopy(raw), "_source_event_surface_handoff_p4": deepcopy(handoff),
    }
    if brain.right_brain.model is not None or brain.right_brain.model_blend_enabled:
        raise RuntimeError("replay_right_brain_model_not_disabled")
    provider_attempts = []

    def no_provider(*_args, **_kwargs):
        provider_attempts.append("attempted")
        raise RuntimeError("replay_provider_call_forbidden")

    # The replay substitutes the *already captured* cognitive result. Any
    # accidental LeftBrain call or newly constructed provider client fails.
    brain.left_brain.think = no_provider
    import openai
    original_openai = openai.OpenAI
    openai.OpenAI = no_provider
    independent_visible_audit = None
    try:
        with _flags(None if arm == "default" else arm, root):
            scope = nullcontext() if arm == "default" or already_scoped else cap.scoped_exact_input_claim(claim)
            with scope, redirect_stdout(io.StringIO()):
                if already_scoped and cap.require_exact_input_claim(root, source, "off") is not claim:
                    raise RuntimeError("off_replay_claim_not_same_scope")
                result = brain.run_turn_debug(source)
                if arm != "default":
                    independent_slot, _ = admit_source_event_slot_p4(
                        source, handoff, deepcopy(raw["logic"])
                    )
                    if independent_slot is None:
                        raise RuntimeError("independent_visible_source_slot_missing")
                    independent_visible_audit = audit_final_source_event_p4(
                        source, independent_slot, result.get("reply")
                    )
    finally:
        openai.OpenAI = original_openai
    if provider_attempts:
        raise RuntimeError("replay_provider_attempt_observed")
    reply = result.get("reply")
    graph = (result.get("runtime_trace") or {}).get("blackboard") or []
    if not isinstance(reply, str) or not reply:
        raise RuntimeError("replay_visible_reply_missing")
    if not brain.memory.saved_episodes or brain.memory.saved_episodes[-1]["reply"] != reply:
        raise RuntimeError("replay_episode_not_visible_reply")
    if not brain.right_brain.history or brain.right_brain.history[-1].get("content") != reply:
        raise RuntimeError("replay_history_not_visible_reply")
    utterances = [row for row in graph if row.get("label") == "utterance"]
    if (len(utterances) != 1 or not isinstance(utterances[0].get("payload"), dict)
            or utterances[0]["payload"].get("reply") != reply):
        raise RuntimeError("replay_utterance_graph_count_invalid")
    if _sha(_canonical(raw)) != raw_sha:
        raise RuntimeError("shared_raw_boundary_mutated")
    if (_sha(_canonical(_surface_state_projection(post_seed))) != post_sha
            or _sha(_canonical(post_event)) != event_sha):
        raise RuntimeError("shared_post_cognition_boundary_mutated")
    audit = result.get("logic", {}).get("source_event_surface_diagnostic_p4")
    if arm != "default":
        nodes = [row.get("payload") for row in graph
                 if row.get("label") == "source_event_exact_input_capability_p4"]
        if len(nodes) != 1 or nodes[0] != cap.public_claim_receipt(claim):
            raise RuntimeError("capability_graph_receipt_missing_or_extra")
        if not isinstance(audit, dict):
            raise RuntimeError("final_surface_audit_missing")
    return {
        "arm": arm,
        "initial_state_sha256": initial_sha,
        "post_cognition_state_sha256": post_sha,
        "post_ingest_event_sha256": event_sha,
        "raw_boundary_sha256": raw_sha,
        "final_reply": reply,
        "final_reply_sha256": _sha(reply.encode("utf-8")),
        "episode_reply_sha256": _sha(brain.memory.saved_episodes[-1]["reply"].encode("utf-8")),
        "history_reply_sha256": _sha(brain.right_brain.history[-1]["content"].encode("utf-8")),
        "utterance_count": len(utterances),
        "audit": deepcopy(audit),
        "independent_visible_audit": deepcopy(independent_visible_audit),
        "logic": deepcopy(result.get("logic")),
        "graph": deepcopy(graph),
        "provider_attempts_during_replay": len(provider_attempts),
    }


def _claim_pair(source: str, off_root: Path, on_root: Path):
    import uruha_source_event_exact_input_capability_p4 as cap

    if off_root.resolve(strict=True) == on_root.resolve(strict=True):
        raise RuntimeError("paired_roots_not_distinct")
    roots = {"off": off_root, "on": on_root}
    for arm, root in roots.items():
        cap.issue_exact_input_permit(root, CASE_ID, arm)
    claims = {}
    try:
        for arm, root in roots.items():
            claims[arm] = cap.claim_exact_input_permit(root, source, arm)
            cap.validate_exact_input_claim(claims[arm], root, source, arm)
    except BaseException:
        for claim in claims.values():
            cap.close_exact_input_claim(claim)
        raise
    return claims


def _fake_response(source: str):
    fixed = json.loads(FIXED.read_text(encoding="utf-8"))
    plans = deepcopy(fixed["fixed_compact_plans"])

    def create(**_kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
            finish_reason="stop",
        )])

    return create


def _run_preflight(source: str) -> dict:
    # Synthetic controller identities are only acceptable in this mock branch.
    from test_p4_source_event_surface_diagnostic_route import _synthetic_prepared_run
    import uruha_source_event_exact_input_capability_p4 as cap

    with _synthetic_prepared_run("off") as off_root, _synthetic_prepared_run("on") as on_root:
        claims = _claim_pair(source, off_root, on_root)
        try:
            with cap.scoped_exact_input_claim(claims["off"]):
                raw, handoff, seed, post_seed, post_event, request = _capture_one_m21(
                    source, _fake_response(source), off_root, claims["off"],
                )
                if not _completed_compact_boundary(raw):
                    raise RuntimeError("preflight_m21_route_not_full_compact")
                if (raw["logic"].get("source_event_core_utility_p4") or {}).get("status") != "no_grounded_candidate":
                    raise RuntimeError("preflight_f7_no_grounded_branch_missing")
                off = _replay_arm(
                    "off", off_root, source, deepcopy(raw), handoff, seed, post_seed, post_event,
                    claims["off"], already_scoped=True,
                )
            raw_sha = _sha(_canonical(raw))
            default = _replay_arm(
                "default", None, source, deepcopy(raw), handoff, seed, post_seed, post_event,
            )
            on = _replay_arm(
                "on", on_root, source, deepcopy(raw), handoff, seed, post_seed, post_event, claims["on"],
            )
            if (default["final_reply"] != off["final_reply"]
                    or len({row["initial_state_sha256"] for row in (default, off, on)}) != 1
                    or len({row["post_cognition_state_sha256"] for row in (default, off, on)}) != 1
                    or len({row["post_ingest_event_sha256"] for row in (default, off, on)}) != 1
                    or len({row["raw_boundary_sha256"] for row in (default, off, on)}) != 1
                    or _sha(_canonical(raw)) != raw_sha):
                raise RuntimeError("preflight_paired_parity_failed")
            if (off["audit"].get("status") != "mismatch"
                    or off["independent_visible_audit"].get("status") != "mismatch"
                    or on["audit"].get("status") != "matched"
                    or on["independent_visible_audit"].get("status") != "matched"):
                raise RuntimeError("preflight_on_only_structural_gold_failed")
            if len(on["final_reply"]) > 28:
                raise RuntimeError("preflight_visible_length_gold_failed")
            return {
                "status": "fake_m21_preflight_only_no_provider",
                "mock_controller_roots": True,
                "source_sha256": _sha(source.encode("utf-8")),
                "request_sha256": _sha(_canonical(request)),
                "initial_state_sha256": off["initial_state_sha256"],
                "post_cognition_state_sha256": off["post_cognition_state_sha256"],
                "post_ingest_event_sha256": off["post_ingest_event_sha256"],
                "raw_boundary_sha256": raw_sha,
                "default_equals_off": True,
                "off_audit_status": off["audit"].get("status"),
                "on_audit_status": on["audit"].get("status"),
                "on_final_reply_for_author_review": on["final_reply"],
                "on_final_reply_sha256": on["final_reply_sha256"],
                "provider_generations": 0,
            }
        finally:
            for claim in claims.values():
                cap.close_exact_input_claim(claim)


def _require_fixed_gold_review(path: Path, source: str, preflight: dict) -> dict:
    """Require external author judgment; a passing audit alone is not gold."""
    if path.is_symlink():
        raise RuntimeError("fixed_gold_review_symlink")
    try:
        path = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError("fixed_gold_review_missing") from exc
    info = os.lstat(path)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or path.is_relative_to(COLLECTION) or path.is_relative_to(ORIGINAL_DIRTY)
            or info.st_size < 2 or info.st_size > 16 * 1024):
        raise RuntimeError("fixed_gold_review_not_private_external_file")
    data = json.loads(path.read_text(encoding="utf-8"))
    frozen = json.loads(PROBE.read_text(encoding="utf-8"))
    case = next(row for row in frozen["positive_cases"] if row["id"] == CASE_ID)
    expected = {
        "schema": "p4_source_event_surface_a_human_author_review_v1",
        "case_id": CASE_ID,
        "source_sha256": _sha(source.encode("utf-8")),
        "fixed_gold_sha256": _sha(_canonical(case["gold"])),
        "on_final_reply_sha256": preflight["on_final_reply_sha256"],
        "reviewer_kind": "user_supplied_human_author",
        "natural_japanese": True,
        "persona_consistent": True,
        "not_overliteral_or_invented": True,
        "verdict": "pass",
    }
    if not isinstance(data, dict) or any(data.get(key) != value for key, value in expected.items()):
        raise RuntimeError("fixed_gold_human_author_review_missing_or_mismatched")
    return {"review_file_sha256": _sha(path.read_bytes()), "review_kind": data["reviewer_kind"]}


def _completed_compact_boundary(raw: dict) -> bool:
    m21 = (raw.get("logic") or {}).get("bounded_slow_path_m21") or {}
    compact = m21.get("compact_general_plan_p2") or {}
    return bool(
        m21.get("route") == "full_planner"
        and m21.get("status") == "completed_within_budget"
        and m21.get("fallback_used") is False
        and m21.get("model_call_completed") is True
        and compact.get("completed") is True
        and compact.get("candidate_count") == 3
        and not compact.get("source_event_candidate_prompt_p4")
        and raw.get("logic", {}).get("planner_repair_applied") is False
    )


def _planner_elapsed_seconds(started: float) -> float:
    return time.perf_counter() - started


def _run_execute(source: str, off_root: Path, on_root: Path, parent: Path,
                 fixed_gold_review: Path) -> dict:
    import uruha_source_event_exact_input_capability_p4 as cap
    from openai import OpenAI
    from uruha_compute_ledger import ComputeLedger, instrument_openai_client

    if off_root.resolve(strict=True) == on_root.resolve(strict=True):
        raise RuntimeError("paired_roots_not_distinct")
    evidence_parent = parent.resolve(strict=True)
    for controller_root in (off_root.resolve(strict=True), on_root.resolve(strict=True)):
        if (evidence_parent == controller_root
                or evidence_parent.is_relative_to(controller_root)
                or controller_root.is_relative_to(evidence_parent)):
            raise RuntimeError("evidence_parent_overlaps_controller_root")
    preflight = _run_preflight(source)  # Zero provider; hard stop if fixed on-only gate drifted.
    review_receipt = _require_fixed_gold_review(fixed_gold_review, source, preflight)
    off_ready = _real_controller_ready(off_root, "off")
    on_ready = _real_controller_ready(on_root, "on")
    if off_ready["port"] == on_ready["port"] or off_ready["pid"] == on_ready["pid"]:
        raise RuntimeError("paired_controller_identity_not_distinct")
    _model_digest()
    root = _private_root(parent)
    report = {
        "schema": SCHEMA, "status": "attempted_incomplete",
        "evidence_level": "one_fresh_m21_boundary_then_isolated_surface_replay_not_web",
        "private_evidence_root": str(root),
        "source_sha256": _sha(source.encode("utf-8")),
        "model": MODEL, "model_digest": MODEL_DIGEST,
        "off_controller": off_ready, "on_controller": on_ready,
        "provider_generation_max": 1, "replay_provider_generation_max": 0,
        "provider_attempts": 0, "provider_total_tokens": None,
        "planner_seconds": None, "arms": [],
        "fixed_gold_review": review_receipt,
        "b_safari_authorized": False,
    }
    claims = {}
    try:
        # This fixed owned 0700 directory makes the single frozen A trial
        # machine-local and independent of caller-selected evidence parents.
        # Claim it before any cognition/provider call; a crash burns the slot.
        _write_private(_global_once_marker(source), {
            "schema": SCHEMA, "status": "attempt_claimed_no_retry",
            "evidence_root": str(root), "source_sha256": report["source_sha256"],
            "off_run_id": off_ready["run_id"], "on_run_id": on_ready["run_id"],
        })
        # A second per-parent marker keeps the evidence directory self-auditing.
        _write_private(parent / f".uruha-p4-source-surface-a-{report['source_sha256']}.attempted.json", {
            "schema": SCHEMA, "status": "attempt_claimed_no_retry",
            "evidence_root": str(root), "source_sha256": report["source_sha256"],
            "off_run_id": off_ready["run_id"], "on_run_id": on_ready["run_id"],
        })
        _write_private(root / "admission.json", report)
        # Both one-use claims are consumed before any A user cognition or
        # generation; failures after this point retain the terminal receipt.
        claims = _claim_pair(source, off_root, on_root)
        if (_real_controller_ready(off_root, "off") != off_ready
                or _real_controller_ready(on_root, "on") != on_ready):
            raise RuntimeError("controller_identity_changed_after_permit_claim")
        ledger = ComputeLedger()
        raw_client = OpenAI(base_url=OPENAI_URL, api_key="ollama", max_retries=0)
        metered = instrument_openai_client(raw_client, ledger)
        captured = []

        def create(**kwargs):
            if captured:
                raise RuntimeError("second_provider_attempt_prohibited")
            _require_request_parity(kwargs, preflight)
            _require_pre_send_token_upper_bound(kwargs)
            captured.append(deepcopy(kwargs))
            report["provider_attempts"] = 1
            # Persist the exact request before crossing the ambiguous provider
            # boundary. A timeout/crash is terminal, never retried.
            _write_private(root / "m21_request_before_call.json", kwargs)
            response = metered.chat.completions.create(**kwargs)
            raw_text = response.choices[0].message.content
            usage = response.usage.model_dump() if response.usage is not None else None
            _write_private(root / "m21_response_after_call.json", {
                "response_content": raw_text,
                "finish_reason": response.choices[0].finish_reason,
                "usage": usage,
            })
            if response.choices[0].finish_reason != "stop" or usage is None:
                raise RuntimeError("m21_finish_or_usage_incomplete")
            return response

        started = time.perf_counter()
        with cap.scoped_exact_input_claim(claims["off"]):
            raw, handoff, seed, post_seed, post_event, request = _capture_one_m21(
                source, create, off_root, claims["off"],
            )
            m21_elapsed = _planner_elapsed_seconds(started)
            _write_private(root / "post_m21_boundary.json", {
                "raw": raw, "handoff": handoff,
                "initial_state_sha256": _sha(_canonical(_initial_projection(seed))),
                "post_cognition_state_sha256": _sha(_canonical(_surface_state_projection(post_seed))),
                "post_ingest_event_sha256": _sha(_canonical(post_event)),
            })
            report["planner_seconds"] = round(m21_elapsed, 6)
            report["request_sha256"] = _sha(_canonical(request))
            report["raw_boundary_sha256"] = _sha(_canonical(raw))
            report["source_utility_status"] = (raw["logic"].get("source_event_core_utility_p4") or {}).get("status")
            summary = ledger.snapshot()["summary"]
            report["provider_total_tokens"] = summary.get("total_tokens")
            report["provider_prompt_tokens"] = summary.get("prompt_tokens")
            report["provider_completion_tokens"] = summary.get("completion_tokens")
            _model_digest()
            if any((
                len(captured) != 1, summary.get("generative_call_count") != 1,
                summary.get("generative_token_accounting_complete") is not True,
                not isinstance(summary.get("total_tokens"), int),
                (summary.get("total_tokens") or 0) > MAX_PROVIDER_TOKENS,
                m21_elapsed > MAX_PLANNER_SECONDS,
                not _completed_compact_boundary(raw),
            )):
                raise RuntimeError("fresh_m21_route_resource_or_accounting_gate_failed")
            off_replay = _replay_arm(
                "off", off_root, source, deepcopy(raw), handoff, seed, post_seed, post_event,
                claims["off"], already_scoped=True,
            )
        raw_sha = report["raw_boundary_sha256"]
        replay_by_arm = {}
        for arm, arm_root, claim in (
            ("default", None, None), ("off", off_root, claims["off"]),
            ("on", on_root, claims["on"]),
        ):
            one = off_replay if arm == "off" else _replay_arm(
                arm, arm_root, source, deepcopy(raw), handoff, seed, post_seed, post_event, claim,
            )
            replay_by_arm[arm] = one
            _write_private(root / f"{arm}_replay_private.json", one)
            report["arms"].append({
                "arm": arm,
                "initial_state_sha256": one["initial_state_sha256"],
                "post_cognition_state_sha256": one["post_cognition_state_sha256"],
                "post_ingest_event_sha256": one["post_ingest_event_sha256"],
                "raw_boundary_sha256": one["raw_boundary_sha256"],
                "final_reply_sha256": one["final_reply_sha256"],
                "audit_status": (one["audit"] or {}).get("status"),
                "visible_relation_status": (one["independent_visible_audit"] or {}).get("status"),
                "utterance_count": one["utterance_count"],
                "provider_attempts_during_replay": one["provider_attempts_during_replay"],
            })
        if (_sha(_canonical(raw)) != raw_sha
                or len({row["initial_state_sha256"] for row in report["arms"]}) != 1
                or len({row["post_cognition_state_sha256"] for row in report["arms"]}) != 1
                or len({row["post_ingest_event_sha256"] for row in report["arms"]}) != 1
                or len({row["raw_boundary_sha256"] for row in report["arms"]}) != 1
                or report["arms"][0]["final_reply_sha256"] != report["arms"][1]["final_reply_sha256"]):
            raise RuntimeError("fresh_a_initial_or_boundary_or_default_off_parity_failed")
        off, on = report["arms"][1:]
        if report["source_utility_status"] != "no_grounded_candidate":
            report["status"] = "fresh_f7_not_no_grounded_candidate_a_fail"
        elif (off["audit_status"] != "mismatch" or off["visible_relation_status"] != "mismatch"
                or on["audit_status"] != "matched" or on["visible_relation_status"] != "matched"
                or len(replay_by_arm["on"]["final_reply"]) > 28):
            report["status"] = "surface_structural_gold_fail"
        else:
            report["status"] = "surface_structural_pass_author_naturalness_pending"
        # The author must inspect the private reply for naturalness/persona.
        # This runner never automatically authorizes B's Safari Send.
        return report
    except BaseException as exc:
        report["status"] = report["status"] if report["status"] != "attempted_incomplete" else "terminal_failure"
        report["terminal_error_type"] = type(exc).__name__
        report["terminal_error"] = str(exc)[:160]
        if isinstance(exc, Exception):
            raise TrialTerminal(str(exc), root) from exc
        raise
    finally:
        for claim in claims.values():
            cap.close_exact_input_claim(claim)
        if not (root / "terminal_receipt.json").exists():
            _write_private(root / "terminal_receipt.json", report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--off-root", type=Path)
    parser.add_argument("--on-root", type=Path)
    parser.add_argument("--private-parent", type=Path)
    parser.add_argument("--fixed-gold-review", type=Path)
    args = parser.parse_args(argv)
    _require_clean_runner_ambient()
    source = _verify_frozen_sources()
    if args.preflight_only:
        if any((args.off_root, args.on_root, args.private_parent, args.fixed_gold_review)):
            parser.error("preflight does not accept real roots or private parent")
        # This local identity check does not invoke a model completion.
        _model_digest()
        print(json.dumps(_run_preflight(source), ensure_ascii=False, sort_keys=True))
        return 0
    if not all((args.off_root, args.on_root, args.private_parent, args.fixed_gold_review)):
        parser.error("execute requires two live controller roots, private parent, and external human-author fixed-gold review")
    # A frozen total-token ceiling is not a hard bound until the exact local
    # server tokenizer/template are validated before this one-shot call.
    if not _pre_send_bound_ready():
        print(json.dumps({
            "status": "review_required",
            "reason_code": "pre_send_provider_total_token_bound_unverified",
            "provider_generations": 0,
            "b_safari_authorized": False,
        }, sort_keys=True), file=sys.stderr)
        return 2
    try:
        report = _run_execute(source, args.off_root, args.on_root, args.private_parent,
                              args.fixed_gold_review)
    except Exception as exc:
        # The detailed exception and any model text stay in the private terminal
        # artifact. Do not spill a provider traceback into public CLI output.
        pointer = None
        retry_prohibited = False
        if isinstance(exc, TrialTerminal):
            candidate = exc.evidence_root / "terminal_receipt.json"
            if candidate.is_file():
                pointer = str(candidate)
            marker = _global_once_marker(source)
            try:
                marked = json.loads(marker.read_text(encoding="utf-8"))
                retry_prohibited = marked.get("evidence_root") == str(exc.evidence_root)
            except (OSError, ValueError, TypeError):
                pass
        print(json.dumps({
            "status": "terminal_or_presend_failure",
            "reason_code": type(exc).__name__,
            "private_terminal_receipt": pointer,
            "provider_retry_prohibited": retry_prohibited,
        }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({key: value for key, value in report.items() if key != "arms"},
                     ensure_ascii=False, sort_keys=True))
    # A completed collection with author review still pending is not a gate
    # PASS; callers must not chain B merely because this process returned 0.
    return 3 if report["status"] == "surface_structural_pass_author_naturalness_pending" else 2


if __name__ == "__main__":
    raise SystemExit(main())
