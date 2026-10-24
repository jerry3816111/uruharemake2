from copy import deepcopy

from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
from uruha_memory_observatory import collect_cognitive_graph
import uruha_web_ui as web


SOURCE = "剛剛又收到一整串新註解，真的有完沒完。"
FOREIGN_CORE = "連註解都不停，真煩人。"
REPAIRED = "コメント止まんないの、普通にうざいな。"


class FakeAuthorizer:
    def __init__(self, *, accepted=True):
        self.accepted = accepted
        self.calls = []

    def authorize_literal_topic_m31(self, user_input, projection):
        self.calls.append((user_input, deepcopy(projection)))
        if not self.accepted:
            return None, {
                "status": "semantic_authority_rejected",
                "reason": "test_rejection",
                "surface_authority": False,
                "model_call_completed": True,
            }
        contract = {
            "status": "semantically_authorized",
            "reason": "source_first_semantics_and_safe_surface_validated",
            "surface_authority": True,
            "model_call_completed": True,
            "confidence": 0.91,
            "response_jp": REPAIRED,
            "surface_anchors_jp": ["コメント", "うざい"],
        }
        return {"core_message_jp": REPAIRED}, contract


def _brain(*, accepted=True):
    brain = object.__new__(UruhaBrainV4_Mac)
    brain.right_brain = RightBrain(load_model=False)
    brain.left_brain = FakeAuthorizer(accepted=accepted)
    return brain


def _logic(core=FOREIGN_CORE):
    return {
        "intent": "chat",
        "scene": "casual",
        "surface_act": "plain_reply",
        "core_message_jp": core,
        "semantic_language_repair_requested_m49": core == FOREIGN_CORE,
        "explicit_desired_response_m25": {"detected": False},
        "correction_aware_surface_m20": {"authoritative": False},
    }


def test_self_monitor_language_repair_keeps_semantic_source_in_plan():
    class CaptureRightBrain:
        def __init__(self):
            self.seen_core = None

        def speak(self, _user_input, logic, _memory_data, _psyche):
            self.seen_core = logic["core_message_jp"]
            assert logic["semantic_language_repair_requested_m49"] is True
            assert "元の意味" in logic["reply_goal"]
            return REPAIRED

        def _refine_conversational_reply(self, reply, *_args, **_kwargs):
            return reply

    brain = object.__new__(UruhaBrainV4_Mac)
    brain.right_brain = CaptureRightBrain()
    logic = _logic()
    repaired = brain._repair_reply_from_self_monitor(
        FOREIGN_CORE,
        logic,
        {"needs_repair": True, "issues": ["non_japanese_leak"]},
        SOURCE,
        {},
        {"mood": 0, "trust": 50},
    )

    assert repaired == REPAIRED
    assert brain.right_brain.seen_core == FOREIGN_CORE
    assert logic["self_monitor_repair"]["after"] == REPAIRED


def test_guard_valid_existing_japanese_core_is_restored_without_model_call():
    brain = _brain()
    logic = _logic("コメントが止まんないの、だるいな。")
    repaired, trace = brain._repair_user_visible_semantics_m49(
        "Translate the original meaning.",
        logic,
        SOURCE,
        memory_data={},
    )

    assert repaired == logic["core_message_jp"]
    assert trace["status"] == "existing_japanese_semantic_core_restored"
    assert trace["surface_authority"] is True
    assert trace["model_call_attempted"] is False
    assert brain.left_brain.calls == []


def test_foreign_core_uses_source_first_authorization_and_visible_anchors():
    brain = _brain()
    logic = _logic()
    repaired, trace = brain._repair_user_visible_semantics_m49(
        "日本語だけで、元の意味を落とさず言い直す",
        logic,
        SOURCE,
        memory_data={},
    )

    assert repaired == REPAIRED
    assert logic["core_message_jp"] == REPAIRED
    assert trace["status"] == "source_first_japanese_repair_authorized"
    assert trace["surface_authority"] is True
    assert trace["source_first_authorization"] is True
    assert trace["model_call_attempted"] is True
    assert trace["model_call_completed"] is True
    assert trace["surface_anchor_count"] == 2
    assert trace["surface_anchors_visible"] is True
    assert trace["raw_dialogue_persisted"] is False
    assert len(brain.left_brain.calls) == 1
    assert brain.left_brain.calls[0][1]["projection_required"] is True


def test_rejected_authorization_keeps_fail_closed_language_fallback():
    brain = _brain(accepted=False)
    logic = _logic()
    candidate, trace = brain._repair_user_visible_semantics_m49(
        "日本語だけで、元の意味を落とさず言い直す",
        logic,
        SOURCE,
        memory_data={},
    )
    visible = brain.right_brain.enforce_user_visible_japanese(
        candidate,
        logic,
        user_input=SOURCE,
        memory_data={},
    )

    assert trace["status"] == "semantic_repair_rejected"
    assert trace["surface_authority"] is False
    assert visible == "ん、その話もう少し聞かせて。"
    assert logic["visible_language_guard"]["final_rejection_reasons"] == []


