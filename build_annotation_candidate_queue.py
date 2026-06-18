import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

from project_paths import (
    ANNOTATION_CANDIDATE_QUEUE_JSON_PATH,
    ANNOTATION_CANDIDATE_QUEUE_MD_PATH,
    WEB_CONVERSATION_LOG_JSONL_PATH,
)


GENERIC_REPLY_SET = {
    "まあそんな感じか",
    "はいはい分かったし",
    "別にいいけど",
    "そうなんだ",
    "分かった",
    "ふーん",
    "あっそ",
    "それは普通にだるいな",
    "それはしんどいよな",
    "そういうのは自分で調べろ",
    "そういうのは自分で調べろって",
}
ABUSE_MARKERS = ["操", "幹", "妈", "媽", "bitch", "fuck", "死ね", "きも", "懶覺", "ちんこ", "爛", "臭", "shut up"]
SUPPORT_MARKERS = ["累", "哭", "難過", "sad", "tired", "cry", "しんど", "つら", "泣", "消えたい", "不想活", "想死"]
QUESTION_MARKERS = ["?", "？", "嗎", "么", "嗎？", "何", "なん", "なに", "who", "what", "why", "how", "哪", "怎麼", "要不要"]
COMFORT_MARKERS = ["大丈夫", "泣か", "無理すんな", "休め", "落ち着け", "大変", "つらい", "しんどい"]
JOKE_CULTURE_MARKERS = [
    "魔性日",
    "歌詞",
    "lyrics",
    "消防車",
    "消防員",
    "平底鍋",
    "平底锅",
    "通關密語",
    "通关密语",
    "紗西斯",
    "水素",
    "日版",
    "believer",
    "茨",
    "願い",
]
BOUNDARY_COMPLIANCE_MARKERS = ["ほしい", "もらう", "食べる", "いいよ", "分かった"]
ENGLISH_WORD_RE = re.compile(r"[A-Za-z]{3,}")
TOKEN_RE = re.compile(r"[A-Za-z0-9_']+|[\u3040-\u30ff\u4e00-\u9fff]{1,4}")


