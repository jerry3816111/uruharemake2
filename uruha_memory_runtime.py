import re
import datetime

def memory_tokens(text):
    """提取用於計算相關性的 token (包含中日文與英數)."""
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u4e00-\u9fff]{1,4}", text.lower())
    return [token for token in tokens if len(token.strip()) >= 1]

def clean_fact_value(value):
    """清理事實描述中的多餘標點符號."""
    if not value:
        return ""
    value = re.sub(r"^[\s:=：,，.。!?！？'\"`]+|[\s:=：,，.。!?！？'\"`]+$", "", str(value))
    value = re.sub(r"\s+", " ", value).strip()
    return value[:32]

def _contains_any_text(text, terms):
    lowered = str(text or "").lower()
    return any(str(term).lower() in lowered for term in terms)

def assess_memory_speakability(anchor, user_input="", trust=50):
    """
    判斷一段記憶現在是否適合被說出口.

    這層不是檢索分數，而是人類式的「社交閘門」：
    有些記憶可以直接說，有些只能作為背景判斷，有些即使想起來也不該講。
    """
    if not anchor:
        return {
            "label": "no_memory",
            "reason": "no_anchor",
            "should_use_explicitly": False,
            "can_quote": False,
            "gravity_multiplier": 0.0,
        }

    source_text = str(anchor.get("source_text") or "")
    value = str(anchor.get("value") or "")
    jp_anchor = str(anchor.get("jp_anchor") or "")
    combined = " ".join([source_text, value, jp_anchor])
    expected = bool(anchor.get("expected"))
    relevance = float(anchor.get("relevance") or 0.0)
    try:
        trust_value = float(trust)
    except Exception:
        trust_value = 50.0

    direct_memory_query = _contains_any_text(
        user_input,
        [
            "記得",
            "记得",
            "覚えて",
            "remember",
            "還記得",
            "还记得",
            "叫什么",
            "叫什麼",
            "剛剛說",
            "刚刚说",
            "我剛剛",
            "我刚刚",
            "名前",
            "呼んで",
            "what did i",
            "さっき",
        ],
    )
    sensitive = _contains_any_text(
        combined,
        [
            "password",
            "密碼",
            "密码",
            "パスワード",
            "住所",
            "address",
            "電話",
            "phone",
            "病院",
            "病気",
            "診断",
            "秘密",
            "secret",
            "日記",
            "diary",
            "隱私",
            "隐私",
            "private",
        ],
    )
    third_party = _contains_any_text(
        combined,
        [
            "他說",
            "她說",
            "他说",
            "她说",
            "朋友",
            "同學",
            "同学",
            "先生",
            "彼女",
            "彼氏",
            "母親",
            "父親",
            "媽媽",
            "爸爸",
            "mom",
            "dad",
            "friend",
        ],
    )

    if sensitive:
        return {
            "label": "suppressed_sensitive",
            "reason": "sensitive_memory",
            "should_use_explicitly": False,
            "can_quote": False,
            "gravity_multiplier": 0.15 if direct_memory_query else 0.0,
        }
    if third_party and not direct_memory_query:
        return {
            "label": "suppressed_third_party",
            "reason": "third_party_memory_without_request",
            "should_use_explicitly": False,
            "can_quote": False,
            "gravity_multiplier": 0.2,
        }
    if trust_value < 25 and not direct_memory_query:
        return {
            "label": "background_only",
            "reason": "low_trust_do_not_surface",
            "should_use_explicitly": False,
            "can_quote": False,
            "gravity_multiplier": 0.35,
        }
    if expected or direct_memory_query:
        return {
            "label": "explicit_ok",
            "reason": "directly_relevant_or_requested",
            "should_use_explicitly": True,
            "can_quote": True,
            "gravity_multiplier": 1.0,
        }
    if relevance >= 0.45:
        return {
            "label": "background_only",
            "reason": "relevant_but_not_requested",
            "should_use_explicitly": False,
            "can_quote": False,
            "gravity_multiplier": 0.55 if relevance >= 0.72 else 0.45,
        }
    return {
        "label": "latent_ok",
        "reason": "weak_contextual_memory",
        "should_use_explicitly": False,
        "can_quote": False,
        "gravity_multiplier": 0.25,
    }

