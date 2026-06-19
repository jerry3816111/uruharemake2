import json
import os
import subprocess
import sys
import time

from project_paths import (
    BASE_DIR,
    COGNITIVE_ARCHITECTURE_REPORT_PATH,
    DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH,
    DOMAIN_EVAL_SUITE_REPORT_PATH,
    FORMAL_BRAIN_BENCHMARKS_REPORT_JSON_PATH,
    HUMAN_SPEECH_LAYER_REPORT_JSON_PATH,
    LONG_DIALOGUE_MEMORY_REPORT_PATH,
    MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH,
    MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH,
    REPLY_DIVERSITY_REPORT_PATH,
    RUNTIME_DYNAMICS_REPORT_PATH,
    SELF_DISTRESS_SURFACE_CONTRACT_REPORT_JSON_PATH,
    SUPPORT_PREFIX_CONTRACT_REPORT_JSON_PATH,
    V2_HUMAN_ANSWER_REPORT_PATH,
)

EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))
REPORT_PATH = DOMAIN_EVAL_SUITE_REPORT_PATH

TASKS = [
    ("cognitive_architecture", "cognitive_architecture_eval.py", COGNITIVE_ARCHITECTURE_REPORT_PATH),
    ("runtime_dynamics", "runtime_dynamics_eval.py", RUNTIME_DYNAMICS_REPORT_PATH),
    ("long_dialogue_memory", "long_dialogue_memory_eval.py", LONG_DIALOGUE_MEMORY_REPORT_PATH),
    ("memory_causal_effect", "memory_causal_effect_eval.py", MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH),
    (
        "memory_speakability_response",
        "memory_speakability_response_eval.py",
        MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH,
    ),
    ("reply_diversity", "reply_diversity_eval.py", REPLY_DIVERSITY_REPORT_PATH),
    ("human_answer_proxy", "eval_v2_human_answer.py", V2_HUMAN_ANSWER_REPORT_PATH),
    ("formal_benchmarks", "run_formal_brain_benchmarks.py", FORMAL_BRAIN_BENCHMARKS_REPORT_JSON_PATH),
    ("human_speech_layer", "run_human_speech_layer_eval.py", HUMAN_SPEECH_LAYER_REPORT_JSON_PATH),
    ("daily_state_self_distress", "daily_state_self_distress_eval.py", DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH),
    ("self_distress_surface_contract", "self_distress_surface_contract_eval.py", SELF_DISTRESS_SURFACE_CONTRACT_REPORT_JSON_PATH),
    ("support_prefix_contract", "support_prefix_contract_eval.py", SUPPORT_PREFIX_CONTRACT_REPORT_JSON_PATH),
]


def _ensure_project_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_project_python()


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    outputs = {}
    task_runs = []
    for key, script, report_path in TASKS:
        print(f"[RUN] {script}")
        started_at = time.time()
        proc = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, script)],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
        )
        outputs[key] = load_json(report_path)
        task_runs.append(
            {
                "task": key,
                "script": script,
                "returncode": proc.returncode,
                "duration_seconds": round(time.time() - started_at, 3),
                "stdout_tail": (proc.stdout or "")[-4000:],
                "stderr_tail": (proc.stderr or "")[-4000:],
                "report_found": bool(outputs[key]),
            }
        )

    summary = {
        "cognitive_architecture": (outputs.get("cognitive_architecture") or {}).get("summary", {}),
        "runtime_dynamics": (outputs.get("runtime_dynamics") or {}).get("summary", {}),
        "long_dialogue_memory": (outputs.get("long_dialogue_memory") or {}).get("summary", {}),
        "memory_causal_effect": (outputs.get("memory_causal_effect") or {}).get("summary", {}),
        "memory_speakability_response": (outputs.get("memory_speakability_response") or {}).get("summary", {}),
        "reply_diversity": (outputs.get("reply_diversity") or {}).get("summary", {}),
        "human_answer_proxy": (outputs.get("human_answer_proxy") or {}).get("summary", {}),
        "formal_benchmarks": (outputs.get("formal_benchmarks") or {}).get("summary", {}),
        "human_speech_layer": (outputs.get("human_speech_layer") or {}).get("metrics", {}),
        "daily_state_self_distress": (outputs.get("daily_state_self_distress") or {}).get("summary", {}),
        "self_distress_surface_contract": (outputs.get("self_distress_surface_contract") or {}).get("summary", {}),
        "support_prefix_contract": (outputs.get("support_prefix_contract") or {}).get("summary", {}),
        "task_runs": task_runs,
    }
    report = {
        "tasks": [task[0] for task in TASKS],
        "summary": summary,
        "reports": outputs,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(REPORT_PATH)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
