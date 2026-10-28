"""A stale Gradio event index must not silently become a session reset.

This proves admission mechanics without a model or a browser.  It is not a
claim that every old-client event mapping is safe.
"""

import asyncio

from gradio.state_holder import SessionState
import pytest

import uruha_web_ui as web


@pytest.mark.parametrize(
    "stale_value", [None, [], ["old turn"], "wrong-instance", "こんにちは"],
)
def test_legacy_or_missing_client_marker_never_resets(monkeypatch, stale_value):
    calls = []
    monkeypatch.setattr(web, "reset_session", lambda: calls.append("reset"))
    result = web.reset_session_browser_bound(stale_value)
    assert len(result) == 14
    assert all(value == web.gr.skip() for value in result)
    assert calls == []


def test_current_client_marker_allows_normal_reset_once(monkeypatch):
    calls = []

    def reset():
        calls.append("reset")
        return tuple(range(13))

    monkeypatch.setattr(web, "reset_session", reset)
    result = web.reset_session_browser_bound(web._RESET_INSTANCE_MARKER)
    assert calls == ["reset"]
    assert result[:-1] == tuple(range(13))
    assert result[-1] == web._browser_graph_tombstone()


def test_old_server_marker_rejected_after_instance_change(monkeypatch):
    previous_marker = web._RESET_INSTANCE_MARKER
    monkeypatch.setattr(web, "_RESET_INSTANCE_MARKER", "new-server-instance-marker")
    monkeypatch.setattr(
        web, "reset_session", lambda: pytest.fail("stale marker reached reset"),
    )
    assert len(web.reset_session_browser_bound(previous_marker)) == 14


def test_real_gradio_event_requires_client_textbox_marker(monkeypatch):
    demo = web.build_demo()  # No launch or model generation.
    components = {component["id"]: component for component in demo.config["components"]}
    matches = [
        (index, event) for index, event in enumerate(demo.config["dependencies"])
        if demo.fns[index].fn.__name__ == "reset_session_browser_bound"
    ]
    assert len(matches) == 1
    reset_index, reset_event = matches[0]
    assert len(reset_event["inputs"]) == 1
    marker_component = components[reset_event["inputs"][0]]
    assert marker_component["type"] == "textbox"
    assert marker_component["props"]["visible"] is False
    assert marker_component["props"]["value"] == web._RESET_INSTANCE_MARKER

    # In this build a pre-0942455 page's 2s timer fn_index 33 collides with
    # Reset.  Gradio ignores the extra old timer input and preprocesses its
    # history list as Textbox text.  Neither that list nor a missing value may
    # reach reset_session(), even through the actual Blocks API dispatch.
    assert reset_index == 33
    real_reset = web.reset_session
    monkeypatch.setattr(
        web, "reset_session", lambda: pytest.fail("stale timer reached reset"),
    )
    result = asyncio.run(demo.process_api(
        reset_index, [[], False], state=SessionState(demo),
    ))
    assert len(result["data"]) == len(reset_event["outputs"]) == 14

    calls = []
    monkeypatch.setattr(web, "reset_session", real_reset)
    # Keep the real reset_session() output shape so Gradio postprocessing is
    # tested as well; only its brain mutation is replaced below.
    monkeypatch.setattr(
        web.RUNTIME, "reset_brain_session", lambda: calls.append("reset"),
    )
    current = asyncio.run(demo.process_api(
        reset_index, [web._RESET_INSTANCE_MARKER], state=SessionState(demo),
    ))
    assert calls == ["reset"]
    assert len(current["data"]) == 14
