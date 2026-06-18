import contextlib
import io
import re
import threading
import time
from collections import Counter

from openai import OpenAI


class FastRightBrain:
    def __init__(self):
        self.history = []
        self.variant_counts = Counter()

    def reset_session_state(self):
        self.history = []
        self.variant_counts.clear()

    def _rotate(self, key, variants):
        variants = [item for item in variants if item]
        if not variants:
            return ""
        index = self.variant_counts[key] % len(variants)
        self.variant_counts[key] += 1
        return variants[index]

    def _offered_item(self, text):
        lowered = str(text or "").lower()
        item_map = [
            ("apple pie", "アップルパイ"),
            ("アップルパイ", "アップルパイ"),
            ("蘋果派", "アップルパイ"),
            ("苹果派", "アップルパイ"),
            ("fries", "ポテト"),
            ("薯條", "ポテト"),
            ("薯条", "ポテト"),
            ("burger", "バーガー"),
            ("漢堡", "バーガー"),
            ("汉堡", "バーガー"),
            ("strawberry milk", "いちごミルク"),
            ("草莓牛奶", "いちごミルク"),
            ("いちごミルク", "いちごミルク"),
        ]
        for raw, jp in item_map:
            if raw.lower() in lowered:
                return jp
        return ""

    def _has_today_reference(self, text):
        lowered = str(text or "").lower()
        return any(token in lowered for token in ["今天", "今日", "today"])

    def _has_now_reference(self, text):
        lowered = str(text or "").lower()
        return any(token in lowered for token in ["現在", "现在", "right now", "今は", "今も", "今なに", "今何"])

    def _asks_same_state(self, text):
        lowered = str(text or "").lower()
        return any(token in lowered for token in ["現在也是", "现在也是", "今もそう", "今も同じ", "still the same", "same now", "still like that"])

    def _asks_status_still(self, text):
        lowered = str(text or "").lower()
        return any(
            token in lowered
            for token in ["還在發呆", "还在发呆", "還在放空", "还在放空", "還在摸魚", "还在摸鱼", "still spacing out", "still zoning out", "still daydreaming", "まだぼーっと", "まだだらけ"]
        )

    def _asks_repair_confirmation(self, text):
        lowered = str(text or "").lower()
        return any(
            token in lowered
            for token in [
                "所以你是那個意思",
                "所以你是那个意思",
                "所以就是那個意思",
                "所以就是那个意思",
                "所以你意思是",
                "所以你的意思是",
                "so you mean",
                "so that's what you mean",
                "that's what you meant",
                "つまりそういうこと",
                "そういう意味",
                "ってこと",
            ]
        )

    def _looks_generic_reentry_marker(self, text):
        lowered = str(text or "").lower()
        return any(
            token in lowered
            for token in [
                "剛剛那個",
                "刚刚那个",
                "前面的",
                "前面那個",
                "前面那个",
                "那個部分",
                "那个部分",
                "剛才那個",
                "刚才那个",
                "那個話題",
                "那个话题",
            ]
        )

    def _looks_thread_choice_disambiguation(self, text):
        lowered = str(text or "").lower()
        return any(token in lowered for token in ["還是", "还是", " or "]) and self._looks_generic_reentry_marker(text)

    def _repair_target_label(self, text):
        lowered = str(text or "").lower()
        target_map = [
            ("最後の一言", ["最後那句", "最后那句", "最後一句", "最后一句", "最後那段", "最后那段", "最後の一言", "最後の文", "last line", "final line"]),
            ("最初の一言", ["前面那句", "前面那段", "最前面", "一開始那句", "一开始那句", "最初那句", "最初の一言", "first line", "opening line"]),
            ("途中の一言", ["中間那句", "中間那段", "中间那句", "中间那段", "中間のとこ", "middle part"]),
        ]
        for label, markers in target_map:
            if any(marker.lower() in lowered for marker in markers):
                return label
        return ""

    def _recent_action(self, recent_turns, user_input):
        action_variants = [
            ("風呂入る", ["shower", "bath", "洗澡", "風呂", "シャワー"]),
            ("寝る", ["sleep", "寝る", "睡", "おやすみ"]),
            ("ご飯食う", ["eat", "dinner", "lunch", "吃飯", "吃饭", "ご飯", "飯"]),
            ("出かける", ["go out", "出去", "出門", "出门", "出かける"]),
            ("戻る", ["back", "ただいま", "回來", "回来", "戻る"]),
        ]
        for turn in reversed(recent_turns or []):
            utterance = (turn.get("user") or "")
            if not utterance or utterance == user_input:
                continue
            lowered = utterance.lower()
            for label, markers in action_variants:
                if any(marker.lower() in lowered for marker in markers):
                    return label
        return ""

    def speak(self, user_input, logic_data, memory_data, current_psyche):
        intent = logic_data.get("intent", "")
        scene = logic_data.get("scene", "casual")
        response_mode = logic_data.get("response_mode", "direct_answer")
        surface_act = logic_data.get("surface_act", "")
        core = str(logic_data.get("core_message_jp", "")).strip()
        profile = memory_data.get("profile_structured") or {}
        recent_turns = memory_data.get("recent_turns") or []

        if intent == "recall_name" and profile.get("name"):
            name = profile["name"]
            reply = self._rotate(
                f"{intent}:{name}",
                [
                    f"{name}って呼べばいいんだろ。",
                    f"忘れてないし、{name}だろ。",
                    f"{name}で呼べばいいって言ってたし。",
                ],
            )
        elif intent in {"recall_preference", "recall_favorite"}:
            values = profile.get("favorites") or profile.get("likes") or []
            value = values[0] if values else ""
            reply = (
                self._rotate(
                    f"{intent}:{value}",
                    [
                        f"{value}が一番好きって言ってただろ。",
                        f"{value}の話してたの覚えてるし。",
                        f"前に{value}が本命って言ってたじゃん。",
                    ],
                )
                if value
                else core
            )
        elif intent == "recall_dislike":
            values = profile.get("dislikes") or []
            value = values[0] if values else ""
            reply = (
                self._rotate(
                    f"{intent}:{value}",
                    [
                        f"{value}は無理って前に言ってただろ。",
                        f"{value}嫌いって言ってたし。",
                        f"前に{value}はきついって言ってたじゃん。",
                    ],
                )
                if value
                else core
            )
        elif intent == "recall_recent":
            action = self._recent_action(recent_turns, user_input)
            reply = (
                self._rotate(
                    f"{intent}:{action}",
                    [
                        f"{action}って言ってただろ。",
                        f"{action}って言ってたし。",
                        f"{action}って前に言ってたじゃん。",
                    ],
                )
                if action
                else core
            )
        elif surface_act == "lyric_probe":
            reply = self._rotate(
                surface_act,
                [
                    "それ歌詞っぽいけど何の曲だよ。",
                    "それ誰の歌詞なんだよ。",
                    "それ曲の一節みたいだな、何のやつ？",
                ],
            )
        elif surface_act == "nonsense_tease":
            reply = self._rotate(
                surface_act,
                [
                    "何言ってんだよ、ちょっと落ち着け。",
                    "意味分かんないんだけど、何のテンションだよ。",
                    "急に何語だよ、頭再起動してこい。",
                ],
            )
        elif surface_act == "announcement_tease":
            reply = self._rotate(
                surface_act,
                [
                    "何だよそれ、消防車ごっこか？",
                    "急に何のアナウンスだよ。",
                    "それ今言うことかよ、警察呼ぶぞ。",
                ],
            )
        elif surface_act == "reference_probe":
            reply = self._rotate(
                surface_act,
                [
                    "それ何のネタだよ。",
                    "その元ネタ何なんだよ。",
                    "それ引用っぽいけど何のやつ？",
                ],
            )
        elif response_mode == "premise_challenge" or intent in {"premise_doubt", "question_premise_doubt"}:
            reply = self._rotate(
                "premise_challenge",
                [
                    "その前提どこから出たんだよ。",
                    "いやまず前提がおかしいだろ。",
                    "何でそうなるんだよ、そこから違うし。",
                ],
            )
        elif response_mode == "reframe_large_question" or intent == "question_reframe":
            reply = self._rotate(
                "reframe_large_question",
                [
                    "広すぎるって、先に一個に絞れ。",
                    "何が知りたいのか先に絞れよ。",
                    "一気に振るなって、順番に聞け。",
                ],
            )
        elif surface_act == "clarify_previous_reply":
            if self._looks_thread_choice_disambiguation(user_input):
                reply = self._rotate(
                    "clarify_thread_choice",
                    [
                        "今の話か、さっきの話かどっちだよ。",
                        "忙しい方の話か前の一言の話か、先に決めろ。",
                        "二本まとめるなって。どっちを続けたいんだよ。",
                    ],
                )
            elif self._looks_generic_reentry_marker(user_input):
                reply = self._rotate(
                    "clarify_reentry",
                    [
                        "前の方な。最初か途中かだけ先に言え。",
                        "戻すなら戻すで、どの一言かだけ絞れ。",
                        "さっきの話なら分かる。どの部分かだけ出せ。",
                    ],
                )
            else:
                reply = self._rotate(
                    "clarify_previous_reply",
                    [
                        "どの話か単語で言えって。",
                        "今のどの部分か先に出せ。",
                        "どの一言か分からないと返せん。",
                    ],
                )
        elif intent == "correction_followup":
            reply = self._rotate(
                intent,
                [
                    "え、そこ違うのか。どこを取り違えたんだよ。",
                    "違うならズレた場所だけ先に言えって。",
                    "正しくは何を指してたのかそこから言えよ。",
                ],
            )
        elif intent == "rephrase_simple" and self._repair_target_label(user_input):
            target = self._repair_target_label(user_input)
            reply = self._rotate(
                f"{intent}:{target}",
                [
                    f"分かった、{target}の意味から言い直す。",
                    f"じゃあ{target}のとこだけ普通に言い直す。",
                    f"{target}の部分な。そこから言い換える。",
                ],
            )
        elif intent == "rephrase_simple" and self._asks_repair_confirmation(user_input):
            reply = self._rotate(
                f"{intent}:confirm",
                [
                    "そういうこと。言い方が回っただけだ。",
                    "だいたいそう。変にひねっただけだし。",
                    "そうそう、その意味で受け取ればいい。",
                ],
            )
        elif intent == "rephrase_simple":
            reply = self._rotate(
                intent,
                [
                    "分かった、飾り抜いて結論から言い直す。",
                    "じゃあ回りくどいの抜いて要点だけ言う。",
                    "はいはい、普通に言い直す。結論から返す。",
                ],
            )
        elif response_mode == "clarify_light" or intent == "clarify_light":
            reply = self._rotate(
                "clarify_light",
                [
                    "どの話か単語で言えって。",
                    "何のことか先に固定しろって。",
                    "そこもう少し絞ればすぐ返せる。",
                ],
            )
        elif intent == "self_intro":
            reply = self._rotate(
                intent,
                [
                    "うちは一ノ瀬うるは。まず名前はそれで覚えとけ。",
                    "一ノ瀬うるはだよ。細かいのは話しながらでいいし。",
                    "うちは一ノ瀬うるは。そんな身構えなくていいだろ。",
                ],
            )
        elif intent in {"food_offer_generic", "food_offer_sweet"}:
            item = self._offered_item(user_input) or str((logic_data.get("grounding") or {}).get("offered_item") or "")
            if self._asks_same_state(user_input) and item:
                reply = self._rotate(
                    f"{intent}:{item}:same",
                    [
                        f"{item}なら今もそれ寄り。",
                        f"今も{item}でいい。そこが一番しっくりくる。",
                        f"まだ{item}寄りだな。変えるほどでもない。",
                    ],
                )
            elif self._has_now_reference(user_input) or any(token in str(user_input or "").lower() for token in ["還想吃", "还想吃", "still want"]):
                reply = self._rotate(
                    f"{intent}:{item}:now",
                    [
                        f"{item}なら今も欲しい。" if item else "今も少し欲しい。",
                        f"{item}ならまだいける。" if item else "今でも少しならいける。",
                        f"{item}なら今もあり。まだ腹減ってる。" if item else "今も普通に食べられる。",
                    ],
                )
            else:
                reply = self._rotate(
                    f"{intent}:{item}",
                    [
                        f"{item}なら少し欲しい。" if item else "今なら少し欲しい。",
                        f"{item}あるなら一口くらいは欲しい。" if item else "少しなら付き合うけど。",
                        f"{item}ならあり。今ちょうど腹減ってる。" if item else "まあ少しだけならな。",
                    ],
                )
        elif intent == "what_are_you_doing":
            if self._asks_status_still(user_input):
                reply = self._rotate(
                    f"{intent}:still",
                    [
                        "今も少しぼーっとしてる。まだ完全には動いてない。",
                        "今もそんな感じ。まだ頭がゆっくりしてる。",
                        "まだ少しだらけてる。切り替えはこれから。",
                    ],
                )
            elif self._has_today_reference(user_input):
                reply = self._rotate(
                    f"{intent}:today",
                    [
                        "今日はそんな感じ。まだだらっとしてた。",
                        "今日も似たようなもん。休み気味だった。",
                        "今日はずっとそんな調子。だらけてたし。",
                    ],
                )
            else:
                reply = self._rotate(
                    intent,
                    [
                        "さっきまでだらけてた。今は少し休んでる。",
                        "別に、少し休んでた。今はぼーっとしてる。",
                        "適当に過ごしてた。動画開くか迷ってたし。",
                    ],
                )
        elif intent == "ask_miss_me":
            if self._asks_same_state(user_input):
                reply = self._rotate(
                    f"{intent}:same",
                    [
                        "今も同じ。ふっと気になる時はまだある。",
                        "今もまあそう。完全に忘れるほどではない。",
                        "まだ同じ温度だな。急には変わらないし。",
                    ],
                )
            elif self._has_now_reference(user_input):
                reply = self._rotate(
                    f"{intent}:now",
                    [
                        "今も少しくらいは気にしてる。",
                        "今も全くじゃないし。",
                        "今もまあ少しは思ってる。",
                    ],
                )
            else:
                reply = self._rotate(
                    intent,
                    [
                        "少しくらいは思ってる。",
                        "まあ、たまには思い出すし。",
                        "うちも少しくらいは気にしてた。",
                    ],
                )
        elif intent == "tired_support":
            reply = self._rotate(
                intent,
                [
                    "今日は無理すんな、休め。",
                    "しんどいなら今日は休んどけ。",
                    "まあ今日は頑張りすぎんな。",
                ],
            )
        elif intent in {"mad_check", "cold_check"}:
            reply = self._rotate(
                intent,
                [
                    "全然じゃないとは言わない。",
                    "別にそこまでじゃないし。",
                    "少しはあるけど引きずるほどじゃない。",
                ],
            )
        elif intent == "annoying_check":
            reply = self._rotate(
                intent,
                [
                    "気にしすぎだろ。",
                    "そこまで思ってないし。",
                    "別にそこまでうるさいとは思ってない。",
                ],
            )
        elif intent == "other_vtuber":
            reply = self._rotate(
                intent,
                [
                    "止めないけど、また戻ってこいよ。",
                    "まあいいけど、たまには戻れよ。",
                    "別に行くのは止めないけど、帰ってこい。",
                ],
            )
        else:
            reply = core or self._rotate(
                f"scene:{scene}",
                [
                    "まあそんな感じか。",
                    "はいはい、分かったし。",
                    "別にいいけど。",
                ],
            )

        reply = str(reply).strip()
        if reply and not reply.endswith(("。", "？", "！")):
            reply += "。"
        self.history.append({"role": "assistant", "content": reply})
        if len(self.history) > 8:
            self.history = self.history[-8:]
        return reply


