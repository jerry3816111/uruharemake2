import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_project_python():
    # Re-exec into the repo venv so imports always come from the compatible env.
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        print(f"⚠️ 偵測到目前 Python 不是專案 venv：{sys.executable}")
        print(f"↪️ 自動切換到：{EXPECTED_PYTHON}")
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_project_python()

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ModuleNotFoundError:
    class _NoColor:
        def __getattr__(self, _name):
            return ""

    def init(*_args, **_kwargs):
        return None

    Fore = _NoColor()
    Style = _NoColor()

# 匯入大腦與感官模組 (增加詳細錯誤印出，精準抓蟲)
try:
    from uruha_brain_mac import UruhaBrainV4_Mac
    from uruha_semantic_persona_surface_m39 import install_m39_surface_verifier

    install_m39_surface_verifier()
except Exception as e:
    print(Fore.RED + f"❌ 載入 uruha_brain_mac.py 失敗！")
    print(Fore.YELLOW + f"詳細錯誤原因: {e}")
    sys.exit(1)

try:
    from uruha_senses import UruhaEars, UruhaMouth
except Exception as e:
    print(Fore.RED + f"❌ 載入 uruha_senses.py 失敗！")
    print(Fore.YELLOW + f"詳細錯誤原因: {e}")
    sys.exit(1)


def main():
    print(Fore.MAGENTA + "="*60)
    print(Fore.MAGENTA + "✨ Uruha 數位生命體 v5.1 (Local V10 Brain + Whisper Turbo) 啟動中 ✨")
    print(Fore.MAGENTA + "="*60)

    # 1. 先啟動大腦。右腦載入最重，先把這段做完，live 模式會比較穩。
    try:
        brain = UruhaBrainV4_Mac()
    except Exception as e:
        print(Fore.RED + f"❌ 大腦系統初始化失敗: {e}")
        sys.exit(1)

    # 2. 啟動感官 (耳朵與嘴巴)
    try:
        ears = UruhaEars()
        mouth = UruhaMouth()
    except Exception as e:
        print(Fore.RED + f"❌ 感官系統初始化失敗: {e}")
        sys.exit(1)

    print(Fore.GREEN + "\n✅ 所有神經網絡連接完畢！Uruha 已經準備好聽你說話了。")
    print(Fore.YELLOW + "💡 提示：直接對麥克風說話。說「再見」或「退出」可結束通話。")
    print(Fore.YELLOW + "💡 STT 使用 Whisper Turbo，右腦使用本機 V10 LoRA。\n")
    print(Fore.MAGENTA + "="*60)

    # 3. 生命主迴圈 (Live Voice-to-Voice Loop)
    while True:
        try:
            # ➡️ 步驟 A：聆聽 (STT)
            user_text = ears.listen_and_transcribe()

            if not user_text:
                continue

            if any(word in user_text.lower() for word in ["再見", "退出", "exit", "bye", "goodbye"]):
                print(Fore.CYAN + "\nUruha: おやすみなさい！またね～ (系統關閉中...)")
                mouth.speak_and_play("おやすみなさい！またね")
                break

            # ➡️ 步驟 B：思考 (Brain)
            print(Style.DIM + "🧠 [大腦思考中...]")
            start_think = time.time()

            reply = brain.live(user_text)

            end_think = time.time()
            print(f"{Fore.CYAN}Uruha: {Fore.WHITE}{reply} {Style.DIM}(思考耗時: {round(end_think - start_think, 2)}s)")

            # ➡️ 步驟 C：說話 (TTS)
            mouth.speak_and_play(reply)

            time.sleep(0.5)

        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n強制關閉系統...")
            break
        except Exception as e:
            print(Fore.RED + f"\n❌ 發生未預期的錯誤: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
