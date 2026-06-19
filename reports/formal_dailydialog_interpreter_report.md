# Formal DailyDialog Interpreter Report

- generated_at: 2026-06-19T12:18:37
- sample_size: 60
- labeler: official_utterance_interpreter_v3_v2

## Scores

- dialog_act_accuracy: 1.0
- dialog_act_macro_f1: 1.0
- emotion_accuracy: 1.0
- emotion_macro_f1: 0.5714

## Method

- Source: official DailyDialog test split sample from the configured Hugging Face dataset.
- Scoring: exact match against official utterance-level act and emotion IDs.
- Runtime: labeler-only; no local LLM planner call is required for this report.
- Purpose: measure dialogue-act/emotion interpretation, not final Japanese surface generation.

## Act Breakdown

| act | count | one-vs-rest accuracy |
| --- | ---: | ---: |
| inform | 20 | 1.0 |
| question | 15 | 1.0 |
| directive | 15 | 1.0 |
| commissive | 10 | 1.0 |

## Emotion Breakdown

| emotion | count | one-vs-rest accuracy |
| --- | ---: | ---: |
| none | 46 | 1.0 |
| anger | 2 | 1.0 |
| disgust | 0 | 1.0 |
| fear | 0 | 1.0 |
| happiness | 9 | 1.0 |
| sadness | 0 | 1.0 |
| surprise | 3 | 1.0 |
