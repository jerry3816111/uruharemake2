"""Prospective red contracts for the P4 source-bound M51 candidate instruction.

These use a fake transport and a fake delivery owner in a fresh process. They
must not contact the model or turn deterministic wiring into a quality claim.
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


def test_only_source_bound_first_step_substitutes_one_candidate_instruction():
    _run("""
        import json
        import uruha_actionable_help_delivery_m45 as action45
        import uruha_crosslingual_help_routing_m47 as m47
        import uruha_state_changing_candidates_m51 as m51
        from uruha_explicit_first_step_route_p4 import classify_first_step_route_p4

        calls = []
        original_system = m51.CANDIDATE_SYSTEM
        payload = {"user_sources": [{"id": "current:1", "kind": "current_user", "text": "source"}]}
        schema = {"properties": {"items": {"type": "array"}}}
        deadline = 987.25
        metrics = {"model_calls_attempted": 0}

        def fake_transport(system, received_payload, received_schema, received_deadline, received_metrics):
            calls.append((system, received_payload, received_schema, received_deadline, received_metrics))
            return {"items": []}

        def fake_delivery(user_input, candidate, logic, sources, call_json=None):
            m51._native_candidates(m51.CANDIDATE_SYSTEM, payload, schema, deadline, metrics)
            return candidate, {m51.LABEL: {"schema": m51.SCHEMA, "status": "no_structurally_valid_candidate"}}

        action45.deliver_action = fake_delivery
        m51._native_candidates = fake_transport
        import uruha_source_bound_candidate_prompt_p4 as subject
        assert subject.install_source_bound_candidate_prompt_p4() is True
        assert subject.install_source_bound_candidate_prompt_p4() is False

        positive = "我要整理桌上散開的便條紙。你會叫我先做什麼？"
        ruled = "我要整理桌上的三張收據，依日期先後排好。你會叫我先做什麼？"
        negatives = [
            "我該先做什麼？",
            "我不要方法，只想抱怨桌上太亂。你會叫我先做什麼？",
            "死にたい。まず何をすればいい？",
            "朋友問我：「我要整理桌子，我該先做什麼？」",
            "There are two notebooks. What should I do first?",
        ]

        def turn(source, forged=None, source_kind="current_user"):
            route = classify_first_step_route_p4(source)
            if forged == "digest":
                route = dict(route, input_digest="not-current-source")
            elif forged == "span":
                route = dict(route, task_spans=[dict(route["task_spans"][0], span_digest="bad")])
            payload["user_sources"][0]["text"] = source
            logic = {
                "explicit_desired_response_m25": {m47.LABEL: route,
                                                  "selected_policy": route.get("selected_policy")},
                m47.LABEL: route,
                "desired_response_policy_m18": route.get("selected_policy"),
            }
            result, trace = action45.deliver_action(
                source, "before", logic,
                [{"id": "current:1" if source_kind == "current_user" else "prior:1",
                  "kind": source_kind, "text": source}],
            )
            assert result == "before"
            observed = calls.pop()
            assert observed[1] is payload and observed[2] is schema
            assert observed[3] is deadline and observed[4] is metrics
            return observed[0], trace

        for source in (positive, ruled):
            changed_system, trace = turn(source)
            assert changed_system != original_system
            assert "source" in changed_system.lower()
            metadata = trace[m51.LABEL]["source_bound_candidate_prompt_p4"]
            assert metadata["applied"] is True
            assert metadata["model_calls_added"] == 0
            assert metadata["raw_candidate_text_persisted"] is False
            assert source not in json.dumps(metadata, ensure_ascii=False)
        for source in negatives:
            unchanged_system, trace = turn(source)
            assert unchanged_system == original_system
            assert "source_bound_candidate_prompt_p4" not in trace[m51.LABEL]
        for kwargs in ({"forged": "digest"}, {"forged": "span"},
                       {"source_kind": "linked_previous_user"}):
            mismatched_system, trace = turn(positive, **kwargs)
            assert mismatched_system == original_system
            assert "source_bound_candidate_prompt_p4" not in trace[m51.LABEL]
        assert m51.CANDIDATE_SYSTEM == original_system
        assert len(calls) == 0
        print(json.dumps({"ok": True}))
    """)


def test_candidate_instruction_is_context_isolated_across_threads():
    _run("""
        import json
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        import uruha_actionable_help_delivery_m45 as action45
        import uruha_crosslingual_help_routing_m47 as m47
        import uruha_state_changing_candidates_m51 as m51
        from uruha_explicit_first_step_route_p4 import classify_first_step_route_p4

        barrier = Barrier(2)
        original_system = m51.CANDIDATE_SYSTEM

        def fake_transport(system, payload, schema, deadline, metrics):
            barrier.wait(timeout=5)
            return system

        def fake_delivery(user_input, candidate, logic, sources, call_json=None):
            seen = m51._native_candidates(
                m51.CANDIDATE_SYSTEM, {"user_sources": sources}, {}, 10.0, {}
            )
            return seen, {m51.LABEL: {"schema": m51.SCHEMA}}

        action45.deliver_action = fake_delivery
        m51._native_candidates = fake_transport
        import uruha_source_bound_candidate_prompt_p4 as subject
        subject.install_source_bound_candidate_prompt_p4()

        def turn(source):
            route = classify_first_step_route_p4(source)
            logic = {"explicit_desired_response_m25": {m47.LABEL: route}}
            return action45.deliver_action(
                source, "before", logic,
                [{"id": "current:1", "kind": "current_user", "text": source}],
            )

        positive = "我要整理桌上散開的便條紙。你會叫我先做什麼？"
        negative = "我該先做什麼？"
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_positive = pool.submit(turn, positive)
            future_negative = pool.submit(turn, negative)
            changed, changed_trace = future_positive.result(timeout=10)
            unchanged, unchanged_trace = future_negative.result(timeout=10)
        assert changed != original_system
        assert unchanged == original_system
        assert changed_trace[m51.LABEL]["source_bound_candidate_prompt_p4"]["applied"] is True
        assert "source_bound_candidate_prompt_p4" not in unchanged_trace[m51.LABEL]
        assert m51.CANDIDATE_SYSTEM == original_system
        print(json.dumps({"ok": True}))
    """)


def test_original_m53_named_label_rejection_remains_after_adapter_install():
    _run("""
        import json
        import uruha_actionable_help_delivery_m45 as action45
        import uruha_goal_progress_delivery_m46 as m46
        import uruha_source_neutral_scaffold_m53 as m53
        import uruha_state_changing_candidates_m51 as m51

        action45.deliver_action = lambda *args, **kwargs: ("before", {m51.LABEL: {}})
        m51._native_candidates = lambda *args, **kwargs: {}
        unchanged_m53 = m53.authorize_named_scaffold_m53
        unchanged_m46 = m46.structural_plan_violations
        import uruha_source_bound_candidate_prompt_p4 as subject
        subject.install_source_bound_candidate_prompt_p4()
        source = [{"id": "current:1", "kind": "current_user",
                   "text": "我要整理桌上散開的便條紙。你會叫我先做什麼？"}]
        plan = {"instruction_jp": "便條紙を『重要』と『不要』に分けてみよ。"}
        decision = m53.authorize_named_scaffold_m53(plan, source)
        assert m53.authorize_named_scaffold_m53 is unchanged_m53
        assert decision["status"] == "blocked"
        assert decision["unsupported_count"] == 2
        assert m46.structural_plan_violations is unchanged_m46
        print(json.dumps({"ok": True}))
    """)
