import os
import time
import requests
import subprocess
import speech_recognition as sr
import whisper
from colorama import init, Fore, Style

init(autoreset=True)

# ===========================
# 🎤 耳朵：Whisper STT (語音轉文字)
# ===========================
class UruhaEars:
    def __init__(self, model_name=None, model_device=None):
        self.model_name = model_name or os.getenv("URUHA_WHISPER_MODEL", "turbo")
        self.model_device = model_device or os.getenv("URUHA_WHISPER_DEVICE", "cpu")

        print(
            Fore.CYAN
            + f"👂 [耳朵] 正在載入 Whisper {self.model_name} "
            + f"(device={self.model_device})..."
        )
        self.model = whisper.load_model(self.model_name, device=self.model_device)
        self.recognizer = sr.Recognizer()

        # Turbo 的定位是低延遲，所以這裡收短一點。
        self.recognizer.pause_threshold = 1.2
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.non_speaking_duration = 0.4

        print(Fore.GREEN + f"✅ [耳朵] Whisper {self.model_name} 載入完成！")

    def _postprocess_transcript(self, user_text):
        user_text = (user_text or "").strip()

        hallucinations = [
            "Thank you.", "Thank you", "Thanks.", "You", "...", "。",
            "謝謝", "謝謝。", "Bye.", "再見。", "Thank you for watching."
        ]
        if user_text in hallucinations or len(user_text.strip("。.,!? ")) == 0:
            return ""
        return user_text

    def _transcribe_path(self, wav_path):
        result = self.model.transcribe(
            wav_path,
            fp16=False,
            temperature=0.0,
            condition_on_previous_text=False,
            verbose=False,
        )
        return self._postprocess_transcript(result["text"])

    def transcribe_audio_file(self, audio_path):
        """將已存在的音訊檔交給 Whisper 辨識。"""
        if not audio_path or not os.path.exists(audio_path):
            return ""
        print(Fore.CYAN + f"⏳ 正在將音訊檔轉換為文字: {audio_path}")
        user_text = self._transcribe_path(audio_path)
        print(Fore.GREEN + f"🗣️ 你說: {user_text}")
        return user_text

    def listen_and_transcribe(self):
        """錄音並使用 Whisper 辨識成文字"""
        with sr.Microphone() as source:
            # Turbo 版本優先追求接話速度，環境音校正縮短。
            self.recognizer.adjust_for_ambient_noise(source, duration=0.25)
            print(Fore.YELLOW + "\n🎤 請開始說話 (短暫停頓可接受，安靜一下就會自動送出)...")
            
            try:
                # 讓 live 模式接話更快，避免麥克風卡太久。
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=20)
            except sr.WaitTimeoutError:
                return "" # 完全沒講話，直接當作空字串
            
        print(Fore.CYAN + "⏳ 正在將語音轉換為文字...")
        
        temp_wav = "temp_user_input.wav"
        with open(temp_wav, "wb") as f:
            f.write(audio.get_wav_data())

        try:
            user_text = self._transcribe_path(temp_wav)
        finally:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)

        print(Fore.GREEN + f"🗣️ 你說: {user_text}")
        return user_text

# ===========================
# 👄 嘴巴：Style-Bert-VITS2 TTS (文字轉語音並播放)
# ===========================
class UruhaMouth:
    def __init__(self, base_url="http://127.0.0.1:5001"):
        self.base_url = base_url
        self.model_id = self._get_model_id()

    def _get_model_id(self):
        """向 Server 查詢並鎖定 Uruha 的 model_id"""
        print(Fore.CYAN + "👄 [嘴巴] 正在連線 TTS Server 尋找 Uruha 的聲音模型...")
        try:
            info_res = requests.get(f"{self.base_url}/models/info")
            info_res.raise_for_status() 
            models_info = info_res.json()
            
            for m_id, m_data in models_info.items():
                if "Uruha" in str(m_data) or "uruha" in str(m_data).lower():
                    print(Fore.GREEN + f"✅ [嘴巴] 成功鎖定 Uruha 聲音模型 (ID: {m_id})！")
                    return int(m_id)
                    
            print(Fore.YELLOW + "⚠️ 找不到名為 Uruha 的模型，預設使用 ID 0")
            return 0
        except Exception as e:
            print(Fore.RED + f"❌ TTS Server 連線失敗: {e}。請確認 API Server 已啟動。")
            return 0

    def speak_and_play(self, text):
        """將日文文字轉換為語音並透過 Mac 喇叭播放，包含計時與防崩潰機制"""
        output_file = self.synthesize_to_file(text)
        if not output_file:
            return
        try:
            print(Fore.GREEN + "🔊 播放中...")
            subprocess.run(["afplay", output_file])
        except Exception as e:
             print(Fore.RED + f"❌ 播放失敗: {e}")

    def synthesize_to_file(self, text, output_file=None):
        """將文字丟給 TTS server，回傳生成好的 wav 檔路徑。"""
        if not text:
            return None
            
        # 防崩潰保護：如果句子超過 90 個字元，強制截斷，避免 TTS Server 報錯 (422)
        if len(text) > 90:
            print(Fore.YELLOW + f"⚠️ [警告] 生成文本過長 ({len(text)}字)，為避免 TTS 崩潰已強制截斷。")
            text = text[:85] + "..."
            
        print(Fore.CYAN + f"🎵 正在生成語音: {text}")
        
        # ⏱️ 開始計時
        tts_start_time = time.time()
        
        voice_url = f"{self.base_url}/voice"
        params = {
            "text": text,
            "model_id": self.model_id,
            "speaker_id": 0,        
            "sdp_ratio": 0.2,       
            "noise": 0.6,           
            "noisew": 0.8,          
            "length": 1.0,          
            "language": "JP",
            "auto_split": "true",
            "style": "Neutral",
            "style_weight": 1.0
        }

        try:
            audio_res = requests.get(voice_url, params=params)
            audio_res.raise_for_status()
            
            tts_end_time = time.time()
            tts_duration = round(tts_end_time - tts_start_time, 2)
            print(Style.DIM + f"⏱️ (語音生成耗時: {tts_duration}s)")
            
            output_file = output_file or "uruha_reply.wav"
            with open(output_file, "wb") as f:
                f.write(audio_res.content)
            return output_file
            
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"❌ 語音生成失敗: {e}")
            if e.response is not None:
                print(Fore.RED + f"伺服器錯誤詳情: {e.response.text}")
        except Exception as e:
             print(Fore.RED + f"❌ 語音生成失敗: {e}")
        return None

# ===========================
# 🧪 單獨測試感官模組
# ===========================
if __name__ == "__main__":
    print(Fore.MAGENTA + "=== 啟動 Uruha 感官測試 ===")
    ears = UruhaEars()
    mouth = UruhaMouth()
    
    print(Fore.MAGENTA + "\n=== 測試開始 ===")
    while True:
        try:
            user_text = ears.listen_and_transcribe()
            if not user_text: continue
            if "再見" in user_text or "exit" in user_text.lower(): break
            test_reply = "えー、あなたが言ったのは、" + user_text + "、ですね。"
            mouth.speak_and_play(test_reply)
        except KeyboardInterrupt:
            break
