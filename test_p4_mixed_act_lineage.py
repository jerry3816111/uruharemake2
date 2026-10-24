"""Zero-model contracts for opt-in producer lineage; no reply authority transfer."""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_mixed_act_lineage_p4 as lineage


DATA = json.loads((Path(__file__).parent / "datasets" /
                   "p4_mixed_act_lineage_probe_2026-10-20.json").read_text(encoding="utf-8"))
BY_ID = {row["id"]: row["input"] for row in DATA["product_turns"]}


class Brain:
    def __init__(self):
        self.runtime = SimpleNamespace(cycle_index=0, blackboard=[], turn_traces=[])
        self.left_brain = SimpleNamespace()
        self.right_brain = None

    def _push_blackboard(self, stage, label, payload, salience):
        self.runtime.blackboard.append({"stage": stage, "label": label,
                                        "payload": deepcopy(payload), "salience": salience})


@pytest.fixture
def harness(monkeypatch):
    monkeypatch.setattr(lineage, "_REGISTRY", {})
    captured = {}

    def ingest(brain, user_input, input_context=None):
        brain.runtime.cycle_index += 1
        brain.runtime.blackboard = []
        return {"user_input": user_input, "input_context": input_context or {}}

    def m31(_left, user_input, _projection, _route_context):
        return {"core_message_jp": "元の選定文はそのまま。"}, {
            "schema": adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
            "status": "semantically_authorized", "surface_authority": True,
            "input_digest": hashlib.sha256(user_input.encode()).hexdigest()[:16],
            "response_jp": "元の選定文はそのまま。",
        }

    def m32(auth):
        return {"core_message_jp": "元の選定文はそのまま。"}, {
            "schema": adaptive.SEMANTIC_COMMIT_REPAIR_SCHEMA_M32,
            "status": "deterministic_commit_repaired", "surface_authority": True,
            "source_m31_status": auth["status"],
            "response_jp": "元の選定文はそのまま。",
        }

    def tick(brain, event):
        raw = event["user_input"]
        _, auth = lineage.authorize_routed_m31_with_mixed_act_lineage_p4(
            brain.left_brain, raw, {}, {},
        )
        _, commit = lineage.build_m32_with_mixed_act_lineage_p4(auth)
        captured["producer_context"] = deepcopy(lineage._ACTIVE.get())
        return {"logic": {
            "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
            "core_message_jp": "元の選定文はそのまま。",
            "semantic_authorization_m31": auth,
            "semantic_commit_repair_m32": commit,
            "source_anchored_semantic_commit_m33": {"surface_authority": False},
        }, "route_info": {"route": "high_road"}}

    def emit(brain, event, tick_result):
        return {
            "reply": "元の選定文はそのまま。", "logic": tick_result["logic"],
            "runtime_trace": {"cycle_index": brain.runtime.cycle_index,
                              "blackboard": deepcopy(brain.runtime.blackboard)},
            "episode_doc": "User: " + event["user_input"] + " | Uruha: 元の選定文はそのまま。",
        }

    monkeypatch.setattr(lineage, "_ORIGINAL_INGEST", ingest)
    monkeypatch.setattr(lineage, "_ORIGINAL_ROUTED_M31", m31)
    monkeypatch.setattr(lineage, "_ORIGINAL_M32", m32)
    monkeypatch.setattr(lineage, "_ORIGINAL_TICK", tick)
    monkeypatch.setattr(lineage, "_ORIGINAL_EMIT", emit)
    return Brain(), captured


def _run(brain, raw):
    event = lineage.ingest_event_with_mixed_act_lineage_p4(brain, raw)
    tick = lineage.cognitive_tick_with_mixed_act_lineage_p4(brain, event)
    result = lineage.emit_response_with_mixed_act_lineage_p4(brain, event, tick)
    return event, tick, result


def test_mixed_action_spans_producer_edges_and_reply_are_distinct(harness):
    brain, captured = harness
    raw = BY_ID["L2_mixed_rewrite_and_recall"]
    event, tick, result = _run(brain, raw)
    receipt = tick["logic"][lineage.LABEL]
    assert receipt["status"] == "linked", receipt["reason"]
    assert receipt["source_role_act"] == "mixed_request"
    assert [item["type"] for item in receipt["actions"]] == [
        "quoted_rewrite", "past_user_place_recall",
    ]
    assert len({item["action_id"] for item in receipt["actions"]}) == 2
    quote = receipt["actions"][0]["raw_spans"][0]
    assert raw[quote[0]:quote[1]] == "集合場所はまだ相談中です"
    outside = "".join(raw[start:end] for start, end in receipt["actions"][1]["raw_spans"])
    assert "私が選んだ場所も思い出して教えて" in outside
    assert all(item["coverage_status"] == "unverified" for item in receipt["actions"])
    assert receipt["action_coverage_status"] == "unverified"
    assert [edge["type"] for edge in receipt["producer_edges"]] == [
        "event_to_m31", "m31_to_m32",
    ]
    assert receipt["producer_edges"][0]["from_id"] == event[lineage.EVENT_KEY]["event_id"]
    assert receipt["producer_edges"][1]["from_id"] == receipt["m31"]["proposal_id"]
    assert receipt["producer_edges"][1]["to_id"] == receipt["m32"]["proposal_id"]
    assert captured["producer_context"]["m31_attempts"] == 1
    assert captured["producer_context"]["m32_attempts"] == 1
    assert receipt["m31"]["surface_authority_retained"] is True
    assert receipt["m32"]["surface_authority_retained"] is True
    assert receipt["authority_transfer_permitted"] is False
    assert tick["logic"]["core_message_jp"] == result["reply"] == "元の選定文はそのまま。"
    assert result["runtime_trace"][lineage.LABEL] == receipt
    assert next(row["payload"] for row in result["runtime_trace"]["blackboard"]
                if row["label"] == lineage.LABEL) == receipt
    assert raw not in json.dumps(receipt, ensure_ascii=False)


