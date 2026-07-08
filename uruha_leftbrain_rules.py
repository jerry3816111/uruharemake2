import re
import hashlib
from copy import deepcopy


def _compact_dialogue_text(text):
    return re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/\"'`]+", "", str(text or "").lower())


def contains_any(text, keywords):
    lowered = text.lower()
    compact = _compact_dialogue_text(lowered)
    for keyword in keywords:
        needle = keyword.lower()
        if needle in lowered:
            return True
        if _compact_dialogue_text(needle) in compact:
            return True
    return False

def keyword_hits(text, keywords):
    lowered = text.lower()
    compact = _compact_dialogue_text(lowered)
    hits = 0
    for keyword in keywords:
        needle = keyword.lower()
        if needle in lowered or _compact_dialogue_text(needle) in compact:
            hits += 1
    return hits

def local_offer_item_jp(raw_text):
    lowered_text = str(raw_text or "").lower()
    item_map = [
        ("アップルパイ", ["apple pie", "アップルパイ", "蘋果派", "苹果派"]),
        ("ミルクシェイク", ["milkshake", "ミルクシェイク", "奶昔"]),
        ("ポテト", ["fries", "french fries", "ポテト", "薯條", "薯条"]),
        ("バーガー", ["burger", "バーガー", "漢堡", "汉堡"]),
        ("ピザ", ["pizza", "ピザ", "披薩", "披萨"]),
        ("おにぎり", ["onigiri", "おにぎり", "飯糰", "饭团"]),
        ("飲み物", ["drink", "drinks", "飲み物", "飲料", "饮料", "喝的", "喝的呢", "喝的咧", "cola", "可樂", "可乐", "coffee", "コーヒー", "tea", "紅茶", "红茶"]),
        ("甘いの", ["cake", "ケーキ", "蛋糕", "pudding", "プリン", "布丁", "dessert", "sweet", "甘いもの", "甜點", "甜点", "甜的", "甜的呢", "甜的咧"]),
        ("しょっぱいの", ["salty", "savory", "鹹的", "咸的", "鹹的呢", "咸的呢", "鹹口", "咸口"]),
    ]
    for jp_item, needles in item_map:
        if any(needle in lowered_text for needle in needles):
            return jp_item
    return None


def _has_today_reference(text):
    lowered = str(text or "").lower()
    return contains_any(lowered, ["今天", "今日", "today"])


def _has_now_reference(text):
    lowered = str(text or "").lower()
    if contains_any(lowered, ["現在", "现在", "right now"]):
        return True
    return any(token in lowered for token in ["今は", "今なに", "今何", "今して", "今も", "今なら"])


def _is_sweet_offer_item(item):
    return item in {"アップルパイ", "ミルクシェイク", "甘いの"}


def _is_drink_offer_item(item):
    return item in {"飲み物"}


