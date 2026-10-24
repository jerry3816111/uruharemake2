"""Opt-in source/speech-act admission for reference-probe plans.

The certificate describes evidence in the *current utterance*, not a fact
about the user's private intent.  It is deliberately conservative: explicit
song/source questions, missing ED/OP subjects, and bounded bare poetic
fragments can enter the old reference path; an embedded glyph or a third-party
report cannot.  The same classifier binds the deterministic seed, self-critique,
candidate selection, optional right-brain rescue, and the runtime graph.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import unicodedata


LABEL = "reference_probe_evidence_p4"
SCHEMA = "uruha_reference_probe_evidence_p4_v1"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_CRITIQUE = None
_ORIGINAL_MULTITICK = None
_ORIGINAL_INTENT_VARIANT = None
_ORIGINAL_TICK = None

# ED/OP are notation for an opening/ending, not substrings of English words.
_ANIME_SONG_SLOT = re.compile(r"(?<![A-Za-z])(?:ED|OP)(?![A-Za-z])", re.I)
_SOURCE_QUESTION = re.compile(
    r"何の曲|何て曲|どの曲|曲名|何の歌|どの歌|どの作品|元ネタ(?:は|って|何|どこ|\?)|"
    r"哪首(?:歌|曲)|什么歌|什麼歌|歌曲名|出自(?:哪里|哪裡)|"
    r"\b(?:what|which) (?:song|track|opening|ending)\b|"
    r"\b(?:song title|source of (?:this|that) (?:lyric|line|meme))\b",
    re.I,
)
_SONG_OBJECT = re.compile(r"歌詞|歌词|歌|曲|song|track|lyric|opening|ending|元ネタ|ネタ", re.I)
_ED_OP_SOURCE_SEEK = re.compile(
    r"何の(?:曲|歌|作品)|何て(?:曲|歌)|どの(?:曲|歌|作品)|曲名|歌の題名|"
    r"哪首|哪一首|什么歌|什麼歌|"
    r"思い出せ|覚えてない|忘れた|想不起|"
    r"\b(?:which|what) (?:song|track|opening|ending)\b|"
    r"\b(?:forgot|remember) (?:the )?(?:song|track|title)\b",
    re.I,
)
_NON_SOURCE_INFORMATION = re.compile(
    r"何時|いつ|時刻|開始|終了|どこ|場所|置き場|"
    r"幾點|几点|什么时候|什麼時候|哪里|哪裡|位置|"
    r"\b(?:when|where|time|location|schedule)\b",
    re.I,
)
_REPORTED_SPEECH = re.compile(
    r"(?:友達|友人|知人|同僚|兄|弟|姉|妹|母|父|先生|店員|係の人|彼|彼女|誰か)"
    r"(?:が|は|から).{0,100}(?:って|と)(?:言|聞|話)|"
    r"(?:朋友|同學|同学|老師|老师|弟弟|姐姐|哥哥|妹妹).{0,100}(?:說|说|告訴|告诉)|"
    r"\b(?:my )?(?:friend|brother|sister|teacher|coworker)\b.{0,100}\b(?:said|told|says)\b",
    re.I,
)
_POETIC_BARE = {
    "夜空", "月光", "影", "霧", "願い", "潮騒", "夕焼け", "雨音", "古い夢", "ガラスの雨",
    "night sky", "moonlight", "shadow", "fog", "old dream",
}
_QUOTE = re.compile(r"^(?:「(?P<corner>[^「」]{1,40})」|『(?P<double>[^『』]{1,40})』|\"(?P<ascii>[^\"]{1,40})\")$")
_BALANCED_QUOTED_SPAN = re.compile(
    r"「[^「」]*」|『[^『』]*』|\"[^\"]*\"|'[^']*'|“[^“”]*”"
)
_POST_TICK_SHADOW_LABELS = frozenset({
    "personhood_action_choice_v2_13",
    "personhood_persona_appraisal_v2_13",
    "active_validation_strategy_v2_13",
    "desired_response_prediction_m18",
    "adaptive_response_dimensions_m18",
    "candidate_plans",
    "planner_ticks",
    "bdi_state",
    "open_loops",
    "bounded_slow_path_planner_m21",
    "semantic_route_outcome_m22",
})


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _is_reference_plan(plan) -> bool:
    return isinstance(plan, dict) and (
        str(plan.get("intent") or "") == "reference_probe"
        or str(plan.get("surface_act") or "") == "reference_probe"
    )


def classify_reference_probe_evidence_p4(user_input: str) -> dict:
    """Return one auditable, raw-text-free current-turn admission receipt."""
    raw = str(user_input or "")
    text = unicodedata.normalize("NFKC", raw).strip()
    normalized = re.sub(r"\s+", " ", text)
    outer = _BALANCED_QUOTED_SPAN.sub("", normalized)
    base = {
        "schema": SCHEMA,
        "input_sha256": _sha(raw),
        "normalized_input_sha256": _sha(text),
        "eligible": False,
        "source_evidence": "none",
        "speech_act": "unknown",
        "reason": "no_source_or_fragment_evidence",
        "raw_dialogue_persisted": False,
        "private_intent_claimed": False,
        "model_calls_added": 0,
    }
    if not text or len(text) > 180:
        return {**base, "reason": "empty_or_outside_bounded_input"}
    # A reported line is an object of conversation, not automatically the
    # user's present request to identify a lyric.  An explicit *outer* source
    # question remains eligible through the ordinary question branch below.
    attributed = bool(_REPORTED_SPEECH.search(normalized))
    source_question_outside_quote = bool(_SOURCE_QUESTION.search(outer))
    if attributed and not source_question_outside_quote:
        return {**base, "speech_act": "third_party_report", "reason": "reported_speech_not_user_source_request"}
    if source_question_outside_quote and _SONG_OBJECT.search(outer):
        return {
            **base, "eligible": True, "source_evidence": "explicit_source_question",
            "speech_act": "ask_song_or_reference_source", "reason": "explicit_source_question_in_current_turn",
        }
    slot = _ANIME_SONG_SLOT.search(normalized)
    if (
        slot and not _NON_SOURCE_INFORMATION.search(outer)
        and (
            _ED_OP_SOURCE_SEEK.search(outer)
            or len(normalized) <= 12 and normalized.endswith(slot.group(0))
        )
    ):
        return {
            **base, "eligible": True, "source_evidence": "ed_op_subject_incomplete",
            "speech_act": "ask_or_offer_incomplete_song_slot", "reason": "ed_op_slot_with_missing_source",
        }
    quoted = _QUOTE.fullmatch(normalized)
    fragment = next((value for value in quoted.groupdict().values() if value), "") if quoted else normalized
    fragment = fragment.strip().casefold()
    if fragment in _POETIC_BARE and len(fragment) <= 16:
        return {
            **base, "eligible": True, "source_evidence": "bare_poetic_fragment",
            "speech_act": "short_unattributed_fragment", "reason": "bounded_standalone_reference_cue",
        }
    if re.search(r"[?？]", normalized):
        act = "non_source_question"
    elif attributed:
        act = "third_party_report"
    else:
        act = "ordinary_statement_or_request"
    return {**base, "speech_act": act}


def rule_plan_with_reference_probe_evidence_p4(self, user_input, current_psyche, memory_data=None):
    plan = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
    if _is_reference_plan(plan) and not classify_reference_probe_evidence_p4(user_input)["eligible"]:
        # None means the existing general planner gets a normal opportunity;
        # there is no substitute utterance or repair-only model call.
        return None
    return plan


def critique_with_reference_probe_evidence_p4(self, plan, user_input, memory_data, current_psyche):
    critique = _ORIGINAL_CRITIQUE(self, plan, user_input, memory_data, current_psyche)
    if classify_reference_probe_evidence_p4(user_input)["eligible"] or not isinstance(critique, dict):
        return critique
    issues = list(critique.get("issues") or [])
    if "missed_reference_behavior" not in issues:
        return critique
    filtered = [item for item in issues if item != "missed_reference_behavior"]
    updated = deepcopy(critique)
    updated["issues"] = filtered
    updated["needs_revision"] = bool(filtered)
    updated["severity"] = round(min(1.0, 0.2 + 0.16 * len(filtered)), 3) if filtered else 0.0
    updated["internal_note"] = " / ".join(
        note for note in str(critique.get("internal_note") or "").split(" / ")
        if "断片やネタへの反応" not in note
    )
    updated["reference_admission_issue_removed_p4"] = True
    return updated


def multitick_with_reference_probe_evidence_p4(
    self, candidate_plans, user_input, memory_data, current_psyche,
    internal_monologue="", tick_budget=None,
):
    candidates = list(candidate_plans or [])
    if not classify_reference_probe_evidence_p4(user_input)["eligible"]:
        candidates = [candidate for candidate in candidates if not _is_reference_plan(candidate)]
        if not candidates:
            # Existing fallback is an ordinary chat plan, not a newly invented
            # fixed source-clarification surface.
            candidates = [self._fallback_plan()]
    return _ORIGINAL_MULTITICK(
        self, candidates, user_input, memory_data, current_psyche,
        internal_monologue=internal_monologue, tick_budget=tick_budget,
    )


def intent_variant_with_reference_probe_evidence_p4(
    self, intent, user_input, current_psyche, memory_data, max_chars=None,
):
    # _chat_rescue_variant eventually calls this for weak shadow/fog tokens.
    # The same source certificate therefore closes that optional last shortcut.
    if intent == "reference_probe" and not classify_reference_probe_evidence_p4(user_input)["eligible"]:
        return None
    return _ORIGINAL_INTENT_VARIANT(
        self, intent, user_input, current_psyche, memory_data, max_chars=max_chars,
    )


def _protected_plan(logic: dict, route_info: dict) -> bool:
    import uruha_adaptive_person_model as adaptive_person

    return bool(
        (route_info or {}).get("route") == "low_road"
        or (logic.get("semantic_route_m22") or {}).get("selected_type") == "safety_sensitive"
        or logic.get("intent") in adaptive_person.PROTECTED_INTENTS
        or logic.get("scene") in adaptive_person.PROTECTED_SCENES
    )


def cognitive_tick_with_reference_probe_evidence_p4(self, event):
    tick = _ORIGINAL_TICK(self, event)
    if not isinstance(tick, dict):
        return tick
    user_input = str((event or {}).get("user_input") or "")
    certificate = classify_reference_probe_evidence_p4(user_input)
    logic = tick.get("logic") or {}
    route_info = tick.get("route_info") or {}
    protected = _protected_plan(logic, route_info)
    prior_selected_reference = _is_reference_plan(logic)
    # Audit the old seed without invoking any generator.  It uses the same
    # current text and memory that fed classify_user_signal in this cycle.
    original_seed = _ORIGINAL_RULE_PLAN(
        self.left_brain, user_input, (event or {}).get("psyche_before") or {},
        (event or {}).get("memory_data") or {},
    )
    certificate["old_seed_reference_candidate"] = _is_reference_plan(original_seed)
    certificate["seed_admission"] = (
        "protected_unchanged" if protected else
        "admitted" if certificate["eligible"] and certificate["old_seed_reference_candidate"] else
        "rejected" if certificate["old_seed_reference_candidate"] else "not_candidate"
    )
    if protected:
        certificate["selected_status"] = "protected_unchanged"
    elif prior_selected_reference and not certificate["eligible"]:
        # Defensive final gate for model/adaptive selection that bypassed the
        # deterministic seed.  Do not fabricate a reference reply.  Normal
        # candidate filtering above should make this rare and auditable.
        fallback = self.left_brain._fallback_plan()
        for key in (
            "candidate_label", "intent", "scene", "listener_state", "reply_goal",
            "jp_summary", "core_message_jp", "cognitive_mode", "response_mode",
            "surface_act", "payload_level", "stance", "constraints",
            "hidden_intent", "grounding", "uncertainty", "premise_check",
            "self_check", "subjective_note_jp", "must_avoid", "user_belief",
            "my_hidden_knowledge", "user_expectation", "internal_monologue",
            "bayes_candidates", "working_memory_used", "mood_impact",
            "trust_impact", "routing_path",
        ):
            logic[key] = deepcopy(fallback[key])
        # These are summaries of the rejected candidate, not properties of
        # the fallback.  Keeping them would falsely present a reference plan
        # as the selected reasoning or carry a source cue into speech.
        for key in (
            "planner_tick_trace", "planner_detected_issues", "planner_unresolved_issues",
            "planner_tick_budget", "human_speech_plan", "reference_subject_jp",
        ):
            logic.pop(key, None)
        logic["planner_tick_count"] = 0
        logic["self_correction_applied"] = False
        logic["planner_repair_applied"] = False
        logic["planner_repair_success"] = False
        if logic.get("dialogue_act") == "reference_probe":
            logic["dialogue_act"] = "direct_chat_answer"
        logic["planner_path"] = "reference_probe_evidence_last_resort_general"
        # Keep actual planning compute cost and performed route, but revoke
        # their authority as descriptions of the plan now handed to speech.
        for key in ("bounded_slow_path_m21", "semantic_route_m22"):
            prior = logic.get(key)
            if isinstance(prior, dict):
                prior["pre_gate_plan_status"] = "shadowed_not_selected"
                prior["post_gate_selected_plan_authority"] = LABEL
                if key == "bounded_slow_path_m21":
                    prior["observed_compute_cost_retained"] = True
        logic["personhood_action_context_v2_13"] = {
            "status": "pre_gate_action_shadowed",
            "post_gate_selected_plan_authority": LABEL,
            "selected_intent": logic["intent"],
        }
        certificate["selected_status"] = "unsupported_selected_reference_rejected"
        certificate["post_tick_authority_override"] = True
        certificate["rejected_plan_specific_payload_cleared"] = True
        certificate["pre_gate_cognitive_nodes_retained_as_shadow"] = True
        self.runtime.last_selected_plan = self._plan_trace_summary(logic)
        self.runtime.active_goal = logic["reply_goal"]
        self.runtime.last_internal_monologue = ""
        self.runtime.last_candidates = []
        self.runtime.planner_tick_trace = []
        self.runtime.planner_tick_count = 0
        self.runtime.self_correction_applied = False
        personhood = getattr(self.runtime, "last_personhood_loop", None)
        if isinstance(personhood, dict):
            personhood = deepcopy(personhood)
            choice = personhood.get("action_choice")
            if isinstance(choice, dict):
                choice["post_gate_status"] = "shadowed_not_selected"
                choice["post_gate_selected_plan_authority"] = LABEL
            self.runtime.last_personhood_loop = personhood
        if hasattr(self, "_derive_open_loops"):
            self.runtime.open_loops = self._derive_open_loops(logic)
            self.runtime.latent_goal_stack = deepcopy(self.runtime.open_loops)
        if hasattr(self.left_brain, "predict_next_user_signal") and hasattr(self.runtime, "set_prediction"):
            prediction = self.left_brain.predict_next_user_signal(
                logic, user_input, (event or {}).get("psyche_before") or {},
                (event or {}).get("memory_data") or {}, mode="reactive",
            )
            logic["prediction_hint"] = prediction
            self.runtime.set_prediction(
                prediction.get("expected_intent", ""),
                prediction.get("expected_valence", 0.0),
                source_plan_intent=prediction.get("source_plan_intent", logic["intent"]),
            )
        for row in self.runtime.blackboard:
            if row.get("label") == "selected_plan":
                row["payload"] = deepcopy(self.runtime.last_selected_plan)
                row["payload"]["post_gate_selected_plan_authority"] = LABEL
            elif row.get("label") in _POST_TICK_SHADOW_LABELS and isinstance(row.get("payload"), dict):
                payload = deepcopy(row["payload"])
                payload["post_gate_plan_status"] = "shadowed_not_selected"
                payload["post_gate_selected_plan_authority"] = LABEL
                if row.get("label") == "bounded_slow_path_planner_m21":
                    payload["observed_compute_cost_retained"] = True
                row["payload"] = payload
    else:
        certificate["selected_status"] = (
            "eligible_reference_selected" if prior_selected_reference else
            "eligible_other_selected" if certificate["eligible"] else
            "ordinary_plan_selected"
        )
    certificate["actual_selected_intent"] = str(logic.get("intent") or "")
    certificate["actual_selected_surface_act"] = str(logic.get("surface_act") or "")
    logic[LABEL] = deepcopy(certificate)
    board = getattr(self.runtime, "blackboard", None)
    if isinstance(board, list):
        node = {"stage": "evidence", "label": LABEL, "payload": deepcopy(certificate), "salience": 0.96}
        index = next((i for i, row in enumerate(board) if row.get("label") == "selected_plan"), len(board))
        board.insert(index, node)
    tick["logic"] = logic
    return tick


def install_reference_probe_evidence_p4() -> bool:
    """Install after the earlier P4 product overlays, in the opt-in entry only."""
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_CRITIQUE
    global _ORIGINAL_MULTITICK, _ORIGINAL_INTENT_VARIANT, _ORIGINAL_TICK
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_CRITIQUE = LeftBrain._critique_plan
    _ORIGINAL_MULTITICK = LeftBrain._run_multitick_planner
    _ORIGINAL_INTENT_VARIANT = RightBrain._intent_variant
    _ORIGINAL_TICK = UruhaBrainV4_Mac.cognitive_tick
    LeftBrain._rule_based_plan = rule_plan_with_reference_probe_evidence_p4
    LeftBrain._critique_plan = critique_with_reference_probe_evidence_p4
    LeftBrain._run_multitick_planner = multitick_with_reference_probe_evidence_p4
    RightBrain._intent_variant = intent_variant_with_reference_probe_evidence_p4
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_reference_probe_evidence_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "classify_reference_probe_evidence_p4",
    "rule_plan_with_reference_probe_evidence_p4",
    "critique_with_reference_probe_evidence_p4",
    "multitick_with_reference_probe_evidence_p4",
    "intent_variant_with_reference_probe_evidence_p4",
    "cognitive_tick_with_reference_probe_evidence_p4",
    "install_reference_probe_evidence_p4",
]
