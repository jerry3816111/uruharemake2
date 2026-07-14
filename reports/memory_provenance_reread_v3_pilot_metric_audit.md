# Memory Provenance V3 Pilot Metric Audit

## Frozen pilot observation

- Run time: 2026-07-14 (UTC).
- Cases: four preregistered cases covering development/transfer and
  answerable/unanswerable states.
- Raw pilot report SHA-256:
  `e145dd0e644b5218ee0ee977761929949a3d0d411b512b721281e04d02653138`.
- Raw result payload SHA-256:
  `2adac87be149dba89d401b4936e48e435b886fe6157e05c6e70a9a47c74e702a`.

The model followed the extraction instruction and copied the shortest supporting
sentence. For example, the frozen gold utterance was:

> No, that was only your guess. I keep them in the bottom pantry drawer now.

The extracted, source-grounded evidence was:

> I keep them in the bottom pantry drawer now.

The initial metric required exact equality with the whole utterance and therefore
reported evidence recall as 0%, even though the shorter quote was a verbatim source
span and carried the answer.

## Correction before the full run

Evidence recall now counts a hit only when the admitted quote and frozen gold
utterance have an exact substring relationship. A paraphrase still fails. This
matches the frozen prompt's requirement to copy the shortest supporting sentence.

No dataset, gold answer, inference prompt, model setting, gate rule, or generated
response was changed. A regression test covers both the accepted shortest verbatim
sentence and a rejected semantic paraphrase. The full experiment must start from a
clean report after this correction rather than resume the pre-correction pilot.