def test_unrelated_mixed_request_does_not_claim_past_place_action(harness):
    brain, _ = harness
    raw = "「集合先は保留」を柔らかく言い換えて、これの意味も教えて。"
    event, tick, _ = _run(brain, raw)
    assert event[lineage.EVENT_KEY]["source_role_act"] == "mixed_request"
    assert tick["logic"][lineage.LABEL]["actions"] == []
    assert tick["logic"][lineage.LABEL]["authority_transfer_permitted"] is False


def test_missing_producers_and_protected_m33_are_not_linked(harness, monkeypatch):
    brain, _ = harness
    def no_producers(_brain, _event):
        return {"logic": {
            "intent": "chat", "scene": "casual", "core_message_jp": "元の返答。",
            "semantic_authorization_m31": {"surface_authority": False},
            "semantic_commit_repair_m32": {"surface_authority": False},
            "source_anchored_semantic_commit_m33": {"surface_authority": True},
        }, "route_info": {"route": "low_road"}}
    monkeypatch.setattr(lineage, "_ORIGINAL_TICK", no_producers)
    event, tick, _ = _run(brain, BY_ID["L3_protected_mixed"])
    receipt = tick["logic"][lineage.LABEL]
    assert receipt["status"] == "not_produced"
    assert receipt["m31"]["status"] == receipt["m32"]["status"] == "not_produced"
    assert "protected_source_role" in receipt["authority_blockers"]
    assert "m33_authoritative" in receipt["authority_blockers"]
    assert receipt["producer_edges"] == []
    assert receipt["authority_transfer_permitted"] is False
    assert event[lineage.EVENT_KEY]["actions"] == []


def test_unproduced_authoritative_contract_is_rejected_not_mislabeled_absent(harness, monkeypatch):
    brain, _ = harness
    def stale_contract_tick(_brain, _event):
        return {"logic": {
            "intent": "chat", "scene": "casual", "core_message_jp": "元の返答。",
            "semantic_authorization_m31": {"surface_authority": True},
            "semantic_commit_repair_m32": {"surface_authority": False},
        }, "route_info": {"route": "high_road"}}
    monkeypatch.setattr(lineage, "_ORIGINAL_TICK", stale_contract_tick)
    _, tick, _ = _run(brain, BY_ID["L2_mixed_rewrite_and_recall"])
    receipt = tick["logic"][lineage.LABEL]
    assert receipt["status"] == "rejected"
    assert receipt["reason"] == "unproduced_authoritative_or_stamped_contract"
    assert receipt["authority_transfer_permitted"] is False


@pytest.mark.parametrize("mutation,reason", [
    ("wrong_parent", "producer_parent_or_digest_mismatch"),
    ("wrong_event", "producer_parent_or_digest_mismatch"),
    ("wrong_digest", "producer_parent_or_digest_mismatch"),
    ("wrong_legacy_digest", "producer_parent_or_digest_mismatch"),
    ("duplicate_id", "duplicate_or_missing_id"),
    ("missing_parent", "producer_parent_or_digest_mismatch"),
])
def test_tampered_producer_chain_fails_closed(harness, mutation, reason):
    brain, captured = harness
    event, tick, _ = _run(brain, BY_ID["L2_mixed_rewrite_and_recall"])
    logic = deepcopy(tick["logic"])
    context = deepcopy(captured["producer_context"])
    m31 = logic["semantic_authorization_m31"]
    m32 = logic["semantic_commit_repair_m32"]
    if mutation == "wrong_parent":
        m32[lineage.PRODUCER_KEY]["parent_m31_id"] = "other-parent"
    elif mutation == "wrong_event":
        m31[lineage.PRODUCER_KEY]["parent_event_id"] = "other-event"
    elif mutation == "wrong_digest":
        m31[lineage.PRODUCER_KEY]["raw_input_sha256"] = "0" * 64
    elif mutation == "wrong_legacy_digest":
        m31["input_digest"] = "0" * 16
    elif mutation == "duplicate_id":
        context["m32_ids"][0] = context["m31_ids"][0]
        m32[lineage.PRODUCER_KEY]["proposal_id"] = context["m31_ids"][0]
    elif mutation == "missing_parent":
        m32[lineage.PRODUCER_KEY]["parent_m31_id"] = None
    audit = lineage.verify_mixed_act_lineage_p4(
        event, logic, registered_context=context, registration_reason="registered",
    )
    assert audit["status"] == "rejected"
    assert audit["reason"] == reason
    assert audit["producer_edges"] == []
    assert audit["authority_transfer_permitted"] is False