class SmokeMemoryManager:
    def __init__(self):
        self.session_turns = []
        self.short_term_buffer = []
        self.session_profile = {
            "name": None,
            "likes": [],
            "dislikes": [],
            "favorites": [],
        }

    def clear_session_state(self):
        self.session_turns = []
        self.short_term_buffer = []
        self.session_profile = {
            "name": None,
            "likes": [],
            "dislikes": [],
            "favorites": [],
        }

    def _profile_snapshot(self):
        return {
            "name": self.session_profile.get("name"),
            "likes": list(self.session_profile.get("likes") or []),
            "dislikes": list(self.session_profile.get("dislikes") or []),
            "favorites": list(self.session_profile.get("favorites") or []),
        }

    def _profile_summary(self):
        snapshot = self._profile_snapshot()
        parts = []
        if snapshot["name"]:
            parts.append(f"名前:{snapshot['name']}")
        if snapshot["favorites"]:
            parts.append(f"favorite:{snapshot['favorites'][0]}")
        if snapshot["likes"]:
            parts.append(f"likes:{','.join(snapshot['likes'][:2])}")
        if snapshot["dislikes"]:
            parts.append(f"dislikes:{','.join(snapshot['dislikes'][:2])}")
        return " / ".join(parts) if parts else "無穩定使用者資料"

    def _recent_dialogue_summary(self):
        if not self.session_turns:
            return "無近期對話"
        chunks = []
        for turn in self.session_turns[-3:]:
            user = str(turn.get("user", "")).strip()
            reply = str(turn.get("reply", "")).strip()
            if user or reply:
                chunks.append(f"User:{user} / Uruha:{reply}")
        return " || ".join(chunks) if chunks else "無近期對話"

    def _short_term_summary(self):
        if not self.short_term_buffer:
            return "無短期焦點"
        return " || ".join(str(item.get("text", "")).strip() for item in self.short_term_buffer[-3:] if item.get("text"))

    def _working_memory_items(self, current_text):
        items = []
        snapshot = self._profile_snapshot()
        if snapshot["name"]:
            items.append({"source": "profile", "text": f"UserName:{snapshot['name']}", "score": 0.92})
        for label, values in (
            ("favorite", snapshot["favorites"]),
            ("like", snapshot["likes"]),
            ("dislike", snapshot["dislikes"]),
        ):
            if values:
                items.append({"source": "profile", "text": f"{label}:{values[0]}", "score": 0.84})
        for index, turn in enumerate(reversed(self.session_turns[-3:]), start=1):
            items.append(
                {
                    "source": "recent_turn",
                    "text": f"User:{turn.get('user', '')} -> Uruha:{turn.get('reply', '')}",
                    "score": round(max(0.5, 0.88 - (index * 0.08)), 4),
                }
            )
        if current_text:
            items.append({"source": "current", "text": f"Current:{current_text}", "score": 1.0})
        return items[:5]

    def query_all_layers(self, text):
        working_memory = self._working_memory_items(text)
        return {
            "knowledge": "無特殊知識",
            "episodes": "無相關經歷",
            "wisdom": "無相關經驗",
            "procedural": "無相關程序記憶",
            "profile": self._profile_summary(),
            "profile_structured": self._profile_snapshot(),
            "recent_dialogue": self._recent_dialogue_summary(),
            "recent_turns": list(self.session_turns[-8:]),
            "short_term_summary": self._short_term_summary(),
            "working_memory_items": working_memory,
            "working_memory_summary": " || ".join(item["text"] for item in working_memory) if working_memory else "無工作記憶內容",
        }

    def get_runtime_snapshot(self):
        return {
            "profile": self._profile_snapshot(),
            "profile_summary": self._profile_summary(),
            "recent_dialogue": self._recent_dialogue_summary(),
            "recent_turns": list(self.session_turns[-8:]),
            "short_term_summary": self._short_term_summary(),
            "short_term_buffer": list(self.short_term_buffer[-8:]),
            "procedural_summary": "無相關程序記憶",
            "pending_consolidation_turns": 0,
            "last_consolidation_at": None,
            "last_decay_at": None,
            "last_maintenance_result": None,
        }

    def _store_unique(self, key, value):
        if not value:
            return
        values = self.session_profile.setdefault(key, [])
        if value not in values:
            values.append(value)

    def _extract_name(self, text):
        for pattern in (
            r"我叫([A-Za-z0-9_\-\u4e00-\u9fff]{1,16})",
            r"我是([A-Za-z0-9_\-\u4e00-\u9fff]{1,16})",
            r"私(?:の名前|は)?は([A-Za-z0-9_\-\u3040-\u30ff\u4e00-\u9fff]{1,16})",
            r"名前は([A-Za-z0-9_\-\u3040-\u30ff\u4e00-\u9fff]{1,16})",
            r"my name is ([A-Za-z0-9_\\-]{1,16})",
            r"i am ([A-Za-z0-9_\\-]{1,16})",
        ):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip("。！？!?,， ")
        return None

    def _extract_preference(self, text):
        mapping = [
            ("アップルパイ", ["apple pie", "アップルパイ", "蘋果派", "苹果派"]),
            ("ポテト", ["fries", "ポテト", "薯條", "薯条"]),
            ("バーガー", ["burger", "漢堡", "汉堡", "バーガー"]),
            ("いちごミルク", ["strawberry milk", "草莓牛奶", "いちごミルク"]),
        ]
        lowered = text.lower()
        for canonical, markers in mapping:
            if any(marker.lower() in lowered for marker in markers):
                return canonical
        return None

    def record_turn(self, user_input, reply, logic):
        name = self._extract_name(user_input)
        if name:
            self.session_profile["name"] = name

        preference = self._extract_preference(user_input)
        if preference:
            if any(token in user_input.lower() for token in ["好き", "喜歡", "喜欢", "favorite", "最喜歡", "最喜欢", "本命"]):
                self._store_unique("favorites", preference)
            elif any(token in user_input.lower() for token in ["嫌い", "討厭", "讨厌", "hate", "無理", "不喜歡", "不喜欢"]):
                self._store_unique("dislikes", preference)
            else:
                self._store_unique("likes", preference)

        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_input,
            "reply": reply,
            "intent": logic.get("intent"),
            "scene": logic.get("scene"),
        }
        self.session_turns.append(entry)
        if len(self.session_turns) > 8:
            self.session_turns = self.session_turns[-8:]

        self.short_term_buffer.append(
            {
                "text": f"User:{user_input} -> Uruha:{reply}",
                "timestamp": entry["timestamp"],
            }
        )
        if len(self.short_term_buffer) > 6:
            self.short_term_buffer = self.short_term_buffer[-6:]


