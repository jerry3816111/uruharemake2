"""Shadow-only Japanese morphology matcher for RightBrain V32."""

from dataclasses import asdict, dataclass
from functools import lru_cache
import re


CONDITIONS = (
    "legacy_control",
    "lemma_polarity",
    "lemma_polarity_reading",
)
CONTENT_POS = {"名詞", "形容詞", "動詞", "副詞"}
POLARITY_POS = {"形容詞", "動詞"}
NEGATION_LEMMAS = {"ない", "ぬ", "ん"}
KANA_ONLY_RE = re.compile(r"[ぁ-んァ-ヶー]+")


@dataclass(frozen=True)
class JapaneseToken:
    surface: str
    pos: str
    lemma: str
    reading: str
    conjugation_form: str


@dataclass(frozen=True)
class MatchTrace:
    hit: bool
    condition: str
    mode: str
    marker: str
    matched_surface: str = ""
    marker_lemma: str = ""
    matched_lemma: str = ""
    marker_negative: bool | None = None
    reply_negative: bool | None = None

    def to_dict(self):
        return asdict(self)


@lru_cache(maxsize=4096)
def analyze_japanese(text):
    import pyopenjtalk

    rows = pyopenjtalk.run_frontend(str(text or ""))
    return tuple(
        JapaneseToken(
            surface=str(row.get("string") or ""),
            pos=str(row.get("pos") or ""),
            lemma=str(row.get("orig") or row.get("string") or ""),
            reading=str(row.get("read") or ""),
            conjugation_form=str(row.get("cform") or ""),
        )
        for row in rows
        if str(row.get("string") or "").strip()
    )


def _content_tokens(tokens):
    return [
        (index, token)
        for index, token in enumerate(tokens)
        if token.pos in CONTENT_POS and token.lemma not in {"", "*"}
    ]


def _has_following_negation(tokens, index):
    for token in tokens[index + 1 : index + 4]:
        if token.pos in CONTENT_POS:
            if token.surface == "て" and token.lemma == "てる":
                continue
            break
        if token.lemma in NEGATION_LEMMAS or token.surface in NEGATION_LEMMAS:
            return True
    return False


def _marker_negative(tokens, index):
    token = tokens[index]
    return token.conjugation_form.startswith("未然") or _has_following_negation(
        tokens,
        index,
    )


def _reply_negative(tokens, index):
    return _has_following_negation(tokens, index)


def _polarity_matches(marker_tokens, marker_index, reply_tokens, reply_index):
    marker_token = marker_tokens[marker_index]
    if marker_token.pos not in POLARITY_POS:
        return True, None, None
    marker_negative = _marker_negative(marker_tokens, marker_index)
    reply_negative = _reply_negative(reply_tokens, reply_index)
    return (
        marker_negative == reply_negative,
        marker_negative,
        reply_negative,
    )


def _is_kana_marker(marker):
    compact = "".join(KANA_ONLY_RE.findall(str(marker or "")))
    return compact == re.sub(r"\s+", "", str(marker or "")) and len(compact) >= 3


def match_marker(reply, marker, condition, legacy_hit):
    """Match one marker while keeping the frozen legacy matcher observable."""
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown V32 condition: {condition}")
    reply = str(reply or "").strip()
    marker = str(marker or "").strip()
    if not reply or not marker:
        return MatchTrace(False, condition, "empty", marker)

    if bool(legacy_hit(reply, marker)):
        return MatchTrace(True, condition, "legacy", marker)
    if condition == "legacy_control":
        return MatchTrace(False, condition, "none", marker)

    marker_tokens = analyze_japanese(marker)
    reply_tokens = analyze_japanese(reply)
    marker_content = _content_tokens(marker_tokens)
    reply_content = _content_tokens(reply_tokens)
    if len(marker_content) != 1:
        return MatchTrace(False, condition, "unsupported_marker_shape", marker)

    marker_index, marker_token = marker_content[0]
    for reply_index, reply_token in reply_content:
        if (
            reply_token.pos == marker_token.pos
            and reply_token.lemma == marker_token.lemma
        ):
            polarity_ok, marker_negative, reply_negative = _polarity_matches(
                marker_tokens,
                marker_index,
                reply_tokens,
                reply_index,
            )
            if polarity_ok:
                return MatchTrace(
                    True,
                    condition,
                    "lemma",
                    marker,
                    matched_surface=reply_token.surface,
                    marker_lemma=marker_token.lemma,
                    matched_lemma=reply_token.lemma,
                    marker_negative=marker_negative,
                    reply_negative=reply_negative,
                )

    if condition != "lemma_polarity_reading" or not _is_kana_marker(marker):
        return MatchTrace(False, condition, "none", marker)
    if marker_token.pos != "名詞" or not marker_token.reading:
        return MatchTrace(False, condition, "reading_not_allowed", marker)

    for _, reply_token in reply_content:
        if (
            reply_token.pos == marker_token.pos
            and reply_token.reading == marker_token.reading
        ):
            return MatchTrace(
                True,
                condition,
                "reading",
                marker,
                matched_surface=reply_token.surface,
                marker_lemma=marker_token.lemma,
                matched_lemma=reply_token.lemma,
            )
    return MatchTrace(False, condition, "none", marker)


def match_group(reply, group, condition, legacy_hit):
    traces = [
        match_marker(reply, marker, condition, legacy_hit)
        for marker in group
    ]
    return any(trace.hit for trace in traces), traces