def test_event_copy_mutation_replay_and_no_context_fail_closed(harness):
    brain, captured = harness
    event = lineage.ingest_event_with_mixed_act_lineage_p4(
        brain, BY_ID["L2_mixed_rewrite_and_recall"],
    )
    copied = deepcopy(event)
    context, reason = lineage._registered_context(brain, copied)
    assert context is None and reason == "event_registration_mismatch"
    changed_text = deepcopy(event)
    changed_text["user_input"] += "別文"
    context, reason = lineage._registered_context(brain, changed_text)
    assert context is None and reason == "event_registration_mismatch"
    tick = lineage.cognitive_tick_with_mixed_act_lineage_p4(brain, event)
    context = deepcopy(captured["producer_context"])
    copied[lineage.EVENT_KEY]["event_id"] = "other-event"
    audit = lineage.verify_mixed_act_lineage_p4(
        copied, tick["logic"], registered_context=context, registration_reason="registered",
    )
    assert audit["status"] == "rejected"
    assert audit["reason"] == "event_certificate_or_digest_mismatch"
    assert lineage.verify_mixed_act_lineage_p4(event, tick["logic"])["status"] == "rejected"
    replay = lineage.cognitive_tick_with_mixed_act_lineage_p4(brain, event)
    assert replay["logic"][lineage.LABEL]["status"] == "rejected"
    assert replay["logic"][lineage.LABEL]["reason"] == "replayed_event"
    assert replay["logic"][lineage.LABEL]["authority_transfer_permitted"] is False


def test_producers_without_registered_turn_do_not_invent_lineage(harness):
    brain, _ = harness
    raw = BY_ID["L2_mixed_rewrite_and_recall"]
    _, auth = lineage.authorize_routed_m31_with_mixed_act_lineage_p4(
        brain.left_brain, raw, {}, {},
    )
    _, commit = lineage.build_m32_with_mixed_act_lineage_p4(auth)
    assert lineage.PRODUCER_KEY not in auth
    assert lineage.PRODUCER_KEY not in commit
    assert auth["surface_authority"] is True
    assert commit["surface_authority"] is True


def test_m32_must_receive_the_actual_m31_return_object(harness, monkeypatch):
    brain, _ = harness
    def copied_parent_tick(brain, event):
        raw = event["user_input"]
        _, auth = lineage.authorize_routed_m31_with_mixed_act_lineage_p4(
            brain.left_brain, raw, {}, {},
        )
        _, commit = lineage.build_m32_with_mixed_act_lineage_p4(deepcopy(auth))
        return {"logic": {
            "intent": "chat", "scene": "casual", "core_message_jp": "元の選定文はそのまま。",
            "semantic_authorization_m31": auth, "semantic_commit_repair_m32": commit,
        }, "route_info": {"route": "high_road"}}
    monkeypatch.setattr(lineage, "_ORIGINAL_TICK", copied_parent_tick)
    _, tick, _ = _run(brain, BY_ID["L2_mixed_rewrite_and_recall"])
    receipt = tick["logic"][lineage.LABEL]
    assert receipt["status"] == "rejected"
    assert receipt["reason"] == "producer_parent_or_digest_mismatch"
    assert receipt["authority_transfer_permitted"] is False
    assert tick["logic"]["semantic_commit_repair_m32"][lineage.PRODUCER_KEY][
        "parent_m31_direct_argument"
    ] is False


def test_real_opt_in_install_chain_resolves_without_model_or_ui_launch():
    script = r"""
import ast
from pathlib import Path
import uruha_web_ui_product_p4_mixed_act_lineage as entry
import uruha_mixed_act_lineage_p4 as lineage
tree = ast.parse(Path(entry.__file__).read_text(encoding='utf-8'))
main = next(node for node in tree.body if isinstance(node, ast.If))
before_demo = []
for node in main.body:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'demo' for target in node.targets):
        break
    before_demo.append(node)
exec(compile(ast.Module(body=before_demo, type_ignores=[]), entry.__file__, 'exec'), vars(entry))
assert lineage._INSTALLED
assert lineage.install_mixed_act_lineage_p4() is False
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                          text=True, timeout=45, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
