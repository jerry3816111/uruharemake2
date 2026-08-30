"""M39 final semantic/persona surface-act verification.

The earlier pragmatic ledger decides *which* response policy to use.  M39 does
not revisit that decision.  It inspects only the final user-visible Japanese
surface for three bounded, observable failures:

* source speaker/third-party role inversion;
* additions of a small set of unsupported event/time/cause concepts; and
* failure to actually perform the already-selected response policy.

The trace stores typed findings and digests, never raw dialogue or private-state
claims.  Protected routes are left untouched.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy


SCHEMA_M39 = "uruha_semantic_persona_surface_verifier_m39"
PROTECTED_ROUTES_M39 = {"safety_sensitive", "factual_or_memory", "deliberation"}

_AGENT_FIRST_PERSON = re.compile(r"(?:^|[。！？\s])(?:私|わたし|うち|一ノ瀬うるは)(?:は|が|、)")
_USER_STATE_PREDICATE = re.compile(
    r"寝|起き|眠|胃|頭|痛|食べ|震|焦|落ち着かな|進んでな|イラつ|困って|怖|不安|行きたく|行きたい|したく|したい"
)
_USER_ADDRESS = re.compile(r"(?:^|[。！？\s])(?:お前|君|あんた|あなた)(?:は|が|、)?")

_FORMAL_REGISTER = re.compile(
    r"承知しました|かしこまりました|どうぞお話しください|(?:です|ます|ください|しましょう)(?:[。！？]|$)"
)

_POLICY_ACT_PATTERNS = {
    "share_arousal": re.compile(r"一緒|ここにいる|そばにいる|隣にいる|付き合|待っとく|そばにおる"),
    "listen_presence": re.compile(r"最後まで聞|聞いてる|話して|話せ|続けて|吐き出|聞くから"),
    "solve_regulation": re.compile(r"まず|先に|一個|一つ|ひとつ|決めよ|手をつけ|整理しよ|やってみ"),
    "care_physiology": re.compile(r"無理すんな|休め|休も|水|食べ|口に入れ|横にな|呼吸|しんど|ゆっくり"),
    "calibrate_need": re.compile(r"どっち|どうしてほしい|何がほしい|どれに近い|どっちに近い|教えて[。？]?$"),
    "playful_tease": re.compile(r"元気すぎ|全力運転|暴走|過動|脳みそ|笑う|じゃん|すぎだろ"),
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _contains_any(text, patterns):
    lowered = str(text or "").lower()
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in patterns)


def _source_frame_m39(source):
    text = str(source or "")
    lowered = text.lower()
    first_person = bool(
        re.search(r"\b(?:i|i'm|i've|i'd|my|me)\b", lowered)
        or re.search(r"我|我的|俺|僕|自分|私", text)
    )
    third_party = bool(
        re.search(
            r"\b(?:friend|roommate|sister|brother|mother|father|coworker|classmate|he|she|they)\b",
            lowered,
        )
        or re.search(r"朋友|室友|妹妹|弟弟|姐姐|哥哥|同學|同学|同事|他|她|友達|妹|弟|姉|兄|母|父", text)
    )
    concepts = []
    if _contains_any(text, [r"sleep", r"awake", r"沒睡", r"没睡", r"睡", r"寝", r"眠"]):
        concepts.append("sleep_state")
    if _contains_any(text, [r"head", r"stomach", r"shaky", r"eat", r"胃", r"頭", r"痛", r"食べ", r"吃", r"抖"]):
        concepts.append("physical_state")
    if _contains_any(text, [r"draft", r"report", r"submission", r"進度", r"报告", r"報告", r"提出物", r"進ま"]):
        concepts.append("work_progress")
    if _contains_any(text, [r"thought", r"brain", r"loop", r"腦", r"脑", r"頭", r"思考", r"止まら"]):
        concepts.append("cognitive_arousal")
    if _contains_any(text, [r"wait", r"result", r"reply", r"response", r"等待", r"結果", r"结果", r"回覆", r"回复", r"待つ", r"返事", r"連絡"]):
        concepts.append("external_wait_or_result")
    if _contains_any(text, [r"morning", r"since four", r"朝", r"早上", r"四時", r"4時"]):
        concepts.append("morning_time")
    if _contains_any(text, [r"work", r"job", r"仕事", r"工作"]):
        concepts.append("work_cause")
    return {
        "schema": "uruha_observable_source_frame_m39",
        "speaker_role": "user_first_person" if first_person else "unspecified",
        "third_party_present": third_party,
        "observable_concepts": sorted(set(concepts)),
        "source_digest": _digest(text),
        "raw_source_persisted": False,
    }


def _selected_policy_m39(logic):
    logic = logic or {}
    branch = logic.get("counterfactual_pragmatic_branch_m34") or {}
    selected = str(((branch.get("selected_branch") or {}).get("policy_id")) or "")
    if selected:
        return selected
    return str(
        logic.get("desired_response_policy_m18")
        or ((logic.get("desired_response_decision_m18") or {}).get("selected") or {}).get("policy_id")
        or ""
    )


def _route_type_m39(logic):
    return str(((logic or {}).get("semantic_route_m22") or {}).get("selected_type") or "")


def _role_violations_m39(frame, reply):
    reply = str(reply or "")
    violations = []
    if (
        frame.get("speaker_role") == "user_first_person"
        and _AGENT_FIRST_PERSON.search(reply)
        and _USER_STATE_PREDICATE.search(reply)
    ):
        violations.append("agent_first_person_owns_user_state")
    if (
        frame.get("third_party_present")
        and _USER_ADDRESS.search(reply)
        and _USER_STATE_PREDICATE.search(reply)
    ):
        violations.append("user_owns_third_party_state")
    return violations


def _unsupported_additions_m39(frame, reply):
    reply = str(reply or "")
    source_concepts = set(frame.get("observable_concepts") or [])
    violations = []
    if "external_wait_or_result" not in source_concepts and re.search(r"結果|返事|連絡|来るまで", reply):
        violations.append("external_reply_or_result")
    if "morning_time" not in source_concepts and re.search(r"朝から|今朝|四時|4時", reply):
        violations.append("unsupported_morning_time")
    if "work_cause" not in source_concepts and re.search(r"仕事で|仕事のせい", reply):
        violations.append("unsupported_work_cause")
    return violations


def policy_act_matches_m39(reply, policy_id):
    policy_id = str(policy_id or "")
    if not policy_id:
        return True
    pattern = _POLICY_ACT_PATTERNS.get(policy_id)
    return bool(pattern and pattern.search(str(reply or "")))


def formal_register_detected_m39(reply):
    return bool(_FORMAL_REGISTER.search(str(reply or "")))


def _repair_reply_m39(frame, policy_id):
    concepts = set(frame.get("observable_concepts") or [])
    policy_id = str(policy_id or "")
    if policy_id == "share_arousal":
        if "work_progress" in concepts:
            return "進んでないのか。まあ、今はうちがここにいる。"
        if "cognitive_arousal" in concepts:
            return "頭が止まらないのか。まあ、今はうちがここにいる。"
        return "そっか。まあ、今はうちがここにいる。"
    if policy_id == "listen_presence":
        return "その話、最後まで聞く。続けて。"
    if policy_id == "solve_regulation":
        return "じゃあ、まず一個だけ決めよ。今すぐ終わる小さいやつ。"
    if policy_id == "care_physiology":
        if "sleep_state" in concepts:
            return "寝てないのか。そりゃしんどいだろ、無理すんな。"
        if "physical_state" in concepts:
            return "それ、体しんどいだろ。今は無理すんな。"
        return "しんどいなら、今は無理すんな。"
    if policy_id == "calibrate_need":
        return "今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？"
    if policy_id == "playful_tease":
        if "cognitive_arousal" in concepts:
            return "頭ずっと全力運転じゃん。ちょっとは休憩覚えろって。"
        return "脳みそ元気すぎだろ。少し落ち着けって。"
    return "ん、そこもう少しだけ聞かせて。"


def inspect_surface_m39(user_input, reply, logic):
    frame = _source_frame_m39(user_input)
    policy_id = _selected_policy_m39(logic)
    route_type = _route_type_m39(logic)
    protected = route_type in PROTECTED_ROUTES_M39
    role_violations = [] if protected else _role_violations_m39(frame, reply)
    unsupported = [] if protected else _unsupported_additions_m39(frame, reply)
    policy_act_match = True if protected else policy_act_matches_m39(reply, policy_id)
    formal_register = False if protected else formal_register_detected_m39(reply)
    return {
        "source_frame": frame,
        "selected_policy_id": policy_id or None,
        "semantic_route_selected_type": route_type or None,
        "protected_route": protected,
        "role_violations": role_violations,
        "unsupported_additions": unsupported,
        "policy_act_match": policy_act_match,
        "formal_register_detected": formal_register,
    }


def verify_and_repair_surface_m39(user_input, reply, logic):
    """Return a bounded final reply and a raw-free audit trace."""

    before = str(reply or "").strip()
    audit_before = inspect_surface_m39(user_input, before, logic)
    protected = bool(audit_before.get("protected_route"))
    violations = [
        *(audit_before.get("role_violations") or []),
        *(audit_before.get("unsupported_additions") or []),
    ]
    if audit_before.get("formal_register_detected"):
        violations.append("formal_register")
    if not audit_before.get("policy_act_match"):
        violations.append("selected_policy_not_realized")

    if protected:
        final_reply = before
        action = "not_applicable"
    elif violations:
        final_reply = _repair_reply_m39(
            audit_before.get("source_frame") or {},
            audit_before.get("selected_policy_id"),
        )
        action = "repair"
    else:
        final_reply = before
        action = "accept"

    audit_after = inspect_surface_m39(user_input, final_reply, logic)
    unresolved = [
        *(audit_after.get("role_violations") or []),
        *(audit_after.get("unsupported_additions") or []),
    ]
    if audit_after.get("formal_register_detected"):
        unresolved.append("formal_register")
    if not audit_after.get("policy_act_match"):
        unresolved.append("selected_policy_not_realized")

    trace = {
        "schema": SCHEMA_M39,
        "status": (
            "protected_route_not_modified"
            if protected
            else "repaired_and_verified"
            if action == "repair" and not unresolved
            else "repair_failed_closed"
            if unresolved
            else "accepted_verified_surface"
        ),
        "action": action,
        "selected_policy_id": audit_before.get("selected_policy_id"),
        "semantic_route_selected_type": audit_before.get("semantic_route_selected_type"),
        "protected_route": protected,
        "source_frame": deepcopy(audit_before.get("source_frame") or {}),
        "violations_before": sorted(set(violations)),
        "role_violations_before": list(audit_before.get("role_violations") or []),
        "unsupported_additions_before": list(audit_before.get("unsupported_additions") or []),
        "policy_act_match_before": bool(audit_before.get("policy_act_match")),
        "formal_register_before": bool(audit_before.get("formal_register_detected")),
        "policy_act_match_after": bool(audit_after.get("policy_act_match")),
        "unresolved_violations": sorted(set(unresolved)),
        "changed": final_reply != before,
        "input_reply_digest": _digest(before),
        "final_reply_digest": _digest(final_reply),
        "raw_dialogue_persisted": False,
        "raw_reply_persisted": False,
        "private_state_truth_claimed": False,
        "fact_memory_write_count": 0,
        "claim_boundary": "bounded visible-surface integrity audit, not private intent truth or open-domain semantic equivalence",
    }
    return final_reply, trace


_INSTALLED_M39 = False
_ORIGINAL_VISIBLE_GUARD_M39 = None
_ORIGINAL_EMIT_RESPONSE_M39 = None


def install_m39_surface_verifier():
    """Install M39 without editing the frozen M37/M38 implementation files."""

    global _INSTALLED_M39, _ORIGINAL_VISIBLE_GUARD_M39, _ORIGINAL_EMIT_RESPONSE_M39
    if _INSTALLED_M39:
        return False

    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_VISIBLE_GUARD_M39 = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_EMIT_RESPONSE_M39 = UruhaBrainV4_Mac.emit_response_if_ready

    def guarded_with_m39(self, reply, logic_data, user_input="", memory_data=None):
        visible = _ORIGINAL_VISIBLE_GUARD_M39(
            self,
            reply,
            logic_data,
            user_input=user_input,
            memory_data=memory_data,
        )
        final_reply, trace = verify_and_repair_surface_m39(
            user_input,
            visible,
            logic_data,
        )
        logic_data["semantic_persona_surface_verifier_m39"] = trace
        language_guard = logic_data.get("visible_language_guard") or {}
        language_guard["pre_m39_final_reply_sha256"] = language_guard.get("final_reply_sha256")
        language_guard["m39_action"] = trace.get("action")
        language_guard["m39_status"] = trace.get("status")
        language_guard["m39_changed"] = trace.get("changed")
        language_guard["final_reply"] = final_reply
        language_guard["final_reply_sha256"] = hashlib.sha256(final_reply.encode("utf-8")).hexdigest()
        language_guard["changed"] = bool(language_guard.get("changed") or trace.get("changed"))
        if trace.get("changed"):
            prior_action = str(language_guard.get("repair_action") or "none")
            language_guard["repair_action"] = f"{prior_action}+m39_semantic_persona_surface_repair"
        logic_data["visible_language_guard"] = language_guard
        return final_reply

    def emit_with_m39_trace(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_M39(self, event, tick_result)
        logic = result.get("logic") or {}
        trace = deepcopy(logic.get("semantic_persona_surface_verifier_m39") or {})
        if not trace:
            return result
        node = {
            "stage": "surface",
            "label": "semantic_persona_surface_verifier_m39",
            "payload": trace,
            "salience": 1.0 if trace.get("action") == "repair" else 0.92,
        }
        runtime_trace = result.get("runtime_trace") or {}
        blackboard = list(runtime_trace.get("blackboard") or [])
        insert_at = next(
            (index for index, item in enumerate(blackboard) if item.get("label") == "utterance"),
            len(blackboard),
        )
        blackboard.insert(insert_at, node)
        runtime_trace["blackboard"] = blackboard
        runtime_trace["semantic_persona_surface_verifier_m39"] = trace
        result["runtime_trace"] = runtime_trace
        if self.runtime.turn_traces:
            self.runtime.turn_traces[-1] = deepcopy(runtime_trace)
        return result

    RightBrain.enforce_user_visible_japanese = guarded_with_m39
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_m39_trace
    _INSTALLED_M39 = True
    return True


__all__ = [
    "PROTECTED_ROUTES_M39",
    "SCHEMA_M39",
    "formal_register_detected_m39",
    "inspect_surface_m39",
    "install_m39_surface_verifier",
    "policy_act_matches_m39",
    "verify_and_repair_surface_m39",
]
