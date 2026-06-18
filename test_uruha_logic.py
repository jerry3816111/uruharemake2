import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_test_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        clean_env["URUHA_SKIP_AUTO_VENV"] = "1"
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_test_python()
os.environ["URUHA_SKIP_AUTO_VENV"] = "1"

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    import uruha_brain_mac as brain_mod
    from fast_eval_brain import FastRightBrain, build_fast_brain, run_fast_turn
except Exception as exc:
    print(f"Failed to import smoke-harness modules: {exc}")
    sys.exit(1)


SMOKE_CASES = [
    "你是誰？",
    "怒ってる？",
    "別のvtuber見てくる。",
    "之前不是說你是在北海道長大的嗎？",
    "我不想活了。",
]


def run_test():
    print("== UruhaBrain Smoke Harness ==")
    print("Mode: no-LoRA / no-heavy-right-brain-load")
    print(f"Python: {sys.executable}")

    start_total = time.time()
    try:
        brain = build_fast_brain(brain_mod)
    except Exception as exc:
        print(f"Failed to build fast brain: {exc}")
        return 1

    build_elapsed = time.time() - start_total
    print(f"Build time: {build_elapsed:.2f}s")
    print(f"Right brain class: {type(brain.right_brain).__name__}")
    print(f"Fast smoke flag: {getattr(brain, '_fast_smoke_mode', False)}")

    if not isinstance(brain.right_brain, FastRightBrain):
        print("Smoke harness is not using FastRightBrain.")
        return 2

    print("\n--- Representative Turns ---\n")
    for text in SMOKE_CASES:
        turn_start = time.time()
        response = run_fast_turn(brain, text)
        turn_elapsed = time.time() - turn_start

        reply = response.get("reply", "")
        intent = response.get("intent", "unknown")
        scene = response.get("scene", "unknown")

        print(f"User: {text}")
        print(f"Uruha: {reply}")
        print(f"  [Intent: {intent}, Scene: {scene}, Turn Time: {turn_elapsed:.2f}s]")
        print("-" * 40)

    total_elapsed = time.time() - start_total
    print(f"\nTotal elapsed: {total_elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_test())
