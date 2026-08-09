#!/usr/bin/env python3
"""Minimal LoCoMo category-2 F1 scorer derived from the official evaluator."""

from __future__ import annotations

import argparse
import json
import string
from collections import Counter

import regex
from nltk.stem import PorterStemmer


STEMMER = PorterStemmer()


def normalize_answer(value):
    value = str(value).replace(",", "")
    value = value.lower()
    value = "".join(character for character in value if character not in set(string.punctuation))
    value = regex.sub(r"\b(a|an|the|and)\b", " ", value)
    return " ".join(value.split())


def f1_score(prediction, ground_truth):
    prediction_tokens = [
        STEMMER.stem(token) for token in normalize_answer(prediction).split()
    ]
    ground_truth_tokens = [
        STEMMER.stem(token) for token in normalize_answer(ground_truth).split()
    ]
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    same = sum(common.values())
    if same == 0 or not prediction_tokens or not ground_truth_tokens:
        return 0.0
    precision = same / len(prediction_tokens)
    recall = same / len(ground_truth_tokens)
    return (2 * precision * recall) / (precision + recall)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prediction")
    parser.add_argument("ground_truth")
    args = parser.parse_args()
    print(json.dumps({"f1": f1_score(args.prediction, args.ground_truth)}))


if __name__ == "__main__":
    main()
