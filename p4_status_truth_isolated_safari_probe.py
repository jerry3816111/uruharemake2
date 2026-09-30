#!/usr/bin/env python3
"""One-off status-only Safari probe with a fake invalid tool response.

Other chat inputs are rejected before the product runtime. The allowed status
turn uses no actual model inference or status-tool executor.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import p4_status_truth_safe_isolated_product_launcher as launcher
import p4_b_safe_isolated_product_launcher_v2 as sandbox


ROOT = Path(__file__).resolve().parent
PORT = 7892


CHILD_CODE = '''
import json
import uruha_web_ui_product_p4_status_truth as entry
import uruha_product_function_calling_p4 as product
import uruha_read_only_function_calling_p4 as core

class InvalidToolProvider:
    def invoke(self, **kwargs):
        return {
            "model": kwargs["model"],
            "message": {"content": "", "tool_calls": [{
                "type": "function",
                "function": {"name": "write_file", "arguments": {}},
            }]},
            "done": True,
            "prompt_eval_count": 0,
            "eval_count": 0,
        }

product._PROVIDER_FACTORY = InvalidToolProvider
def reject_status_reader(runtime):
    raise AssertionError("diagnostic_status_reader_must_not_run")
product.read_product_runtime_status = reject_status_reader
previous_run_turn = entry._base._run_turn
def status_only_turn(user_text, *args, **kwargs):
    if not core.classify_runtime_status_request(str(user_text or "")).get("selected"):
        raise RuntimeError("diagnostic_status_only")
    return previous_run_turn(user_text, *args, **kwargs)
entry._base._run_turn = status_only_turn
demo = entry._base.build_demo()
demo.queue(default_concurrency_limit=1)
print(json.dumps({"ready": True, "fake_provider_only": True}), flush=True)
demo.launch(server_name="127.0.0.1", server_port=7892, inbrowser=False,
            css=entry._base.WEB_CSS, head=entry._base.WEB_HEAD)
'''


def main() -> int:
    summary, env, layout, created, profile = launcher.preflight_status_truth(
        python_arg=str(ROOT / ".venv/product_checks/bin/python"),
        runtime_root_arg=None,
        reuse_runtime=False,
        port=PORT,
        prewarm=False,
    )
    command = sandbox.sandbox_command(
        profile, [summary["python"], "-c", CHILD_CODE]
    )
    print(
        json.dumps(
            {
                "url": f"http://127.0.0.1:{PORT}/",
                "runtime_root": str(layout["runtime_root"]),
                "fake_provider_only": True,
                "actual_model_inference_count": 0,
                "status_tool_execution_count": 0,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            return process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            return process.wait()
    finally:
        if created:
            shutil.rmtree(layout["runtime_root"], ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
