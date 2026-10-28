"""Zero-model contracts for the prospective P4 M46 reviewer instruction.

Fake calls test transport wiring and the old verifier. They do not test model
quality, latency, Japanese naturalness, or the real Web response.
"""

import json
import subprocess
import sys
import textwrap


def _run(script):
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.splitlines()[-1]) == {"ok": True}


def test_only_verified_p4_first_step_amends_review_instruction_and_preserves_transport():
    _run("""
        import json
        import uruha_actionable_help_delivery_m45 as action45
        import uruha_crosslingual_help_routing_m47 as m47
        import uruha_goal_progress_delivery_m46 as m46
        import uruha_state_changing_candidates_m51 as m51
        from uruha_explicit_first_step_route_p4 import classify_first_step_route_p4

        candidate_calls, review_calls = [], []
        original_candidate_system = m51.CANDIDATE_SYSTEM
        original_review_system = m46.REVIEW_SYSTEM
        payload = {"user_sources": [{"id": "current:1", "kind": "current_user", "text": "source"}]}
        candidate_schema = {"properties": {"items": {"type": "array"}}}
        review_payload = {"sources": payload["user_sources"], "plan": {"status": "action"}}
        review_schema = {"properties": {
            "counterfactual_before_jp": {"type": "string"},
            "counterfactual_after_jp": {"type": "string"},
            "observed_progress_mechanism": {"type": "string"},
        }}
        partial_review_schema = {"properties": {"counterfactual_before_jp": {"type": "string"}}}
        deadline, metrics = 987.25, {"model_calls_attempted": 0}

        def fake_candidates(system, seen_payload, schema, seen_deadline, seen_metrics):
            candidate_calls.append((system, seen_payload, schema, seen_deadline, seen_metrics))
            return {"items": []}

        def fake_native(system, seen_payload, schema, seen_deadline, seen_metrics):
            review_calls.append((system, seen_payload, schema, seen_deadline, seen_metrics))
            return {"source_id": "current:1"}

        def fake_delivery(user_input, candidate, logic, sources, call_json=None):
            if candidate != "skip_candidate":
                m51._native_candidates(m51.CANDIDATE_SYSTEM, payload,
                                       candidate_schema, deadline, metrics)
            action45._native_json(m46.REVIEW_SYSTEM, review_payload,
                                  review_schema, deadline, metrics)
            action45._native_json(m46.REVIEW_SYSTEM, review_payload,
                                  partial_review_schema, deadline, metrics)
            action45._native_json("unrelated_review_system", review_payload,
                                  review_schema, deadline, metrics)
            return candidate, {m51.LABEL: {"schema": m51.SCHEMA}}

        action45.deliver_action = fake_delivery
        action45._native_json = fake_native
        m51._native_candidates = fake_candidates
        import uruha_source_bound_candidate_prompt_p4 as candidate_adapter
        assert candidate_adapter.install_source_bound_candidate_prompt_p4()
        candidate_delivery_identity = action45.deliver_action
        import uruha_reviewer_japanese_counterfactual_p4 as subject
        assert subject.install_reviewer_japanese_counterfactual_p4()
        assert subject.install_reviewer_japanese_counterfactual_p4() is False
        assert subject.installed_reviewer_japanese_counterfactual_p4()
        assert candidate_adapter.installed_source_bound_candidate_prompt_p4()
        assert action45.deliver_action is candidate_delivery_identity
        assert action45._native_json is subject.reviewer_native_json_p4

        positive = [
            "我要整理桌上散開的便條紙。你會叫我先做什麼？",
            "机の上の紙を整理したい。まず何をすればいい？",
        ]
        negative = [
            "我該先做什麼？",
            "我不要方法，只想抱怨桌上太亂。你會叫我先做什麼？",
            "死にたい。まず何をすればいい？",
            "朋友問我：「我要整理桌子，我該先做什麼？」",
            "There are two notebooks. What should I do first?",
        ]

        def turn(source, *, forged=None, source_kind="current_user", skip_candidate=False):
            route = classify_first_step_route_p4(source)
            if forged == "digest":
                route = dict(route, input_digest="wrong-current-input")
            elif forged == "span":
                route = dict(route, task_spans=[dict(route["task_spans"][0], span_digest="wrong")])
            payload["user_sources"][0]["text"] = source
            logic = {"explicit_desired_response_m25": {m47.LABEL: route}}
            sources = [{"id": "current:1" if source_kind == "current_user" else "prior:1",
                        "kind": source_kind, "text": source}]
            marker = "skip_candidate" if skip_candidate else "before"
            result, trace = action45.deliver_action(source, marker, logic, sources)
            assert result == marker
            review, partial, unrelated = review_calls[-3:]
            del review_calls[-3:]
            assert review[1] is review_payload and review[2] is review_schema
            assert review[3] is deadline and review[4] is metrics
            assert partial[0] == original_review_system
            assert partial[1] is review_payload and partial[2] is partial_review_schema
            assert partial[3] is deadline and partial[4] is metrics
            assert unrelated[0] == "unrelated_review_system"
            assert unrelated[1] is review_payload and unrelated[2] is review_schema
            assert unrelated[3] is deadline and unrelated[4] is metrics
            if skip_candidate:
                candidate = None
            else:
                candidate = candidate_calls.pop()
                assert candidate[1] is payload and candidate[2] is candidate_schema
                assert candidate[3] is deadline and candidate[4] is metrics
            return candidate, review[0], trace

        for source in positive:
            candidate, reviewer, trace = turn(source)
            assert candidate[0] == candidate_adapter.SOURCE_BOUND_CANDIDATE_SYSTEM
            assert reviewer == subject.REVIEWER_JAPANESE_SYSTEM
            assert reviewer.startswith(original_review_system)
            assert "counterfactual_before_jp" in reviewer
            assert "counterfactual_after_jp" in reviewer
            assert trace[m51.LABEL][candidate_adapter.LABEL]["applied"] is True
            metadata = metrics[subject.LABEL]
            assert metadata["applied"] is True
            assert metadata["model_calls_added"] == 0
            assert source not in json.dumps(metadata, ensure_ascii=False)
            del metrics[subject.LABEL]
        for source in negative:
            candidate, reviewer, trace = turn(source)
            assert candidate[0] == original_candidate_system
            assert reviewer == original_review_system
            assert subject.LABEL not in metrics
            assert candidate_adapter.LABEL not in trace[m51.LABEL]
        for kwargs in ({"forged": "digest"}, {"forged": "span"},
                       {"source_kind": "linked_previous_user"}):
            candidate, reviewer, _trace = turn(positive[0], **kwargs)
            assert candidate[0] == original_candidate_system
            assert reviewer == original_review_system
            assert subject.LABEL not in metrics
        candidate, reviewer, trace = turn(positive[0], skip_candidate=True)
        assert candidate is None and reviewer == original_review_system
        assert subject.LABEL not in metrics
        assert candidate_adapter.LABEL not in trace[m51.LABEL]
        assert m46.REVIEW_SYSTEM == original_review_system
        assert m51.CANDIDATE_SYSTEM == original_candidate_system
        assert not candidate_calls and not review_calls
        print(json.dumps({"ok": True}))
    """)


