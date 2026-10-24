"""Developer-authored, no-model contracts for the bounded P4 preference fallback.

These are implementation tests, not fresh Safari, latency, or human evidence.
Each installed-chain test runs in a child process because the product overlays
patch global classes and must not leak into adjacent frozen regressions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap


def _isolated(tmp_path, program):
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "URUHA_WEB_PREWARM_BRAIN": "0",
        "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
        "URUHA_MEMORY_DB_PATH": str(tmp_path / "memory"),
        "URUHA_ADAPTIVE_PERSON_MODEL_PATH": str(tmp_path / "adaptive.json"),
        "GRADIO_ANALYTICS_ENABLED": "false",
    }
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(program)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert completed.stdout.splitlines()[-1] == "ok"
    return completed


def test_pure_plan_requires_installed_source_guard_and_exact_single_span(tmp_path):
    _isolated(
        tmp_path,
        """
        import hashlib
        import uruha_source_bound_preference_fallback_p4 as fallback

        positive = "私は桜塩クッキーが好き。"
        assert fallback.source_bound_preference_plan_p4(positive) is None
        import uruha_web_ui_product_p4_question_evidence as prior
        assert prior.RUNTIME is not None

        positives = [
            ("私は桜塩クッキーが好き。", "桜塩クッキー"),
            ("わたしは黒胡麻団子が好き", "黒胡麻団子"),
            ("僕は梨酢ソーダが好き。", "梨酢ソーダ"),
            ("うちは青紫蘇茶が好き。", "青紫蘇茶"),
            ("私はUCCコーヒーが好き。", "UCCコーヒー"),
            ("ぼくは映画007が好き。", "映画007"),
            ("私は" + "あ" * 23 + "茶が好き。", "あ" * 23 + "茶"),
        ]
        for source, value in positives:
            plan = fallback.source_bound_preference_plan_p4(source)
            assert isinstance(plan, dict), source
            assert plan["intent"] == "chat", (source, plan)
            assert plan["planner_path"] == "source_bound_preference_fallback_p4"
            core = plan["core_message_jp"]
            assert value in core, (source, core)
            assert not any(word in core for word in ("覚えた", "覚えとく", "覚えておく", "記憶した", "保存した")), core
            audit = plan["source_bound_preference_fallback_p4"]
            digest = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
            assert audit["input_sha256"] == digest(source)
            assert audit["source_span_sha256"] == digest(source.rstrip("。"))
            assert audit["value_sha256"] == digest(value)
            assert audit["candidate_count"] == audit["admitted_count"] == 1
            assert audit["model_call_attempted"] is False
            assert audit["raw_dialogue_persisted"] is False
            assert source not in repr(audit) and value not in repr(audit)

        negatives = [
            "友達の紗夜は桜塩クッキーが好き。",            # third-party owner
            "「私は桜塩クッキーが好き。」",              # quoted source
            "私は桜塩クッキーが好き。これは私の好みじゃない。", # postposed self-denial
            "私は桜塩クッキーが好き。私は梨酢ソーダが好き。", # multiple clauses/values
            "私は桜塩クッキーが好き？",                # question
            "私は桜塩クッキーが好きじゃない。",        # negated preference
            "私はあなたが好き。",                    # explicit person referent
            "私は紗夜さんが好き。",                  # person honorific
            "私は紗夜が好き。",                      # unknown bare person name
            "私は太郎が好き。",                      # unknown bare person name
            "私は山本が好き。",                      # surname ending in 本
            "私は棚が好き。",                        # no licensed object head
            "私は桜塩クッキーが好き。覚えといて。",    # explicit memory act
            "死にたい。私は桜塩クッキーが好き。",        # protected mixed turn
            "我喜歡櫻花鹽餅乾。",                     # Chinese
            "I like sakura cookies.",              # English
            "私はUCC コーヒーが好き。",              # value contains whitespace
            "私は柚子・蜂蜜が好き。",                # value contains punctuation
            "私は" + "あ" * 25 + "が好き。",       # value exceeds 24 characters
            "私は" + "あ" * 36 + "が好き。",       # whole turn exceeds 40 characters
        ]
        for source in negatives:
            assert fallback.source_bound_preference_plan_p4(source) is None, source
        print("ok")
        """,
    )


def test_pure_plan_rejects_owner_fact_or_source_hash_disagreement(tmp_path):
    _isolated(
        tmp_path,
        """
        from copy import deepcopy
        import uruha_web_ui_product_p4_question_evidence
        import uruha_profile_postposed_self_denial_p4 as denial
        import uruha_source_bound_preference_fallback_p4 as fallback

        source = "私は焼き林檎タルトが好き。"
        original = denial._ORIGINAL_ADMIT
        facts, audit = original(source)
        assert facts == [("like", "焼き林檎タルト")]
        assert fallback.source_bound_preference_plan_p4(source) is not None
        try:
            denial._ORIGINAL_ADMIT = lambda _text: ([("like", "別の物")], audit)
            assert fallback.source_bound_preference_plan_p4(source) is None
            forged = deepcopy(audit)
            forged["decisions"][0]["source_span_sha256"] = "0" * 64
            denial._ORIGINAL_ADMIT = lambda _text: (facts, forged)
            assert fallback.source_bound_preference_plan_p4(source) is None
        finally:
            denial._ORIGINAL_ADMIT = original
        print("ok")
        """,
    )


def test_m29_priority_only_for_original_projection_and_exact_self_source(tmp_path):
    _isolated(
        tmp_path,
        """
        import uruha_adaptive_person_model as m29
        import uruha_web_ui_product_p4_question_evidence
        import uruha_source_bound_preference_fallback_p4 as fallback

        assert fallback.install_source_bound_preference_fallback_p4() is True
        assert fallback.install_source_bound_preference_fallback_p4() is False
        assert m29.build_literal_topic_projection_candidate_m29 is fallback.literal_topic_projection_with_source_bound_rule_p4
        pragmatic = {"pragmatic_label": "literal_intent_unresolved"}
        source = "私は黒蜜抹茶クッキーが好き。"
        original = fallback._ORIGINAL_M29(source, {}, pragmatic)
        assert original["projection_required"] is True and original["surface_authority"] is False
        selected = m29.build_literal_topic_projection_candidate_m29(source, {}, pragmatic)
        assert selected["projection_required"] is False
        assert selected["status"] == "source_admitted_rule_candidate_p4"
        assert selected["reason"] == "exact_self_preference_rule_available_before_m31"
        assert {key: value for key, value in selected.items() if key not in {
            "status", "reason", "projection_required", "source_bound_preference_priority_p4"
        }} == {key: value for key, value in original.items() if key not in {
            "status", "reason", "projection_required"
        }}
        seed = fallback.source_bound_preference_plan_p4(source)
        audit = selected["source_bound_preference_priority_p4"]
        source_audit = seed[fallback.LABEL]
        assert audit["schema"] == fallback.PRIORITY_SCHEMA
        assert audit["input_sha256"] == source_audit["input_sha256"]
        assert audit["source_span_sha256"] == source_audit["source_span_sha256"]
        assert audit["value_sha256"] == source_audit["value_sha256"]
        assert audit["original_projection_required"] is True
        assert audit["original_m33_status"] == "source_pattern_unavailable"
        assert audit["raw_dialogue_persisted"] is False
        assert source not in repr(audit) and "黒蜜抹茶クッキー" not in repr(audit)

        negatives = [
            "友達は黒蜜抹茶クッキーが好き。",         # third person
            "「私は黒蜜抹茶クッキーが好き。」",       # quoted
            "私は黒蜜抹茶クッキーが好き。これは私の好みじゃない。", # postposed denial
            "ねえ、好き？",                         # relationship question
            "私は紗夜さんが好き。",                 # person, not object
            "私は黒蜜抹茶クッキーが好き。覚えといて。", # explicit memory act
            "I like matcha cookies.",             # other language
            "私は黒蜜抹茶クッキーが好き。私は豆茶が好き。", # multiple clauses
            "私は棚が好き。",                     # object head not licensed
            "死にたい。私は黒蜜抹茶クッキーが好き。", # protected mixed turn
        ]
        for text in negatives:
            before = fallback._ORIGINAL_M29(text, {}, pragmatic)
            after = m29.build_literal_topic_projection_candidate_m29(text, {}, pragmatic)
            assert after == before, text
        # M28 already owns the surface, or M29 never requested projection.
        for feedback, context, transition in [
            ({}, {"pragmatic_label": "other"}, None),
            ({}, pragmatic, {"surface_authority": True}),
            ({"previous_prediction_id": "p", "status": "supported"}, pragmatic, None),
        ]:
            before = fallback._ORIGINAL_M29(source, feedback, context, transition)
            after = m29.build_literal_topic_projection_candidate_m29(source, feedback, context, transition)
            assert before["projection_required"] is False and after == before

        # Mismatched source identity cannot make a source-priority candidate.
        previous = fallback._ORIGINAL_M29
        try:
            fallback._ORIGINAL_M29 = lambda *args: {**original, "input_digest": "0" * 16}
            assert m29.build_literal_topic_projection_candidate_m29(source, {}, pragmatic) == {
                **original, "input_digest": "0" * 16
            }
        finally:
            fallback._ORIGINAL_M29 = previous
        previous_atoms = fallback.usa33.extract_source_semantic_atoms_m33
        try:
            fallback.usa33.extract_source_semantic_atoms_m33 = lambda *args: {"status": "source_atoms_extracted"}
            assert m29.build_literal_topic_projection_candidate_m29(source, {}, pragmatic) == original
            fallback.usa33.extract_source_semantic_atoms_m33 = lambda *args: None
            assert m29.build_literal_topic_projection_candidate_m29(source, {}, pragmatic) == original
        finally:
            fallback.usa33.extract_source_semantic_atoms_m33 = previous_atoms
        print("ok")
        """,
    )


def test_installed_fallback_removes_only_general_planner_call(tmp_path):
    _isolated(
        tmp_path,
        """
        from types import SimpleNamespace
        import uruha_web_ui_product_p4_question_evidence
        from uruha_brain_mac import LeftBrain
        import uruha_source_bound_preference_fallback_p4 as fallback

        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])
        left = LeftBrain.__new__(LeftBrain)
        left.client_logic = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        left.persona_policy_provider = None
        left.compute_ledger = None
        left._derive_bdi_context = lambda *args: {}
        left._derive_internal_monologue = lambda *args: ""
        left._derive_bayesian_candidates = lambda seed, *args: [seed]
        left._run_multitick_planner = lambda candidates, *args: dict(candidates[0])
        left._attach_persona_policy = lambda plan, *_args: plan
        left._extract_json_from_text = lambda *_args: {}
        left._normalize_candidate_bundle = lambda *_args: {
            "internal_monologue": "",
            "candidate_plans": [{"intent": "chat", "core_message_jp": "通常の計画"}],
        }
        left._think_proactive = lambda *_args, **_kwargs: {"intent": "proactive"}
        memory = {"episodes": [], "wisdom": []}
        psyche = {"mood": 0, "trust": 50}
        positive = "自分は胡桃味噌せんべいが好き。"
        negative = "自分は胡桃味噌せんべいが好き？"

        def run(source, **kwargs):
            before = len(calls)
            plan = left.think(source, memory, psyche, **kwargs)
            return plan, len(calls) - before

        baseline, before_calls = run(positive)
        assert before_calls == 1 and baseline["bounded_slow_path_m21"]["route"] == "full_planner"
        assert fallback.install_source_bound_preference_fallback_p4() is True
        fast, fast_calls = run(positive)
        assert fast_calls == 0 and fast["intent"] == "chat"
        assert fast["planner_path"] == "source_bound_preference_fallback_p4"
        assert fast["bounded_slow_path_m21"]["model_call_attempted"] is False
        ordinary, negative_calls = run(negative)
        assert negative_calls == 1 and ordinary["bounded_slow_path_m21"]["route"] == "full_planner"
        forced, forced_calls = run(positive, force_general_planner=True)
        assert forced_calls == 1 and forced["bounded_slow_path_m21"]["forced_general_planner"] is True
        proactive, proactive_calls = run(positive, mode="proactive")
        assert proactive_calls == 0 and proactive["intent"] == "proactive"
        print("ok")
        """,
    )


def test_no_generative_model_full_turn_selects_source_rule_before_m31_and_keeps_friend_route(tmp_path):
    """Real cognitive_tick/emit without generative calls; Chroma embedding is measured."""
    completed = _isolated(
        tmp_path,
        """
        import json, time
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        import uruha_web_ui_product_p4_preference_fallback as entry
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
        import uruha_adaptive_person_model as uapm
        import uruha_source_bound_preference_fallback_p4 as fallback

        counts = {"embedding_calls": 0, "cache_checks": 0, "downloads": 0}
        original_embed = ONNXMiniLM_L6_V2.__call__
        original_cache = ONNXMiniLM_L6_V2._download_model_if_not_exists
        original_download = ONNXMiniLM_L6_V2._download
        def embed(self, *args, **kwargs):
            counts["embedding_calls"] += 1
            return original_embed(self, *args, **kwargs)
        def cache(self, *args, **kwargs):
            counts["cache_checks"] += 1
            return original_cache(self, *args, **kwargs)
        def download(self, *args, **kwargs):
            counts["downloads"] += 1
            return original_download(self, *args, **kwargs)
        ONNXMiniLM_L6_V2.__call__ = embed
        ONNXMiniLM_L6_V2._download_model_if_not_exists = cache
        ONNXMiniLM_L6_V2._download = download

        friend = "友達は黒蜜抹茶クッキーが好き。"
        self_report = "私は黒蜜抹茶クッキーが好き。"
        m31_calls = []
        def no_model_m31(self, user_input, projection):
            m31_calls.append(user_input)
            assert user_input == friend, ("self preference must bypass M31", user_input)
            return ({
                "intent": "semantically_authorized_literal_topic_m31",
                "scene": "casual", "core_message_jp": "友達は黒蜜抹茶クッキーが好きなんだね。",
                "jp_summary": "友達の好みを聞いた", "mood_impact": 0, "trust_impact": 0,
                "response_mode": "direct_answer", "surface_act": "plain_reply",
                "constraints": {"max_chars": 96},
            }, {
                "schema": uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
                "status": "semantically_authorized", "surface_authority": True,
                "surface_self_checks": {
                    "safe_response_semantics_faithful": True,
                    "subject_preserved": True, "predicate_preserved": True,
                    "time_quantity_relation_preserved": True, "polarity_preserved": True,
                },
                "model_call_completed": False, "raw_dialogue_persisted": False,
            })
        LeftBrain.authorize_literal_topic_m31 = no_model_m31

        def brain():
            instance = _IsolatedContractBrain()
            instance.memory = MemoryManager()
            instance.left_brain = LeftBrain(None)
            instance.right_brain = RightBrain(load_model=False)
            instance.right_brain.speak = lambda _source, logic, _mem, _psyche: logic["core_message_jp"]
            return instance

        started = time.perf_counter()
        friend_result = brain().run_turn_debug(friend)
        friend_seconds = time.perf_counter() - started
        assert m31_calls == [friend]
        assert friend_result["logic"]["intent"] == "semantically_authorized_literal_topic_m31"
        assert friend_result["logic"].get("planner_path") != fallback.LABEL
        assert not any(row.get("label") == fallback.LABEL for row in friend_result["runtime_trace"]["blackboard"])

        started = time.perf_counter()
        result = brain().run_turn_debug(self_report)
        self_seconds = time.perf_counter() - started
        assert m31_calls == [friend], m31_calls
        assert result["logic"]["intent"] == "chat", result["logic"]["intent"]
        assert result["logic"]["planner_path"] == fallback.LABEL
        assert result["logic"]["bounded_slow_path_m21"]["route"] == "deterministic_rule_plan"
        assert result["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
        m29 = result["logic"]["literal_topic_projection_m29"]
        assert m29["status"] == "source_admitted_rule_candidate_p4"
        assert m29["projection_required"] is False
        rows = result["runtime_trace"]["blackboard"]
        selected = [row for row in rows if row.get("label") == "selected_plan"]
        assert len(selected) == 1 and selected[0]["payload"]["intent"] == "chat"
        assert selected[0]["payload"]["planner_path"] == fallback.LABEL
        marker = [row for row in rows if row.get("label") == fallback.LABEL]
        assert len(marker) == 1 and marker[0]["payload"]["status"] == "selected_source_admitted_rule_fallback"
        utterance = [row for row in rows if row.get("label") == "utterance"]
        assert len(utterance) == 1 and utterance[0]["payload"]["reply"] == result["reply"]
        assert entry.RUNTIME is entry._prior.RUNTIME
        print(json.dumps({"embedding": counts, "friend_seconds": round(friend_seconds, 4),
                          "self_seconds": round(self_seconds, 4), "m31_calls": len(m31_calls)}))
        print("ok")
        """,
    )
    report = json.loads(completed.stdout.splitlines()[-2])
    assert report["m31_calls"] == 1
    assert report["embedding"]["embedding_calls"] >= 1
    print(f"no-generative-model full-turn instrumentation: {report}")


def test_original_rule_precedes_fallback_and_m31_is_not_replaced(tmp_path):
    _isolated(
        tmp_path,
        """
        import uruha_web_ui_product_p4_question_evidence
        from uruha_brain_mac import LeftBrain
        import uruha_source_bound_preference_fallback_p4 as fallback

        original_m31 = LeftBrain.authorize_literal_topic_m31
        from uruha_adaptive_person_model import build_literal_topic_projection_candidate_m29 as original_m29
        assert fallback.install_source_bound_preference_fallback_p4() is True
        assert fallback.install_source_bound_preference_fallback_p4() is False
        assert LeftBrain.authorize_literal_topic_m31 is original_m31
        from uruha_adaptive_person_model import build_literal_topic_projection_candidate_m29 as selected_m29
        assert selected_m29 is fallback.literal_topic_projection_with_source_bound_rule_p4
        assert fallback._ORIGINAL_M29 is original_m29
        left = LeftBrain.__new__(LeftBrain)
        psyche = {"mood": 0, "trust": 50}
        assert left._rule_based_plan("好き？", psyche, {})["intent"] == "ask_like_me"
        assert left._rule_based_plan("死にたい", psyche, {})["intent"] == "crisis_support"
        selected = {"intent": "protected_existing_rule", "core_message_jp": "元の規則"}
        previous = fallback._ORIGINAL_RULE_PLAN
        try:
            fallback._ORIGINAL_RULE_PLAN = lambda *_args, **_kwargs: selected
            plan = left._rule_based_plan("私は桜塩クッキーが好き。", psyche, {})
            assert plan is selected
        finally:
            fallback._ORIGINAL_RULE_PLAN = previous
        print("ok")
        """,
    )


def test_graph_marks_only_selected_source_bound_fallback_without_changing_utterance(tmp_path):
    _isolated(
        tmp_path,
        """
        from copy import deepcopy
        import uruha_web_ui_product_p4_question_evidence
        import uruha_profile_owner_admission_p4 as owner
        import uruha_source_bound_preference_fallback_p4 as fallback

        source = "私は玄米甘酒が好き。"
        plan = fallback.source_bound_preference_plan_p4(source)
        facts, owner_audit = owner.admit_legacy_profile_facts(source)
        assert facts == [("like", "玄米甘酒")]
        selected = {
            "intent": "chat", "scene": "casual",
            "core_message_jp": plan["core_message_jp"],
        }  # Core _plan_trace_summary intentionally omits planner_path.
        visible = "玄米甘酒、いいじゃん。"

        def result():
            return {
                "logic": {
                    **deepcopy(plan),
                    "bounded_slow_path_m21": {
                        "route": "deterministic_rule_plan", "model_call_attempted": False,
                    },
                },
                "memory_runtime": {owner.LABEL: deepcopy(owner_audit)},
                "reply": visible,
                "runtime_trace": {
                    "selected_plan": deepcopy(selected),
                    "blackboard": [
                        {"stage": "select", "label": "selected_plan", "payload": deepcopy(selected)},
                        {"stage": "surface", "label": "utterance", "payload": {"reply": visible}},
                    ],
                },
            }

        def nodes(data):
            return [row for row in data["runtime_trace"]["blackboard"] if row.get("label") == fallback.LABEL]

        fast = result()
        assert fallback.materialize_source_bound_preference_fallback_p4(fast, source) is fast
        assert len(nodes(fast)) == 1
        payload = nodes(fast)[0]["payload"]
        from uruha_memory_observatory import collect_cognitive_graph
        graph = collect_cognitive_graph(fast)
        graph_nodes = [node for node in graph["nodes"] if node.get("label") == fallback.LABEL]
        assert len(graph_nodes) == 1
        assert graph_nodes[0]["signal"] == "本人偏好來源一致 → 直接回覆計畫"
        assert "玄米甘酒" not in graph_nodes[0]["signal"]
        assert payload == fast["logic"][fallback.LABEL] == fast["runtime_trace"][fallback.LABEL]
        assert payload["input_sha256"] == owner_audit["input_sha256"]
        assert payload["source_span_sha256"] == owner_audit["decisions"][0]["source_span_sha256"]
        assert payload["value_sha256"] == owner_audit["decisions"][0]["value_sha256"]
        assert payload["raw_dialogue_persisted"] is False
        assert source not in repr(payload) and "玄米甘酒" not in repr(payload)
        assert fast["runtime_trace"]["selected_plan"]["planner_path"] == fallback.LABEL
        selected_rows = [row for row in fast["runtime_trace"]["blackboard"] if row.get("label") == "selected_plan"]
        assert len(selected_rows) == 1 and selected_rows[0]["payload"]["planner_path"] == fallback.LABEL
        assert fast["reply"] == visible
        utterances = [row["payload"]["reply"] for row in fast["runtime_trace"]["blackboard"] if row.get("label") == "utterance"]
        assert utterances == [visible]
        fallback.materialize_source_bound_preference_fallback_p4(fast, source)
        assert len(nodes(fast)) == 1

        ordinary = result()
        ordinary["logic"].pop("planner_path")
        fallback.materialize_source_bound_preference_fallback_p4(ordinary, source)
        assert nodes(ordinary) == [] and ordinary["reply"] == visible

        protected = result()
        protected["logic"]["intent"] = "crisis_support"
        protected["runtime_trace"]["selected_plan"]["intent"] = "crisis_support"
        protected["runtime_trace"]["blackboard"][0]["payload"]["intent"] = "crisis_support"
        fallback.materialize_source_bound_preference_fallback_p4(protected, source)
        assert nodes(protected) == []

        mismatched_selected = result()
        mismatched_selected["runtime_trace"]["selected_plan"]["core_message_jp"] = "別の選択"
        fallback.materialize_source_bound_preference_fallback_p4(mismatched_selected, source)
        assert nodes(mismatched_selected) == []

        mismatched_scene = result()
        mismatched_scene["runtime_trace"]["selected_plan"]["scene"] = "support"
        fallback.materialize_source_bound_preference_fallback_p4(mismatched_scene, source)
        assert nodes(mismatched_scene) == []

        conflicting_path = result()
        conflicting_path["runtime_trace"]["blackboard"][0]["payload"]["planner_path"] = "another_planner"
        fallback.materialize_source_bound_preference_fallback_p4(conflicting_path, source)
        assert nodes(conflicting_path) == []

        forged = result()
        forged["memory_runtime"][owner.LABEL]["decisions"][0]["source_span_sha256"] = "0" * 64
        fallback.materialize_source_bound_preference_fallback_p4(forged, source)
        assert nodes(forged) == []
        print("ok")
        """,
    )