def attention_factors(candidate, query_tokens, now):
    """
    拆解記憶候選者的注意力來源.

    這層對應人類的「注意力閘門」：不是只看向量相似度，而是同時看情緒強度、
    自我相關性、未完成事件與危險訊號。
    """
    metadata = candidate.get("metadata") or {}
    text = str(candidate.get("text", "") or "")

    distance = candidate.get("distance")
    if distance is None:
        similarity_score = 0.22
    else:
        similarity_score = max(0.0, 1.0 - min(1.0, float(distance)))

    text_tokens = memory_tokens(text)
    overlap = len(set(query_tokens) & set(text_tokens))
    overlap_bonus = min(0.45, overlap * 0.09)

    recency_bonus = 0.0
    timestamp = metadata.get("timestamp")
    if timestamp:
        try:
            if isinstance(timestamp, str):
                ts_dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            else:
                ts_dt = timestamp
            age_seconds = max(0.0, (now - ts_dt).total_seconds())
            recency_bonus = 1.0 / ((age_seconds / 3600.0) + 1.0)
        except Exception:
            recency_bonus = 0.0
    elif candidate.get("source") in {"short_term", "recent_turn", "profile"}:
        recency_bonus = 0.4

    strength_bonus = 0.0
    strength = metadata.get("strength")
    try:
        if strength is not None:
            strength_bonus = min(0.35, max(0.0, float(strength)) * 0.28)
    except Exception:
        strength_bonus = 0.0

    source_bias = {
        "short_term": 0.28,
        "recent_turn": 0.24,
        "profile": 0.18,
        "procedural": 0.12,
        "episode": 0.08,
        "wisdom": 0.05,
        "knowledge": 0.0,
    }.get(candidate.get("source"), 0.0)

    emotional_bonus = 0.0
    for key in ("emotional_weight", "mood_impact", "trust_impact", "salience"):
        try:
            if metadata.get(key) is not None:
                emotional_bonus = max(emotional_bonus, min(0.22, abs(float(metadata.get(key))) * 0.08))
        except Exception:
            continue

    self_relevance_terms = [
        "うち",
        "一ノ瀬",
        "Uruha",
        "uruha",
        "ユーザー",
        "使用者",
        "相手",
        "好き",
        "嫌い",
        "覚えて",
        "remember",
        "名前",
        "name",
    ]
    self_relevance_bonus = 0.16 if any(term in text for term in self_relevance_terms) else 0.0

    unresolved_bonus = 0.0
    if metadata.get("unresolved") or metadata.get("open_loop") or metadata.get("pending"):
        unresolved_bonus = 0.18
    elif candidate.get("source") == "procedural":
        unresolved_bonus = 0.1

    threat_terms = [
        "死",
        "消え",
        "危ない",
        "怖",
        "嫌",
        "痛",
        "操你",
        "fuck",
        "bitch",
        "懶叫",
        "ちんこ",
    ]
    threat_bonus = 0.18 if any(term.lower() in text.lower() for term in threat_terms) else 0.0

    decay_penalty = 0.0
    if metadata.get("decay_flag"):
        decay_penalty += 0.28
    try:
        decay_multiplier = float(metadata.get("decay_multiplier", 1.0) or 1.0)
    except Exception:
        decay_multiplier = 1.0

    brevity_penalty = 0.0 if len(text) <= 120 else 0.12
    raw_score = (
        similarity_score
        + recency_bonus
        + overlap_bonus
        + strength_bonus
        + source_bias
        + emotional_bonus
        + self_relevance_bonus
        + unresolved_bonus
        + threat_bonus
        - brevity_penalty
        - decay_penalty
    )
    score = raw_score * max(0.3, min(1.0, decay_multiplier))
    return {
        "similarity": round(similarity_score, 4),
        "overlap": round(overlap_bonus, 4),
        "recency": round(recency_bonus, 4),
        "strength": round(strength_bonus, 4),
        "source_bias": round(source_bias, 4),
        "emotional": round(emotional_bonus, 4),
        "self_relevance": round(self_relevance_bonus, 4),
        "unresolved": round(unresolved_bonus, 4),
        "threat": round(threat_bonus, 4),
        "brevity_penalty": round(brevity_penalty, 4),
        "decay_penalty": round(decay_penalty, 4),
        "decay_multiplier": round(max(0.3, min(1.0, decay_multiplier)), 4),
        "score": round(score, 4),
    }

def salience_score(candidate, query_tokens, now):
    """
    計算記憶候選者的顯著性分數 (Salience Score).

    考慮因素:
    - 相似度 (Distance)
    - Token 重疊度 (Overlap)
    - 時效性 (Recency)
    - 強化程度 (Strength)
    - 來源偏見 (Source Bias)
    - 長度懲罰 (Brevity Penalty)
    - 衰減 (Decay)
    """
    return attention_factors(candidate, query_tokens, now)["score"]

def build_working_memory(text, candidates, working_memory_limit=5):
    """從候選記憶中挑選最顯著的放入 Working Memory."""
    query_tokens = memory_tokens(text)
    now = datetime.datetime.now()

    scored = []
    seen = set()
    for candidate in candidates:
        normalized = re.sub(r"\s+", " ", candidate["text"]).strip()
        if not normalized:
            continue
        # 使用 (來源, 前120字) 作為去重 key
        key = (candidate["source"], normalized[:120])
        if key in seen:
            continue
        seen.add(key)

        item = dict(candidate)
        item["attention_factors"] = attention_factors(item, query_tokens, now)
        item["score"] = item["attention_factors"]["score"]
        scored.append(item)

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:working_memory_limit]