def test_neutral_translation_cannot_erase_observable_complaint_act():
    class NeutralAuthorizer(FakeAuthorizer):
        def authorize_literal_topic_m31(self, user_input, projection):
            self.calls.append((user_input, deepcopy(projection)))
            neutral = "注釈がまた届くんだね。"
            return {"core_message_jp": neutral}, {
                "status": "semantically_authorized",
                "reason": "synthetic_neutral_candidate",
                "surface_authority": True,
                "model_call_completed": True,
                "confidence": 0.95,
                "response_jp": neutral,
                "surface_anchors_jp": ["注釈"],
            }

    brain = _brain()
    brain.left_brain = NeutralAuthorizer()
    original = "日本語だけで、元の意味を落とさず言い直す"
    repaired, trace = brain._repair_user_visible_semantics_m49(
        original,
        _logic(),
        SOURCE,
        memory_data={},
    )

    assert repaired == original
    assert trace["status"] == "semantic_repair_rejected"
    assert trace["required_observable_act"] == "frustration_complaint"
    assert trace["required_observable_act_preserved"] is False
    assert brain.left_brain.calls[0][1]["required_observable_act"] == "frustration_complaint"


def test_english_complaint_core_uses_same_observable_act_contract():
    class EnglishAuthorizer(FakeAuthorizer):
        def authorize_literal_topic_m31(self, user_input, projection):
            self.calls.append((user_input, deepcopy(projection)))
            candidate = "通知が止まんないの、だるいな。"
            return {"core_message_jp": candidate}, {
                "status": "semantically_authorized",
                "reason": "synthetic_english_source_authorized",
                "surface_authority": True,
                "model_call_completed": True,
                "confidence": 0.92,
                "response_jp": candidate,
                "surface_anchors_jp": ["通知", "だるい"],
            }

    brain = _brain()
    brain.left_brain = EnglishAuthorizer()
    logic = _logic("The notifications won't stop. This is annoying.")
    logic["semantic_language_repair_requested_m49"] = True
    repaired, trace = brain._repair_user_visible_semantics_m49(
        "The notifications won't stop. This is annoying.",
        logic,
        "The notifications won't stop. This is annoying.",
        memory_data={},
    )

    assert repaired == "通知が止まんないの、だるいな。"
    assert trace["status"] == "source_first_japanese_repair_authorized"
    assert trace["required_observable_act"] == "frustration_complaint"
    assert trace["required_observable_act_preserved"] is True


def test_protected_memory_route_never_calls_source_first_repair():
    brain = _brain()
    logic = {
        **_logic(),
        "intent": "recall_favorite",
        "memory_use_expected": True,
        "memory_anchor": {
            "kind": "favorite_drink",
            "jp_anchor": "ほうじ茶",
            "value": "ほうじ茶",
            "terms": ["ほうじ茶"],
        },
    }
    original = "日本語だけで、元の意味を落とさず言い直す"
    repaired, trace = brain._repair_user_visible_semantics_m49(
        original,
        logic,
        "今一番好きな飲み物は何？",
        memory_data={},
    )

    assert repaired == original
    assert trace["status"] == "protected_route_not_repaired"
    assert trace["reason"] == "memory_grounded_surface"
    assert brain.left_brain.calls == []


def test_graph_and_web_trace_expose_repair_authority_before_language_guard():
    repair = {
        "schema": "uruha_semantic_preserving_japanese_repair_m49",
        "status": "source_first_japanese_repair_authorized",
        "surface_authority": True,
    }
    graph = collect_cognitive_graph(
        {
            "user_text": SOURCE,
            "reply": REPAIRED,
            "runtime_trace": {
                "blackboard": [
                    {
                        "stage": "verify",
                        "label": "japanese_semantic_repair_m49",
                        "payload": repair,
                    },
                    {
                        "stage": "surface",
                        "label": "visible_language_guard",
                        "payload": {
                            "schema": "uruha_visible_language_guard_v1",
                            "repair_action": "none",
                        },
                    },
                ]
            },
        }
    )
    ids = {node["label"]: node["id"] for node in graph["nodes"]}
    edges = {(edge["source"], edge["target"]) for edge in graph["edges"]}

    assert (
        ids["japanese_semantic_repair_m49"],
        ids["visible_language_guard"],
    ) in edges
    compact = web._compact_runtime_trace_m24(
        {"semantic_preserving_japanese_repair_m49": repair}
    )
    assert compact["semantic_preserving_japanese_repair_m49"]["surface_authority"] is True
