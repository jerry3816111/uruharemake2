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
    SURFACE_MICROPLANNING_REPORT_JSON_PATH,
    V2_HUMAN_ANSWER_REPORT_PATH,
)

EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))
REPORT_PATH = DOMAIN_EVAL_SUITE_REPORT_PATH
TASK_TIMEOUT_SECONDS = int(os.environ.get("URUHA_EVAL_TASK_TIMEOUT_SECONDS", "600"))
FORMAL_BENCHMARK_REFRESH_ENV = "URUHA_DOMAIN_REFRESH_FORMAL"
REUSABLE_REPORT_TASKS = {"formal_benchmarks"}

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
    ("surface_microplanning", "eval_surface_microplanning_holdout.py", SURFACE_MICROPLANNING_REPORT_JSON_PATH),
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


def should_reuse_existing_report(task_key, report_path, env=None):
    env = os.environ if env is None else env
    refresh_requested = str(env.get(FORMAL_BENCHMARK_REFRESH_ENV, "0")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return task_key in REUSABLE_REPORT_TASKS and os.path.exists(report_path) and not refresh_requested


def should_reuse_report_for_missing_runner(script_path, report_path):
    return not os.path.exists(script_path) and os.path.exists(report_path)


def task_run_succeeded(row):
    mode = str((row or {}).get("execution_mode") or "")
    if mode.startswith("reused_existing_report"):
        return bool((row or {}).get("report_found"))
    return (row or {}).get("returncode") == 0 and bool((row or {}).get("report_found"))


def main():
    outputs = {}
    task_runs = []
    for key, script, report_path in TASKS:
        script_path = os.path.join(BASE_DIR, script)
        if should_reuse_report_for_missing_runner(script_path, report_path):
            print(f"[REUSE: MISSING RUNNER] {script}: {report_path}")
            outputs[key] = load_json(report_path)
            task_runs.append(
                {
                    "task": key,
                    "script": script,
                    "returncode": None,
                    "duration_seconds": 0.0,
                    "stdout_tail": "",
                    "stderr_tail": f"Runner is not tracked at {script_path}; reused the existing report.",
                    "report_found": bool(outputs[key]),
                    "execution_mode": "reused_existing_report_missing_runner",
                    "report_path": report_path,
                    "refresh_instruction": "Add the missing runner to the repository before refreshing this task.",
                }
            )
            continue

        if should_reuse_existing_report(key, report_path):
            print(f"[REUSE] {script}: {report_path}")
            outputs[key] = load_json(report_path)
            task_runs.append(
                {
                    "task": key,
                    "script": script,
                    "returncode": None,
                    "duration_seconds": 0.0,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "report_found": bool(outputs[key]),
                    "execution_mode": "reused_existing_report",
                    "report_path": report_path,
                    "refresh_instruction": f"Set {FORMAL_BENCHMARK_REFRESH_ENV}=1 to execute this task.",
                }
            )
            continue

        print(f"[RUN] {script}")
        started_at = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, script_path],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=TASK_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
            proc = subprocess.CompletedProcess(
                args=exc.cmd,
                returncode=124,
                stdout=stdout,
                stderr=f"{stderr}\nTimed out after {TASK_TIMEOUT_SECONDS} seconds.",
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
                "execution_mode": "executed",
                "report_path": report_path,
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
        "surface_microplanning": (outputs.get("surface_microplanning") or {}).get("summary", {}),
        "task_runs": task_runs,
        "execution_ok": all(task_run_succeeded(row) for row in task_runs),
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
    return 0 if summary["execution_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
