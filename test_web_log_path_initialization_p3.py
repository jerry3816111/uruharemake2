"""Regression for isolated Web log path initialization."""

import os
from pathlib import Path
import subprocess
import sys


def test_environment_overridden_web_log_parent_directories_are_created(tmp_path):
    jsonl_path = tmp_path / "jsonl" / "nested" / "turns.jsonl"
    text_path = tmp_path / "text" / "nested" / "turns.txt"
    program = r'''
from pathlib import Path
import os
import uruha_web_ui
jsonl = Path(os.environ["URUHA_WEB_LOG_JSONL_PATH"])
text = Path(os.environ["URUHA_WEB_LOG_TXT_PATH"])
assert uruha_web_ui.WEB_LOG_JSONL == str(jsonl.resolve())
assert uruha_web_ui.WEB_LOG_TXT == str(text.resolve())
assert jsonl.parent.is_dir()
assert text.parent.is_dir()
assert not jsonl.exists()
assert not text.exists()
'''
    env = {
        **os.environ,
        "URUHA_WEB_LOG_JSONL_PATH": str(jsonl_path),
        "URUHA_WEB_LOG_TXT_PATH": str(text_path),
        "URUHA_WEB_PREWARM_BRAIN": "0",
        "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
        "GRADIO_ANALYTICS_ENABLED": "false",
    }
    subprocess.run(
        [sys.executable, "-c", program],
        cwd=Path(__file__).resolve().parent,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
