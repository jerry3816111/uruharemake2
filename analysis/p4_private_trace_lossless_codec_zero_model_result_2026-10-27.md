# P4 private trace codec: zero-model result, not Safari acceptance

Status: **bounded storage mechanism PASS on existing isolated development
rows and synthetic integration contracts; fresh product/Safari pending**.
The frozen design is `research/p4_private_trace_lossless_codec_freeze_2026-10-27.md`;
the frozen-reader SHA amendment is
`research/p4_private_trace_codec_frozen_reader_amendment_2026-10-27.md`.
No archived row, research result, formal DB, or user memory was rewritten.

## Before → after, same logical data

The unchanged 2026-10-21 isolated native-Safari D0–D10 source has 11 rows,
51,242,729 bytes, and SHA-256
`1284bc9fc0d2eac1c2202c2d3f18fe84b0d1e8dadace1f4cdeee8adf6ce31529`.
A **read-only in-memory** pass of the new production `encode_private_log_record`
and `decode_conversation_log_record` yielded:

| Measurement | Plain original | New encoded candidate | Boundary |
|---|---:|---:|---|
| 11-row serialized bytes | 51,242,729 | 9,133,485 | 82.18% less, above the frozen ≥60% engineering threshold |
| Row 11 bytes | 6,716,958 | 1,090,222 | Both below current 16 MiB row cap |
| Full logical equality | — | 11/11 | Every field actually present in each original row; receipt parity is separately synthetic-tested |
| Row 11 write+read median CPU, 7 repeats | 0.0662 s | 0.1468 s | +0.0806 s, below frozen ≤1.0 s threshold |

The production writer now serializes only the full `cognition_trace` inside
owner-only private rows as versioned zlib6/base64 with original length and
SHA-256. Shared strict bounded decoding preserves logical rows for Web graph,
receipt readback and trace-dependent offline tools. Legacy rows stay plain and
readable; public/nonprivate rows remain plain. Browser graph HMAC continues to
bind raw persisted bytes, not the decoded projection. Malformed, unknown,
oversized, incomplete or corrupt latest private rows fail closed. No model
tokens were spent on this batch; benchmark CPU is local-machine only.

## Verification tiers

- Unchanged-source baseline for four adjacent Web files: **83 passed**. The
  initial `python3` resolved to Python 3.14 without pytest; using the
  repository's documented `.venv/product_checks/bin/python` fixed only the
  invocation, not source.
- New codec contract first failed collection on absent module as intended.
  Final affected suite: **206 passed**, 9 dependency/deprecation warnings,
  16.68 s. It covers lossless Unicode/nested parity, legacy/encoded reader
  parity, malformed base64/zlib/length/SHA/version/extra stream/oversize,
  duplicate keys, latest-row corruption without old-row fallback, private
  graph HMAC, semantic episode, compute receipt and nonprivate plain logging.
  Eight M45–M52 audit outputs matched between synthetic legacy/encoded rows
  after excluding their expected source-path metadata. Five render modules
  imported. These are zero-model/synthetic contracts, not visual Safari proof.
- The V84–V88 SHA-locked `planner_supervision_v76.py` and V90-locked
  forbidden-projection builder remain byte-identical to frozen SHA. An
  **explicit** offline bridge decodes new rows before V76 input-context use;
  the old standalone V76 loader itself is not advertised as compressed-log
  compatible.
- A broader historical V90 suite produced **70 passed / 3 failed**. Its
  production-brain and Web SHA expectations were already stale at the
  committed pre-batch HEAD, before this codec, as verified by `git show HEAD`
  hashes. The historical lock was not altered or relabelled PASS. This is a
  separate current-main revalidation debt, not codec or persona evidence.

## What this does not prove and next gate

This has not written a new real-model private row, run a fresh 50-turn
current-product session, measured real browser reload latency, inspected a
native Safari graph, obtained a screenshot, improved reply quality, or solved
P4-B real process containment. The original D0–D10 source was exposed during
development, so the 82.18% figure is a product feasibility measurement, not
holdout/generalization evidence. A fresh isolated Web/Safari turn with private
0700/0600 paths must verify natural Japanese visible reply, new encoded row,
actual graph hydration/content and no formal DB write before Safari acceptance.
A separate reviewed journal/controller design is needed before a new 50-turn
product run; do not reuse the old D run as new evidence. P4-B real B Send
remains `REVIEW_REQUIRED`.
