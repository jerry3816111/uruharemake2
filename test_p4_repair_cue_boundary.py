"""Zero-model contracts for the opt-in Japanese repair interjection boundary."""

import os
import subprocess
import sys
from unittest.mock import patch

import pytest

from uruha_brain_mac import RightBrain
import uruha_repair_cue_boundary_p4 as boundary


_PLAIN = {"intent": "chat", "scene": "casual", "surface_act": "plain_reply", "response_mode": "direct_answer"}
_ORIGINAL = RightBrain._dialogue_act_from_plan


def _act(user, logic=None, *, enabled=True):
    brain = RightBrain.__new__(RightBrain)
    with patch.object(boundary, "_ORIGINAL_DIALOGUE_ACT", _ORIGINAL):
        with patch.dict(os.environ, {"URUHA_P4_REPAIR_CUE_BOUNDARY": "1" if enabled else "0"}):
            return boundary.dialogue_act_with_repair_cue_boundary_p4(brain, logic or _PLAIN, user)


@pytest.mark.parametrize("user", [
    "水筒を見える棚に置いておくなら、どこがよさそう？",
    "「了解です」を柔らかく言い換えるとどうなる？",
    "机の位置を変えるなら、先に何を測ればいい？",
    "クリップを使える場所に置こう。",
    "教えてほしいのは、今日の日付だよ。",
])
def test_embedded_e_is_not_a_repair_cue(user):
    assert _act(user, enabled=False) == "repair_check"  # recorded old behavior
    assert _act(user) == "direct_chat_answer"


@pytest.mark.parametrize("user", [
    "え？さっきの意味が分からなかった。",
    "え、もう一度言って。",
    "え。今の話を確認したい。",
    "え",
    "Huh? Could you say that again?",
    "蛤？你剛才說的是什麼意思？",
])
def test_true_repair_cues_remain_repair_check(user):
    assert _act(user) == _act(user, enabled=False) == "repair_check"


def test_quoted_interjection_and_no_cue_do_not_trigger_repair():
    for user in ("『え？』を字幕にして。", "『彼、え？と聞いた』を字幕にして。"):
        assert _act(user, enabled=False) == "repair_check"
        assert _act(user) == "direct_chat_answer"
    assert _act("本棚のどこが空いてる？") == "direct_chat_answer"


def test_higher_priority_routes_remain_unchanged():
    for user, logic in [
        ("机の位置を変えるなら？", {**_PLAIN, "response_mode": "clarify_light"}),
        ("見える位置に置きたい。", {**_PLAIN, "surface_act": "protective_brake"}),
        ("見える位置に置きたい。", {**_PLAIN, "intent": "recall_recent"}),
    ]:
        assert _act(user, logic) == _act(user, logic, enabled=False)


def test_product_install_and_speech_plan_are_effective_in_subprocess():
    script = """
import os
from uruha_brain_mac import RightBrain
from uruha_repair_cue_boundary_p4 import install_repair_cue_boundary_p4
original = RightBrain._dialogue_act_from_plan
os.environ['URUHA_P4_REPAIR_CUE_BOUNDARY'] = '1'
assert install_repair_cue_boundary_p4() is True
assert install_repair_cue_boundary_p4() is False
brain = RightBrain.__new__(RightBrain)
brain.history = []
logic = {'intent': 'chat', 'scene': 'casual', 'surface_act': 'plain_reply', 'response_mode': 'direct_answer', 'core_message_jp': '少し測ろう'}
user = '机の位置を変えるなら、先に何を測ればいい？'
assert original(brain, logic, user) == 'repair_check'
assert brain._dialogue_act_from_plan(logic, user) == 'direct_chat_answer'
plan = brain.build_human_speech_plan(logic, user, {}, {})
assert plan['dialogue_act'] == 'direct_chat_answer', plan
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=45, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_product_entry_resolves_without_serving_in_subprocess():
    script = """
import ast
from pathlib import Path
import uruha_web_ui_product_p4_repair_cue_boundary as entry
tree = ast.parse(Path(entry.__file__).read_text(encoding='utf-8'))
def resolve(node):
    if isinstance(node, ast.Name):
        return vars(entry)[node.id]
    if isinstance(node, ast.Attribute):
        return getattr(resolve(node.value), node.attr)
    raise AssertionError(type(node).__name__)
targets = [node.func for node in ast.walk(tree)
           if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
           and (node.func.attr.startswith('install_') or node.func.attr == 'build_demo')]
assert len(targets) == 20, len(targets)
assert all(callable(resolve(target)) for target in targets)
assert callable(entry.install_location_advice_act_handoff_p4)
assert callable(entry.install_repair_cue_boundary_p4)
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=45, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_controller_points_to_new_isolated_entry_in_subprocess():
    script = """
from pathlib import Path
import p4_repair_cue_boundary_detached_control as controller
assert controller.ENTRYPOINT.name == 'uruha_web_ui_product_p4_repair_cue_boundary.py'
assert controller.base_controller.ENTRYPOINT == controller.ENTRYPOINT
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=45, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