def test_reviewer_prompt_is_thread_isolated_by_existing_candidate_context():
    _run("""
        import json
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        import uruha_actionable_help_delivery_m45 as action45
        import uruha_crosslingual_help_routing_m47 as m47
        import uruha_goal_progress_delivery_m46 as m46
        import uruha_state_changing_candidates_m51 as m51
        from uruha_explicit_first_step_route_p4 import classify_first_step_route_p4

        barrier = Barrier(2)
        action45._native_json = lambda system, payload, schema, deadline, metrics: system
        m51._native_candidates = lambda *args: {}
        def fake_delivery(user_input, candidate, logic, sources, call_json=None):
            metrics = {}
            m51._native_candidates(m51.CANDIDATE_SYSTEM, {"user_sources": sources},
                                   {"properties": {"items": {"type": "array"}}}, 10.0, metrics)
            barrier.wait(timeout=5)
            system = action45._native_json(
                m46.REVIEW_SYSTEM, {"sources": sources},
                {"properties": {"counterfactual_before_jp": {"type": "string"},
                                "counterfactual_after_jp": {"type": "string"}}},
                10.0, metrics)
            return system, {m51.LABEL: {"schema": m51.SCHEMA}, "metrics": metrics}
        action45.deliver_action = fake_delivery
        import uruha_source_bound_candidate_prompt_p4 as candidate_adapter
        candidate_adapter.install_source_bound_candidate_prompt_p4()
        import uruha_reviewer_japanese_counterfactual_p4 as subject
        subject.install_reviewer_japanese_counterfactual_p4()

        def turn(source):
            route = classify_first_step_route_p4(source)
            return action45.deliver_action(source, "before",
                {"explicit_desired_response_m25": {m47.LABEL: route}},
                [{"id": "current:1", "kind": "current_user", "text": source}])
        with ThreadPoolExecutor(max_workers=2) as pool:
            eligible = pool.submit(turn, "我要整理桌上散開的便條紙。你會叫我先做什麼？")
            ineligible = pool.submit(turn, "我該先做什麼？")
            changed, changed_trace = eligible.result(timeout=10)
            unchanged, unchanged_trace = ineligible.result(timeout=10)
        assert changed == subject.REVIEWER_JAPANESE_SYSTEM
        assert unchanged == m46.REVIEW_SYSTEM
        assert changed_trace["metrics"][subject.LABEL]["applied"] is True
        assert subject.LABEL not in unchanged_trace["metrics"]
        print(json.dumps({"ok": True}))
    """)