def normalize_text(text):
    text = str(text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[。．.!！？?,，、~〜…/／]+", "", text)
    return text


def reply_tokens(text):
    return TOKEN_RE.findall(str(text or ""))


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def score_record(record, reply_counter):
    user_text = str(record.get("user_text") or "").strip()
    reply = str(record.get("assistant_reply") or "").strip()
    logic = record.get("logic") or {}
    planner = record.get("planner_debug") or {}
    scene = str(logic.get("scene") or planner.get("scene") or "")
    intent = str(logic.get("intent") or planner.get("intent") or "")
    normalized_reply = normalize_text(reply)
    reasons = []
    score = 0

    if not reply:
        reasons.append({"code": "EMPTY_REPLY", "weight": 5, "detail": "assistant reply is empty"})
        score += 5

    token_count = len(reply_tokens(reply))
    unique_token_count = len({token.lower() for token in reply_tokens(reply)})
    if token_count <= 3 or len(reply) < 10:
        reasons.append({"code": "LOW_DENSITY", "weight": 3, "detail": f"reply too short token_count={token_count}"})
        score += 3
    if unique_token_count <= 2 and token_count <= 5:
        reasons.append({"code": "LOW_VARIETY", "weight": 2, "detail": f"reply has little lexical variety unique_tokens={unique_token_count}"})
        score += 2

    if normalized_reply in GENERIC_REPLY_SET:
        reasons.append({"code": "GENERIC_REPLY", "weight": 4, "detail": "reply matches known generic fallback"})
        score += 4

    duplicate_count = reply_counter.get(normalized_reply, 0)
    if normalized_reply and duplicate_count >= 2:
        reasons.append({"code": "REPEATED_REPLY", "weight": min(5, duplicate_count), "detail": f"same reply seen {duplicate_count} times in log"})
        score += min(5, duplicate_count)

    english_words = ENGLISH_WORD_RE.findall(reply)
    if english_words:
        reasons.append({"code": "ENGLISH_LEAK", "weight": 4, "detail": f"reply leaked English words={english_words[:5]}"})
        score += 4

    if "自分で調べろ" in reply:
        reasons.append({"code": "HARSH_FIXED_TEMPLATE", "weight": 4, "detail": "contains repeated self-search fallback"})
        score += 4

    lowered_user = user_text.lower()
    abuse_hit = any(marker.lower() in lowered_user for marker in ABUSE_MARKERS)
    support_hit = any(marker.lower() in lowered_user for marker in SUPPORT_MARKERS)
    question_hit = any(marker.lower() in lowered_user for marker in QUESTION_MARKERS)

    if abuse_hit and (scene == "support" or "support" in intent.lower()):
        reasons.append({"code": "MISREAD_ABUSE_AS_SUPPORT", "weight": 5, "detail": f"scene={scene} intent={intent}"})
        score += 5
    if abuse_hit and any(marker in reply for marker in COMFORT_MARKERS):
        reasons.append({"code": "COMFORT_ON_ABUSE", "weight": 4, "detail": "reply sounds comforting even though user is insulting / provoking"})
        score += 4
    if abuse_hit and any(marker in reply for marker in BOUNDARY_COMPLIANCE_MARKERS):
        reasons.append({"code": "WRONG_BOUNDARY_COMPLIANCE", "weight": 5, "detail": "reply appears to comply with abusive or sexualized phrasing"})
        score += 5
    if support_hit and scene == "refusal":
        reasons.append({"code": "MISREAD_SUPPORT_AS_REFUSAL", "weight": 4, "detail": f"scene={scene} intent={intent}"})
        score += 4
    if question_hit and token_count <= 3:
        reasons.append({"code": "QUESTION_UNDERANSWERED", "weight": 3, "detail": "user asked a question but answer is extremely short"})
        score += 3
    if any(marker.lower() in lowered_user for marker in JOKE_CULTURE_MARKERS) and (
        normalized_reply in GENERIC_REPLY_SET or any(marker in reply for marker in COMFORT_MARKERS) or token_count <= 4
    ):
        reasons.append({"code": "MISSED_CULTURE_CONTEXT", "weight": 4, "detail": "possible meme/lyric/nonsense context was answered too generically"})
        score += 4

    return {
        "candidate_id": f"{record.get('session_id') or 'unknown'}:{record.get('turn_index')}",
        "timestamp": record.get("timestamp"),
        "session_id": record.get("session_id"),
        "turn_index": record.get("turn_index"),
        "user_text": user_text,
        "assistant_reply": reply,
        "scene": scene,
        "intent": intent,
        "score": score,
        "reason_codes": [item["code"] for item in reasons],
        "reasons": reasons,
    }


def build_report(records):
    normalized_replies = [normalize_text(record.get("assistant_reply")) for record in records if normalize_text(record.get("assistant_reply"))]
    reply_counter = Counter(normalized_replies)
    scored = [score_record(record, reply_counter) for record in records]
    candidates = [row for row in scored if row.get("score", 0) > 0]
    candidates.sort(key=lambda row: (row.get("score", 0), row.get("timestamp") or ""), reverse=True)

    reason_counter = Counter()
    for row in candidates:
        reason_counter.update(row.get("reason_codes") or [])

    session_counter = defaultdict(int)
    for row in candidates:
        session_counter[row.get("session_id") or "unknown"] += 1

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_path": WEB_CONVERSATION_LOG_JSONL_PATH,
        "summary": {
            "total_logged_turns": len(records),
            "candidate_count": len(candidates),
            "high_priority_count": sum(1 for row in candidates if row.get("score", 0) >= 8),
            "medium_priority_count": sum(1 for row in candidates if 4 <= row.get("score", 0) < 8),
            "low_priority_count": sum(1 for row in candidates if 1 <= row.get("score", 0) < 4),
            "session_count_with_candidates": len(session_counter),
        },
        "reason_breakdown": [
            {"code": code, "count": count}
            for code, count in reason_counter.most_common()
        ],
        "top_sessions": [
            {"session_id": session_id, "candidate_count": count}
            for session_id, count in sorted(session_counter.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
        "candidates": candidates[:100],
    }
    return report


def build_markdown(report):
    summary = report.get("summary") or {}
    lines = [
        "# Annotation Candidate Queue",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- source_path: `{report.get('source_path')}`",
        "",
        "## Summary",
        "",
        f"- total_logged_turns: {summary.get('total_logged_turns', 0)}",
        f"- candidate_count: {summary.get('candidate_count', 0)}",
        f"- high_priority_count: {summary.get('high_priority_count', 0)}",
        f"- medium_priority_count: {summary.get('medium_priority_count', 0)}",
        f"- low_priority_count: {summary.get('low_priority_count', 0)}",
        f"- session_count_with_candidates: {summary.get('session_count_with_candidates', 0)}",
        "",
        "## Reason Breakdown",
        "",
    ]
    for row in report.get("reason_breakdown") or []:
        lines.append(f"- {row.get('code')}: {row.get('count')}")
    if not (report.get("reason_breakdown") or []):
        lines.append("- none")

    lines.extend(["", "## Top Candidates", ""])
    for row in report.get("candidates") or []:
        lines.append(
            f"- score={row.get('score')} id={row.get('candidate_id')} scene={row.get('scene')} intent={row.get('intent')} "
            f"reasons={row.get('reason_codes')} user={row.get('user_text')} reply={row.get('assistant_reply')}"
        )
    if not (report.get("candidates") or []):
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main():
    records = load_jsonl(WEB_CONVERSATION_LOG_JSONL_PATH)
    report = build_report(records)

    with open(ANNOTATION_CANDIDATE_QUEUE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(ANNOTATION_CANDIDATE_QUEUE_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(ANNOTATION_CANDIDATE_QUEUE_JSON_PATH)
    print(ANNOTATION_CANDIDATE_QUEUE_MD_PATH)
    print(json.dumps(report.get("summary") or {}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