def working_memory_summary(items, working_memory_limit=5):
    """產生 Working Memory 的文字摘要."""
    if not items:
        return "無工作記憶內容"
    return " || ".join(
        f"{item['source']}[{item['score']:.2f}]: {item['text'][:80]}"
        for item in items[:working_memory_limit]
    )

def profile_snapshot(session_profile):
    """從 session profile 建立快照."""
    return {
        "name": session_profile.get("name"),
        "likes": list((session_profile.get("likes") or [])[:6]),
        "dislikes": list((session_profile.get("dislikes") or [])[:6]),
        "favorites": list((session_profile.get("favorites") or [])[:6]),
    }

def profile_summary(session_profile):
    """產生個人資料摘要字串."""
    parts = []
    if session_profile.get("name"):
        parts.append(f"Name={session_profile['name']}")

    favs = session_profile.get("favorites") or []
    if favs:
        parts.append("Favorites=" + "/".join(favs[:3]))

    likes = session_profile.get("likes") or []
    if likes:
        parts.append("Likes=" + "/".join(likes[:4]))

    dislikes = session_profile.get("dislikes") or []
    if dislikes:
        parts.append("Dislikes=" + "/".join(dislikes[:4]))

    return " | ".join(parts) if parts else "無穩定使用者資料"

def recent_dialogue_summary(session_turns):
    """產生近期對話摘要."""
    if not session_turns:
        return "無近期對話"
    slices = session_turns[-4:]
    return " || ".join(
        f"User:{turn.get('user', '')} -> Uruha:{turn.get('reply', '')}" for turn in slices
    )

def short_term_summary(short_term_buffer):
    """產生短期緩衝摘要."""
    if not short_term_buffer:
        return "無短期緩衝"
    visible = []
    for item in short_term_buffer[-4:]:
        text = clean_fact_value(item.get('text', ''))
        visible.append(f"{item.get('strength', 0.0):.2f}:{text[:36]}")
    return " || ".join(visible) if visible else "無短期緩衝"

def query_collection_candidates(collection, text, source, limit=20):
    """封裝 ChromaDB 集合查詢並轉為候選格式."""
    try:
        res = collection.query(
            query_texts=[text],
            n_results=limit,
            include=["documents", "metadatas", "distances", "ids"],
        )
    except Exception:
        return []

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    ids = (res.get("ids") or [[]])[0]

    candidates = []
    for idx, doc in enumerate(docs):
        if not isinstance(doc, str) or not doc.strip():
            continue
        candidates.append(
            {
                "source": source,
                "text": doc.strip(),
                "metadata": metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {},
                "distance": float(distances[idx]) if idx < len(distances) and distances[idx] is not None else None,
                "memory_id": ids[idx] if idx < len(ids) else None,
                "collection_name": source,
            }
        )
    return candidates

def recent_turn_candidates(session_turns):
    """將近期對話轉為候選格式."""
    candidates = []
    for turn in session_turns[-8:]:
        text = f"User:{turn.get('user', '')} -> Uruha:{turn.get('reply', '')}".strip()
        if not text:
            continue
        candidates.append(
            {
                "source": "recent_turn",
                "text": text,
                "metadata": {
                    "timestamp": turn.get("timestamp"),
                    "intent": turn.get("intent"),
                    "scene": turn.get("scene")
                },
                "distance": 0.0,
            }
        )
    return candidates

def short_term_candidates(short_term_buffer):
    """將短期緩衝轉為候選格式."""
    candidates = []
    for item in short_term_buffer[-12:]:
        text = item.get("text", "").strip()
        if not text:
            continue
        candidates.append(
            {
                "source": "short_term",
                "text": text,
                "metadata": {
                    "timestamp": item.get("timestamp"),
                    "strength": item.get("strength", 0.0),
                    "intent": item.get("intent"),
                    "scene": item.get("scene"),
                },
                "distance": 0.0,
            }
        )
    return candidates

def profile_candidates(profile_snapshot_data):
    """將個人資料快照轉為候選格式."""
    candidates = []
    if profile_snapshot_data.get("name"):
        candidates.append(
            {
                "source": "profile",
                "text": f"Name={profile_snapshot_data['name']}",
                "metadata": {"field": "name"},
                "distance": 0.0,
            }
        )
    for field in ("favorites", "likes", "dislikes"):
        for value in profile_snapshot_data.get(field, [])[:3]:
            candidates.append(
                {
                    "source": "profile",
                    "text": f"{field}={value}",
                    "metadata": {"field": field},
                    "distance": 0.0,
                }
            )
    return candidates