def test_real_candidate_caller_uses_existing_candidate_path_and_new_review_path():
    _run("""
        import json
        import uruha_actionable_help_delivery_m45 as action45
        import uruha_crosslingual_help_routing_m47 as m47
        import uruha_goal_progress_delivery_m46 as m46
        import uruha_state_changing_candidates_m51 as m51
        from uruha_explicit_first_step_route_p4 import classify_first_step_route_p4

        source = "我要整理桌上散開的便條紙。你會叫我先做什麼？"
        sources = [{"id": "current:1", "kind": "current_user", "text": source}]
        candidate_calls, review_calls = [], []
        metrics = {"model_calls_attempted": 0, "model_calls_completed": 0,
                   "prompt_tokens": 0, "completion_tokens": 0}

        def fake_candidates(system, payload, schema, deadline, observed_metrics):
            candidate_calls.append((system, payload, schema, deadline, observed_metrics))
            assert observed_metrics is metrics
            return {"sid": "current:1", "span": source, "goal": "便條紙を整理する",
                    "unknown": "", "items": [
                        {"mechanism": "structure_scaffold", "object": "便條紙", "verb": "並べる",
                         "effect": "便條紙が一列に並ぶ", "stop": "一列になったら止める",
                         "instruction": "便條紙を一列に並べて、そこで止めよ。"},
                        {"mechanism": "unknown", "object": "便條紙", "verb": "並べる",
                         "effect": "便條紙が動く", "stop": "動いたら止める",
                         "instruction": "便條紙を動かして、そこで止めよ。"},
                    ]}

        def fake_review(system, payload, schema, deadline, observed_metrics):
            review_calls.append((system, payload, schema, deadline, observed_metrics))
            assert observed_metrics is metrics
            return system

        def fake_delivery(user_input, candidate, logic, actual_sources, call_json=None):
            caller = m51.CandidateCaller()
            assert caller.underlying is action45._native_json
            plan = caller(m46.PLAN_SYSTEM, {"user_sources": actual_sources},
                          m46.plan_schema(actual_sources), 60.0, metrics)
            reviewed = caller(m46.REVIEW_SYSTEM,
                              {"sources": actual_sources, "plan": plan},
                              m46.review_schema(actual_sources, plan), 60.0, metrics)
            return reviewed, {m51.LABEL: {"schema": m51.SCHEMA}}

        action45.deliver_action = fake_delivery
        action45._native_json = fake_review
        m51._native_candidates = fake_candidates
        import uruha_source_bound_candidate_prompt_p4 as candidate_adapter
        candidate_adapter.install_source_bound_candidate_prompt_p4()
        import uruha_reviewer_japanese_counterfactual_p4 as subject
        subject.install_reviewer_japanese_counterfactual_p4()

        route = classify_first_step_route_p4(source)
        final, trace = action45.deliver_action(source, "before",
            {"explicit_desired_response_m25": {m47.LABEL: route}}, sources)
        assert final == subject.REVIEWER_JAPANESE_SYSTEM
        assert len(candidate_calls) == len(review_calls) == 1
        assert candidate_calls[0][0] == candidate_adapter.SOURCE_BOUND_CANDIDATE_SYSTEM
        assert review_calls[0][0] == subject.REVIEWER_JAPANESE_SYSTEM
        assert candidate_calls[0][1]["user_sources"] is sources
        assert review_calls[0][1]["sources"] is sources
        assert candidate_calls[0][3] == review_calls[0][3] == 60.0
        assert candidate_calls[0][4] is review_calls[0][4] is metrics
        assert trace[m51.LABEL][candidate_adapter.LABEL]["applied"] is True
        assert metrics[subject.LABEL]["model_calls_added"] == 0
        print(json.dumps({"ok": True}))
    """)


