"""Query-conditioned selection for active typed profile memories.

The selector is deliberately independent from answer generation. It returns a
small evidence contract and never authorizes production answer use by itself.
"""

from __future__ import annotations

import resource
import sys
import time
from pathlib import Path


ENCODER_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ENCODER_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"

MEMORY_REQUEST_POSITIVE_SCORE_MIN = 0.2
MEMORY_REQUEST_MARGIN_MIN = 0.02
CANDIDATE_SIMILARITY_MIN = 0.3
CANDIDATE_SIMILARITY_NAME_MIN = 0.28
AMBIGUITY_MARGIN_MIN = 0.04
SELECTED_CANDIDATE_COUNT_MAX = 1

_REQUEST_CUES = (
    "覚えて",
    "思い出",
    "記憶",
    "前に",
    "前の会話",
    "言ってた",
    "話した",
    "教えた",
    "伝えて",
    "更新でき",
    "残ってる",
    "呼び名",
    "呼ばれ方",
    "ニックネーム",
)

_POSITIVE_PROTOTYPES = (
    "以前の会話で私が伝えた個人情報を記憶から思い出して答えて",
    "私について前に話した好みや名前を覚えているか確認したい",
    "保存された私の情報が今も記憶にあるか教えて",
)

_NEGATIVE_PROTOTYPES = (
    "今日は少し疲れたので普通に雑談したい",
    "今の出来事について相談したい",
    "一般的な質問に答えてほしい",
)

_FACT_LABELS = {
    "name": "使用者が呼んでほしい名前",
    "like": "使用者が好きなもの",
    "dislike": "使用者が嫌い・苦手なもの",
    "favorite": "使用者が一番好きなもの",
}


def _rss_bytes():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform == "darwin" else rss * 1024)


class MultilingualProfileSelector:
    """Frozen local encoder and deterministic profile-memory selection policy."""

    def __init__(self):
        from transformers import AutoModel, AutoTokenizer

        rss_before = _rss_bytes()
        started = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(
            ENCODER_MODEL,
            revision=ENCODER_REVISION,
            local_files_only=True,
        )
        self.model = AutoModel.from_pretrained(
            ENCODER_MODEL,
            revision=ENCODER_REVISION,
            local_files_only=True,
            low_cpu_mem_usage=True,
        )
        self.model.eval()
        self.load_seconds = time.perf_counter() - started
        self.peak_rss_delta_bytes = max(0, _rss_bytes() - rss_before)
        self._prototype_vectors = self.encode([*_POSITIVE_PROTOTYPES, *_NEGATIVE_PROTOTYPES])

    def encode(self, texts):
        import torch

        values = [str(text or "").strip() for text in texts]
        tokens = self.tokenizer(
            values,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        )
        with torch.inference_mode():
            hidden = self.model(**tokens).last_hidden_state
            mask = tokens["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            return torch.nn.functional.normalize(pooled, p=2, dim=1)

    @staticmethod
    def candidate_key(candidate, *, include_provenance):
        metadata = candidate.get("metadata") or {}
        fact_type = str(metadata.get("fact_type") or "").casefold()
        value = str(metadata.get("value") or "").strip()
        label = _FACT_LABELS.get(fact_type, "使用者について保存された情報")
        key = f"{label}: {value}"
        source = str(metadata.get("source_utterance") or "").strip()
        if include_provenance and source:
            key += f"。以前の発言: {source}"
        return key

    def select(self, query, candidates, *, include_provenance):
        import torch

        started = time.perf_counter()
        query = str(query or "").strip()
        rows = list(candidates or [])
        query_vector = self.encode([query])
        positive = torch.mv(self._prototype_vectors[: len(_POSITIVE_PROTOTYPES)], query_vector[0])
        negative = torch.mv(self._prototype_vectors[len(_POSITIVE_PROTOTYPES) :], query_vector[0])
        positive_score = float(positive.max().item())
        negative_score = float(negative.max().item())
        semantic_request = (
            positive_score >= MEMORY_REQUEST_POSITIVE_SCORE_MIN
            and positive_score - negative_score >= MEMORY_REQUEST_MARGIN_MIN
        )
        cue_request = any(cue in query for cue in _REQUEST_CUES)
        memory_requested = cue_request or semantic_request

        scored = []
        if memory_requested and rows:
            keys = [self.candidate_key(row, include_provenance=include_provenance) for row in rows]
            vectors = self.encode(keys)
            similarities = torch.mv(vectors, query_vector[0]).tolist()
            for row, key, similarity in zip(rows, keys, similarities):
                scored.append(
                    {
                        "candidate": row,
                        "memory_id": str(row.get("memory_id") or ""),
                        "key": key,
                        "similarity": float(similarity),
                        "threshold": (
                            CANDIDATE_SIMILARITY_NAME_MIN
                            if str((row.get("metadata") or {}).get("fact_type") or "").casefold() == "name"
                            else CANDIDATE_SIMILARITY_MIN
                        ),
                    }
                )
            scored.sort(key=lambda item: (-item["similarity"], item["memory_id"]))

        status = "not_requested"
        selected = []
        if memory_requested:
            eligible = [item for item in scored if item["similarity"] >= item["threshold"]]
            if not eligible:
                status = "requested_but_unavailable"
            elif len(eligible) > 1 and eligible[0]["similarity"] - eligible[1]["similarity"] < AMBIGUITY_MARGIN_MIN:
                status = "requested_but_ambiguous"
            else:
                status = "selected"
                selected = [item["candidate"] for item in eligible[:SELECTED_CANDIDATE_COUNT_MAX]]

        elapsed = time.perf_counter() - started
        return {
            "selected_candidates": selected,
            "contract": {
                "schema": "uruha_profile_memory_selection_v1",
                "status": status,
                "memory_requested": memory_requested,
                "answer_use_authorized": False,
                "selected_memory_ids": [str(row.get("memory_id") or "") for row in selected],
                "request_scores": {
                    "positive": positive_score,
                    "negative": negative_score,
                    "margin": positive_score - negative_score,
                    "lexical_cue": cue_request,
                },
                "candidate_scores": [
                    {
                        key: item[key]
                        for key in ("memory_id", "key", "similarity", "threshold")
                    }
                    for item in scored
                ],
                "selector_seconds": elapsed,
                "include_provenance": bool(include_provenance),
            },
        }


def encoder_snapshot_path():
    return (
        Path.home()
        / ".cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
        / "snapshots"
        / ENCODER_REVISION
    )
