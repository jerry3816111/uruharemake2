#!/usr/bin/env python3
"""Deterministic target-local discourse cues for V45."""

import re


SENTENCE_BOUNDARY_RE = re.compile(r"[。！？!?；;]")
CLAUSE_BOUNDARY_RE = re.compile(r"[、，,。！？!?；;]")


def _spans(text, boundary_re):
    spans = []
    start = 0
    for match in boundary_re.finditer(text):
        end = match.end()
        spans.append((start, end))
        start = end
    if start < len(text) or not spans:
        spans.append((start, len(text)))
    return spans


def _containing_span(spans, anchor):
    for start, end in spans:
        if anchor["start"] < end and anchor["end"] > start:
            return (start, end)
    return (0, 0)


def detect_focus_discourse_signals(user_input, candidate, patterns):
    text = str(user_input or "")
    compiled = {name: re.compile(pattern) for name, pattern in patterns.items()}
    matches = {
        name: [
            {"signal_type": name, "text": match.group(0), "start": match.start(), "end": match.end()}
            for match in regex.finditer(text)
        ]
        for name, regex in compiled.items()
    }
    sentences = _spans(text, SENTENCE_BOUNDARY_RE)
    clauses = _spans(text, CLAUSE_BOUNDARY_RE)
    rows = []
    for anchor in candidate["anchors"]:
        sentence_start, sentence_end = _containing_span(sentences, anchor)
        clause_start, clause_end = _containing_span(clauses, anchor)
        linked = []
        for signal_type, signal_rows in matches.items():
            for signal in signal_rows:
                same_sentence = (
                    signal["start"] < sentence_end and signal["end"] > sentence_start
                )
                if not same_sentence:
                    continue
                if signal_type == "ongoing_action_cessation":
                    same_clause = signal["start"] < clause_end and signal["end"] > clause_start
                    if not same_clause:
                        continue
                if signal_type == "referential_request_withdrawal" and signal["start"] < anchor["end"]:
                    continue
                linked.append(signal)
        unique = {
            (row["signal_type"], row["start"], row["end"], row["text"]): row
            for row in linked
        }
        rows.append(
            {
                "anchor": {
                    "text": anchor["text"],
                    "start": anchor["start"],
                    "end": anchor["end"],
                },
                "signals": [unique[key] for key in sorted(unique)],
            }
        )
    return rows