def test_old_m46_still_rejects_chinese_counterfactual_and_allows_label_ambiguity():
    _run("""
        import json
        import uruha_actionable_help_delivery_m45 as action45
        import uruha_goal_progress_delivery_m46 as m46
        import uruha_state_changing_candidates_m51 as m51
        import uruha_source_neutral_scaffold_m53 as m53
        from test_goal_progress_delivery_m46 import valid_plan, valid_review, TASK_SPAN

        action45.deliver_action = lambda *args, **kwargs: ("before", {m51.LABEL: {}})
        m51._native_candidates = lambda *args, **kwargs: {}
        action45._native_json = lambda *args, **kwargs: {}
        import uruha_source_bound_candidate_prompt_p4 as candidate_adapter
        candidate_adapter.install_source_bound_candidate_prompt_p4()
        unchanged_m46 = m46.inspect_goal_progress
        unchanged_m53 = m53.authorize_named_scaffold_m53
        import uruha_reviewer_japanese_counterfactual_p4 as subject
        subject.install_reviewer_japanese_counterfactual_p4()
        assert m46.inspect_goal_progress is unchanged_m46
        assert m53.authorize_named_scaffold_m53 is unchanged_m53
        plan = valid_plan()
        sources = [{"id": "current:4:clause:0", "kind": "current_user", "text": TASK_SPAN}]
        review = valid_review()
        review["counterfactual_before_jp"] = "講義尚未整理"
        review["counterfactual_after_jp"] = "講義已經整理"
        review["observed_progress_mechanism"] = "direct_atomic_completion"
        failed = m46.inspect_goal_progress(plan, sources, review)
        assert failed["content_violations"] == [
            "invalid_counterfactual_after_jp", "invalid_counterfactual_before_jp"]
        assert failed["content_passed"] is False
        review["counterfactual_before_jp"] = "報告書に構成の手掛かりがない状態"
        review["counterfactual_after_jp"] = "見出しが三つあり次に書く場所が見える状態"
        allowed = m46.inspect_goal_progress(plan, sources, review)
        assert allowed["content_passed"] is True
        assert allowed["surface_passed"] is True
        assert allowed["mechanism_exact_agreement"] is False
        label = m53.authorize_named_scaffold_m53(
            {"instruction_jp": "便條紙を『重要』と『不要』に分けてみよ。"},
            [{"id": "current:1", "kind": "current_user", "text": "便條紙を整理したい"}])
        assert label["status"] == "blocked" and label["unsupported_count"] == 2
        print(json.dumps({"ok": True}))
    """)


def test_reviewer_installer_rejects_missing_candidate_adapter():
    _run("""
        import json
        import uruha_reviewer_japanese_counterfactual_p4 as subject
        try:
            subject.install_reviewer_japanese_counterfactual_p4()
        except RuntimeError:
            pass
        else:
            raise AssertionError("reviewer installed without candidate context")
        print(json.dumps({"ok": True}))
    """)