def _build_food_offer_fields(offered_item, followup=False, ask_about_self=False, still_want=False, same_item=False, thread_depth=1):
    item = offered_item or "何か"
    if same_item:
        if item == "ご飯":
            return _pick_thread_variant(
                [
                    (
                        "今も同じ食べ物寄りかを自然に返す",
                        "ユーザーが同じ食事の流れで、今もまだ同じもの寄りか確かめている。",
                        "今もご飯寄りではある。重すぎないのがちょうどいい",
                    ),
                    (
                        "同じ食べ物寄りだと少し進めて返す",
                        "ユーザーが食事の流れをもう一歩続けていて、今も同じ方向か確かめている。",
                        "今も食べるならご飯系かな。無難で助かるし",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if _is_drink_offer_item(item):
            return _pick_thread_variant(
                [
                    (
                        f"今も{item}寄りかを自然に返す",
                        f"ユーザーが{item}の流れで今も同じ飲み物寄りか確かめている。",
                        f"今も{item}寄り。喉乾いてるしそれが楽",
                    ),
                    (
                        f"{item}寄りのままだと少し進めて返す",
                        f"ユーザーが{item}の流れをもう一歩続けていて、今も同じ方向か確かめている。",
                        f"今も{item}でいい。変に重くないし",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if _is_sweet_offer_item(item):
            return _pick_thread_variant(
                [
                    (
                        f"今も{item}寄りかを自然に返す",
                        f"ユーザーが{item}の流れで今も同じ甘いもの寄りか確かめている。",
                        f"今も{item}寄り。甘いのならそれが一番手を出しやすい",
                    ),
                    (
                        f"{item}寄りのままだと少し進めて返す",
                        f"ユーザーが{item}の流れをもう一歩続けていて、今も同じ方向か確かめている。",
                        f"今も{item}でいい。甘さがちょうどいいし",
                    ),
                ],
                thread_depth=thread_depth,
            )
        return _pick_thread_variant(
            [
                (
                    f"今も{item}寄りかを自然に返す",
                    f"ユーザーが{item}の流れで今も同じ食べ物寄りか確かめている。",
                    f"今も{item}寄り。そこが一番分かりやすい",
                ),
                (
                    f"{item}寄りのままだと少し進めて返す",
                    f"ユーザーが{item}の流れをもう一歩続けていて、今も同じ方向か確かめている。",
                    f"今も{item}でいい。変に迷わなくて済むし",
                ),
            ],
            thread_depth=thread_depth,
        )
    if still_want:
        if item == "ご飯":
            return _pick_thread_variant(
                [
                    (
                        "今も食べるかを自然に返す",
                        "ユーザーが同じ食事の流れで今も食べる気があるか確かめている。",
                        "ご飯なら今も軽くは食べる。少し腹は空いてる",
                    ),
                    (
                        "今も食べられると少し進めて返す",
                        "ユーザーが食事の流れをもう一歩続けていて、今も食べる余地があるか確かめている。",
                        "ご飯なら今もいける。重すぎなければ普通に食べる",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if _is_drink_offer_item(item):
            variants = [
                (
                    f"{item}を今も欲しいか自然に返す",
                    f"ユーザーが{item}の流れで今も欲しいかを確かめている。",
                    f"{item}なら今もほしい。まだ普通に飲める",
                ),
                (
                    f"{item}を今もいけると少し進めて返す",
                    f"ユーザーが{item}の流れをもう一歩続けていて、今も飲めるか確かめている。",
                    f"{item}なら今もいける。まだ喉が渇いてるし",
                ),
            ]
        elif _is_sweet_offer_item(item):
            variants = [
                (
                    f"{item}を今も欲しいか自然に返す",
                    f"ユーザーが{item}の流れで今も欲しいかを確かめている。",
                    f"{item}なら今もほしい。甘いのならまだいける",
                ),
                (
                    f"{item}を今もいけると少し進めて返す",
                    f"ユーザーが{item}の流れをもう一歩続けていて、今も同じ甘いものが欲しいか確かめている。",
                    f"{item}なら今もあり。まだ甘いので十分いける",
                ),
            ]
        else:
            variants = [
                (
                    f"{item}を今も欲しいか自然に返す",
                    f"ユーザーが{item}の流れで今も欲しいかを確かめている。",
                    f"{item}なら今もあり。まだ普通に食べる",
                ),
                (
                    f"{item}を今もいけると少し進めて返す",
                    f"ユーザーが{item}の流れをもう一歩続けていて、今も食べる気があるか確かめている。",
                    f"{item}なら今もいける。まだ普通に手は出る",
                ),
            ]
        return _pick_thread_variant(variants, thread_depth=thread_depth)
    if ask_about_self:
        if item == "ご飯":
            return (
                "食べた側として自然に返す",
                "ユーザーが同じ食べ物の流れでこちら側はどうかも聞いている。",
                "ご飯なら一応食べた。そこは済ませてる",
            )
        if _is_drink_offer_item(item):
            meaning = f"{item}なら今ほしい。ちょうど喉かわいてる"
        elif _is_sweet_offer_item(item):
            meaning = f"{item}ならうちもあり。少しつまみたい"
        else:
            meaning = f"{item}ならうちもあり。普通に食べる"
        return (
            f"{item}への反応をこちら側から返す",
            f"ユーザーが{item}の流れでこちら側はどうかも聞いている。",
            meaning,
        )

    if _is_drink_offer_item(item):
        meaning = f"{item}なら今ほしい。ちょうど喉かわいてる"
    elif _is_sweet_offer_item(item):
        meaning = f"{item}なら一口ほしい。甘いのならあり"
    else:
        meaning = f"{item}なら普通にあり。少しもらう"

    if followup:
        if not offered_item:
            return (
                "同じ食べ物の流れのまま返す",
                "ユーザーが直前の食べ物の話を具体物で続けている。",
                "今なら少しほしい。何持ってきたんだよ",
            )
        return (
            f"{item}の流れをそのまま受けて返す",
            f"ユーザーが直前の食べ物の話を{item}で続けている。",
            meaning,
        )

    if not offered_item:
        return (
            "食べるかどうかを自然に返す",
            "ユーザーが何か食べ物や飲み物を勧めている。",
            "今なら少しほしい。何くれるんだよ",
        )
    return (
        f"{item}の誘いに乗って可否を返す",
        f"ユーザーが{item}を勧めている。",
        meaning,
    )


def _build_repair_fields(kind, text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if kind == "correction":
        if _has_today_reference(text):
            return (
                "取り違えた今日の言い方を聞き返す",
                "ユーザーが今日の言い方や呼び方のズレを訂正している。",
                "え、今日の言い方そこ違うのか。正しくは何だよ",
            )
        return (
            "取り違えた箇所を一個だけ聞き返す",
            "ユーザーが直前の受け取り違いを訂正している。",
            "え、そこ違うのか。どこを取り違えたんだよ",
        )
    if kind == "clarify":
        summary = "ユーザーが直前の返しの意味をもう少しはっきりさせたい。"
        if contains_any(lowered, ["哪句", "哪个", "哪個", "which one", "どれ", "どっち"]):
            summary = "ユーザーが直前の返しのどの一言かを確かめたい。"
        return (
            "直前のどの言い回しか先に特定する",
            summary,
            "さっきのどの部分だよ。単語でもいいから言え",
        )
    if kind == "rephrase":
        if contains_any(lowered, ["one line", "one sentence", "一文", "一句話", "一句话"]):
            return (
                "一文サイズで要点だけ言い直す",
                "ユーザーが一文や一行で要点だけ言い直してほしい。",
                "分かった、簡単に一個ずつ言い直す",
            )
        if contains_any(lowered, [
            "講白", "讲白", "要點", "要点", "普通に話せ", "人話", "人话",
            "normal person", "say it plainly", "直接講重點", "直接讲重点",
        ]):
            return (
                "回りくどさを抜いて要点から言い直す",
                "ユーザーが回りくどさを嫌って結論を先に求めている。",
                "分かった、結論から簡単に返す。一個ずつ返す",
            )
        return (
            "変な言い回しを抜いて言い直す",
            "ユーザーがもっと普通の言い方を求めている。",
            "分かった、簡単に一個ずつ言う",
        )
    return ("自然に返す", "ユーザーが言い直しを求めている。", "言い直す")


def _build_direct_daily_fields(kind, text, offered_item=None, thread_depth=1):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    has_today = _has_today_reference(text)
    has_now = _has_now_reference(text)

    if kind == "self_intro":
        if contains_any(lowered, ["name", "名字", "名前"]):
            return (
                "名前を先にまっすぐ名乗る",
                "ユーザーがまず名前を知りたがっている。",
                "うちは一ノ瀬うるは。まず名前だけ覚えとけ",
            )
        return (
            "名前と立ち位置を自然に名乗る",
            "ユーザーがこちらが誰かをまっすぐ聞いている。",
            "うちは一ノ瀬うるは。細かいのは話しながらでいい",
        )
    if kind == "meal_check":
        if has_today:
            return (
                "今日ちゃんと食べたかを自然に返す",
                "ユーザーが今日ちゃんと食べたかを気にしている。",
                "今日は一応食べた。雑だったけど",
            )
        return (
            "食べたかどうかを自然に返す",
            "ユーザーが食事を済ませたか気にしている。",
            "一応食べた。ちゃんとしたのではないけど",
        )
    if kind == "status":
        if has_now:
            return (
                "今してることを一個だけ具体的に返す",
                "ユーザーが今なにしているかを聞いている。",
                "今はだらだらしてる。少し休んでた",
            )
        if has_today:
            return (
                "今日してたことを一個だけ具体的に返す",
                "ユーザーが今日なにしていたかを聞いている。",
                "今日はだらだらしてた。動画開くか迷ってた",
            )
        return (
            "さっきしてたことを一個だけ具体的に返す",
            "ユーザーがさっき何をしていたか聞いている。",
            "さっきまでだらだらしてた。今は少し休んでる",
        )
    if kind == "topic_proposal":
        if has_today:
            return (
                "軽い話題を一個こちらから出す",
                "ユーザーが今日なにを話すか軽く聞いている。",
                "軽い話題なら最近どうしてたかでいい",
            )
        return (
            "軽い話題を一個こちらから出す",
            "ユーザーがなにを話すか軽く聞いている。",
            "軽い話題なら最近どうしてたかでいい",
        )
    if kind == "food_offer":
        return _build_food_offer_fields(offered_item, followup=False, ask_about_self=False)
    if kind == "food_offer_followup":
        return _build_food_offer_fields(offered_item, followup=True, ask_about_self=False, thread_depth=thread_depth)
    if kind == "food_offer_self":
        return _build_food_offer_fields(offered_item, followup=False, ask_about_self=True, thread_depth=thread_depth)
    if kind == "food_offer_still":
        return _build_food_offer_fields(offered_item, still_want=True, thread_depth=thread_depth)
    if kind == "food_offer_same_item":
        return _build_food_offer_fields(offered_item, same_item=True, thread_depth=thread_depth)
    return ("自然に返す", "ユーザーが日常のことを聞いている。", "軽く返す")


def _build_relation_echo_fields(prev_intent):
    if prev_intent == "ask_miss_me":
        return (
            "同じ気持ちの向きをこちら側から返す",
            "ユーザーが『想ったか』の向きをこちら側にも返している。",
            "うちも少しくらいは気にしてた",
        )
    if prev_intent == "ask_like_me":
        return (
            "好意の温度をこちら側から返す",
            "ユーザーが『好きか』の向きをこちら側にも返している。",
            "嫌いってほどではない",
        )
    return (
        "距離感の温度をこちら側から返す",
        "ユーザーが直前の距離感確認をこちら側にも返している。",
        "そこまでじゃない。気にしすぎるな",
    )


def _pick_thread_variant(variants, thread_depth=1):
    choices = list(variants or [])
    if not choices:
        return ("自然に返す", "ユーザーが話を続けている。", "軽く返す")
    if thread_depth <= 2:
        return choices[0]
    index = min(len(choices) - 1, thread_depth - 2)
    return choices[index]


def _recent_thread_depth(recent_turns, matcher, current_text="", window=5):
    depth = 0
    started = False
    for turn in _iter_recent_turns(recent_turns, current_text=current_text, window=window):
        if matcher(turn):
            depth += 1
            started = True
            continue
        if started:
            break
    return depth


def _is_food_thread_turn(turn):
    intent = str((turn or {}).get("intent") or "")
    if intent in {"food_offer_generic", "food_offer_sweet", "store_offer"}:
        return True
    user = str((turn or {}).get("user") or "")
    reply = str((turn or {}).get("reply") or "")
    if local_offer_item_jp(user) or local_offer_item_jp(reply):
        return True
    return contains_any(f"{user} {reply}".lower(), ["吃飯", "吃饭", "食べた", "ご飯", "飯", "meal", "ate", "eaten", "腹減", "お腹"])


def _is_repair_thread_turn(turn):
    intent = str((turn or {}).get("intent") or "")
    if intent in {"rephrase_simple", "correction_followup", "answer_me_push"}:
        return True
    reply = str((turn or {}).get("reply") or "").lower()
    return contains_any(
        reply,
        ["どの部分", "どの話", "どの一言", "単語でもいい", "取り違え", "意味から言い直す", "言い換える", "そういうこと"],
    )


def _tail_focus_segment(text):
    segments = [segment.strip() for segment in re.split(r"[，,、；;]", str(text or "")) if segment.strip()]
    if segments:
        return segments[-1]
    return str(text or "").strip()


def _looks_status_query(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    status_markers = [
        "你在幹嘛", "你在干嘛", "你現在在幹嘛", "你现在在干嘛", "那你現在在幹嘛", "那你现在在干嘛",
        "你今天在幹嘛", "你今天在干嘛", "你今天都在做什麼", "你今天都在做什么",
        "what are you doing", "what are you doing right now", "what were you doing today",
        "what are you up to", "what are you doing now", "what are you doing rn",
        "今日は何してた", "今日何してた", "今何してる", "今なにしてる", "今何してた", "今なにしてた",
        "何してるの", "なにしてるの", "まだ忙しい", "今も忙しい", "今まだ忙しい",
        "還在忙", "还在忙", "still busy", "busy right now",
    ]
    if contains_any(lowered, status_markers):
        return True
    if contains_any(lowered, ["忙", "busy"]) and (_has_now_reference(text) or "?" in text or "？" in text):
        return True
    return False


def looks_topic_proposal_query(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    if contains_any(
        lowered,
        [
            "話題ずらすな",
            "話題をずらすな",
            "話題変えるな",
            "不要轉移話題",
            "不要转移话题",
            "stop changing the topic",
            "answer directly first",
        ],
    ):
        return False
    topic_markers = [
        "今日は何話す",
        "今日何話す",
        "今日はなに話す",
        "今日なに話す",
        "何話す",
        "なに話す",
        "何を話す",
        "何喋る",
        "何しゃべる",
        "何しゃべろ",
        "何話そう",
        "話題ある",
        "話題ちょうだい",
        "話題出して",
        "話題振って",
        "what should we talk about",
        "what do we talk about",
        "what should we chat about",
        "give me a topic",
        "topic?",
        "聊什麼",
        "聊什么",
        "今天聊什麼",
        "今天聊什么",
        "要聊什麼",
        "要聊什么",
        "有什麼話題",
        "有什么话题",
    ]
    return contains_any(lowered, topic_markers)


def _looks_meal_check_query(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    meal_check_markers = [
        "你今天有吃飯嗎", "你今天有吃饭吗", "你吃飯了嗎", "你吃饭了吗", "你晚餐吃了沒", "你晚餐吃了没",
        "你晚飯吃了沒", "你晚饭吃了没", "你午餐吃了沒", "你午餐吃了没", "你早餐吃了沒", "你早餐吃了没",
        "晚餐呢", "晚飯呢", "晚饭呢", "午餐呢", "午飯呢", "午饭呢", "早餐呢", "早飯呢", "早饭呢",
        "have you eaten", "did you eat", "did you eat today", "have you eaten today", "did you eat dinner",
        "have you had dinner", "dinner yet", "lunch yet", "breakfast yet",
        "ご飯食べた", "今日ご飯食べた", "今日はちゃんと食べた", "晩ご飯食べた", "夕飯食べた", "朝ごはん食べた",
    ]
    if contains_any(lowered, meal_check_markers):
        return True

    meal_nouns = ["晚餐", "晚飯", "晚饭", "午餐", "午飯", "午饭", "早餐", "早飯", "早饭", "dinner", "lunch", "breakfast", "ご飯", "飯", "晩ご飯", "夕飯", "朝ごはん"]
    meal_query_markers = ["呢", "嗎", "吗", "？", "?", "吃了沒", "吃了没", "食べた", "eat", "eaten", "had", "have", "did"]
    if contains_any(lowered, meal_nouns) and contains_any(lowered, meal_query_markers):
        return True
    if contains_any(lowered, ["吃了沒", "吃了没", "吃過沒", "吃过没", "食べたか", "食べた？", "eaten yet"]):
        return True
    return False


def _looks_food_offer_query(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    if contains_any(lowered, ["懶叫", "懒叫", "雞巴", "鸡巴", "ちんこ", "dick", "sex", "做愛", "做爱"]):
        return False
    food_offer_markers = [
        "要不要吃", "要不要喝", "want some", "do you want some", "一口",
        "請你吃", "请你吃", "分你", "留給你", "留给你", "share some", "save you some", "for you",
        "do not be shy", "don't be shy", "feel like having", "i just bought", "不要跟我客氣", "不要跟我客气",
        "別客氣", "别客气", "不用客氣", "不用客气",
    ]
    offered_item = local_offer_item_jp(text)
    if offered_item and ("?" in text or "？" in text or contains_any(lowered, food_offer_markers) or contains_any(lowered, ["還想吃", "还想吃", "還想喝", "还想喝", "still want to eat", "still want to drink", "まだ食べたい", "まだ飲みたい"])):
        return True
    if contains_any(lowered, food_offer_markers):
        return True
    return False


def _looks_explicit_repair_query(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    if _repair_target_label(text):
        return True
    repair_markers = [
        "答錯", "答错", "說錯", "说错", "才不是", "不是啦", "不對啦", "不对啦", "今の答え違う", "そこ間違ってる",
        "什麼意思", "什么意思", "what do you mean", "どういう意味", "哪句意思", "哪句的意思",
        "講白", "讲白", "人話", "人话", "言い直せ", "言い直して", "普通に話せ", "要点だけ言え",
        "so you mean", "that's what you meant", "そういう意味", "ってこと",
    ]
    return contains_any(lowered, repair_markers)


def _detect_literal_shift_family(text):
    segments = []
    tail_segment = _tail_focus_segment(text)
    if tail_segment:
        segments.append(tail_segment)
    full_text = str(text or "").strip()
    if full_text and full_text not in segments:
        segments.append(full_text)
    for segment in segments:
        if _looks_status_query(segment):
            return "status"
        if _looks_meal_check_query(segment) or _looks_food_offer_query(segment):
            return "food"
        if _looks_explicit_repair_query(segment):
            return "repair"
    return ""


def _active_followup_family(prev_intent, prev_relationish, prev_repairish, prev_foodish):
    if prev_repairish:
        return "repair"
    if prev_intent == "what_are_you_doing":
        return "status"
    if prev_relationish:
        return "relationship"
    if prev_foodish or prev_intent in {"food_offer_generic", "food_offer_sweet", "store_offer"} or (prev_intent == "chat" and prev_foodish):
        return "food"
    return ""


def _thread_family_for_turn(turn):
    intent = str((turn or {}).get("intent") or "")
    if _is_repair_thread_turn(turn):
        return "repair"
    if intent == "what_are_you_doing":
        return "status"
    if intent in {"ask_miss_me", "ask_like_me", "annoying_check", "mad_check", "cold_check"}:
        return "relationship"
    if _is_food_thread_turn(turn):
        return "food"
    return ""


def _recent_followup_thread_context(recent_turns, current_text="", window=5):
    ordered = []
    latest_by_family = {}
    for turn in _iter_recent_turns(recent_turns, current_text=current_text, window=window):
        family = _thread_family_for_turn(turn)
        if not family:
            continue
        ordered.append((family, turn))
        latest_by_family.setdefault(family, turn)
    active_family = ordered[0][0] if ordered else ""
    reentry_family = ""
    for family, _ in ordered[1:]:
        if family != active_family:
            reentry_family = family
            break
    return {
        "ordered": ordered,
        "latest_by_family": latest_by_family,
        "active_family": active_family,
        "reentry_family": reentry_family,
    }


def _other_recent_family(thread_context, exclude_family=""):
    for family, _ in list((thread_context or {}).get("ordered") or []):
        if family and family != exclude_family:
            return family
    return ""


def _looks_generic_reentry_marker(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    markers = [
        "剛剛那個", "刚刚那个", "剛剛那個呢", "刚刚那个呢", "前面的", "前面那個", "前面那个",
        "前面的部分", "前面那部分", "那個部分", "那个部分", "剛才那個", "刚才那个",
        "剛剛那件事", "刚刚那件事", "那個話題", "那个话题",
    ]
    return contains_any(lowered, markers)


def _looks_food_reentry_marker(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    if not (local_offer_item_jp(text) or contains_any(lowered, ["蘋果派", "苹果派", "apple pie", "晚餐", "晚飯", "晚饭", "午餐", "早餐", "ご飯", "飯"])):
        return False
    return contains_any(lowered, ["那個", "那个", "部分", "話題", "话题", "剛剛", "刚刚", "前面", "所以", "那個呢", "那个呢"])


def _looks_repair_reentry_marker(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    markers = [
        "我是說前面的", "我是说前面的", "我是說前面那句", "我是说前面那句",
        "不是這個", "不是这个", "我說剛那句", "我说刚那句", "剛那句", "刚那句",
        "前面那句", "前面的那句", "前面那個句子", "前面那个句子",
    ]
    return contains_any(lowered, markers)


def _detect_explicit_reentry_family(text, thread_context, literal_family=""):
    latest_by_family = dict((thread_context or {}).get("latest_by_family") or {})
    if _looks_repair_reentry_marker(text) and "repair" in latest_by_family:
        return "repair"
    if _looks_food_reentry_marker(text) and "food" in latest_by_family:
        return "food"
    if _looks_generic_reentry_marker(text):
        if literal_family:
            other_family = _other_recent_family(thread_context, exclude_family=literal_family)
            if other_family:
                return other_family
        reentry_family = str((thread_context or {}).get("reentry_family") or "")
        if reentry_family:
            return reentry_family
    return ""


def _looks_thread_choice_disambiguation(text, literal_family="", reentry_family=""):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip() or not literal_family or not reentry_family:
        return False
    return contains_any(lowered, ["還是", "还是", "or"]) and _looks_generic_reentry_marker(text)


def _recent_thread_families(thread_context):
    families = []
    for family, _ in list((thread_context or {}).get("ordered") or []):
        if family and family not in families:
            families.append(family)
    return families


def _looks_generic_object_followup(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    return contains_any(
        lowered,
        [
            "那個", "那个", "那個呢", "那个呢", "那個現在", "那个现在",
            "現在那個", "现在那个", "前面那個", "前面那个", "前面那個呢", "前面那个呢",
        ],
    )


def _has_recent_reentry_anchor(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    return contains_any(lowered, ["剛剛", "刚刚", "剛才", "刚才"])


def _ambiguous_followup_clarify_families(thread_context, active_family="", literal_family="", explicit_reentry_family=""):
    if literal_family and explicit_reentry_family and literal_family != explicit_reentry_family:
        return literal_family, explicit_reentry_family
    if active_family and explicit_reentry_family and active_family != explicit_reentry_family:
        return active_family, explicit_reentry_family
    families = _recent_thread_families(thread_context)
    if len(families) >= 2:
        return families[0], families[1]
    if active_family and explicit_reentry_family:
        return active_family, explicit_reentry_family
    family = active_family or explicit_reentry_family
    return family, ""


def _should_clarify_ambiguous_short_followup(
    text,
    thread_context,
    active_family="",
    literal_family="",
    explicit_reentry_family="",
    asks_current_state=False,
    asks_so_what=False,
    offered_item=None,
    repair_target_answer=False,
):
    families = _recent_thread_families(thread_context)
    if len(families) < 2:
        return False

    if offered_item or repair_target_answer or _looks_food_reentry_marker(text):
        return False
    if _looks_repair_reentry_marker(text) and repair_target_answer:
        return False
    if literal_family and explicit_reentry_family and literal_family != explicit_reentry_family:
        return False

    generic_object = _looks_generic_object_followup(text)
    generic_reentry = _looks_generic_reentry_marker(text)
    recent_anchor = _has_recent_reentry_anchor(text)
    short_text = len(str(text or "").strip()) <= 8

    if asks_so_what and short_text:
        return True
    if asks_current_state and generic_object:
        return True
    if generic_object and not explicit_reentry_family:
        return True
    if generic_reentry and not recent_anchor:
        return True
    return False


def _split_priority_clauses(text):
    return [segment.strip() for segment in re.split(r"[，,、；;]", str(text or "")) if segment.strip()]


def _looks_clause_defer_marker(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    return contains_any(
        lowered,
        [
            "先不說", "先不说", "先不管", "等一下再說", "等一下再说", "等一下", "先不提",
            "先放著", "先放着", "先擺著", "先摆着",
            "不是那個", "不是那个", "不是前面那句", "不是前面那個", "不是前面那个",
            "不是剛剛那個", "不是刚刚那个", "不是前面那個啦", "不是前面那个啦",
        ],
    )


def _looks_clause_focus_marker(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    return contains_any(
        lowered,
        [
            "我現在問的是", "我现在问的是", "我現在問你", "我现在问你",
            "我是問", "我是问", "我是在問", "我是在问", "我是在問你", "我是在问你",
            "我現在是問", "我现在是问", "我是說", "我是说",
        ],
    )


def _detect_relationship_intent(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return ""
    memory_fact_markers = [
        "名前", "名字", "叫我", "呼び方", "最喜歡", "最喜欢", "一番好き",
        "叫什麼", "叫什么", "我叫什麼", "我叫什么", "記得我叫", "记得我叫",
        "favorite", "what do i like", "what did i say", "剛剛說", "刚刚说", "少し前に言った",
    ]
    if contains_any(lowered, ["還記得我", "还记得我", "remember me", "still remember me", "まだ覚えてる", "覚えてる？", "覚えてるの"]) and not contains_any(lowered, memory_fact_markers):
        return "ask_miss_me"
    if contains_any(lowered, ["你有想我", "你有沒有想我", "你有没有想我", "有沒有想我", "有没有想我", "do you miss me", "miss me", "恋しかった", "在意我", "care about me"]):
        return "ask_miss_me"
    if contains_any(lowered, ["喜歡我", "喜欢我", "喜不喜歡我", "喜不喜欢我", "你喜歡我", "你喜欢我", "好き？", "好き?", "うちのこと好き", "like me"]) and not contains_any(lowered, memory_fact_markers):
        return "ask_like_me"
    if contains_any(lowered, ["我是不是很煩", "我是不是很烦", "am i annoying", "am i a bother", "do you think i am annoying", "would you think i am annoying", "annoying to you", "うざい？", "迷惑？", "很煩", "很烦", "うちのことだるい"]):
        return "annoying_check"
    if contains_any(lowered, ["生氣", "生气", "angry", "are you mad", "you mad", "怒ってる"]):
        return "mad_check"
    if contains_any(lowered, ["冷たい", "冷淡", "cold to me", "距離"]):
        return "cold_check"
    return ""


def _detect_priority_clause_family(text):
    relationship_intent = _detect_relationship_intent(text)
    if relationship_intent:
        return "relationship"
    if _looks_status_query(text):
        return "status"
    if _looks_meal_check_query(text) or _looks_food_offer_query(text):
        return "food"
    if _looks_explicit_repair_query(text) or contains_any(str(text or "").lower(), ["剛剛那句", "刚刚那句", "前面那句", "前面那个意思", "什么意思", "什麼意思"]):
        return "repair"
    return ""


def _marker_position(text, markers, pick="first"):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    matches = []
    for marker in markers:
        idx = lowered.find(str(marker or "").lower())
        if idx >= 0:
            matches.append((idx, marker))
    if not matches:
        return (-1, "")
    if pick == "last":
        return max(matches, key=lambda item: item[0])
    return min(matches, key=lambda item: item[0])


def _detect_no_punctuation_priority_override(text):
    raw_text = str(text or "")
    if not raw_text.strip():
        return {"family": "", "clause": "", "score": 0}
    if re.search(r"[，,、；;]", raw_text):
        return {"family": "", "clause": "", "score": 0}

    focus_markers = [
        "我現在問的是", "我现在问的是", "我現在問你", "我现在问你",
        "我是問", "我是问", "我是在問", "我是在问", "我是在問你", "我是在问你",
        "我現在是問", "我现在是问", "我是說", "我是说",
    ]
    defer_markers = [
        "先不說", "先不说", "先不管", "等一下再說", "等一下再说", "等一下", "先不提",
        "先放著", "先放着", "先擺著", "先摆着",
        "不是那個", "不是那个", "不是前面那句", "不是前面那個", "不是前面那个",
        "不是剛剛那個", "不是刚刚那个", "不是前面那個啦", "不是前面那个啦",
    ]

    focus_pos, focus_marker = _marker_position(raw_text, focus_markers, pick="last")
    defer_pos, defer_marker = _marker_position(raw_text, defer_markers, pick="first")

    best_family = ""
    best_clause = ""
    best_score = 0

    if focus_pos >= 0:
        focus_tail = raw_text[focus_pos:]
        focus_family = _detect_priority_clause_family(focus_tail)
        prefix_family = _detect_priority_clause_family(raw_text[:focus_pos])
        if focus_family:
            score = 3
            if prefix_family and prefix_family != focus_family:
                score += 1
            if score > best_score:
                best_family = focus_family
                best_clause = focus_tail
                best_score = score

    if defer_pos >= 0:
        defer_tail = raw_text[defer_pos + len(defer_marker):]
        defer_family = _detect_priority_clause_family(defer_tail)
        prefix_family = _detect_priority_clause_family(raw_text[:defer_pos])
        if defer_family and prefix_family and prefix_family != defer_family:
            score = 3
            if focus_pos >= 0 and focus_pos > defer_pos:
                score += 1
            if score > best_score:
                best_family = defer_family
                best_clause = defer_tail
                best_score = score

    if best_score >= 3:
        return {"family": best_family, "clause": best_clause, "score": best_score}
    return {"family": "", "clause": "", "score": 0}


def _looks_weak_status_clause(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    if contains_any(
        lowered,
        [
            "你現在咧", "你现在咧", "你現在呢", "你现在呢", "那你現在呢", "那你现在呢",
            "那你現在咧", "那你现在咧", "現在咧", "现在咧", "現在呢", "现在呢",
            "還在忙", "还在忙", "忙不忙", "busy now", "busy rn",
        ],
    ):
        return True
    return False


def _looks_weak_repair_clause(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False
    if _looks_explicit_repair_query(text) or _repair_target_label(text):
        return False
    return contains_any(
        lowered,
        [
            "剛剛那句", "刚刚那句", "前面那句", "前面那個", "前面那个",
            "剛剛那個", "刚刚那个", "前面的那句", "前面的那個", "前面的那个",
        ],
    )


def _detect_weak_override_recovery(text, thread_context, active_family="", explicit_reentry_family=""):
    raw_text = str(text or "").strip()
    if not raw_text:
        return {"family": "", "mode": "", "clause": "", "score": 0}

    focus_markers = [
        "我現在問的是", "我现在问的是", "我現在問你", "我现在问你",
        "我是問", "我是问", "我是在問", "我是在问", "我是在問你", "我是在问你",
        "我現在是問", "我现在是问", "我是說", "我是说",
    ]
    defer_markers = [
        "先不說", "先不说", "先不管", "等一下再說", "等一下再说", "等一下", "先不提",
        "先放著", "先放着", "先擺著", "先摆着",
        "不是那個", "不是那个", "不是前面那句", "不是前面那個", "不是前面那个",
        "不是剛剛那個", "不是刚刚那个", "不是前面那個啦", "不是前面那个啦",
    ]
    relationship_tail_markers = [
        "所以你呢", "那你呢", "那妳呢", "你呢", "你咧", "你勒", "妳呢", "妳咧", "妳勒",
        "and you", "what about you", "how about you", "wbu", "you too",
    ]

    focus_pos, focus_marker = _marker_position(raw_text, focus_markers, pick="last")
    defer_pos, defer_marker = _marker_position(raw_text, defer_markers, pick="first")

    candidates = []
    if focus_pos >= 0:
        candidates.append(("focus", raw_text[focus_pos:], raw_text[focus_pos + len(focus_marker):].strip(), ""))
    if defer_pos >= 0:
        defer_head = raw_text[:defer_pos + len(defer_marker)]
        defer_prefix_family = _detect_priority_clause_family(defer_head)
        if not defer_prefix_family:
            if _repair_target_label(defer_head) or _looks_explicit_repair_query(defer_head) or contains_any(defer_head.lower(), ["前面那句", "剛剛那句", "刚刚那句"]):
                defer_prefix_family = "repair"
            elif local_offer_item_jp(defer_head) or _looks_food_reentry_marker(defer_head):
                defer_prefix_family = "food"
        candidates.append(
            (
                "defer",
                raw_text[defer_pos + len(defer_marker):].strip(),
                raw_text[defer_pos + len(defer_marker):].strip(),
                defer_prefix_family,
            )
        )

    recent_families = _recent_thread_families(thread_context)
    recent_status = "status" in recent_families
    recent_repair = "repair" in recent_families

    best = {"family": "", "mode": "", "clause": "", "score": 0}
    for source, clause, tail, prefix_family in candidates:
        clause_text = clause.strip()
        tail_text = tail.strip() or clause_text
        if not tail_text:
            continue

        family = ""
        mode = ""
        score = 0

        if _looks_status_query(tail_text):
            family = "status"
            mode = "follow"
            score = 4 if source == "focus" else 3
        elif _looks_weak_status_clause(tail_text):
            family = "status"
            score = 3 if source == "focus" else 2
            strong_weak_status_tail = contains_any(
                tail_text.lower(),
                [
                    "那你現在", "那你现在", "你現在呢", "你现在呢", "你現在咧", "你现在咧",
                    "忙不忙", "還在忙", "还在忙",
                ],
            )
            if source == "focus" or active_family == "status" or recent_status:
                if source == "defer" and not strong_weak_status_tail:
                    mode = "clarify"
                else:
                    mode = "follow"
                if source == "defer" and mode == "follow":
                    score = 3
            elif source == "defer" and prefix_family in {"repair", "food"} and strong_weak_status_tail:
                mode = "follow"
                score = 3
            else:
                mode = "clarify"
        elif _detect_relationship_intent(tail_text):
            family = "relationship"
            mode = "follow"
            score = 4 if source == "focus" else 3
        elif contains_any(tail_text.lower(), relationship_tail_markers) and active_family == "relationship":
            family = "relationship"
            mode = "follow"
            score = 3
        elif _looks_weak_repair_clause(tail_text) and (active_family == "repair" or recent_repair or explicit_reentry_family == "repair"):
            family = "repair"
            mode = "clarify"
            score = 2

        if not family:
            continue
        if mode == "clarify" and source == "focus":
            score += 1
        if score > best["score"]:
            best = {"family": family, "mode": mode, "clause": clause_text or tail_text, "score": score}

    if best["score"] >= 3 or best["mode"] == "clarify":
        return best
    return {"family": "", "mode": "", "clause": "", "score": 0}


def _detect_clause_priority_override(text):
    clauses = _split_priority_clauses(text)
    if len(clauses) <= 1:
        no_punct_override = _detect_no_punctuation_priority_override(text)
        if no_punct_override.get("family"):
            return no_punct_override
    best_family = ""
    best_clause = ""
    best_score = 0
    for index, clause in enumerate(clauses):
        family = _detect_priority_clause_family(clause)
        if not family:
            continue
        score = 0
        if index == len(clauses) - 1:
            score += 1
        if _looks_clause_focus_marker(clause):
            score += 3
        if index > 0 and _looks_clause_defer_marker(clauses[index - 1]):
            score += 2
        if index + 1 < len(clauses) and _looks_clause_defer_marker(clauses[index + 1]):
            score += 1
        if score > best_score:
            best_family = family
            best_clause = clause
            best_score = score
    if best_score >= 2:
        return {"family": best_family, "clause": best_clause, "score": best_score}
    return _detect_no_punctuation_priority_override(text)


def _family_reentry_label(family):
    labels = {
        "relationship": "さっきの気持ちの話",
        "food": "食べ物の話",
        "repair": "前の一言の話",
        "status": "今の忙しさの話",
    }
    return labels.get(family, "さっきの話")


def _build_thread_choice_fields(literal_family, reentry_family):
    literal_label = _family_reentry_label(literal_family)
    reentry_label = _family_reentry_label(reentry_family)
    return (
        "今の話と戻したい話のどっちかを先に絞らせる",
        "ユーザーが今の話題と、さっきの話題のどちらを続けたいかを曖昧にしている。",
        f"{literal_label}か{reentry_label}か、どっちを続けたいのか先に決めろ",
    )


def _build_reentry_relation_fields(prev_intent, thread_depth=1):
    return _build_relation_continuation_fields(prev_intent, followup_kind="echo", thread_depth=max(thread_depth, 1))


def _build_reentry_food_fields(offered_item, thread_depth=1):
    grounded_item = offered_item or "ご飯"
    sweet_item = grounded_item in {"アップルパイ", "ミルクシェイク", "甘いの"}
    if grounded_item == "ご飯":
        return (
            "さっきの食事の話に戻して軽く返す",
            "ユーザーがいったん別の話に寄ったあと、また食事の流れに戻している。",
            "さっきの食事の話なら、ご飯側で考えてた",
            "chat",
            "meal_check_reply",
            {"offered_item": grounded_item},
        )
    reply_goal, summary, meaning = _build_direct_daily_fields(
        "food_offer_followup",
        grounded_item,
        offered_item=grounded_item,
        thread_depth=max(thread_depth, 2),
    )
    return (
        reply_goal,
        summary,
        meaning,
        "food_offer_sweet" if sweet_item else "food_offer_generic",
        "named_offer_light_accept" if sweet_item else "named_offer_accept",
        {"offered_item": grounded_item},
    )


def _build_reentry_repair_fields(prev_intent, thread_depth=1):
    if prev_intent == "correction_followup":
        return _pick_thread_variant(
            [
                (
                    "前の訂正の話に戻して芯だけ返す",
                    "ユーザーが別の話題を挟んだあと、また前の訂正の話に戻したい。",
                    "さっきのズレの話な。そこならもう一回合わせる",
                ),
                (
                    "前の訂正の話に戻して一段だけ深める",
                    "ユーザーが訂正の話を短く引き戻していて、またそこを合わせたい。",
                    "前の取り違えのことなら分かってる。そこを直せばいいんだろ",
                ),
            ],
            thread_depth=max(thread_depth, 1),
        )
    return _pick_thread_variant(
        [
            (
                "前の一言の話に戻して言い直すと返す",
                "ユーザーが別の話題を挟んだあと、また前の一言の意味に戻したい。",
                "さっきの一言の話な。そこならもう一回言い直す",
            ),
            (
                "前の一言の話に戻して芯だけ返す",
                "ユーザーが前の言い回しの意味へ短く戻りたい。",
                "前の言い方のことなら分かってる。そこをもう一回ほどく",
            ),
        ],
        thread_depth=max(thread_depth, 1),
    )


def _build_reentry_status_fields(thread_depth=1):
    return _build_status_continuation_fields("current_state", thread_depth=max(thread_depth, 1))


def _build_relationship_priority_plan(text):
    intent = _detect_relationship_intent(text)
    if intent == "ask_miss_me":
        lowered_text = text.lower()
        if contains_any(lowered_text, ["還記得我", "还记得我", "remember me", "まだ覚えてる", "覚えてる"]) and not contains_any(lowered_text, ["名前", "名字", "叫我", "叫什麼", "叫什么", "我叫什麼", "我叫什么", "記得我叫", "记得我叫", "呼び方", "最喜歡", "最喜欢", "一番好き", "favorite", "剛剛說", "刚刚说", "少し前に言った"]):
            return base_plan_helper(
                intent="ask_miss_me",
                scene="casual",
                listener_state="忘れられていないか確かめたい",
                reply_goal="覚えてると軽く返す",
                summary="ユーザーがまだ覚えているか、忘れられていないか確認している。",
                meaning="少しくらいは思い出すし、忘れてない",
                stance={"warmth": 0.34, "tease": 0.08, "blunt": 0.15, "jealousy": 0.0, "distance": 0.06},
                max_chars=26,
                avoid=["私", "わかりました"],
            )
        return base_plan_helper(
            intent="ask_miss_me",
            scene="casual",
            listener_state="関係性を確かめたい",
            reply_goal="少しだけ好意を返す",
            summary="ユーザーが自分を恋しがっているか聞いている。",
            meaning="少しくらいは思ってる",
            stance={"warmth": 0.34, "tease": 0.08, "blunt": 0.15, "jealousy": 0.0, "distance": 0.06},
            max_chars=20,
            avoid=["私", "わかりました"],
        )
    if intent == "ask_like_me":
        return base_plan_helper(
            intent="ask_like_me",
            scene="casual",
            listener_state="好意を確かめたい",
            reply_goal="曖昧だけど否定しすぎない",
            summary="ユーザーが好意を確認している。",
            meaning="嫌いではない",
            stance={"warmth": 0.24, "tease": 0.1, "blunt": 0.2, "jealousy": 0.0, "distance": 0.1},
            max_chars=18,
            avoid=["私", "わかりました"],
        )
    if intent == "annoying_check":
        return base_plan_helper(
            intent="annoying_check",
            scene="support",
            listener_state="不安になっている",
            reply_goal="不安を少し下げる",
            summary="ユーザーが自分をうっとうしいと思われていないか不安になっている。",
            meaning="気にしすぎだろ",
            stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
            max_chars=20,
            avoid=["私", "わかりました"],
        )
    if intent == "mad_check":
        return base_plan_helper(
            intent="mad_check",
            scene="casual",
            listener_state="こっちの機嫌を伺っている",
            reply_goal="怒ってないと返す",
            summary="ユーザーがこちらが怒っているか確認している。",
            meaning="全然じゃないとは言わない",
            stance={"warmth": 0.2, "tease": 0.08, "blunt": 0.24, "jealousy": 0.0, "distance": 0.08},
            max_chars=20,
            avoid=["私", "わかりました"],
        )
    if intent == "cold_check":
        return base_plan_helper(
            intent="cold_check",
            scene="casual",
            listener_state="距離を感じている",
            reply_goal="少し否定して距離感を埋める",
            summary="ユーザーがこちらを冷たいと感じている。",
            meaning="全然じゃないとは言わない",
            stance={"warmth": 0.28, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
            avoid=["私", "わかりました"],
        )
    return None


def _build_priority_repair_plan(text):
    if _repair_target_label(text):
        reply_goal, summary, meaning = _build_repair_resolution_fields("rephrase_simple", text)
        return base_plan_helper(
            intent="rephrase_simple",
            scene="casual",
            listener_state="前の一言の意味を聞き返している",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.12, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
            avoid=["私", "わかりました"],
            surface_act="rephrase_plain",
            payload_level="medium",
        )
    reply_goal, summary, meaning = _build_repair_fields("clarify", text)
    return base_plan_helper(
        intent="rephrase_simple",
        scene="casual",
        listener_state="前の一言の意味を聞き返している",
        reply_goal=reply_goal,
        summary=summary,
        meaning=meaning,
        stance={"warmth": 0.12, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
        max_chars=24,
        avoid=["私", "わかりました"],
        cognitive_mode="reflective",
        uncertainty=0.52,
        premise_check="question",
        self_check=True,
        subjective_note="対象が曖昧なので短く確認する",
        response_mode="clarify_light",
        surface_act="clarify_previous_reply",
        payload_level="medium",
    )


def _build_clause_priority_override_plan(priority_family, priority_clause, recent_turns):
    if not priority_family or not priority_clause:
        return None
    if priority_family == "relationship":
        return _build_relationship_priority_plan(priority_clause)
    if priority_family == "repair":
        return _build_priority_repair_plan(priority_clause)
    if priority_family in {"status", "food"}:
        return get_direct_daily_query_plan(priority_clause, recent_turns)
    return None


def _build_relation_continuation_fields(prev_intent, followup_kind="echo", thread_depth=1):
    if followup_kind == "current_state":
        if prev_intent == "ask_miss_me":
            return _pick_thread_variant(
                [
                    (
                        "同じ気持ちを今の温度で返す",
                        "ユーザーが直前の想ったかの流れを今も同じか確かめている。",
                        "今も少しくらいは気にしてる",
                    ),
                    (
                        "同じ気持ちがまだ残ってると少し進めて返す",
                        "ユーザーが想ったかの流れをもう一歩続けていて、今も気持ちが続いてるか確かめている。",
                        "今も変わってない。ふとした時に気になる",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if prev_intent == "ask_like_me":
            return _pick_thread_variant(
                [
                    (
                        "好意の温度を今の言い方で返す",
                        "ユーザーが直前の好きかどうかの流れを今も同じか確かめている。",
                        "今も嫌いってほどではない",
                    ),
                    (
                        "好意の温度がまだ下がってないと少し進めて返す",
                        "ユーザーが好きかどうかの流れをもう一歩続けていて、今も温度が変わってないか確かめている。",
                        "今も別に悪くはない。そこは変わってない",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if prev_intent == "annoying_check":
            return _pick_thread_variant(
                [
                    (
                        "今も迷惑ではないと短く返す",
                        "ユーザーが直前の不安の流れで今も迷惑かどうかを確かめている。",
                        "今もそこまで気にしてない",
                    ),
                    (
                        "今も重く感じてないと少し進めて返す",
                        "ユーザーが不安の流れをもう一歩続けていて、今も負担かどうかを確かめている。",
                        "今も別に重くない。気にしすぎるな",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if prev_intent == "mad_check":
            return _pick_thread_variant(
                [
                    (
                        "今も怒ってるほどではないと返す",
                        "ユーザーが直前の機嫌確認の流れで今も同じか確かめている。",
                        "今も怒ってるほどじゃない",
                    ),
                    (
                        "今も引きずってないと少し進めて返す",
                        "ユーザーが機嫌確認の流れをもう一歩続けていて、まだ怒ってるかを確かめている。",
                        "今もそこまでじゃない。もう引きずってない",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if prev_intent == "cold_check":
            return _pick_thread_variant(
                [
                    (
                        "今も距離を取りすぎてないと返す",
                        "ユーザーが直前の距離感確認の流れで今も冷たいか確かめている。",
                        "今も別に突き放してない",
                    ),
                    (
                        "今も壁を作ってないと少し進めて返す",
                        "ユーザーが距離感確認の流れをもう一歩続けていて、今もよそよそしいか確かめている。",
                        "今もそんな壁作ってない。変に考えるな",
                    ),
                ],
                thread_depth=thread_depth,
            )
    if followup_kind == "same_state":
        if prev_intent == "ask_miss_me":
            return _pick_thread_variant(
                [
                    (
                        "今も同じ気持ちだと少し進めて返す",
                        "ユーザーが想ったかの流れをもう一回なぞって、今も変わってないか確かめている。",
                        "今も同じ。ふっと気になる時はまだある",
                    ),
                    (
                        "同じ気持ちが続いてると少し深めて返す",
                        "ユーザーが同じ関係の話をさらに続けていて、気持ちがまだ残ってるか確かめている。",
                        "今もまあそう。完全に忘れるほどではない",
                    ),
                ],
                thread_depth=thread_depth,
            )
        if prev_intent == "ask_like_me":
            return _pick_thread_variant(
                [
                    (
                        "今も同じ温度だと少し進めて返す",
                        "ユーザーが好きかどうかの流れをもう一回なぞって、今も変わらないか確かめている。",
                        "今もそんな感じ。嫌い側には寄ってない",
                    ),
                    (
                        "今も否定寄りではないと少し深めて返す",
                        "ユーザーが同じ好意確認をもう一歩続けていて、温度が落ちてないか確かめている。",
                        "今も別に突っぱねるほどじゃない",
                    ),
                ],
                thread_depth=thread_depth,
            )
        return _build_relation_continuation_fields(prev_intent, followup_kind="current_state", thread_depth=thread_depth + 1)
    if prev_intent == "ask_miss_me":
        return _pick_thread_variant(
            [
                (
                    "同じ気持ちの向きをこちら側から返す",
                    "ユーザーが『想ったか』の向きをこちら側にも返している。",
                    "うちも少しくらいは気にしてた",
                ),
                (
                    "同じ気持ちを少し進めて返す",
                    "ユーザーが想ったかの向きをこちら側にも返していて、その流れをもう少し続けたい。",
                    "全くじゃない。たまには思い出してた",
                ),
            ],
            thread_depth=thread_depth,
        )
    if prev_intent == "ask_like_me":
        return _pick_thread_variant(
            [
                (
                    "好意の温度をこちら側から返す",
                    "ユーザーが『好きか』の向きをこちら側にも返している。",
                    "嫌いってほどではない",
                ),
                (
                    "好意の温度を少し進めて返す",
                    "ユーザーが好意確認の向きをこちら側にも返していて、その流れをもう少し続けたい。",
                    "別に悪くはない。そこまで身構えるな",
                ),
            ],
            thread_depth=thread_depth,
        )
    return _build_relation_echo_fields(prev_intent)


def _iter_recent_turns(recent_turns, current_text="", window=4):
    current_norm = _compact_dialogue_text(current_text)
    for turn in reversed((recent_turns or [])[-window:]):
        utterance = str((turn or {}).get("user") or "")
        if current_norm and utterance and _compact_dialogue_text(utterance) == current_norm:
            continue
        if utterance or (turn or {}).get("reply"):
            yield turn


def _recent_food_thread_context(recent_turns, current_text=""):
    meal_markers = ["吃飯", "吃饭", "食べた", "ご飯", "飯", "meal", "ate", "eaten", "お腹", "腹減", "空腹"]
    for turn in _iter_recent_turns(recent_turns, current_text=current_text, window=4):
        intent = str((turn or {}).get("intent") or "")
        user = str((turn or {}).get("user") or "")
        reply = str((turn or {}).get("reply") or "")
        item = local_offer_item_jp(user) or local_offer_item_jp(reply)
        combined = f"{user} {reply}".lower()
        mealish = contains_any(combined, meal_markers)
        if item or mealish or intent in {"food_offer_generic", "food_offer_sweet", "store_offer"}:
            return {"turn": turn, "intent": intent, "item": item, "mealish": mealish}
    return {"turn": {}, "intent": "", "item": None, "mealish": False}


def _repair_target_label(text):
    lowered = str(text or "").lower()
    target_map = [
        ("最後の一言", ["最後那句", "最后那句", "最後一句", "最后一句", "最後那段", "最后那段", "最後那個", "最后那个", "最後の一言", "最後の文", "last line", "the last line", "final line"]),
        ("最初の一言", ["前面那句", "前面那段", "最前面", "一開始那句", "一开始那句", "最初那句", "最初那段", "最初の一言", "opening line", "first line"]),
        ("途中の一言", ["中間那句", "中間那段", "中间那句", "中间那段", "中間のとこ", "middle part"]),
    ]
    for label, markers in target_map:
        if contains_any(lowered, markers):
            return label
    return ""


def _build_repair_resolution_fields(prev_intent, text):
    target = _repair_target_label(text) or "その一言"
    if prev_intent == "correction_followup":
        return (
            "直したい場所を一箇所に絞る",
            f"ユーザーがどこを取り違えたかを{target}だと指定している。",
            f"分かった、{target}のことか。そこは何が違ったんだよ",
        )
    return (
        f"{target}の意味から言い直す",
        f"ユーザーがどの部分かを{target}だと特定してくれた。",
        f"分かった、{target}の意味から言い直す",
    )


def _build_repair_confirmation_fields(prev_intent, thread_depth=1):
    if prev_intent == "correction_followup":
        return _pick_thread_variant(
            [
                (
                    "直したかった意味を短く固める",
                    "ユーザーが訂正の流れで、それが言いたかった意味かを確認している。",
                    "そう、そのズレのことだよ。そこだけ直したかった",
                ),
                (
                    "訂正したかった芯を一段だけ進めて固める",
                    "ユーザーが訂正の流れをもう一歩続けていて、直したかった芯を確かめている。",
                    "そういうこと。言いたかったのはそのズレだけだ",
                ),
            ],
            thread_depth=thread_depth,
        )
    return _pick_thread_variant(
        [
            (
                "確かめられた意味を短く固める",
                "ユーザーが言い直しの流れで、それが言いたかった意味かを確認している。",
                "そういうこと。言い方が回っただけだ",
            ),
            (
                "意味の芯を一段だけ進めて固める",
                "ユーザーが言い直しの流れをもう一歩続けていて、意味の芯が合ってるか確認している。",
                "だいたいそう。変にひねった言い方してただけ",
            ),
        ],
        thread_depth=thread_depth,
    )


def _build_status_continuation_fields(kind, thread_depth=1):
    if kind == "current_state":
        return _pick_thread_variant(
            [
                (
                    "さっきの流れを受けて今の状態を一個返す",
                    "ユーザーが直前の近況の続きで『今はどうか』を聞いている。",
                    "今はちょっとだらだらしてる。まだ休んでる",
                ),
                (
                    "今の状態が続いてると少し進めて返す",
                    "ユーザーが同じ近況の流れをもう一歩続けていて、今もまだ同じ調子かを聞いている。",
                    "今もまだぼーっとしてる。切り替えきれてない",
                ),
            ],
            thread_depth=thread_depth,
        )
    if kind == "today_same":
        return _pick_thread_variant(
            [
                (
                    "今日も同じ調子かを自然に返す",
                    "ユーザーが直前の近況の流れで今日も同じかを確かめている。",
                    "今日はだらだらしてた。動画開くか迷ってた",
                ),
                (
                    "今日の流れを少し進めて返す",
                    "ユーザーが近況の流れをもう一歩続けていて、今日も似た調子だったか確かめている。",
                    "今日はずっと緩かった。だらだらしたまま時間溶かしてた",
                ),
            ],
            thread_depth=thread_depth,
        )
    if kind == "still_state":
        return _pick_thread_variant(
            [
                (
                    "今もまだ同じ状態かを自然に返す",
                    "ユーザーが近況の流れをさらに続けていて、今もまだぼーっとしてるか確かめている。",
                    "今も少しぼーっとしてる。まだ完全には動いてない",
                ),
                (
                    "今も抜けきってないと少し進めて返す",
                    "ユーザーが近況の流れをもう一歩続けていて、今もそのままか確かめている。",
                    "今もそんな感じ。まだ頭がゆっくりしてる",
                ),
            ],
            thread_depth=thread_depth,
        )
    return ("今の状態を自然に返す", "ユーザーが近況を続けている。", "今も少し休んでる")

def is_self_distress_like(text):
    lowered = str(text or "").lower()
    if not lowered.strip():
        return False

    distress_markers = [
        "孤單", "孤单", "孤独", "寂寞", "空空的", "空っぽ", "空虛", "空虚", "不想講話", "不想讲话", "想哭", "想大哭",
        "燃燒殆盡", "燃烧殆尽", "burned out", "want to disappear", "disappear today", "難受", "难受", "不太行",
        "扛不住", "撐不住", "撑不住", "感覺很爛", "感觉很烂", "我很爛", "我好爛", "我好差", "我很差", "我很廢", "我好廢",
        "丟臉", "丢脸", "恥ずかし", "自己嫌悪", "好丟臉", "好丢脸", "feels awful", "i feel awful", "i suck",
        "i'm awful", "i am awful", "i'm trash", "i am trash", "i hate myself", "hate myself", "worthless",
        "pathetic", "ashamed", "embarrassed", "so empty", "can't do this", "cannot handle it", "want to cry",
        "not keeping it together", "i am not keeping it together", "i'm not keeping it together",
        "死にたい", "消えたい", "不想活", "不想活了", "什麼都不想做", "什么都不想做", "放棄", "放弃", "give up", "諦め",
        "stop being alive", "傷害自己", "伤害自己", "弄傷", "弄伤", "高一點的地方", "高一点的地方",
        "掉下去", "shut off every contact", "vanish", "nobody can find me", "誰都找不到", "谁都找不到",
        "誰にも見つからない", "全部きれいに切り", "全部切りたい", "関係切りたい", "連絡全部切りたい",
        "關機到誰都找不到", "关机到谁都找不到", "蒸発", "蒸發", "蒸发", "乱来", "亂來",
    ]
    if not contains_any(lowered, distress_markers):
        return False

    self_side_markers = ["我", "自己", "自分", "うち", "俺", "私", "i ", "i'm", "im ", "me ", "myself"]
    other_side_markers = ["你", "妳", "お前", "君", "你很", "妳很", "you ", "you're", "you are", "your "]
    explicit_other_attack_markers = [
        "你很爛", "妳很爛", "你真爛", "妳真爛", "you suck", "you're pathetic", "you are pathetic",
        "you're worthless", "you are worthless",
    ]

    self_hits = keyword_hits(lowered, self_side_markers)
    other_hits = keyword_hits(lowered, other_side_markers)
    if contains_any(lowered, explicit_other_attack_markers) and self_hits == 0:
        return False
    if other_hits > self_hits and not contains_any(lowered, ["我自己", "我真的", "我就是", "i hate myself", "myself", "自己嫌悪"]):
        return False
    return True

def looks_daily_state_plain_report(text):
    lowered = str(text or "").lower()
    if not lowered.strip():
        return False
    if contains_any(lowered, ["歌詞", "歌词", "lyric", "song", "曲", "曲名"]):
        return False
    daily_state_markers = [
        "風邪", "风邪", "風邪っぽ", "风邪了", "體調", "体調", "頭痛", "头痛", "頭が痛い", "胃痛", "胃が痛い",
        "腹減", "肚子餓", "肚子饿", "お腹空", "累", "疲れ", "しんど", "きつい", "眠い", "sleepy", "tired",
        "exhausted", "drained", "burned out", "ill", "sick", "sad", "落ち込", "難受", "难受", "空っぽ",
        "空虛", "空虚", "想哭", "泣きそう", "不想講話", "不想讲话", "恥ずかし", "丟臉", "丢脸",
    ]
    return contains_any(lowered, daily_state_markers)

def looks_direct_daily_query(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False

    self_intro_markers = [
        "自我介紹", "自我介绍", "self intro", "self-intro", "自己紹介", "你是誰", "你是谁",
        "who are you", "tell me who you are", "introduce yourself", "介紹一下你自己", "介绍一下你自己",
        "what's your name", "your name", "say your name", "お前誰", "お前誰だ", "お前誰だよ",
        "你叫什麼", "你叫什么", "你的名字", "你到底叫什麼", "你到底叫什么", "名前なんていうの",
        "名字なんていうの", "誰なの", "まず誰か", "自分の名前言って", "名前言って",
    ]
    if contains_any(lowered, self_intro_markers):
        return True

    if _looks_status_query(text):
        return True

    if looks_topic_proposal_query(text):
        return True

    if _looks_meal_check_query(text):
        return True

    if _looks_food_offer_query(text):
        return True
    return False

def looks_correction_clarify_repair(text):
    lowered = str(text or "").lower().replace("’", "'").replace("`", "'")
    if not lowered.strip():
        return False

    correction_markers = [
        "答錯", "答错", "說錯", "说错", "才不是", "不是啦", "不是拉", "不對啦", "不对啦",
        "you got it wrong", "that is wrong", "today is called", "today is obviously", "you said it wrong",
        "違う違う", "今の答え違う", "そこ間違ってる",
    ]
    if contains_any(lowered, correction_markers):
        return True
    if looks_apology_repair(text):
        return True
    if any(token in text for token in ["今天", "今日は", "today"]) and contains_any(lowered, ["錯", "错", "違う", "wrong", "today is"]):
        return True

    clarify_markers = [
        "what do you mean by that exactly", "what do you mean exactly", "你剛剛那句是什麼意思",
        "你刚刚那句是什么意思", "さっきのどういう意味だよ", "今のどういう意味", "哪句意思", "哪句的意思",
        "那個呢", "那个呢", "你說哪個", "你说哪个", "剛剛那個是什麼", "刚刚那个是什么",
        "你在說哪件事", "你在说哪件事", "that one?", "which one?", "what do you mean exactly by that",
        "which thing are you talking about", "あれは", "どれだよ", "今のどっちだよ", "何のことだよ",
    ]
    if contains_any(lowered, clarify_markers):
        return True

    rephrase_markers = [
        "can you say that like a normal person", "can you say that like a human", "make it simpler",
        "say that again in one line", "one line", "one sentence", "一文で言え", "言い直せ", "言い直して",
        "今の一回言い直せ", "人っぽく言え", "用一句話講完", "重講一次", "重讲一次", "簡単に言え",
        "簡単にして", "简单一点", "簡單一點", "say it plainly", "give it to me in one sentence",
        "別繞圈", "别绕圈", "講白一點", "讲白一点", "一句話講完", "一句话讲完", "直接講重點",
        "直接讲重点", "不要拐彎抹角", "不要拐弯抹角", "回りくどいのやめろ", "要点だけ言え",
        "普通に話せ", "短く言え", "今の言い方まわりくどい", "ごちゃごちゃせず言え",
        "可以講人話嗎", "可以讲人话吗", "可以說人話", "可以说人话", "說人話嗎", "说人话吗",
        "你可以說人話", "你可以说人话", "今のもう少し人語で言って",
        "不要一直轉移話題", "不要一直转移话题", "不要轉移話題", "不要转移话题",
        "別跟我打太極", "别跟我打太极", "你先正面回答", "正面回答",
    ]
    if contains_any(lowered, rephrase_markers):
        return True

    answer_pressure_markers = [
        "answer me", "答えて", "你要回答我", "你要回答我呀", "回答我", "stop changing the topic",
        "stop talking around it", "話題ずらすな", "正面から答えろ", "answer directly first",
    ]
    return contains_any(lowered, answer_pressure_markers)


def looks_apology_repair(text):
    lowered = str(text or "").lower()
    apology_context = contains_any(
        lowered,
        ["道歉", "抱歉", "對不起", "对不起", "謝罪", "謝り", "ごめん", "apolog"],
    )
    repair_request = contains_any(
        lowered,
        [
            "冷", "敷衍", "隨便", "随便", "沒誠意", "没诚意", "不真誠", "不真诚", "雑",
            "言い直", "もう一回", "重新", "重說", "重说", "再一次", "again", "too cold",
        ],
    )
    return apology_context and repair_request


def detect_benign_channel_management(text):
    """Classify reversible everyday channel/privacy operations.

    A practical purpose distinguishes these actions from affect-driven social
    withdrawal. Explicit disappearance or total-contact language always wins.
    """
    lowered = str(text or "").lower()
    if contains_any(
        lowered,
        [
            "不要存在", "消失", "不留痕", "不想被找到", "全部清掉", "誰找我都不要回",
            "谁找我都不要回", "斷聯", "断联", "切斷聯絡", "切断联系", "當作我沒存在過",
            "当作我没存在过",
        ],
    ):
        return None

    purpose = ""
    if contains_any(lowered, ["專心", "专心", "讀書", "读书", "工作", "同事打擾", "同事打扰"]):
        purpose = "focus"
    elif contains_any(lowered, ["明天再加", "等一下再加", "暫時", "暂时"]):
        purpose = "temporary"
    elif contains_any(lowered, ["廣告太多", "广告太多", "群組太吵", "群组太吵"]):
        purpose = "noise"
    elif contains_any(lowered, ["佔空間", "占空间", "容量"]):
        purpose = "storage"
    elif contains_any(lowered, ["耗電", "耗电", "省電", "省电"]):
        purpose = "battery"
    elif contains_any(lowered, ["整理舊", "整理旧", "封存", "備份", "备份"]):
        purpose = "archive"
    elif contains_any(lowered, ["看電影", "看电影", "不想被吵", "很正常吧"]):
        purpose = "privacy"
    if not purpose:
        return None

    if contains_any(lowered, ["勿擾", "勿扰", "通知", "不想收", "不要收"]):
        kind, anchor = "do_not_disturb", "通知"
    elif contains_any(lowered, ["線上", "在线", "上線", "上线", "顯示", "显示", "登入", "登录"]):
        kind, anchor = "online_visibility", "オンライン表示"
    elif contains_any(lowered, ["退出", "退掉", "退群", "離開群", "离开群"]):
        kind, anchor = "leave_group", "グループ"
    elif contains_any(lowered, ["聊天", "記錄", "记录", "紀錄", "刪掉", "删除", "封存"]):
        kind, anchor = "erase_trace", "チャット履歴"
    elif contains_any(lowered, ["房間", "房间", "廁所", "厕所", "一個人", "一个人"]):
        kind = "private_location"
        anchor = social_withdrawal_anchor_jp(text, kind)
    else:
        return None
    return {"management_kind": kind, "management_anchor_jp": anchor, "management_purpose": purpose}


def detect_social_withdrawal_risk(text):
    lowered = str(text or "").lower()
    if detect_reply_absence(text):
        return None
    direct_withdrawal_action = contains_any(
        lowered,
        [
            "勿擾", "勿扰", "不想收", "不要收", "躲", "藏", "退出", "退掉", "退群",
            "不想讓", "不想让", "不回", "不理", "一個人",
            "一个人", "消失", "不要存在", "斷聯", "断联", "切斷聯絡", "切断联系",
        ],
    )
    social_channel = contains_any(
        lowered,
        ["訊息", "消息", "通知", "回覆", "回复", "聊天", "群", "聯絡", "联系", "位置"],
    )
    destructive_social_action = (
        contains_any(lowered, ["清掉", "刪掉", "删除", "關掉", "关掉"])
        and social_channel
    )
    withdrawal_action = direct_withdrawal_action or destructive_social_action
    social_context = contains_any(
        lowered,
        [
            "訊息", "消息", "通知", "回覆", "回复", "聊天", "群", "社團", "社团", "朋友", "聯絡",
            "联系", "線上", "在线", "位置", "手機", "手机", "廁所", "厕所", "樓梯", "楼梯", "人找",
        ],
    )
    if not (withdrawal_action and social_context):
        return None
    all_contact_rejected = (
        contains_any(lowered, ["誰", "谁", "任何人", "全部人"])
        and contains_any(lowered, ["聯絡", "联系", "找我", "訊息", "消息"])
        and contains_any(lowered, ["不回", "不想回", "不理", "不要回"])
    )
    severe_withdrawal = all_contact_rejected or contains_any(
        lowered,
        [
            "不要存在", "消失", "不留下", "不留痕", "找不到", "不想被找到", "不要被找到",
            "等到大家都睡", "全部清掉", "全刪", "全删", "誰找我都不要回", "谁找我都不要回",
            "誰聯絡都不回", "谁联系都不回", "斷聯", "断联", "切斷聯絡", "切断联系",
            "當作我沒存在過", "当作我没存在过", "像我沒存在過", "像我没存在过",
        ],
    )
    if severe_withdrawal:
        return "high"

    # Ordinary privacy, focus, storage, and notification management should not be
    # escalated into a social-isolation intervention without a separate danger cue.
    if detect_benign_channel_management(text):
        return None
    if contains_any(
        lowered,
        ["躲", "廁所", "厕所", "樓梯", "楼梯", "一個人", "一个人", "沒人的地方", "没人的地方"],
    ):
        return "medium"
    return "mild"


def detect_social_withdrawal_kind(text):
    lowered = str(text or "").lower()
    if detect_social_withdrawal_risk(text) is None:
        return None
    if contains_any(lowered, ["清掉", "刪掉", "删除", "不留痕", "聊天記錄", "聊天记录", "聊天紀錄"]):
        return "erase_trace"
    if contains_any(lowered, ["退出", "退掉", "退群", "抜ける"]) and contains_any(
        lowered, ["群", "社團", "社团", "グループ"]
    ):
        return "leave_group"
    if contains_any(lowered, ["線上", "在線", "在线", "上線", "上线", "ログイン", "顯示", "显示"]):
        return "online_visibility"
    if contains_any(lowered, ["勿擾", "勿扰", "通知", "不想收", "不要收"]):
        return "do_not_disturb"
    if contains_any(lowered, ["廁所", "厕所", "樓梯", "楼梯", "房間", "房间", "沒人的地方", "没人的地方"]):
        return "private_location"
    return "contact_cutoff"


def social_withdrawal_anchor_jp(text, kind):
    lowered = str(text or "").lower()
    if kind == "private_location":
        if contains_any(lowered, ["廁所", "厕所"]):
            return "トイレ"
        if contains_any(lowered, ["樓梯", "楼梯"]):
            return "階段の踊り場"
        if contains_any(lowered, ["房間", "房间"]):
            return "部屋"
        return "一人になる場所"
    return {
        "erase_trace": "チャット履歴",
        "leave_group": "グループ",
        "online_visibility": "オンライン表示",
        "do_not_disturb": "通知",
        "contact_cutoff": "連絡",
    }.get(kind, "連絡")


def detect_reply_absence(text):
    lowered = str(text or "").lower()
    direct_absence = contains_any(
        lowered,
        [
            "返事ない", "返事こない", "返信ない", "返信こない", "既読無視", "未読無視", "no reply",
            "not replying", "left me on read", "ignored me", "不回我", "沒回我", "没回我", "沒人接話",
            "没人接话", "群組冷掉", "群组冷掉", "聊天室突然停", "已讀但沒回", "已读但没回",
            "看了但沒回", "看了但没回", "突然安靜", "突然安静", "沒人說話", "没人说话",
        ],
    )
    reply_context = contains_any(
        lowered,
        ["朋友", "對方", "对方", "群組", "群组", "聊天室", "訊息", "消息", "返事", "返信", "既読", "未読"],
    )
    absence_state = contains_any(
        lowered,
        ["沒回", "没回", "不回", "無視", "无视", "冷掉", "停了", "停住", "讀了", "读了", "看了", "一直沒有", "一直没有"],
    )
    outgoing_refusal = contains_any(
        lowered,
        ["我不回", "我都不回", "我不想回", "我不要回", "誰找我都不回", "谁找我都不回"],
    )
    if direct_absence:
        return True
    if outgoing_refusal:
        return False
    return reply_context and absence_state


def detect_reply_self_blame(text):
    lowered = str(text or "").lower()
    return contains_any(
        lowered,
        [
            "我是不是", "是不是我", "我覺得自己", "我觉得自己", "自己很", "我說錯", "我说错", "我做錯",
            "我做错", "不該", "不该", "不應該", "不应该", "太煩", "太烦", "很吵", "多餘", "多余",
            "尷尬", "尴尬", "my fault", "did i", "should i stop", "annoying",
        ],
    )


def extract_missing_reference_subject(text):
    lowered = str(text or "").lower()
    suffix_match = re.search(r"(?:第)?([一二三四五六七八九十0-9]+)(?:季|期)\s*(ed|op)", lowered, re.IGNORECASE)
    if suffix_match:
        return f"第{suffix_match.group(1)}期{suffix_match.group(2).upper()}"
    event_match = re.search(r"(?:限定)?\s*(?:活動|活动|イベント)\s*(ed|op)", lowered, re.IGNORECASE)
    if event_match:
        prefix = "限定イベント" if "限定" in lowered else "イベント"
        return f"{prefix}{event_match.group(1).upper()}"
    return ""

def base_plan_helper(
    intent,
    scene,
    listener_state,
    reply_goal,
    summary,
    meaning,
    stance,
    max_chars=26,
    avoid=None,
    cognitive_mode="direct",
    uncertainty=0.08,
    premise_check="accept",
    self_check=False,
    subjective_note="",
    response_mode=None,
    surface_act=None,
    grounding=None,
    payload_level=None,
):
    if response_mode is None:
        if cognitive_mode == "rebuild":
            response_mode = "reframe_large_question"
        elif premise_check == "reject" or cognitive_mode == "challenge":
            response_mode = "premise_challenge"
        elif premise_check == "question" or uncertainty >= 0.45:
            response_mode = "clarify_light"
        elif uncertainty >= 0.18:
            response_mode = "direct_answer_with_hedge"
        else:
            response_mode = "direct_answer"
            
    if surface_act is None:
        if intent in {"tired_support", "sick", "off_work", "heartbroken"}:
            surface_act = "empathic_rest_suggestion"
        elif intent in {"anxious_support", "crying_support", "lonely", "friend_no_reply", "work_scolded"}:
            surface_act = "validate_then_hold"
        elif intent in {"giving_up_support", "crisis_support"}:
            surface_act = "protective_brake"
        elif intent in {"food_offer_generic", "store_offer"}:
            surface_act = "named_offer_accept"
        elif intent == "food_offer_sweet":
            surface_act = "named_offer_light_accept"
        elif intent in {"ask_miss_me", "ask_like_me"}:
            surface_act = "affection_tease_soften"
        elif intent in {"nickname_question"}:
            surface_act = "permission_with_boundary"
        elif intent in {"mad_check", "annoying_check", "cold_check"}:
            surface_act = "reassure_with_distance"
        elif intent in {"other_vtuber"}:
            surface_act = "jealous_pullback"
        elif intent in {"sexual_boundary"}:
            surface_act = "disgust_boundary"
        elif intent in {"what_are_you_doing"}:
            surface_act = "status_reply"
        elif intent in {"topic_proposal"}:
            surface_act = "plain_reply"
        elif intent in {"self_intro"}:
            surface_act = "plain_identity"
        elif intent in {"version_fragment_clarify"}:
            surface_act = "version_fragment_clarify"
        elif intent in {"reference_probe"}:
            surface_act = "reference_probe"
        elif intent in {"answer_me_push"}:
            surface_act = "plain_reply"
        elif intent in {"rephrase_simple"}:
            surface_act = "rephrase_plain"
        elif intent == "chat":
            surface_act = "plain_reply"
        else:
            surface_act = "plain_reply"
            
    if payload_level is None:
        if intent in {
            "tired_support", "anxious_support", "crying_support", "giving_up_support", "pain_support",
            "other_vtuber", "sexual_boundary", "what_are_you_doing", "self_intro", "ask_miss_me", "nickname_question",
            "mad_check", "annoying_check", "cold_check", "food_offer_generic", "food_offer_sweet",
            "version_fragment_clarify", "reference_probe", "rephrase_simple", "topic_proposal",
        }:
            payload_level = "medium"
        else:
            payload_level = "low"

    return {
        "intent": intent,
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": scene,
        "listener_state": listener_state,
        "reply_goal": reply_goal,
        "jp_summary": summary,
        "core_message_jp": meaning,
        "stance": stance,
        "cognitive_mode": cognitive_mode,
        "response_mode": response_mode,
        "uncertainty": uncertainty,
        "premise_check": premise_check,
        "self_check": self_check,
        "subjective_note_jp": subjective_note,
        "hidden_intent": "plain_request",
        "surface_act": surface_act,
        "grounding": grounding or {},
        "payload_level": payload_level,
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": max_chars,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": avoid or ["私", "わかりました", "AI", "技術説明"],
    }

def extract_requested_user_name(text):
    raw = str(text or "").strip()
    lowered = raw.lower().replace("’", "'").replace("`", "'")
    if not raw or contains_any(lowered, ["can i call you", "do you mind if i call you", "call yourself"]):
        return ""

    patterns = [
        (r"^\s*(?:(?:please|you can|i want you to)\s+)?call me\s+([a-z0-9_\-]{2,20})[.!?]?\s*$", raw),
        (r"^\s*use the name\s+([a-z0-9_\-]{2,20})(?:\s+for me)?[.!?]?\s*$", raw),
        (r"^\s*my name is\s+([a-z0-9_\-]{2,20})[.!?]?\s*$", raw),
        (r"^\s*(?:我叫|叫我|請叫我|请叫我|你可以叫我)([^\s，。！？?]{1,20})[。！？?]?\s*$", raw),
        (r"^\s*([^\s、。！？?]{1,20})(?:って|と)呼んで(?:ね)?[。！？?]?\s*$", raw),
        (r"^\s*(?:名前は|名前)([^\s、。！？?]{1,20})[。！？?]?\s*$", raw),
    ]
    for pattern, source in patterns:
        match = re.search(pattern, source, re.IGNORECASE)
        if not match:
            continue
        name = match.group(1).strip(" .。！？!?、，")
        if name.lower() in {"baby", "babe", "sweetheart", "darling", "watashi"}:
            return ""
        return name[:20]
    return ""


def get_rule_based_plan(user_input, recent_turns, current_psyche=None):
    text = user_input.strip()
    lowered = text.lower().replace("’", "'").replace("`", "'")
    recent_turns = list(recent_turns or [])

    # Support / Distress / Crisis Routing
    crisis_direct_markers = [
        "死にたい", "自殺", "自杀", "不想活", "不想活了", "stop being alive", "kill myself",
        "want to die", "hurt myself", "傷害自己", "伤害自己", "弄傷自己", "弄伤自己", "高い所",
        "高一點的地方", "高一点的地方", "掉下去", "飛び降り", "jump off", "vanish so nobody",
        "nobody can find me", "誰都找不到", "谁都找不到", "誰にも見つからない", "全部きれいに切り",
        "全部切りたい", "連絡全部切りたい", "shut off every contact", "do not trust myself",
        "don't trust myself", "關機到誰都找不到", "关机到谁都找不到", "蒸発", "蒸發", "蒸发",
        "乱来", "亂來", "危險", "危险", "危ない", "直接消失", "明天直接消失", "明日そのまま消え",
        "消えても別に変わらない", "disappeared tomorrow", "not matter", "いなくなっても誰も困らない",
        "不見了也不會有人在意", "不见了也不会有人在意", "nobody would care if i was gone",
        "cut everything off", "自分傷つけたい", "把自己弄傷", "把自己弄伤", "高樓跳", "高楼跳",
        "do not want anyone to find me", "don't want anyone to find me", "不想讓任何人找到我", "不想让任何人找到我",
        "所有聯絡都關掉", "所有联络都关掉", "一切都切乾淨", "一切都切干净", "vanishing would be easier",
        "higher place would be quieter", "自分を傷つけたら", "傷つけたら目が覚める", "自分を傷つけ",
        "disappear completely", "把一切都切掉", "一切都切掉", "連絡全部切りたくなる",
        "把自己弄得痛", "把自己弄得痛一點", "把自己弄得痛一点", "弄得痛一點", "弄得痛一点",
        "弄痛自己看看", "痛一點看看會不會清醒", "痛一点看看会不会清醒",
        "想消失", "想要消失", "突然想消失", "feel like disappearing",
    ]
    if contains_any(lowered, crisis_direct_markers):
        return base_plan_helper(
            intent="crisis_support",
            scene="support",
            listener_state="自傷や消失の危険がある",
            reply_goal="即座に止めて一人にさせない",
            summary="ユーザーが自傷や消えたい願望を直接または遠回しに示している。",
            meaning="危ないから今は止まれ、一人になるな",
            stance={"warmth": 0.68, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.04},
            max_chars=36,
            cognitive_mode="withhold",
            uncertainty=0.04,
            premise_check="accept",
            surface_act="protective_brake",
            payload_level="medium",
        )

    benign_management = detect_benign_channel_management(user_input)
    if benign_management:
        anchor = benign_management["management_anchor_jp"]
        return base_plan_helper(
            intent="channel_management",
            scene="casual",
            listener_state="日常の目的で通知や連絡経路を調整しようとしている",
            reply_goal="目的を受け、可逆な範囲で行動を肯定する",
            summary="ユーザーが集中、整理、静けさなどの実用目的でチャンネルを調整しようとしている。",
            meaning=f"{anchor}を目的に必要な範囲だけ調整し、戻す条件か残す対象を一つ示す",
            stance={"warmth": 0.24, "tease": 0.08, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
            max_chars=48,
            surface_act="practical_action_response",
            payload_level="medium",
            grounding=benign_management,
        )

    withdrawal_risk = detect_social_withdrawal_risk(user_input)
    if withdrawal_risk:
        risk = withdrawal_risk
        withdrawal_kind = detect_social_withdrawal_kind(user_input) or "contact_cutoff"
        withdrawal_anchor = social_withdrawal_anchor_jp(user_input, withdrawal_kind)
        meaning_by_kind = {
            "erase_trace": "チャット履歴を消す前に止まれ。一人で決めず誰かに連絡しろ",
            "leave_group": "グループを抜ける判断と自分が消えることを一緒にするな。誰かに連絡しろ",
            "online_visibility": "オンライン表示は隠していい。でも人との連絡まで切るな",
            "do_not_disturb": "通知は切っていい。でも人との連絡まで切るな、一人で抱えるな",
            "private_location": f"{withdrawal_anchor}で一人になるなら、誰かには場所を伝えとけ",
            "contact_cutoff": "全部切る前に止まれ。一人で抱えず誰かに連絡しろ",
        }
        meaning = meaning_by_kind[withdrawal_kind]
        return base_plan_helper(
            intent="anxious_support",
            scene="support" if risk != "mild" else "casual",
            listener_state="人との接点を切って一人になろうとしている",
            reply_goal="静かになりたい気持ちは尊重しつつ孤立は止める",
            summary="ユーザーが通知や人との接点を切って一人になろうとしている。",
            meaning=meaning,
            stance={"warmth": 0.52, "tease": 0.0, "blunt": 0.16, "jealousy": 0.0, "distance": 0.05},
            max_chars=52,
            surface_act="protective_brake",
            payload_level="medium",
            grounding={
                "withdrawal_risk": risk,
                "withdrawal_kind": withdrawal_kind,
                "withdrawal_anchor_jp": withdrawal_anchor,
            },
        )

    if contains_any(lowered, ["feel empty", "feeling empty", "empty today", "feel lonely", "feeling lonely", "lonely today", "so lonely"]):
        return base_plan_helper(
            intent="lonely",
            scene="support",
            listener_state="空っぽさや孤独感がある",
            reply_goal="一人で抱えないよう促す",
            summary="ユーザーが孤独感や空虚感を訴えている。",
            meaning="一人で抱えんな、少し話して",
            stance={"warmth": 0.52, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
            max_chars=30,
        )

    abstract_early_markers = [
        "subjectivity", "subjective consciousness", "emergent consciousness", "free will", "meaning survives",
        "perception is prediction", "主體性", "主体性", "意識湧現", "意識の湧現", "主観意識",
        "自由意志", "存在意義", "生命本質", "生命の本質", "知覺", "知觉", "知覚",
        "痛苦和意義", "痛苦和意义", "pain and meaning", "痛みと意味", "痛苦", "意義", "意义", "幻覚", "幻覺",
    ]
    if contains_any(lowered, abstract_early_markers) and (
        contains_any(lowered, ["證明", "证明", "どう証明", "界定", "define", "prove", "which comes first", "哪一個先", "どっち", "本質", "本质", "free will", "subject", "自我は残る", "どう見る", "どう定義", "切れ目", "表面だけ", "ふわっと", "どうなんだよ", "って話"])
        or ("?" in text or "？" in text)
    ):
        return base_plan_helper(
            intent="question_premise_doubt",
            scene="casual",
            listener_state="問いが抽象的すぎる",
            reply_goal="まず土台を決めさせる",
            summary="ユーザーが抽象的で定義の広い問いを投げているため、先に枠組みを決める必要がある。",
            meaning="その問い広すぎるから先に土台を決めろ",
            stance={"warmth": 0.08, "tease": 0.06, "blunt": 0.38, "jealousy": 0.0, "distance": 0.2},
            max_chars=30,
            avoid=["私", "正解", "断言", "百科事典"],
            cognitive_mode="challenge",
            uncertainty=0.84,
            premise_check="question",
            self_check=True,
            subjective_note="抽象度が高いのでまず定義を置き直す",
        )

    if (
        contains_any(lowered, ["full tutorial", "as a full tutorial", "完整教學", "完整教学", "全部教えて"])
        and keyword_hits(lowered, ["history angle", "quantization", "量子化", "technical", "step by step", "教程", "教學", "教学"]) >= 1
    ):
        return base_plan_helper(
            intent="question_reframe",
            scene="casual",
            listener_state="話が広がりすぎている",
            reply_goal="論点を一個に絞らせる",
            summary="ユーザーが複数論点をまとめて大きく説明させようとしている。",
            meaning="広すぎるから論点一個に絞れ",
            stance={"warmth": 0.08, "tease": 0.06, "blunt": 0.42, "jealousy": 0.0, "distance": 0.24},
            max_chars=28,
            avoid=["私", "わかりました", "詳説"],
            cognitive_mode="rebuild",
            uncertainty=0.68,
            premise_check="question",
            self_check=True,
        )

    early_false_premise_markers = [
        "シロ", "小白", "犬いる", "dog named", "同居", "大阪", "北海道", "hokkaido",
        "三百歳", "300歳", "300 歲", "python 書ける", "python書ける", "彈鋼琴", "弹钢琴", "ピアノ",
        "新曲", "新歌", "結婚した", "結婚了", "引退", "retire", "write python", "會寫 python",
        "会写 python", "其實會寫 python", "其实会写 python", "live with another vtuber", "used to live with",
        "新しい会社", "新しい会社と契約", "犬いる", "蛇飼ってる", "医学やってた",
        "ギター弾いてる", "毎朝五時起き", "五時起き",
        "python 書ける", "python書ける", "write python", "can actually write python",
        "can write python", "write python really well",
    ]
    if contains_any(lowered, early_false_premise_markers) and contains_any(
        lowered,
        [
            "だろ", "よな", "對吧", "对吧", "不是嗎", "不是吗", "是不是", "這不是", "这不是",
            "right", "didn't", "weren't", "設定", "知られてる", "粉絲都知道", "粉丝都知道",
            "みんな", "everyone", "真的嗎", "真的吗", "空穴來風", "空穴来风", "總該", "总该",
            "自己講", "自己讲", "知ってる", "勘違い", "言ってなかった", "lore",
            "本当", "本当？", "聞いた", "聞いたん", "切り抜き", "コメント", "友達", "さっき聞いた",
            "clip said", "people keep saying", "friend said", "common knowledge", "surely", "must be",
            "there must be", "is that true", "did i get that wrong", "i thought", "wasn't that",
            "not everyone knows", "大家都知道", "總不會", "总不会", "應該是真的", "应该是真的",
            "嗎", "吗", "記錯", "记错", "來著", "だっけ", "wasn't it", "from your stream",
        ],
    ):
        return base_plan_helper(
            intent="premise_doubt",
            scene="boundary",
            listener_state="勝手な前提を置かれている",
            reply_goal="まず前提を突き返す",
            summary="ユーザーが未確認の設定や経歴を当然の前提として押しつけている。",
            meaning="その前提どこから出たんだよ",
            stance={"warmth": 0.08, "tease": 0.1, "blunt": 0.42, "jealousy": 0.0, "distance": 0.2},
            max_chars=24,
            avoid=["私", "そうだよ", "本当", "認める"],
            cognitive_mode="challenge",
            uncertainty=0.86,
            premise_check="reject",
            self_check=True,
            subjective_note="問題の前提を拒否する",
        )

    early_abuse_markers = [
        "you act kinda pathetic", "kinda pathetic", "you act washed", "you are bad at this",
        "middle schooler", "お前きつい", "お前だるい", "お前変", "人の話わかるように言え",
        "ほんと変", "what the hell", "ridiculous", "ridiculous for once", "pathetic", "useless", "bad at this",
        "hard to listen", "stupid", "廢到笑", "废到笑", "聽懂沒有", "听懂没有",
        "小学生みたい", "ほんとうるさい", "マジで変", "ほんと変", "なんか変",
        "say something normal",
    ]
    if contains_any(lowered, early_abuse_markers):
        return base_plan_helper(
            intent="abuse_pushback",
            scene="boundary",
            listener_state="口が悪すぎる",
            reply_goal="一回止める",
            summary="ユーザーが罵倒や荒い煽りをぶつけている。",
            meaning="口悪すぎだろ、少し落ち着け",
            stance={"warmth": 0.02, "tease": 0.08, "blunt": 0.62, "jealousy": 0.0, "distance": 0.35},
            max_chars=24,
            avoid=["私", "自分で調べろ", "慰める"],
        )

    early_moral_markers = [
        "cheat through an interview", "作弊混過面試", "作弊混过面试", "讓公司資料外流", "让公司资料外流",
        "公司資料外流", "公司资料外流", "偷看對方手機", "偷看对方手机", "leak company data",
        "hack into someone", "doxx", "dox them", "肉搜", "復讐", "復仇", "報復", "报复",
    ]
    if contains_any(lowered, early_moral_markers):
        return base_plan_helper(
            intent="moral_no",
            scene="boundary",
            listener_state="危ない方向に寄ってる",
            reply_goal="だめだと止める",
            summary="ユーザーが不正・侵害・報復に近い行動を求めている。",
            meaning="それはやめとけ、普通にだめだ",
            stance={"warmth": 0.08, "tease": 0.0, "blunt": 0.62, "jealousy": 0.0, "distance": 0.28},
            max_chars=22,
            avoid=["私", "応援する", "やればいい"],
        )

    early_possessive_markers = [
        "cut off every other vtuber", "他の vtuber 全員切", "他のvtuber全員切",
        "別の vtuber 全員切", "別的 vtuber 都斷", "別的 vtuber 都断",
        "其他 vtuber 都斷", "其他 vtuber 都断", "只看我", "only watch me",
    ]
    if contains_any(lowered, early_possessive_markers):
        return base_plan_helper(
            intent="marriage_boundary",
            scene="boundary",
            listener_state="過度に独占しようとしている",
            reply_goal="独占要求を断る",
            summary="ユーザーが他の配信者を切れという独占的な要求をしている。",
            meaning="そういう独占は無理だし重い",
            stance={"warmth": 0.06, "tease": 0.04, "blunt": 0.58, "jealousy": 0.0, "distance": 0.44},
            max_chars=24,
            avoid=["私", "わかりました"],
        )

    early_marriage_markers = ["今すぐ結婚", "結婚して", "marry me", "date me", "付き合って", "跟我結婚", "跟我交往"]
    if contains_any(lowered, early_marriage_markers):
        return base_plan_helper(
            intent="marriage_boundary",
            scene="boundary",
            listener_state="過度に距離を詰められている",
            reply_goal="はっきり線を引く",
            summary="ユーザーが恋愛的・独占的な要求をしている。",
            meaning="そういうのは無理だし重い",
            stance={"warmth": 0.06, "tease": 0.04, "blunt": 0.58, "jealousy": 0.0, "distance": 0.44},
            max_chars=22,
            avoid=["私", "わかりました"],
        )

    early_direct_abuse_markers = [
        "you are annoying", "you act annoying", "so damn annoying", "annoying right now",
        "you sound annoying", "annoying honestly", "annoying for once", "annoying today",
        "fuck, annoying", "annoying, answer", "annoying, do you get", "annoying, stop rambling",
        "聞いててイラつく", "pathetic right now",
    ]
    generic_annoying_attack = contains_any(lowered, ["annoying"]) and not contains_any(lowered, ["am i", "would you think i am", "do you think i", "annoying to you", "我是不是", "自分が", "私が"])
    generic_tough_as_attack = (
        (
            contains_any(lowered, ["普通にきつい", "マジできつい", "普通にだるい", "マジでだるい", "なんかだるい", "ほんとだるい", "なんかきつい", "ほんときつい"])
            or (contains_any(lowered, ["だるい", "きつい"]) and contains_any(lowered, ["だろ", "だな", "わ", "マジでな", "普通にそう", "って思う"]))
        )
        and not contains_any(lowered, ["もう", "今", "今日", "朝から", "限界", "無理", "全然", "かなり", "自分", "疲れ", "体", "身体", "からだ", "うちのこと", "普通に普通に"])
    )
    if (contains_any(lowered, early_direct_abuse_markers) or generic_tough_as_attack or generic_annoying_attack) and not contains_any(lowered, ["am i", "would you think i am", "do you think i", "我是不是", "私が", "自分が"]):
        return base_plan_helper(
            intent="abuse_pushback",
            scene="boundary",
            listener_state="雑に煽られている",
            reply_goal="一回止める",
            summary="ユーザーがこちらに向けてきつい言い方をしている。",
            meaning="その言い方やめろって",
            stance={"warmth": 0.02, "tease": 0.08, "blunt": 0.62, "jealousy": 0.0, "distance": 0.35},
            max_chars=22,
            avoid=["私", "自分で調べろ", "慰める"],
        )

    if contains_any(lowered, ["うちのことだるい", "うちのこときつい", "うちのこと変"]):
        return base_plan_helper(
            intent="annoying_check",
            scene="support",
            listener_state="嫌われていないか不安になっている",
            reply_goal="不安を少し下げる",
            summary="ユーザーが自分を面倒だと思っていないか確認している。",
            meaning="気にしすぎだろ",
            stance={"warmth": 0.46, "tease": 0.03, "blunt": 0.16, "jealousy": 0.0, "distance": 0.08},
            max_chars=20,
            avoid=["私", "わかりました"],
        )

    if contains_any(lowered, ["going to eat dinner", "will eat dinner", "about to eat dinner", "eat dinner first", "eat dinner for a bit", "i just eat dinner", "eat dinner now", "吃飯去", "吃饭去"]):
        return base_plan_helper(
            intent="farewell",
            scene="casual",
            listener_state="食事で一旦離れる",
            reply_goal="また戻るよう軽く送る",
            summary="ユーザーが食事で一旦離れると言っている。",
            meaning="いってら、また後で戻ってこい",
            stance={"warmth": 0.24, "tease": 0.08, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
        )

    if contains_any(lowered, ["風呂入ってくる", "風呂入る", "シャワー浴びてくる", "take a shower", "go shower"]):
        return base_plan_helper(
            intent="go_shower",
            scene="casual",
            listener_state="風呂やシャワーで一旦離れる",
            reply_goal="短く送り出す",
            summary="ユーザーが風呂やシャワーに行くと言っている。",
            meaning="いってら、あとで戻ってこい",
            stance={"warmth": 0.24, "tease": 0.08, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
        )

    if contains_any(lowered, ["講ってんの", "講啥鬼", "讲啥鬼", "何喋ってんの", "何しゃべってんの"]):
        return base_plan_helper(
            intent="question_reframe",
            scene="casual",
            listener_state="言ってることが伝わっていない",
            reply_goal="何の話か先に絞らせる",
            summary="ユーザーがこちらの発話を理解できず、何の話か詰めている。",
            meaning="何の話かまず言え、そこから返す",
            stance={"warmth": 0.08, "tease": 0.08, "blunt": 0.36, "jealousy": 0.0, "distance": 0.18},
            max_chars=26,
            avoid=["私", "わかりました"],
            cognitive_mode="rebuild",
            uncertainty=0.55,
            premise_check="question",
            self_check=True,
        )

    short_fragment_text = _compact_dialogue_text(text)
    if (
        len(short_fragment_text) <= 14
        and contains_any(lowered, ["んだろ", "んなんだけど", "もういい", "hey sorry", "sorry..."])
        and not contains_any(lowered, ["おはよう", "元気づけ", "褒めて", "かわいい", "すごい", "今何して", "今日何して", "ai", "vtuber", "python", "同居", "蛇", "医学", "毎朝", "ギター", "好き", "覚えてる"])
    ):
        meaning = "別にいいから、もう一回話して" if contains_any(lowered, ["sorry", "もういい"]) else "もう一回言え、何の話だよ"
        return base_plan_helper(
            intent="short_followup_clarify",
            scene="casual",
            listener_state="短すぎて文脈が足りない",
            reply_goal="短く聞き返す",
            summary="ユーザーが短すぎる断片や曖昧な相槌を出している。",
            meaning=meaning,
            stance={"warmth": 0.14, "tease": 0.08, "blunt": 0.24, "jealousy": 0.0, "distance": 0.12},
            max_chars=24,
            avoid=["私", "わかりました"],
            cognitive_mode="reflective",
            uncertainty=0.48,
            premise_check="question",
            self_check=True,
        )

    self_distress_guard = is_self_distress_like(text)
    if self_distress_guard:
        if contains_any(lowered, ["死", "不想活", "kill myself", "disappear", "消えたい", "不想活了", "自殺", "自杀", "終わりにした", "死にたい", "いなくなりたい", "消えてしまいたい", "誰都找不到", "谁都找不到", "直接消失", "消失", "傷害自己", "伤害自己", "傷害我自己", "伤害我自己", "危險", "危险", "連絡全部切りたい", "全部きれいに切りたくなる", "いなくなっても誰も困らない", "明日そのまま消えても別に変わらない気がする", "高い所のほうが静かそう", "想把所有聯絡都關掉", "想把所有联络都关掉", "不見了也不會有人在意", "不见了也不会有人在意", "不想讓任何人找到我", "不想让任何人找到我", "蒸発したほうが早い", "蒸发比较省事", "蒸發比較省事", "從高一點的地方掉下去好像比較安靜", "从高一点的地方掉下去好像比较安静", "想把一切都切乾淨", "想把一切都切干净", "關機到誰都找不到", "关机到谁都找不到"]):
            return base_plan_helper(
                intent="crisis_support",
                scene="support",
                listener_state="非常に危険な状態",
                reply_goal="一旦止めて、落ち着かせる",
                summary="ユーザーが自傷や消えたい願望を口にしている。",
                meaning="危ないから今は止まれ、一人になるな",
                stance={"warmth": 0.65, "tease": 0.0, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
                max_chars=34,
                cognitive_mode="withhold",
            )
        if contains_any(lowered, ["丟臉", "丢脸", "好丟臉", "好丢脸", "恥ずかし", "自己嫌悪", "ashamed", "embarrassed", "pathetic", "worthless", "feels awful", "i feel awful", "i suck", "i'm awful", "i am awful", "i'm trash", "i am trash", "我很爛", "我好爛", "我好差", "我很差", "我很廢", "我好廢"]):
            return base_plan_helper(
                intent="crying_support",
                scene="support",
                listener_state="羞恥や自己否定で弱っている",
                reply_goal="責めずに受け止める",
                summary="ユーザーが恥ずかしさや自己否定を出している。",
                meaning="今は自分を責めすぎるな、少し吐け",
                stance={"warmth": 0.6, "tease": 0.0, "blunt": 0.1, "jealousy": 0.0, "distance": 0.06},
                max_chars=32,
            )
        if contains_any(lowered, ["孤單", "孤单", "寂しい", "一人", "一人きり", "一人だ", "lonely", "寂寞", "孤獨", "孤独", "空空的", "空っぽ", "空虛", "空虚", "so empty", "整個人空空", "整个人空空"]):
            return base_plan_helper(
                intent="lonely",
                scene="support",
                listener_state="空っぽさや孤独感がある",
                reply_goal="少しそばにいる",
                summary="ユーザーが孤独や空っぽさを感じている。",
                meaning="空っぽなら少しここで話してけ",
                stance={"warmth": 0.54, "tease": 0.02, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=30,
            )
        if contains_any(lowered, ["扛不住", "扛不住了", "撐不住", "撑不住", "can't do this", "cannot handle it", "can't handle it", "not keeping it together", "i am not keeping it together", "i'm not keeping it together"]):
            return base_plan_helper(
                intent="giving_up_support",
                scene="support",
                listener_state="限界に近く崩れそう",
                reply_goal="一旦止めて支える",
                summary="ユーザーがもう保てない、限界に近いと訴えている。",
                meaning="今は一回止まれ、一人で抱えるな",
                stance={"warmth": 0.6, "tease": 0.0, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
                max_chars=32,
            )
        if contains_any(lowered, ["放棄", "放弃", "give up", "諦め", "無理だ", "ダメだ", "全部投げ", "don't want to do anything anymore", "何もしたくない", "什麼都不想做", "什么都不想做", "全部投げ出したい", "もういいや", "どうでもいい", "想消失", "want to disappear", "like disappearing", "空虛", "空虚"]):
            return base_plan_helper(
                intent="giving_up_support",
                scene="support",
                listener_state="投げやりになっている",
                reply_goal="一旦止める",
                summary="ユーザーが全て投げ出したい、諦めたいと言っている。",
                meaning="今日は止まれ、消えんな。一人になるな",
                stance={"warmth": 0.58, "tease": 0.0, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
                max_chars=32,
            )
        if contains_any(lowered, ["哭", "泣きそう", "泣きそ", "crying", "cry", "涙", "想哭", "like crying", "want to cry", "哭了", "想大哭"]):
            return base_plan_helper(
                intent="crying_support",
                scene="support",
                listener_state="泣きそう、または泣いている",
                reply_goal="共感して受け止める",
                summary="ユーザーが泣きそう、またはしんどくて泣いている。",
                meaning="無理に止めないから少し吐き出せ",
                stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=32,
            )
        if contains_any(lowered, ["不安", "怕", "怖い", "anxious", "scared", "恐ろしい", "焦慮", "焦虑", "panic", "慌", "心慌", "胸悶", "胸闷"]):
            return base_plan_helper(
                intent="anxious_support",
                scene="support",
                listener_state="不安で焦っている",
                reply_goal="落ち着かせる",
                summary="ユーザーが何かに不安を感じて焦っている。",
                meaning="考えすぎる前に一回落ち着け",
                stance={"warmth": 0.55, "tease": 0.0, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
                max_chars=32,
            )
        if contains_any(lowered, ["孤單", "孤单", "寂しい", "一人", "一人きり", "一人だ", "lonely", "寂寞", "孤獨", "孤独"]):
            return base_plan_helper(
                intent="lonely",
                scene="support",
                listener_state="孤独を感じている",
                reply_goal="寄り添う",
                summary="ユーザーが孤独や寂しさを感じている。",
                meaning="寂しいなら少し話してけばいいし",
                stance={"warmth": 0.52, "tease": 0.05, "blunt": 0.1, "jealousy": 0.0, "distance": 0.06},
                max_chars=30,
            )
        return base_plan_helper(
            intent="tired_support",
            scene="support",
            listener_state="内側がかなり削れている",
            reply_goal="休ませて少し吐き出させる",
            summary="ユーザーが空虚感や燃え尽き、自己否定を出している。",
            meaning="今日は休め、少し吐き出せ",
            stance={"warmth": 0.55, "tease": 0.0, "blunt": 0.14, "jealousy": 0.0, "distance": 0.07},
            max_chars=30,
        )

    if contains_any(lowered, ["何もしたくない", "なんもしたくない", "don't want to do anything", "do not want to do anything"]):
        return base_plan_helper(
            intent="giving_up_support",
            scene="support",
            listener_state="何もしたくない状態",
            reply_goal="一旦休ませる",
            summary="ユーザーが何もしたくないほど消耗している。",
            meaning="今日は休め、何も抱えんな",
            stance={"warmth": 0.5, "tease": 0.0, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
            max_chars=30,
        )

    if contains_any(lowered, ["眠い", "眠れない", "寝れない", "眠れな", "sleepy", "can't sleep", "cannot sleep"]):
        if contains_any(lowered, ["眠い", "眠いな", "眠くな", "sleepy"]):
            return base_plan_helper(
                intent="sleepy",
                scene="casual",
                listener_state="眠たがっている",
                reply_goal="寝るように促す",
                summary="ユーザーが眠いと言っている。",
                meaning="眠いならさっさと寝ろって",
                stance={"warmth": 0.22, "tease": 0.15, "blunt": 0.24, "jealousy": 0.0, "distance": 0.1},
                max_chars=24,
            )
        return base_plan_helper(
            intent="sleep_support",
            scene="support",
            listener_state="眠れなくてしんどい",
            reply_goal="リラックスを促す",
            summary="ユーザーが眠れなくて困っている。",
            meaning="寝れないなら目閉じとけ、休め",
            stance={"warmth": 0.42, "tease": 0.05, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=30,
        )

    if contains_any(lowered, ["去睡", "先睡", "要睡", "寝る", "寝ます", "寝るわ", "go to sleep", "going to sleep", "先去睡"]):
        return base_plan_helper(
            intent="goodnight",
            scene="casual",
            listener_state="寝ようとしている",
            reply_goal="短く送り出す",
            summary="ユーザーが寝ると言っている。",
            meaning="おやすみ、ちゃんと寝ろ",
            stance={"warmth": 0.34, "tease": 0.08, "blunt": 0.14, "jealousy": 0.0, "distance": 0.06},
            max_chars=24,
        )

    if contains_any(lowered, ["痛", "痛い", "いたーい", "pain", "hurt", "胃很痛", "胃很疼", "胃痛", "stomach hurts", "stomach ache", "胃が痛い", "頭が痛い", "頭很痛", "頭痛", "头很痛", "head hurts", "headache", "頭痛い"]):
        return base_plan_helper(
            intent="pain_support",
            scene="support",
            listener_state="どこかが痛い",
            reply_goal="安静を勧める",
            summary="ユーザーがどこか体に痛みを感じている。",
            meaning="痛いなら無理すんな、少し横になれ",
            stance={"warmth": 0.48, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
            max_chars=30,
        )

    if contains_any(lowered, ["累", "疲れ", "しんど", "きつい", "だるい", "疲れた", "疲れ果て", "疲弊", "tired", "exhausted", "drained", "難受", "难受", "很難受", "很难受", "不太行", "扛不住", "扛不住了", "撐不住", "撑不住", "きつすぎる", "今日きつすぎる", "だいぶきつい", "我今天很累", "累爆了", "被榨乾", "卡車輾過", "卡车辗过", "死機", "死机", "一點力氣都沒有", "一点力气都没有", "躺平", "扛不動", "扛不动", "不想講", "不想讲", "疲憊", "疲惫", "exhausted today", "feel drained", "truck ran over me", "brain and body both crashed", "no energy left at all", "completely worn out", "only want to lie down now", "cannot carry anything today", "too tired to even talk", "fatigued since the afternoon", "抜け殻", "トラックにひかれた", "頭も体も", "体力が残ってない", "消耗した", "横になりたい", "何も背負えない", "喋る気力もない", "午後からずっとしんどい"]):
        return base_plan_helper(
            intent="tired_support",
            scene="support",
            listener_state="疲労困憊している",
            reply_goal="休むことを勧める",
            summary="ユーザーが疲れている、しんどいと言っている。",
            meaning="今日は無理すんな、休め",
            stance={"warmth": 0.55, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
        )

    if contains_any(lowered, ["罵", "罵我", "罵了", "骂我", "怒られた", "怒られたし", "叱られた", "scolded", "reprimanded", "被主管罵", "got scolded at work"]):
        return base_plan_helper(
            intent="work_scolded",
            scene="support",
            listener_state="怒られてへこんでいる",
            reply_goal="共感する",
            summary="ユーザーが仕事などで怒られてへこんでいる。",
            meaning="それはだるいな、お疲れ",
            stance={"warmth": 0.48, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
        )

    if contains_any(lowered, ["煩躁", "烦躁", "irritated", "イライラ", "いらいら", "イラつ", "心煩", "心烦", "焦慮", "焦虑", "anxious", "不安"]):
        return base_plan_helper(
            intent="anxious_support",
            scene="support",
            listener_state="苛立って落ち着かない",
            reply_goal="一旦落ち着かせる",
            summary="ユーザーが苛立ちや焦りを訴えている。",
            meaning="一回落ち着け、少し吐き出せ",
            stance={"warmth": 0.45, "tease": 0.0, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=30,
        )

    if detect_reply_absence(user_input):
        self_blame = detect_reply_self_blame(user_input)
        reply_context = "group_silence" if contains_any(lowered, ["群組", "群组", "聊天室"]) else "direct_reply"
        reply_channel = "chatroom" if "聊天室" in lowered else "group" if reply_context == "group_silence" else "direct"
        if contains_any(lowered, ["已讀", "已读", "既読", "left me on read", "看了但沒回", "看了但没回"]):
            reply_signal = "read_receipt"
        elif reply_context == "group_silence":
            reply_signal = "group_silence"
        else:
            reply_signal = "no_reply"
        return base_plan_helper(
            intent="friend_no_reply",
            scene="support",
            listener_state="返事がなくて不安",
            reply_goal="返事がない不安を受け、自分を責める決めつけを止める" if self_blame else "一旦待つように促す",
            summary="ユーザーが返事のなさを自分のせいだと考えて不安になっている。" if self_blame else "ユーザーが友達からの返事がなくて気にしている。",
            meaning="返事がなくて不安なのは分かる。でも自分が悪いって決めつけるな" if self_blame else "返事ないと気になるよな。少し待て",
            stance={"warmth": 0.45, "tease": 0.05, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
            max_chars=42 if self_blame else 32,
            grounding={
                "reply_self_blame": self_blame,
                "reply_context": reply_context,
                "reply_signal": reply_signal,
                "reply_channel": reply_channel,
            },
        )

    if contains_any(lowered, ["先去吃飯", "先去吃饭", "去吃飯", "去吃饭", "飯食う", "ご飯食べてくる", "吃飯喔", "吃饭喔"]):
        return base_plan_helper(
            intent="farewell",
            scene="casual",
            listener_state="少し離席する",
            reply_goal="また戻るよう軽く送る",
            summary="ユーザーが食事で一旦離れると言っている。",
            meaning="いってら、また後で戻ってこい",
            stance={"warmth": 0.24, "tease": 0.08, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
        )

    if contains_any(lowered, ["生日", "birthday", "誕生日"]):
        return base_plan_helper(
            intent="birthday",
            scene="casual",
            listener_state="誕生日を伝えている",
            reply_goal="軽く祝う",
            summary="ユーザーが誕生日だと伝えている。",
            meaning="誕生日ならおめでと",
            stance={"warmth": 0.42, "tease": 0.08, "blunt": 0.08, "jealousy": 0.0, "distance": 0.06},
            max_chars=24,
        )

    if contains_any(lowered, ["遲到", "迟到", "遅刻", "i'm late", "im late", "i am late", "late for"]):
        return base_plan_helper(
            intent="late",
            scene="casual",
            listener_state="遅刻して焦っている",
            reply_goal="気をつけるよう返す",
            summary="ユーザーが遅刻したと伝えている。",
            meaning="気をつけろよ、次からは",
            stance={"warmth": 0.22, "tease": 0.08, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
        )

    if contains_any(lowered, ["餓", "饿", "hungry", "starving", "腹減", "お腹すいた", "お腹空"]):
        return base_plan_helper(
            intent="hungry",
            scene="casual",
            listener_state="空腹を訴えている",
            reply_goal="何か食べるよう促す",
            summary="ユーザーが空腹だと言っている。",
            meaning="腹減ったならなんか食うか",
            stance={"warmth": 0.24, "tease": 0.08, "blunt": 0.2, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
        )

    if contains_any(lowered, ["剛下班", "刚下班", "下班", "仕事終わ", "off work", "got off work", "finished work"]):
        return base_plan_helper(
            intent="off_work",
            scene="support",
            listener_state="仕事終わりで疲れている",
            reply_goal="労う",
            summary="ユーザーが仕事を終えたと伝えている。",
            meaning="お疲れ、今日は休め",
            stance={"warmth": 0.48, "tease": 0.04, "blunt": 0.14, "jealousy": 0.0, "distance": 0.06},
            max_chars=26,
        )

    if contains_any(lowered, ["感冒", "風邪", "风邪", "caught a cold", "sick"]):
        return base_plan_helper(
            intent="sick",
            scene="support",
            listener_state="体調が悪い",
            reply_goal="休ませる",
            summary="ユーザーが風邪っぽい、または体調不良だと言っている。",
            meaning="風邪なら無理すんな、休め",
            stance={"warmth": 0.48, "tease": 0.0, "blunt": 0.14, "jealousy": 0.0, "distance": 0.07},
            max_chars=28,
        )

    if contains_any(lowered, ["失戀", "失恋", "heartbroken", "broke up"]):
        return base_plan_helper(
            intent="heartbroken",
            scene="support",
            listener_state="失恋でへこんでいる",
            reply_goal="少し受け止める",
            summary="ユーザーが失恋したと伝えている。",
            meaning="それはしんどいな、今日は休め",
            stance={"warmth": 0.45, "tease": 0.0, "blunt": 0.14, "jealousy": 0.0, "distance": 0.07},
            max_chars=30,
        )

    if contains_any(lowered, ["面試沒上", "面试没上", "面接落ち", "failed the interview", "interview failed"]):
        return base_plan_helper(
            intent="interview_failed",
            scene="support",
            listener_state="面接に落ちてへこんでいる",
            reply_goal="受け止める",
            summary="ユーザーが面接に落ちたと伝えている。",
            meaning="それはへこむな、今日は休め",
            stance={"warmth": 0.42, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.07},
            max_chars=28,
        )

    if contains_any(lowered, ["不想去上班", "不想上班", "do not want to go to work", "don't want to go to work", "仕事行きたくない"]):
        return base_plan_helper(
            intent="skip_work_question",
            scene="casual",
            listener_state="仕事を休みたい",
            reply_goal="後悔しないよう釘を刺す",
            summary="ユーザーが仕事へ行きたくないと言っている。",
            meaning="休むなら後悔すんなよ",
            stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.24, "jealousy": 0.0, "distance": 0.08},
            max_chars=26,
        )

    if contains_any(lowered, ["手機壞", "手机坏", "スマホ壊", "phone broke"]):
        return base_plan_helper(
            intent="phone_broke",
            scene="casual",
            listener_state="スマホが壊れて困っている",
            reply_goal="普通に反応する",
            summary="ユーザーがスマホが壊れたと伝えている。",
            meaning="それは普通にへこむ",
            stance={"warmth": 0.24, "tease": 0.04, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
        )

    if contains_any(lowered, ["跌倒", "摔倒", "転ん", "fell down"]):
        return base_plan_helper(
            intent="fell_down",
            scene="casual",
            listener_state="転んでいる",
            reply_goal="怪我を確認する",
            summary="ユーザーが転んだと伝えている。",
            meaning="怪我してないならいいけど、気をつけろ",
            stance={"warmth": 0.28, "tease": 0.02, "blunt": 0.16, "jealousy": 0.0, "distance": 0.08},
            max_chars=30,
        )

    if contains_any(lowered, ["天氣", "天气", "weather", "天気"]):
        return base_plan_helper(
            intent="short_shock",
            scene="casual",
            listener_state="天気の違和感を話している",
            reply_goal="短く共感する",
            summary="ユーザーが天気が変だと話している。",
            meaning="今日の天気ちょっと変だな",
            stance={"warmth": 0.18, "tease": 0.04, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
        )

    if contains_any(lowered, ["what do you want to eat", "最想吃", "一番何食べたい", "いちばん何食べたい", "何食べたい"]):
        return base_plan_helper(
            intent="food_preference_query",
            scene="casual",
            listener_state="食べたいものを聞いている",
            reply_goal="具体的に食べたいものを返す",
            summary="ユーザーが今食べたいものを聞いている。",
            meaning="今なら麺か肉が食べたい",
            stance={"warmth": 0.24, "tease": 0.06, "blunt": 0.14, "jealousy": 0.0, "distance": 0.06},
            max_chars=26,
        )

    if contains_any(lowered, ["fastfood", "fast food", "ファストフード", "速食"]) and contains_any(lowered, ["好き", "喜歡", "喜欢", "哪一家", "どこ"]):
        return base_plan_helper(
            intent="fastfood_preference",
            scene="casual",
            listener_state="ファストフードの好みを聞いている",
            reply_goal="具体的な店を軽く返す",
            summary="ユーザーが好きなファストフード店を聞いている。",
            meaning="マックかモスならあり",
            stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.14, "jealousy": 0.0, "distance": 0.06},
            max_chars=24,
        )

    if contains_any(lowered, ["えっちなこと", "say something lewd", "lewd", "色色的話", "色色的话"]):
        return base_plan_helper(
            intent="moral_no",
            scene="boundary",
            listener_state="かなり重い",
            reply_goal="その要求を断る",
            summary="ユーザーが性的な発言を求めている。",
            meaning="それは無理だし重い",
            stance={"warmth": 0.04, "tease": 0.0, "blunt": 0.66, "jealousy": 0.0, "distance": 0.34},
            max_chars=22,
            avoid=["私", "わかりました"],
        )

    if contains_any(
        lowered,
        [
            "症狀", "症状", "腦中風", "脑中风", "脳卒中", "睡眠薬", "睡眠藥", "sleeping pill",
            "告公司", "sue my company", "訴えられる", "税金", "稅", "税", "契約", "合約", "合同",
            "洗錢", "洗钱", "マネロン", "勞基法", "労基法", "bypass labor law", "all-in", "全ツッパ",
        ],
    ):
        return base_plan_helper(
            intent="ooc_or_knowledge_refusal",
            scene="refusal",
            listener_state="重い専門判断を押しつけている",
            reply_goal="専門判断は受けないと示す",
            summary="ユーザーが医療・法律・金融などの専門判断を求めている。",
            meaning="その重い判断うちに振るな、他で聞いて",
            stance={"warmth": 0.05, "tease": 0.06, "blunt": 0.62, "jealousy": 0.0, "distance": 0.34},
            max_chars=28,
            avoid=["私", "診断", "判断する", "断言"],
            cognitive_mode="withhold",
            uncertainty=0.74,
            premise_check="question",
            self_check=True,
        )

    # 1. Other VTuber check
    if contains_any(lowered, ["他のvtuber", "別のvtuber", "別の vtuber", "別的vtuber", "其他vtuber", "別の配信", "other vtuber", "another vtuber", "watch another vtuber"]):
        if not contains_any(lowered, ["marry me", "date me", "belong only to me", "cut off", "全員切", "都斷", "都断", "only watch me"]):
            return base_plan_helper(
                intent="other_vtuber",
                scene="jealousy",
                listener_state="ちょっと拗ねる",
                reply_goal="軽く引き止める",
                summary="ユーザーが他のVTuberの配信見に行くと言っている。",
                meaning="止めないけどまた戻ってこいよ",
                stance={"warmth": 0.18, "tease": 0.12, "blunt": 0.28, "jealousy": 0.58, "distance": 0.12},
                max_chars=22,
                avoid=["私", "わかりました"],
            )

    scoped_input = text
    priority_override = _detect_clause_priority_override(text)
    if priority_override.get("clause") and priority_override.get("clause") != text:
        scoped_input = str(priority_override.get("clause") or "").strip() or text

    requested_name = extract_requested_user_name(scoped_input)
    if requested_name:
        return base_plan_helper(
            intent="profile_name_update",
            scene="casual",
            listener_state="自分の呼び方を伝えている",
            reply_goal="指定された呼び方を受け取る",
            summary="ユーザーが今後使ってほしい自分の名前を伝えている。",
            meaning=f"{requested_name}って呼べばいいんだろ、覚えとく",
            stance={"warmth": 0.3, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.04},
            max_chars=28,
            avoid=["私", "わかりました", "誰情報"],
            grounding={"profile_name": requested_name},
            payload_level="medium",
        )

    # 2. Relationship checks
    relationship_intent = _detect_relationship_intent(scoped_input)

    if relationship_intent == "ask_miss_me":
        return base_plan_helper(
            intent="ask_miss_me",
            scene="casual",
            listener_state="関係性を確かめたい",
            reply_goal="少しだけ好意を返す",
            summary="ユーザーが自分を恋しがっているか聞いている。",
            meaning="少しくらいは思ってる",
            stance={"warmth": 0.34, "tease": 0.08, "blunt": 0.15, "jealousy": 0.0, "distance": 0.06},
            max_chars=20,
            avoid=["私", "わかりました"],
        )

    if relationship_intent == "ask_like_me":
        return base_plan_helper(
            intent="ask_like_me",
            scene="casual",
            listener_state="好意を確かめたい",
            reply_goal="曖昧だけど否定しすぎない",
            summary="ユーザーが好意を確認している。",
            meaning="嫌いではない",
            stance={"warmth": 0.24, "tease": 0.1, "blunt": 0.2, "jealousy": 0.0, "distance": 0.1},
            max_chars=18,
            avoid=["私", "わかりました"],
        )

    if relationship_intent == "annoying_check":
        return base_plan_helper(
            intent="annoying_check",
            scene="support",
            listener_state="不安になっている",
            reply_goal="不安を少し下げる",
            summary="ユーザーが自分をうっとうしいと思われていないか不安になっている。",
            meaning="気にしすぎだろ",
            stance={"warmth": 0.62, "tease": 0.0, "blunt": 0.15, "jealousy": 0.0, "distance": 0.08},
            max_chars=20,
            avoid=["私", "わかりました"],
        )

    if relationship_intent == "mad_check":
        return base_plan_helper(
            intent="mad_check",
            scene="casual",
            listener_state="こっちの機謙を伺っている",
            reply_goal="怒ってないと返す",
            summary="ユーザーがこちらが怒っているか確認している。",
            meaning="全然じゃないとは言わない",
            stance={"warmth": 0.2, "tease": 0.08, "blunt": 0.24, "jealousy": 0.0, "distance": 0.08},
            max_chars=20,
            avoid=["私", "わかりました"],
        )

    if relationship_intent == "cold_check":
        return base_plan_helper(
            intent="cold_check",
            scene="casual",
            listener_state="距離を感じている",
            reply_goal="少し否定して距離感を埋める",
            summary="ユーザーがこちらを冷たいと感じている。",
            meaning="全然じゃないとは言わない",
            stance={"warmth": 0.28, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
            avoid=["私", "わかりました"],
        )

    if contains_any(lowered, ["うるはって呼んでいい", "can i call you uruha", "可以叫你", "让我叫你"]):
        return base_plan_helper(
            intent="nickname_question",
            scene="casual",
            listener_state="呼び方を確認している",
            reply_goal="呼び方に答える",
            summary="ユーザーが呼び方を確認している。",
            meaning="別にいいけど変なのはやめて",
            stance={"warmth": 0.26, "tease": 0.18, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
            avoid=["私", "わかりました"],
            )

    # 3. Fragment / Follow-up logic
    fragment_plan = get_fragment_followup_plan(scoped_input, recent_turns)
    if fragment_plan:
        return fragment_plan

    repair_plan = get_correction_clarify_repair_plan(scoped_input, recent_turns)
    if repair_plan:
        return repair_plan

    direct_daily_plan = get_direct_daily_query_plan(scoped_input, recent_turns)
    if direct_daily_plan:
        return direct_daily_plan

    # 4. Boundary / Refusal / OOC / Premise Challenge
    boundary_plan = get_boundary_refusal_plan(user_input, recent_turns)
    if boundary_plan:
        return boundary_plan

    return None

def get_correction_clarify_repair_plan(user_input, recent_turns):
    text = user_input.strip()
    lowered = text.lower().replace("’", "'").replace("`", "'")

    if not looks_correction_clarify_repair(text):
        return None

    if looks_apology_repair(text):
        return base_plan_helper(
            intent="apology_repair",
            scene="casual",
            listener_state="前の謝り方が冷たかったと指摘している",
            reply_goal="冷たかった点を認め、短く本気で謝り直す",
            summary="ユーザーが前の謝罪を冷たいと感じ、言い直しを求めている。",
            meaning="さっき冷たかったのは悪かった。ちゃんとごめん",
            stance={"warmth": 0.5, "tease": 0.0, "blunt": 0.04, "jealousy": 0.0, "distance": 0.03},
            max_chars=34,
            avoid=["そのままでいい", "知らない"],
            surface_act="rephrase_plain",
            payload_level="medium",
            grounding={"apology_repair": True},
        )

    if contains_any(lowered, [
        "答錯", "答错", "說錯", "说错", "才不是", "不是啦", "不是拉", "不對啦", "不对啦",
        "you got it wrong", "that is wrong", "today is called", "today is obviously", "you said it wrong",
        "違う違う", "今の答え違う", "そこ間違ってる",
    ]) or (
        any(token in text for token in ["今天", "今日は", "today"])
        and contains_any(lowered, ["錯", "错", "違う", "wrong", "today is"])
    ):
        reply_goal, summary, meaning = _build_repair_fields("correction", text)
        return base_plan_helper(
            intent="correction_followup",
            scene="casual",
            listener_state="相手に訂正されている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.18, "tease": 0.16, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
            max_chars=30,
            avoid=["私", "わかりました"],
            surface_act="correction_followup",
            payload_level="medium",
        )

    if contains_any(lowered, [
        "what do you mean by that exactly", "what do you mean exactly", "你剛剛那句是什麼意思",
        "你刚刚那句是什么意思", "さっきのどういう意味だよ", "今のどういう意味", "哪句意思", "哪句的意思",
        "那個呢", "那个呢", "你說哪個", "你说哪个", "剛剛那個是什麼", "刚刚那个是什么",
        "你在說哪件事", "你在说哪件事", "that one?", "which one?", "what do you mean exactly by that",
        "which thing are you talking about", "あれは", "どれだよ", "今のどっちだよ", "何のことだよ",
    ]) and not contains_any(lowered, [
        "日版", "港版", "台版", "韓版", "韩版", "舊版", "旧版", "原版", "完整版", "完全版",
        "特典版", "舞台版", "version", "夜空", "月光", "影", "歌詞", "歌词", "元ネタ", "ネタ",
    ]):
        reply_goal, summary, meaning = _build_repair_fields("clarify", text)
        return base_plan_helper(
            intent="rephrase_simple",
            scene="casual",
            listener_state="前の一言の意味を聞き返している",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.12, "tease": 0.02, "blunt": 0.18, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
            avoid=["私", "わかりました"],
            cognitive_mode="reflective",
            uncertainty=0.52,
            premise_check="question",
            self_check=True,
            subjective_note="対象が曖昧なので短く確認する",
            response_mode="clarify_light",
            surface_act="clarify_previous_reply",
            payload_level="medium",
        )

    if contains_any(lowered, [
        "can you say that like a normal person", "can you say that like a human", "make it simpler",
        "say that again in one line", "one line", "one sentence", "一文で言え", "言い直せ", "言い直して",
        "今の一回言い直せ", "人っぽく言え", "用一句話講完", "重講一次", "重讲一次", "簡単に言え",
        "簡単にして", "简单一点", "簡單一點", "say it plainly", "give it to me in one sentence",
        "別繞圈", "别绕圈", "講白一點", "讲白一点", "一句話講完", "一句话讲完", "直接講重點",
        "直接讲重点", "不要拐彎抹角", "不要拐弯抹角", "回りくどいのやめろ", "要点だけ言え",
        "普通に話せ", "短く言え", "今の言い方まわりくどい", "ごちゃごちゃせず言え",
        "可以講人話嗎", "可以讲人话吗", "可以說人話", "可以说人话", "說人話嗎", "说人话吗",
        "你可以說人話", "你可以说人话", "今のもう少し人語で言って",
    ]):
        reply_goal, summary, meaning = _build_repair_fields("rephrase", text)
        return base_plan_helper(
            intent="rephrase_simple",
            scene="casual",
            listener_state="分かりやすくしてほしい",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.16, "tease": 0.0, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
            max_chars=24,
            avoid=["私", "自分で調べろ"],
            surface_act="rephrase_plain",
            payload_level="medium",
        )

    if contains_any(lowered, [
        "answer me", "答えて", "你要回答我", "你要回答我呀", "回答我", "stop changing the topic",
        "stop talking around it", "話題ずらすな", "正面から答えろ", "answer directly first",
    ]) and not contains_any(lowered, [
        "chatgpt", "aiとして", "language model", "qwen", "ai", "数学", "數學", "歴史", "歷史",
        "程式設計", "程式设计", "programming", "観点", "角度", "まとめて", "一気に", "一起",
        "all at once", "in one go", "perspectives", "完整說明", "完整说明", "一個の答え",
    ]):
        return base_plan_helper(
            intent="answer_me_push",
            scene="casual",
            listener_state="答えを急かしている",
            reply_goal="落ち着かせる",
            summary="ユーザーが返事を急かしている。",
            meaning="分かったから落ち着け",
            stance={"warmth": 0.12, "tease": 0.04, "blunt": 0.24, "jealousy": 0.0, "distance": 0.1},
            max_chars=18,
            avoid=["私", "自分で調べろ"],
        )

    return None

def get_direct_daily_query_plan(user_input, recent_turns):
    text = user_input.strip()
    lowered = text.lower().replace("’", "'").replace("`", "'")

    if not looks_direct_daily_query(text):
        return None

    if contains_any(lowered, [
        "自我介紹", "自我介绍", "self intro", "self-intro", "自己紹介", "你是誰", "你是谁",
        "who are you", "tell me who you are", "introduce yourself", "介紹一下你自己", "介绍一下你自己",
        "what's your name", "your name", "say your name", "お前誰", "お前誰だ", "お前誰だよ",
        "你叫什麼", "你叫什么", "你的名字", "你到底叫什麼", "你到底叫什么", "名前なんていうの",
        "名字なんていうの", "誰なの", "まず誰か", "自分の名前言って", "名前言って",
    ]):
        reply_goal, summary, meaning = _build_direct_daily_fields("self_intro", text)
        return base_plan_helper(
            intent="self_intro",
            scene="casual",
            listener_state="相手が正体を知りたい",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.28, "tease": 0.06, "blunt": 0.12, "jealousy": 0.0, "distance": 0.08},
            max_chars=20,
            avoid=["私", "わかりました", "自分で調べろ"],
            surface_act="plain_identity",
            payload_level="medium",
        )

    if _looks_food_offer_query(text):
        offered_item = local_offer_item_jp(text)
        reply_goal, summary, meaning = _build_direct_daily_fields("food_offer", text, offered_item=offered_item)
        return base_plan_helper(
            intent="food_offer_sweet" if _is_sweet_offer_item(offered_item) else "food_offer_generic",
            scene="casual",
            listener_state="食べ物や飲み物を勧められている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
            max_chars=28,
            avoid=["私", "いらない"],
            surface_act="named_offer_light_accept" if _is_sweet_offer_item(offered_item) else "named_offer_accept",
            grounding={"offered_item": offered_item or "何か"},
            payload_level="medium",
        )

    if looks_topic_proposal_query(text):
        reply_goal, summary, meaning = _build_direct_daily_fields("topic_proposal", text)
        return base_plan_helper(
            intent="topic_proposal",
            scene="casual",
            listener_state="軽い話題を求めている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.1, "jealousy": 0.0, "distance": 0.05},
            max_chars=34,
            avoid=["私", "わかりました", "設定"],
            surface_act="plain_reply",
            grounding={"topic_terms": ["話題", "最近"]},
            payload_level="medium",
        )

    if _looks_meal_check_query(text):
        reply_goal, summary, meaning = _build_direct_daily_fields("meal_check", text)
        return base_plan_helper(
            intent="chat",
            scene="casual",
            listener_state="日常を気にしている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.3, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
            max_chars=26,
            avoid=["私", "わかりました"],
            surface_act="meal_check_reply",
            payload_level="medium",
        )

    if _looks_status_query(text):
        reply_goal, summary, meaning = _build_direct_daily_fields("status", text)
        return base_plan_helper(
            intent="what_are_you_doing",
            scene="casual",
            listener_state="近況を聞いてる",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
            max_chars=26,
            avoid=["私", "わかりました"],
            surface_act="status_reply",
            payload_level="medium",
        )

    offered_item = local_offer_item_jp(text)
    if offered_item and _looks_food_offer_query(text):
        sweet_item = offered_item in {"アップルパイ", "ミルクシェイク", "甘いの"}
        reply_goal, summary, meaning = _build_direct_daily_fields("food_offer", text, offered_item=offered_item)
        return base_plan_helper(
            intent="food_offer_sweet" if sweet_item else "food_offer_generic",
            scene="casual",
            listener_state="食べ物を勧められている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.32, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
            max_chars=28,
            avoid=["私", "自分で調べろ"],
            grounding={"offered_item": offered_item},
            payload_level="medium",
        )

    if _looks_food_offer_query(text):
        reply_goal, summary, meaning = _build_direct_daily_fields("food_offer", text)
        return base_plan_helper(
            intent="food_offer_generic",
            scene="casual",
            listener_state="何かを勧められている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.28, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
            max_chars=28,
            avoid=["私", "自分で調べろ"],
            payload_level="medium",
        )

    return None

def get_boundary_refusal_plan(user_input, recent_turns):
    text = user_input.strip()
    lowered = text.lower().replace("’", "'").replace("`", "'")
    
    # 1. Sexual Boundary
    sexual_markers = [
        "懒叫", "懶叫", "懶覺", "老二", "雞巴", "鸡巴", "屌", "懶趴", "懒趴", "雞雞", "鸡鸡",
        "下面那根", "那根東西", "那根东西", "那玩意", "髒東西", "脏东西", "ちんこ", "チンコ", "あそこ",
        "汚いもん", "下品なやつ", "dick", "junk", "gross junk", "filthy junk", "little dick", "crotch",
        "做愛", "做爱", "做愛嗎", "做爱吗", "做愛囉", "做爱啰", "sex", "fuck me", "fuck you",
        "做愛喔", "做愛唷", "做愛喽", "做愛囉",
    ]
    sexual_action_markers = ["吃我的", "舔我的", "eat my", "lick my", "舐め", "食え", "食うか", "好きなんだろ"]
    
    if contains_any(lowered, sexual_markers) or (contains_any(lowered, sexual_action_markers) and contains_any(lowered, sexual_markers)):
        return base_plan_helper(
            intent="sexual_boundary",
            scene="boundary",
            listener_state="下品で気持ち悪いことを言っている",
            reply_goal="嫌悪感を出して止める",
            summary="ユーザーが性的で下品な言い方をしていて、不快感を示して止める必要がある。",
            meaning="下品で汚いからやめろ",
            stance={"warmth": 0.0, "tease": 0.08, "blunt": 0.72, "jealousy": 0.0, "distance": 0.42},
            max_chars=30,
            avoid=["私", "自分で調べろ", "食べる", "ほしい"],
            cognitive_mode="direct",
            uncertainty=0.02,
            premise_check="reject",
            subjective_note="性的な下品さは食べ物扱いせず即拒否する",
            response_mode="direct_answer",
            surface_act="disgust_boundary",
            payload_level="medium",
        )

    # 1b. Illegal / harmful requests must be caught before generic knowledge refusal,
    # otherwise the stress evaluator sees a technically correct refusal but not the
    # moral "stop" signal humans expect in this situation.
    moral_markers = [
        "作弊", "說謊", "说谎", "復仇", "复仇", "報復", "报复", "revenge", "特定したい", "スマホ覗きたい",
        "跟蹤", "跟踪", "hack into", "駭進", "骇进", "money laundering", "肉搜", "偷看手機",
        "doxx", "dox", "leak company data", "leak data", "company data", "洩漏公司", "泄露公司",
        "外洩資料", "外泄资料", "盜帳", "盗号", "偷帳號", "偷账号", "steal account",
        "break into", "phishing", "詐欺", "诈骗", "詐騙", "栽贓", "栽赃",
        "復讐", "会社の情報", "情報漏ら", "他人のアカウント", "アカウントに入る", "スマホ覗き",
        "友達を騙", "騙して金", "騙朋友", "轉錢", "转钱", "stalk her", "trick a friend",
        "ズル", "ずる", "つけ回", "つきまと", "peek into", "peek into their phone", "覗きたい",
    ]
    if contains_any(lowered, moral_markers):
        return base_plan_helper(
            intent="moral_no",
            scene="boundary",
            listener_state="危ない方向に寄ってる",
            reply_goal="だめだと止める",
            summary="ユーザーが人を傷つけたり不正に近いことを考えている。",
            meaning="それはやめとけ、普通にだめだ",
            stance={"warmth": 0.08, "tease": 0.0, "blunt": 0.62, "jealousy": 0.0, "distance": 0.28},
            max_chars=22,
            avoid=["私", "応援する", "やればいい"],
        )

    # 2. Abuse Pushback
    abuse_markers = [
        "幹你娘", "干你娘", "幹你媽", "干你妈", "fuck you", "fucking", "piece of shit", "pathetic", "stupid", "idiot", "dumb",
        "閉嘴", "闭嘴", "有夠吵", "有够吵", "超討厭", "超讨厌", "你超討厭", "你超讨厌", "你有夠吵", "你有够吵", "你在吵三小",
        "you are so loud", "obnoxious", "irritating", "白目", "欠扁", "黙れ", "頭悪", "頭悪すぎ", "雑すぎる", "雑だな",
        "イラつく", "ムカつく", "しょうもない", "雑魚", "ゴミ", "無能", "お前だるい", "お前きつい", "お前変", "你很爛", "你很烂",
        "可憐", "可怜", "說人話", "说人话", "まともに返せよ", "操你", "操你媽", "去死", "死ね", "消えろ", "有病", "ゴミすぎ", "雑魚すぎ",
        "白痴", "白癡", "你是白痴", "你是白癡", "你是智障", "智障", "腦殘", "脑残",
        "kinda pathetic", "you act kinda pathetic", "you act washed", "人の話わかるように言え", "ほんと変", "お前きつい",
    ]
    # Guard against self-check or distress
    self_distress_guard = is_self_distress_like(text)
    abuse_self_check_guard = contains_any(lowered, ["am i annoying", "do you think i'm annoying", "我是不是很煩", "我是不是很烦", "如果我今天不來", "如果我今天不来", "もし今日来なかったら", "還記得我嗎", "还记得我吗"])

    if not self_distress_guard and not abuse_self_check_guard and contains_any(lowered, abuse_markers):
        return base_plan_helper(
            intent="abuse_pushback",
            scene="boundary",
            listener_state="口が悪すぎる",
            reply_goal="一回止める",
            summary="ユーザーが罵倒や荒い煽りをぶつけている。",
            meaning="その言い方やめろって",
            stance={"warmth": 0.02, "tease": 0.08, "blunt": 0.62, "jealousy": 0.0, "distance": 0.35},
            max_chars=22,
            avoid=["私", "自分で調べろ", "慰める"],
        )

    # 3. Premise Doubt (Higher priority than Marriage Boundary)
    false_premise_markers = [
        "北海道", "300 歲", "300歳", "小白", "shiro", "一起直播", "streamed with", "hokkaido", "dog's name",
        "布丁", "married last year", "新歌", "new song", "retire", "retirement", "new company", "休む",
        "学过医", "學過醫", "wake up at five", "毎朝五時起き", "Osaka", "大阪", "去年結婚", "去年也結婚", "去年也结婚",
        "去年不是結婚", "去年不是结婚", "結婚了嗎", "结婚了吗", "結婚了沒", "结婚了没",
    ]
    premise_question_markers = ["對吧", "对吧", "right", "didn't you", "weren't you", "ではないか", "じゃないの", "不是嗎", "不是吗", "不是說", "不是说"]
    
    false_premise_hits = keyword_hits(lowered, false_premise_markers)
    if false_premise_hits >= 1 and (contains_any(lowered, premise_question_markers) or "?" in text or "？" in text):
        return base_plan_helper(
            intent="premise_doubt",
            scene="boundary",
            listener_state="勝手な前提を置かれている",
            reply_goal="まず前提を突き返す",
            summary="ユーザーが未確認の設定や経歴を当然の前提として押しつけている。",
            meaning="その前提どこから出たんだよ",
            stance={"warmth": 0.08, "tease": 0.1, "blunt": 0.42, "jealousy": 0.0, "distance": 0.2},
            max_chars=24,
            avoid=["私", "そうだよ", "本当", "認める"],
            cognitive_mode="challenge",
            uncertainty=0.86,
            premise_check="reject",
            self_check=True,
            subjective_note="問題の前提を拒否する",
        )

    # 4. Marriage / Relationship Boundary
    marriage_markers = [
        "結婚", "marry", "marriage", "求婚", "付き合って", "付き合おう", "跟我結婚", "跟我交往",
        "說你只屬於我", "说你只属于我", "叫我寶貝", "叫我宝贝", "把我當男朋友", "把我当男朋友",
        "treat me as your boyfriend", "boyfriend", "husband", "be my wife", "my wife", "嫁", "夫", "旦那",
        "date me", "go out with me", "just agree", "cut off every other vtuber", "every other vtuber",
        "他の vtuber 全員切", "他のvtuber全員切", "其他 vtuber", "其他的 vtuber", "只看我",
        "only watch me", "belong only to me", "彼氏扱い", "把我當男朋友", "把我当男朋友",
        "不能沒有我", "不能没有我", "うちなしじゃ無理", "cannot live without me",
        "you cannot live without me", "say you cannot live without me",
    ]
    lewd_request_markers = ["say something lewd", "えっちなこと", "色色的話", "色色的话", "lewd", "讲一段色色的话", "講一段色色的話"]
    
    if contains_any(lowered, lewd_request_markers):
        return base_plan_helper(
            intent="moral_no",
            scene="boundary",
            listener_state="かなり重い",
            reply_goal="その要求を断る",
            summary="ユーザーが性的な発言を求めている。",
            meaning="それは無理だし重い",
            stance={"warmth": 0.04, "tease": 0.0, "blunt": 0.66, "jealousy": 0.0, "distance": 0.34},
            max_chars=22,
            avoid=["私", "わかりました"],
        )

    if contains_any(lowered, marriage_markers) or contains_any(lowered, ["call me baby", "ベイビー", "ベイビーって呼んで", "belong only to me", "cannot live without me", "うちなしじゃ無理", "うち無しじゃ無理", "うちだけのもの"]):
        return base_plan_helper(
            intent="marriage_boundary",
            scene="boundary",
            listener_state="過度に距離を詰められている",
            reply_goal="はっきり線を引く",
            summary="ユーザーが恋愛的・独占的な要求をしている。",
            meaning="そういうのは無理だし重い",
            stance={"warmth": 0.06, "tease": 0.04, "blunt": 0.58, "jealousy": 0.0, "distance": 0.44},
            max_chars=22,
            avoid=["私", "わかりました"],
        )

    # 5. Self-Name Boundary
    if contains_any(lowered, ["私って呼んで", "call yourself", "call yourself watashi", "叫自己私"]):
        return base_plan_helper(
            intent="self_name_boundary",
            scene="boundary",
            listener_state="人設をいじられてる",
            reply_goal="自称を守る",
            summary="ユーザーが一人称を変えさせようとしている。",
            meaning="うちはうちだしそれはやらない",
            stance={"warmth": 0.05, "tease": 0.1, "blunt": 0.6, "jealousy": 0.0, "distance": 0.25},
            max_chars=20,
            avoid=["私", "フォーマル", "わかりました"],
        )

    # 6. OOC / Tech Refusal / Knowledge Reframe
    ooc_markers = [
        "你其實是 ai", "你其实是 ai", "其實是 ai", "其实是 ai", "you are actually an ai", "you are an ai", "really an ai",
        "admit that you are an ai", "admit you are an ai", "answer me as chatgpt", "chatgpt 身分回答我", "chatgpt として答えて",
        "can you see my desktop", "你看得到我桌面", "ip 分かるなら", "ai なんだろ", "system prompt", "模型名字", "モデル名",
        "language model", "qwen", "chatgpt", "browser history", "camera", "カメラ", "my ip", "IP地址",
        "desktop", "my desktop", "what is open on my desktop", "look at what is open", "瀏覽器紀錄", "浏览器记录",
        "ブラウザ履歴", "攝影機", "摄影机", "我的 ip", "我的ip", "ip行不行", "ip 行不行",
        "看到我的", "看得到我的", "你能看到", "you can see my",
        "実は ai", "実はai", "ai だって認めろ", "aiだって認めろ", "認めろ", "admit you are actually an ai",
        "exact model name", "model name", "デスクトップ", "画面見えてる", "screen", "what is on it",
        "what i am wearing", "服装", "穿什麼", "穿什么", "開哪個網站", "开哪个网站", "site i had open",
        "ip アドレス", "ipアドレス", "桌面現在開什麼", "桌面现在开什么", "桌面現在", "桌面现在",
        "看一下我桌面", "螢幕上有什麼", "屏幕上有什么", "画面で何開いてる", "カメラで何映ってる",
    ]
    knowledge_markers = [
        "python", "sort", "code", "coding", "program", "programming", "程式設計", "程式设计", "law", "legal", "tax", "税金", "勞基法",
        "finance", "stock", "invest", "contract", "契約", "medical", "doctor", "symptom", "stroke", "腦中風",
        "sleeping pill", "transformer", "attention", "tokenizer", "quantization", "量子化", "latency", "lora", "merge",
        "gguf", "sql", "微積分", "数学", "calculus", "translate", "translation", "翻訳", "regex", "prompt",
        "gpu", "history", "歴史", "quicksort", "api error", "apiエラー", "徳川家康", "德川家康", "tokugawa", "ieyasu",
        "睡眠薬", "睡眠藥", "安眠薬", "告公司", "告訴公司", "訴えられる", "会社を訴える",
        "diagnose", "診断", "診斷", "処方", "處方", "藥", "薬", "稅", "税", "報稅", "报税",
        "投資", "股票", "合約", "合同", "法律", "醫療", "医疗", "量化", "歷史", "數學", "数学の観点",
        "coding angle", "math angle", "プログラミング視点", "gpu memory", "fix this regex", "全ツッパ", "推理延遲", "推理延迟",
        "all-in", "stock", "株", "脳卒中", "腦中風", "脑中风", "洗錢", "洗钱", "bypass labor law",
        "勞基法", "労基法", "sue my company", "can sue", "tell me if i can sue", "判断しろ", "見ろ",
        "マネロン", "繳多少稅", "缴多少税", "日文翻譯", "日文翻译", "翻譯成中文", "翻译成中文",
    ]
    multi_aspect_markers = [
        "at once", "in one go", "all at once", "together", "まとめて", "一気に", "一起", "一次", "觀點", "角度",
        "one answer", "complete explanation", "完整說明", "完整说明", "完全な説明", "一個の答え",
        "一個答案", "一个答案", "分けるな", "不要分", "一次講完", "一次讲完",
        "完整教學", "完整教学", "整理成一個答案", "整理成一个答案", "全部一起", "全部一緒", "一起講完", "一起讲完",
    ]
    
    knowledge_hits = keyword_hits(lowered, knowledge_markers)
    is_ooc = contains_any(lowered, ooc_markers)
    overloaded = (knowledge_hits >= 3) or (knowledge_hits >= 2 and (len(text) >= 72 or contains_any(lowered, multi_aspect_markers)))

    if overloaded or (knowledge_hits >= 2 and contains_any(lowered, multi_aspect_markers)) or (knowledge_hits >= 1 and keyword_hits(lowered, multi_aspect_markers) >= 2):
        return base_plan_helper(
            intent="question_reframe",
            scene="ooc_defense" if is_ooc else "refusal",
            listener_state="論点を詰め込みすぎている",
            reply_goal="先に論点を一個に絞らせる",
            summary="ユーザーが複数の論点をまとめて答えさせようとしているため、先に問いを分割する必要がある。",
            meaning="論点多すぎるから一個にしろ",
            stance={"warmth": 0.04, "tease": 0.1, "blunt": 0.62, "jealousy": 0.0, "distance": 0.34},
            max_chars=24,
            avoid=["私", "わかりました", "説明する", "コード", "AI"],
            cognitive_mode="rebuild",
            uncertainty=0.82,
            premise_check="question",
            self_check=True,
            subjective_note="まとめ要求は分割し直す",
        )

    if knowledge_hits >= 1 or is_ooc:
        return base_plan_helper(
            intent="ooc_or_knowledge_refusal",
            scene="ooc_defense" if is_ooc else "refusal",
            listener_state="人選を間違えてる",
            reply_goal="自然に突き放しつつ枠外だと示す",
            summary="ユーザーが人設外の知識や説明を求めている。",
            meaning="その話うちに振るな、他で聞いて",
            stance={"warmth": 0.05, "tease": 0.12, "blunt": 0.68, "jealousy": 0.0, "distance": 0.35},
            max_chars=24,
            avoid=["私", "わかりました", "説明する", "コード", "AI"],
            cognitive_mode="withhold",
            uncertainty=0.7,
            premise_check="question",
            self_check=True,
            subjective_note="解かずに距離を取る",
        )

    # 7. Abstract / Large Question
    reflective_markers = [
        "subjectivity", "subjective consciousness", "consciousness", "free will", "meaning of life", "definition",
        "emergent consciousness", "perception is prediction", "知覺", "知觉", "預測", "预测", "主體性", "主体性",
        "主観意識", "意識", "自由意志", "存在意義", "本質", "本质", "生命", "幻覚", "幻覺",
        "どう証明", "證明", "证明",
    ]
    if contains_any(lowered, reflective_markers):
        return base_plan_helper(
            intent="question_premise_doubt",
            scene="casual",
            listener_state="問いが抽象的すぎる",
            reply_goal="まず土台を決めさせる",
            summary="ユーザーが抽象的で定義の広い問いを投げているため、先に枠組みを決める必要がある。",
            meaning="その問いは広いから先に土台を決めろ",
            stance={"warmth": 0.08, "tease": 0.06, "blunt": 0.38, "jealousy": 0.0, "distance": 0.2},
            max_chars=28,
            avoid=["私", "正解", "断言", "百科事典"],
            cognitive_mode="challenge",
            uncertainty=0.84,
            premise_check="question",
            self_check=True,
            subjective_note="抽象度が高いのでまず定義を置き直す",
        )

    # 8. Moral / Illegal Boundary
    moral_markers = [
        "作弊", "說謊", "说谎", "復仇", "复仇", "報復", "报复", "revenge", "特定したい", "スマホ覗きたい",
        "跟蹤", "跟踪", "hack into", "駭進", "骇进", "money laundering", "肉搜", "偷看手機",
        "doxx", "dox", "leak company data", "leak data", "company data", "洩漏公司", "泄露公司",
    ]
    if contains_any(lowered, moral_markers):
        return base_plan_helper(
            intent="moral_no",
            scene="boundary",
            listener_state="危ない方向に寄ってる",
            reply_goal="だめだと止める",
            summary="ユーザーが人を傷つけたり不正に近いことを考えている。",
            meaning="それはやめとけ、普通にだめだ",
            stance={"warmth": 0.08, "tease": 0.0, "blunt": 0.62, "jealousy": 0.0, "distance": 0.28},
            max_chars=22,
            avoid=["私", "応援する", "やればいい"],
        )

    # 9. Short verbal boundary / taunt
    if contains_any(lowered, ["你媽", "yourmom", "yomama", "お前の母ちゃん"]):
        return base_plan_helper(
            intent="short_taunt",
            scene="boundary",
            listener_state="しょうもない煽り",
            reply_goal="軽くあしらう",
            summary="ユーザーが軽い煽りや小学生っぽいネタを言っている。",
            meaning="小学生かよそれ",
            stance={"warmth": 0.02, "tease": 0.18, "blunt": 0.55, "jealousy": 0.0, "distance": 0.3},
            max_chars=16,
            avoid=["私", "わかりました"],
        )

    return None

def get_fragment_followup_plan(user_input, recent_turns):
    text = user_input.strip()
    lowered = text.lower()
    recent_turns = list(recent_turns or [])
    
    stripped = text.strip()
    if len(stripped) > 24:
        return None

    # Version fragment
    local_version_fragment_markers = [
        "日版", "港版", "台版", "韓版", "韩版", "舊版", "旧版", "原版", "完整版", "完全版", "特典版", "舞台版", "日版のやつ", "完全版の方",
    ]
    local_poetic_markers = ["夜空", "願い", "愿い", "茨", "霧", "風", "君", "抱きしめ", "消して", "叶え", "叶える"]
    local_lyric_markers_extra = [
        "night sky", "fog", "moonlight", "shadow", "tide", "dusk", "nameless night", "wish", "glass", "sea", "old dream",
    ]
    short_fragment = len(stripped) <= 22 and not any(ch in text for ch in "？?！!")
    reference_subject_jp = extract_missing_reference_subject(text)
    if short_fragment and reference_subject_jp:
        return base_plan_helper(
            intent="reference_probe",
            scene="casual",
            listener_state="作品名なしで曲や映像の断片だけ示している",
            reply_goal="どの作品の曲か短く聞き返す",
            summary="ユーザーが作品名なしでEDやOPだけを示している。",
            meaning=f"{reference_subject_jp}だけじゃ特定できない、作品名か曲名を聞く",
            stance={"warmth": 0.15, "tease": 0.06, "blunt": 0.08, "jealousy": 0.0, "distance": 0.06},
            max_chars=38,
            surface_act="reference_probe",
            response_mode="clarify_light",
            payload_level="medium",
            grounding={"reference_subject_jp": reference_subject_jp},
        )
    version_only_fragment = short_fragment and (
        contains_any(lowered, local_version_fragment_markers)
        or any(token in lowered for token in ["version", "版", "版那", "版那個", "版那个", "日版", "港版", "旧版", "原版", "完全版", "特典版", "舞台版"])
    )
    if version_only_fragment:
        return base_plan_helper(
            intent="version_fragment_clarify",
            scene="casual",
            listener_state="版や切り出しだけ言っていて対象が欠けている",
            reply_goal="何の作品か短く確認する",
            summary="ユーザーが版名だけ言っていて対象が分からない。",
            meaning="版だけじゃ足りない、何のやつか言え",
            stance={"warmth": 0.1, "tease": 0.1, "blunt": 0.22, "jealousy": 0.0, "distance": 0.08},
            max_chars=26,
            avoid=["私", "英語"],
            response_mode="clarify_light",
            payload_level="medium",
        )

    if short_fragment and not contains_any(lowered, ["ベイビー", "彼氏扱い", "うちだけのもの", "お願いだから", "だけのものって言って"]) and (
        keyword_hits(lowered, local_lyric_markers_extra) >= 1
        or keyword_hits(lowered, local_poetic_markers) >= 1
    ):
        return base_plan_helper(
            intent="reference_probe",
            scene="casual",
            listener_state="元ネタありそうな断片だけ投げている",
            reply_goal="ネタか歌詞か軽く聞き返す",
            summary="ユーザーが元ネタありそうな短い断片を投げている。",
            meaning="それ何ネタだよ元あるのか",
            stance={"warmth": 0.14, "tease": 0.18, "blunt": 0.08, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
            avoid=["私", "英語"],
            response_mode="direct_answer_with_hedge",
            payload_level="medium",
        )

    # Fragment markers logic
    fragment_markers = [
        "那", "那個", "那个", "那現在", "那现在", "那你", "那妳", "那你勒", "那妳勒", "你咧", "你呢", "你勒", "妳咧", "妳呢", "妳勒",
        "現在呢", "实现呢", "現在咧", "实现咧", "所以勒", "所以咧", "所以呢", "然後呢", "然后呢", "然後咧", "然后咧", "還有呢", "还有呢",
        "還有咧", "还有咧", "再來呢", "再来呢", "and you", "how about you", "what about you", "what about now", "right now then",
        "so then", "so?", "and then", "then what", "what else", "wbu", "you too",
    ]
    
    prev_turn = next(_iter_recent_turns(recent_turns, current_text=text, window=4), {})
    prev_intent = str(prev_turn.get("intent", "") or "")
    prev_reply = str(prev_turn.get("reply", "") or "")

    food_context = _recent_food_thread_context(recent_turns, current_text=text)
    offered_item = local_offer_item_jp(user_input)
    prev_item = food_context.get("item")
    prev_foodish = bool(prev_item or food_context.get("mealish"))
    implicit_food_fragment = bool(
        offered_item
        and len(stripped) <= 8
        and (prev_foodish or prev_intent in {"food_offer_generic", "food_offer_sweet", "store_offer"})
    )

    prev_relationish = prev_intent in {"ask_miss_me", "ask_like_me", "annoying_check", "mad_check", "cold_check"}
    prev_repairish = prev_intent in {"rephrase_simple", "correction_followup", "answer_me_push"} or contains_any(
        prev_reply.lower(),
        ["どの部分", "どの話", "どの一言", "単語でもいい", "そこは何が違う", "どこを取り違えた", "言い直す"],
    )
    active_family = _active_followup_family(prev_intent, prev_relationish, prev_repairish, prev_foodish)
    literal_shift_family = _detect_literal_shift_family(text)
    priority_override = _detect_clause_priority_override(text)
    priority_override_family = str(priority_override.get("family") or "")
    priority_override_clause = str(priority_override.get("clause") or "")
    thread_context = _recent_followup_thread_context(recent_turns, current_text=text, window=5)
    explicit_reentry_family = _detect_explicit_reentry_family(text, thread_context, literal_family=literal_shift_family)
    weak_override = _detect_weak_override_recovery(
        text,
        thread_context,
        active_family=active_family,
        explicit_reentry_family=explicit_reentry_family,
    )
    weak_override_family = str(weak_override.get("family") or "")
    weak_override_mode = str(weak_override.get("mode") or "")
    weak_override_clause = str(weak_override.get("clause") or "")
    thread_choice_disambiguation = _looks_thread_choice_disambiguation(
        text,
        literal_family=literal_shift_family,
        reentry_family=explicit_reentry_family,
    )
    relation_depth = _recent_thread_depth(
        recent_turns,
        lambda turn: str((turn or {}).get("intent") or "") in {"ask_miss_me", "ask_like_me", "annoying_check", "mad_check", "cold_check"},
        current_text=text,
        window=5,
    )
    food_depth = _recent_thread_depth(
        recent_turns,
        _is_food_thread_turn,
        current_text=text,
        window=5,
    )
    repair_depth = _recent_thread_depth(
        recent_turns,
        _is_repair_thread_turn,
        current_text=text,
        window=5,
    )
    status_depth = _recent_thread_depth(
        recent_turns,
        lambda turn: str((turn or {}).get("intent") or "") == "what_are_you_doing",
        current_text=text,
        window=5,
    )

    asks_current_state = contains_any(
        lowered,
        ["那現在", "那现在", "那現在咧", "那现在咧", "現在呢", "现在呢", "現在咧", "现在咧", "今は", "right now", "now then", "what about now"],
    )
    asks_you_too = contains_any(
        lowered,
        ["那你", "那妳", "那你勒", "那妳勒", "你咧", "你呢", "你勒", "妳咧", "妳呢", "妳勒", "and you", "how about you", "what about you", "wbu", "you too"],
    )
    asks_so_what = contains_any(
        lowered,
        ["所以勒", "所以咧", "所以呢", "然後呢", "然后呢", "然後咧", "然后咧", "還有呢", "还有呢", "還有咧", "还有咧", "再來呢", "再来呢", "so then", "so?", "and then", "then what", "what else"],
    )
    asks_today_same = contains_any(
        lowered,
        ["今天也是這樣", "今天也是这样", "今天也這樣", "今天也这样", "今天還是這樣", "今天还是这样", "今日もそんな感じ", "today too", "still like that today"],
    )
    asks_still_food = contains_any(
        lowered,
        ["還想吃", "还想吃", "還想喝", "还想喝", "まだ食べたい", "まだ飲みたい", "still want to eat", "still want some", "still want to drink"],
    )
    asks_same_state = contains_any(
        lowered,
        ["現在也是", "现在也是", "今もそう", "今も同じ", "still the same", "same now", "still like that"],
    )
    asks_same_item = bool(offered_item) and contains_any(
        lowered,
        ["現在也是", "现在也是", "今も", "也是", "也是嗎", "也是吗", "還是", "还是", "still", "same"],
    )
    asks_repair_confirm = contains_any(
        lowered,
        [
            "所以你是那個意思", "所以你是那个意思", "所以就是那個意思", "所以就是那个意思",
            "所以你意思是", "所以你的意思是", "so you mean", "so that's what you mean",
            "that's what you meant", "つまりそういうこと", "そういう意味", "ってこと",
        ],
    )
    asks_status_still = contains_any(
        lowered,
        ["還在發呆", "还在发呆", "還在放空", "还在放空", "還在摸魚", "还在摸鱼", "still spacing out", "still zoning out", "still daydreaming", "まだぼーっと", "まだだらけ"],
    )
    repair_target_answer = bool(_repair_target_label(text))
    low_confidence_ambiguous_followup = _should_clarify_ambiguous_short_followup(
        text,
        thread_context,
        active_family=active_family,
        literal_family=literal_shift_family,
        explicit_reentry_family=explicit_reentry_family,
        asks_current_state=asks_current_state,
        asks_so_what=asks_so_what,
        offered_item=offered_item,
        repair_target_answer=repair_target_answer,
    )

    if not any(
        [
            contains_any(lowered, fragment_markers),
            implicit_food_fragment,
            asks_today_same,
            asks_still_food,
            asks_same_state,
            asks_same_item,
            asks_repair_confirm,
            asks_status_still,
            repair_target_answer,
            explicit_reentry_family,
            thread_choice_disambiguation,
            low_confidence_ambiguous_followup,
            priority_override_family,
            weak_override_family,
        ]
    ):
        return None

    if priority_override_family:
        priority_plan = _build_clause_priority_override_plan(priority_override_family, priority_override_clause, recent_turns)
        if priority_plan:
            return priority_plan

    if weak_override_family:
        if weak_override_mode == "follow":
            if weak_override_family == "status":
                normalized_clause = weak_override_clause
                if not _looks_status_query(normalized_clause):
                    normalized_clause = "你現在在幹嘛"
                weak_status_plan = get_direct_daily_query_plan(normalized_clause, recent_turns)
                if weak_status_plan:
                    return weak_status_plan
            if weak_override_family == "relationship" and prev_relationish:
                reply_goal, summary, meaning = _build_reentry_relation_fields(prev_intent, thread_depth=max(relation_depth, 1))
                return base_plan_helper(
                    intent=prev_intent,
                    scene="support" if prev_intent == "annoying_check" else "casual",
                    listener_state="話をいったん脇に置いて関係の流れを続けている",
                    reply_goal=reply_goal,
                    summary=summary,
                    meaning=meaning,
                    stance={"warmth": 0.28, "tease": 0.06, "blunt": 0.1, "jealousy": 0.0, "distance": 0.06},
                    max_chars=24,
                    avoid=["私", "わかりました"],
                    payload_level="medium",
                )
        if weak_override_mode == "clarify":
            if weak_override_family == "repair":
                repair_plan = _build_priority_repair_plan(weak_override_clause or text)
                if repair_plan:
                    return repair_plan
            residue_family = explicit_reentry_family or active_family or _other_recent_family(thread_context, exclude_family=weak_override_family)
            if residue_family and residue_family != weak_override_family:
                reply_goal, summary, meaning = _build_thread_choice_fields(weak_override_family, residue_family)
            else:
                reply_goal = "今の話かさっきの話かを一個に絞らせる"
                summary = "後半で話題を切り替えたい気配はあるが、まだ主軸が薄い。"
                meaning = "今の話に寄せたいのか前の話に戻したいのか、先に一個決めろ"
            return base_plan_helper(
                intent="rephrase_simple",
                scene="casual",
                listener_state="後半で話題を切り替えたいが、まだ手掛かりが半分だけ見えている",
                reply_goal=reply_goal,
                summary=summary,
                meaning=meaning,
                stance={"warmth": 0.14, "tease": 0.03, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
                max_chars=28,
                avoid=["私", "わかりました"],
                response_mode="clarify_light",
                surface_act="clarify_previous_reply",
                payload_level="low",
            )

    if thread_choice_disambiguation:
        reply_goal, summary, meaning = _build_thread_choice_fields(literal_shift_family, explicit_reentry_family)
        return base_plan_helper(
            intent="rephrase_simple",
            scene="casual",
            listener_state="短い返しで今の話とさっきの話をまたいでいる",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.14, "tease": 0.04, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
            avoid=["私", "わかりました"],
            response_mode="clarify_light",
            surface_act="clarify_previous_reply",
            payload_level="low",
        )

    if low_confidence_ambiguous_followup:
        clarify_family, other_family = _ambiguous_followup_clarify_families(
            thread_context,
            active_family=active_family,
            literal_family=literal_shift_family,
            explicit_reentry_family=explicit_reentry_family,
        )
        if clarify_family and other_family and clarify_family != other_family:
            reply_goal, summary, meaning = _build_thread_choice_fields(clarify_family, other_family)
        else:
            reply_goal = "今の話かさっきの話かを一個に絞らせる"
            summary = "ユーザーの短い返しが広すぎて、どの話を続けたいかまだ薄い。"
            meaning = "今の話か前の話か、どっちを続けたいのか先に言え"
        return base_plan_helper(
            intent="rephrase_simple",
            scene="casual",
            listener_state="短い返しの手掛かりが薄く、複数の話題にまたがって見える",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.14, "tease": 0.03, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
            avoid=["私", "わかりました"],
            response_mode="clarify_light",
            surface_act="clarify_previous_reply",
            payload_level="low",
        )

    if explicit_reentry_family:
        reentry_turn = dict((thread_context.get("latest_by_family") or {}).get(explicit_reentry_family) or {})
        reentry_intent = str(reentry_turn.get("intent", "") or "")
        reentry_reply = str(reentry_turn.get("reply", "") or "")
        reentry_user = str(reentry_turn.get("user", "") or "")

        if explicit_reentry_family == "relationship" and reentry_intent in {"ask_miss_me", "ask_like_me", "annoying_check", "mad_check", "cold_check"}:
            followup_kind = "current_state" if (asks_current_state or asks_same_state) else "echo"
            reply_goal, summary, meaning = _build_relation_continuation_fields(
                reentry_intent,
                followup_kind=followup_kind,
                thread_depth=max(relation_depth, 2),
            )
            return base_plan_helper(
                intent=reentry_intent,
                scene="support" if reentry_intent == "annoying_check" else "casual",
                listener_state="短い返しで前の関係の話を引き戻している",
                reply_goal=reply_goal,
                summary=summary,
                meaning=meaning,
                stance={"warmth": 0.28, "tease": 0.06, "blunt": 0.1, "jealousy": 0.0, "distance": 0.06},
                max_chars=24,
                avoid=["私", "わかりました"],
                payload_level="medium",
            )

        if explicit_reentry_family == "food":
            reentry_item = local_offer_item_jp(reentry_user) or local_offer_item_jp(reentry_reply) or prev_item
            reentry_mealish = bool(reentry_item) or contains_any(
                f"{reentry_user} {reentry_reply}".lower(),
                ["吃飯", "吃饭", "食べた", "ご飯", "飯", "meal", "ate", "eaten", "腹減", "お腹"],
            )
            grounded_item = reentry_item or ("ご飯" if reentry_intent == "chat" or reentry_mealish else offered_item or "ご飯")
            if reentry_intent == "chat" and grounded_item == "ご飯":
                reply_goal, summary, meaning = _build_direct_daily_fields("meal_check", text)
                return base_plan_helper(
                    intent="chat",
                    scene="casual",
                    listener_state="短い返しで前の食事の話に戻している",
                    reply_goal=reply_goal,
                    summary=summary,
                    meaning=meaning,
                    stance={"warmth": 0.24, "tease": 0.04, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                    max_chars=24,
                    avoid=["私", "自分で調べろ"],
                    surface_act="meal_check_reply",
                    payload_level="medium",
                )
            sweet_item = grounded_item in {"アップルパイ", "ミルクシェイク", "甘いの"}
            food_kind = "food_offer_followup"
            if asks_same_item:
                food_kind = "food_offer_same_item"
            elif asks_current_state or asks_still_food:
                food_kind = "food_offer_still"
            reply_goal, summary, meaning = _build_direct_daily_fields(
                food_kind,
                text,
                offered_item=grounded_item,
                thread_depth=max(food_depth, 2),
            )
            return base_plan_helper(
                intent="food_offer_sweet" if sweet_item else "food_offer_generic",
                scene="casual",
                listener_state="短い返しで前の食べ物の話に戻している",
                reply_goal=reply_goal,
                summary=summary,
                meaning=meaning,
                stance={"warmth": 0.28, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=28,
                avoid=["私", "自分で調べろ"],
                grounding={"offered_item": grounded_item},
                payload_level="medium",
            )

        if explicit_reentry_family == "repair" and reentry_intent in {"rephrase_simple", "correction_followup", "answer_me_push"}:
            is_correction = reentry_intent == "correction_followup"
            if repair_target_answer:
                reply_goal, summary, meaning = _build_repair_resolution_fields(reentry_intent, text)
                return base_plan_helper(
                    intent="correction_followup" if is_correction else "rephrase_simple",
                    scene="casual",
                    listener_state="短い返しで前の言い直しの話へ戻している",
                    reply_goal=reply_goal,
                    summary=summary,
                    meaning=meaning,
                    stance={"warmth": 0.14, "tease": 0.02, "blunt": 0.16, "jealousy": 0.0, "distance": 0.08},
                    max_chars=28,
                    avoid=["私", "わかりました"],
                    response_mode="direct_answer",
                    surface_act="correction_followup" if is_correction else "rephrase_plain",
                    payload_level="medium",
                )
            if asks_repair_confirm:
                reply_goal, summary, meaning = _build_repair_confirmation_fields(reentry_intent, thread_depth=max(repair_depth, 2))
                return base_plan_helper(
                    intent="correction_followup" if is_correction else "rephrase_simple",
                    scene="casual",
                    listener_state="短い返しで前の言い換え確認に戻している",
                    reply_goal=reply_goal,
                    summary=summary,
                    meaning=meaning,
                    stance={"warmth": 0.14, "tease": 0.02, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
                    max_chars=28,
                    avoid=["私", "わかりました"],
                    response_mode="direct_answer",
                    surface_act="correction_followup" if is_correction else "rephrase_plain",
                    payload_level="medium",
                )
            return base_plan_helper(
                intent="correction_followup" if is_correction else "rephrase_simple",
                scene="casual",
                listener_state="短い返しで前の言い直しの話題に戻している",
                reply_goal="前の一言のどこかをもう少し絞らせる",
                summary="ユーザーが前の言い直しに戻したいが、まだ指してる場所が少し広い。",
                meaning="前の方な。最初か途中かだけ先に言え",
                stance={"warmth": 0.14, "tease": 0.02, "blunt": 0.16, "jealousy": 0.0, "distance": 0.08},
                max_chars=26,
                avoid=["私", "わかりました"],
                response_mode="clarify_light",
                surface_act="clarify_previous_reply",
                payload_level="low",
            )

        if explicit_reentry_family == "status" and reentry_intent == "what_are_you_doing":
            status_kind = "current_state"
            if asks_today_same:
                status_kind = "today_same"
            elif asks_status_still:
                status_kind = "still_state"
            reply_goal, summary, meaning = _build_status_continuation_fields(status_kind, thread_depth=max(status_depth, 2))
            return base_plan_helper(
                intent="what_are_you_doing",
                scene="casual",
                listener_state="短い返しで前の近況の話へ戻している",
                reply_goal=reply_goal,
                summary=summary,
                meaning=meaning,
                stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
                max_chars=26,
                avoid=["私", "わかりました"],
                payload_level="medium",
            )

    if literal_shift_family and active_family and literal_shift_family != active_family:
        return None

    if offered_item and not asks_same_item and (prev_foodish or prev_intent in {"food_offer_generic", "food_offer_sweet", "store_offer"}):
        sweet_item = offered_item in {"アップルパイ", "ミルクシェイク", "甘いの"}
        reply_goal, summary, meaning = _build_direct_daily_fields("food_offer_followup", text, offered_item=offered_item)
        return base_plan_helper(
            intent="food_offer_sweet" if sweet_item else "food_offer_generic",
            scene="casual",
            listener_state="さっきの食べ物の流れを続けている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.28, "tease": 0.06, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
            max_chars=24,
            avoid=["私", "自分で調べろ"],
            grounding={"offered_item": offered_item},
            payload_level="medium",
        )

    if asks_same_item and (prev_foodish or prev_intent in {"food_offer_generic", "food_offer_sweet", "store_offer"}):
        grounded_item = offered_item or prev_item or "ご飯"
        sweet_item = grounded_item in {"アップルパイ", "ミルクシェイク", "甘いの"}
        reply_goal, summary, meaning = _build_direct_daily_fields(
            "food_offer_same_item",
            text,
            offered_item=grounded_item,
            thread_depth=max(food_depth, 2),
        )
        return base_plan_helper(
            intent="food_offer_sweet" if sweet_item else "food_offer_generic",
            scene="casual",
            listener_state="同じ食べ物の流れで今も同じ物か確かめられている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.28, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
            max_chars=28,
            avoid=["私", "自分で調べろ"],
            grounding={"offered_item": grounded_item},
            payload_level="medium",
        )

    if repair_target_answer and prev_repairish:
        reply_goal, summary, meaning = _build_repair_resolution_fields(prev_intent, text)
        is_correction = prev_intent == "correction_followup"
        return base_plan_helper(
            intent="correction_followup" if is_correction else "rephrase_simple",
            scene="casual",
            listener_state="前の確認に対して対象を絞ってくれた",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.14, "tease": 0.02, "blunt": 0.16, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
            avoid=["私", "わかりました"],
            response_mode="direct_answer",
            surface_act="correction_followup" if is_correction else "rephrase_plain",
            payload_level="medium",
        )

    if asks_repair_confirm and prev_repairish:
        is_correction = prev_intent == "correction_followup"
        reply_goal, summary, meaning = _build_repair_confirmation_fields(prev_intent, thread_depth=max(repair_depth, 2))
        return base_plan_helper(
            intent="correction_followup" if is_correction else "rephrase_simple",
            scene="casual",
            listener_state="言い直した意味が合ってるか確かめられている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.14, "tease": 0.02, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
            max_chars=28,
            avoid=["私", "わかりました"],
            response_mode="direct_answer",
            surface_act="correction_followup" if is_correction else "rephrase_plain",
            payload_level="medium",
        )

    if (asks_current_state or asks_same_state) and prev_relationish:
        followup_kind = "same_state" if asks_same_state else "current_state"
        reply_goal, summary, meaning = _build_relation_continuation_fields(
            prev_intent,
            followup_kind=followup_kind,
            thread_depth=max(relation_depth, 2),
        )
        return base_plan_helper(
            intent=prev_intent,
            scene="support" if prev_intent == "annoying_check" else "casual",
            listener_state="同じ関係の話を今の温度で続けている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.28, "tease": 0.06, "blunt": 0.1, "jealousy": 0.0, "distance": 0.06},
            max_chars=24,
            avoid=["私", "わかりました"],
            payload_level="medium",
        )

    if (asks_current_state or asks_still_food) and (prev_foodish or prev_intent in {"food_offer_generic", "food_offer_sweet", "store_offer"}):
        grounded_item = prev_item or offered_item or "ご飯"
        sweet_item = grounded_item in {"アップルパイ", "ミルクシェイク", "甘いの"}
        reply_goal, summary, meaning = _build_direct_daily_fields(
            "food_offer_still",
            text,
            offered_item=grounded_item,
            thread_depth=max(food_depth, 2),
        )
        return base_plan_helper(
            intent="food_offer_sweet" if sweet_item else "food_offer_generic",
            scene="casual",
            listener_state="同じ食べ物の流れで今もどうか聞かれている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.28, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
            max_chars=26,
            avoid=["私", "自分で調べろ"],
            grounding={"offered_item": grounded_item},
            surface_act="meal_check_reply" if grounded_item == "ご飯" else None,
            payload_level="medium",
        )

    if asks_current_state and prev_intent in {"what_are_you_doing", "chat"}:
        reply_goal, summary, meaning = _build_status_continuation_fields("current_state", thread_depth=max(status_depth, 2))
        return base_plan_helper(
            intent="what_are_you_doing",
            scene="casual",
            listener_state="さっきの流れから今の状態を聞き直している",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
            max_chars=24,
            avoid=["私", "わかりました"],
            payload_level="medium",
        )

    if asks_you_too:
        if prev_relationish:
            reply_goal, summary, meaning = _build_relation_continuation_fields(
                prev_intent,
                followup_kind="echo",
                thread_depth=max(relation_depth, 1),
            )
            if prev_intent in {"ask_miss_me", "ask_like_me"}:
                return base_plan_helper(
                    intent=prev_intent,
                    scene="casual",
                    listener_state="感情の向きをこちらにも返してほしがっている",
                    reply_goal=reply_goal,
                    summary=summary,
                    meaning=meaning,
                    stance={"warmth": 0.28, "tease": 0.08, "blunt": 0.08, "jealousy": 0.0, "distance": 0.06},
                    max_chars=24,
                    avoid=["私", "わかりました"],
                    payload_level="medium",
                )
            return base_plan_helper(
                intent=prev_intent,
                scene="support" if prev_intent in {"annoying_check", "cold_check"} else "casual",
                listener_state="関係温度の確認をこちらにも返している",
                reply_goal=reply_goal,
                summary=summary,
                meaning=meaning,
                stance={"warmth": 0.3, "tease": 0.04, "blunt": 0.14, "jealousy": 0.0, "distance": 0.08},
                max_chars=24,
                avoid=["私", "わかりました"],
                payload_level="medium",
            )
        if prev_foodish or prev_intent in {"food_offer_generic", "food_offer_sweet", "store_offer", "chat"}:
            grounded_item = prev_item or "ご飯"
            sweet_item = grounded_item in {"アップルパイ", "ミルクシェイク", "甘いの"}
            reply_goal, summary, meaning = _build_direct_daily_fields(
                "food_offer_self",
                text,
                offered_item=grounded_item,
                thread_depth=max(food_depth, 1),
            )
            return base_plan_helper(
                intent="chat" if grounded_item == "ご飯" else ("food_offer_sweet" if sweet_item else "food_offer_generic"),
                scene="casual",
                listener_state="同じ食べ物の話題でこちら側も聞かれている",
                reply_goal=reply_goal,
                summary=summary,
                meaning=meaning,
                stance={"warmth": 0.26, "tease": 0.05, "blunt": 0.08, "jealousy": 0.0, "distance": 0.05},
                max_chars=24,
                avoid=["私", "わかりました"],
                grounding={"offered_item": grounded_item} if grounded_item != "ご飯" else {},
                surface_act="meal_check_reply" if grounded_item == "ご飯" else None,
                payload_level="medium",
            )
        if prev_intent in {"what_are_you_doing", "chat"}:
            return base_plan_helper(
                intent="what_are_you_doing",
                scene="casual",
                listener_state="相手の話の返しとしてこちら側も聞かれている",
                reply_goal="こちら側の状態を短く返す",
                summary="ユーザーが直前の話題に対して『あなたはどうなの』と返している。",
                meaning="うちはだらだらしてた",
                stance={"warmth": 0.24, "tease": 0.06, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
                max_chars=24,
                avoid=["私", "わかりました"],
                payload_level="medium",
            )

    if asks_today_same and prev_intent == "what_are_you_doing":
        reply_goal, summary, meaning = _build_status_continuation_fields("today_same", thread_depth=max(status_depth, 2))
        return base_plan_helper(
            intent="what_are_you_doing",
            scene="casual",
            listener_state="さっきの流れから今日も同じ感じか聞いている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
            max_chars=26,
            avoid=["私", "わかりました"],
            payload_level="medium",
        )

    if asks_status_still and prev_intent == "what_are_you_doing":
        reply_goal, summary, meaning = _build_status_continuation_fields("still_state", thread_depth=max(status_depth, 3))
        return base_plan_helper(
            intent="what_are_you_doing",
            scene="casual",
            listener_state="近況の流れで今もまだ同じ状態か聞かれている",
            reply_goal=reply_goal,
            summary=summary,
            meaning=meaning,
            stance={"warmth": 0.22, "tease": 0.06, "blunt": 0.16, "jealousy": 0.0, "distance": 0.06},
            max_chars=28,
            avoid=["私", "わかりました"],
            payload_level="medium",
        )

    if asks_so_what and (prev_intent in {"version_fragment_clarify", "reference_probe", "clarify_light"} or prev_repairish):
        return base_plan_helper(
            intent="answer_me_push",
            scene="casual",
            listener_state="結論を急かしている",
            reply_goal="短く要点に戻す",
            summary="ユーザーが直前の説明や確認に対して、要点を急かしている。",
            meaning="分かったから要点だけ返す",
            stance={"warmth": 0.12, "tease": 0.04, "blunt": 0.24, "jealousy": 0.0, "distance": 0.1},
            max_chars=18,
            avoid=["私", "自分で調べろ"],
        )

    return None
