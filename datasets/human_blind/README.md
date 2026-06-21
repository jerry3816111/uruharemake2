# Human Blind Rating Sources

This directory preserves the raw inputs used by `import_human_blind_evidence.py`.
The importer never edits these files.

## v15 partial pilot

- Original package: `rightbrain_meaning_unseen_v15_fresh_after_reply_priority_repair`.
- `v15_partial_ratings.csv`: exported human ratings; 48 of 160 candidate rows are complete.
- `v15_rating_key.jsonl`: blinded label to system mapping.
- `v15_rating_sheet.csv`: task input and candidate output text.

## v16 compact follow-up

- Original package: `rightbrain_meaning_v16_followup_compact_blind_rating`.
- `v16_partial_ratings.csv`: exported human ratings; 28 of 48 candidate rows are complete.
- `v16_rating_key.jsonl`: blinded label to system mapping.
- `v16_rating_sheet.csv`: task input and candidate output text.

The evidence report compares all four systems. Only rows mapped to
`S0_URUHA_RIGHTBRAIN` are imported into the Uruha human-feedback annotation
stream. Blank ratings and control-system outputs are never counted as Uruha
annotations.

The generated evidence report records SHA-256 hashes for every ratings, key,
and sheet file. Rating timestamps have date-only precision because the source
files establish `2026-05-24`, not an exact completion time.