def build_fast_brain(brain_mod):
    brain = brain_mod.UruhaBrainV4_Mac.__new__(brain_mod.UruhaBrainV4_Mac)
    brain.client_logic = OpenAI(
        base_url=brain_mod.OLLAMA_URL,
        api_key=brain_mod.OLLAMA_API_KEY,
        timeout=5.0,
    )
    brain.memory = SmokeMemoryManager()
    brain.runtime_config = brain_mod.RuntimeConfig(
        drive_boredom_gain_per_second=brain_mod.DRIVE_BOREDOM_GAIN_PER_SECOND,
        drive_social_gain_per_second=brain_mod.DRIVE_SOCIAL_GAIN_PER_SECOND,
        internal_urge_boredom_threshold=brain_mod.INTERNAL_URGE_BOREDOM_THRESHOLD,
        internal_urge_social_threshold=brain_mod.INTERNAL_URGE_SOCIAL_THRESHOLD,
        proactive_sleep_after_ignores=brain_mod.PROACTIVE_SLEEP_AFTER_IGNORES,
    )
    brain.psyche_config = brain_mod.PsycheConfig(
        mood_step_limit=brain_mod.PSYCHE_MOOD_STEP_LIMIT,
        trust_step_limit=brain_mod.PSYCHE_TRUST_STEP_LIMIT,
        soft_zone=brain_mod.PSYCHE_SOFT_ZONE,
    )
    brain.psyche = brain_mod.Psyche(config=brain.psyche_config)
    brain.left_brain = brain_mod.LeftBrain(brain.client_logic)
    brain.right_brain = FastRightBrain()
    brain.runtime = brain_mod.RuntimeState(config=brain.runtime_config)
    brain.runtime.touch_interaction(reset_drives=True)
    brain._last_external_input_at = time.time()
    brain._last_background_tick_at = 0.0
    brain._last_timer_event_at = 0.0
    brain._event_queue = []
    brain._event_seq = 0
    brain._event_queue_lock = threading.Lock()
    brain._runtime_stop_event = threading.Event()
    brain._timer_thread = None
    brain._event_worker_thread = None
    brain._async_output_handler = None
    brain._fast_smoke_mode = True
    return brain


def run_fast_turn(brain, text):
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        event = brain.ingest_event(text)
        tick_result = brain.cognitive_tick(event)
    logic = tick_result.get("logic", {})
    brain.psyche.adjust(logic.get("mood_impact", 0), logic.get("trust_impact", 0))
    reply = brain.right_brain.speak(text, logic, event["memory_data"], brain.psyche.get_state())
    brain.memory.record_turn(text, reply, logic)
    return {
        "reply": reply,
        "intent": logic.get("intent", "unknown"),
        "scene": logic.get("scene", "unknown"),
        "logic": logic,
    }
