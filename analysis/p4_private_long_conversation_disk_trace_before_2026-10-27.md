# P4 private long-conversation trace storage: read-only before audit

Status: **problem and dependencies located; no storage code, compression
ratio, Safari acceptance, or product improvement yet**. This is independent
of the P4-B real runner containment NO-GO. It serves the local-PC long-chat
and reloadable node-graph product requirement; it is not a new research M.

## Measured problem versus extrapolation

- The frozen cost0/cost1 isolated private rows were 1,081,976 and 1,079,953
  bytes; their `cognition_trace` portions were about 853–855 KB and complete
  compute receipts about 17.6 KB
  (`research/p4_product_turn_compute_retention_plan_2026-10-23.md`).
- A distinct fresh `retention0` Safari row was 1,067,339 bytes
  (`analysis/p4_product_turn_compute_retention_fresh_product_result_2026-10-23.md`).
  Fifty rows at that one-row size would occupy 53,366,950 bytes (~50.9 MiB).
  **That is an extrapolation, not a measured 50-turn product session**; real
  row size, RSS, reload latency and disk growth could vary.
- The prior 50-turn zero-model test proved scoped ledger calls retire from
  RAM. It did **not** compress the append-only private JSONL. This audit did
  not reopen a representative private row or measure a new compression ratio.

## Why deleting trace fields would lose evidence

`uruha_web_ui.py:_append_conversation_log` writes full `cognition_trace`
with each row. `_observatory_result_from_log_record` uses
`runtime_trace`/`runtime_state` for the reloaded graph; the semantic episode
selector needs `psyche_after`; annotation proxy uses
`runtime_trace.selected_plan`. `planner_supervision_v76.input_context_from_log`
uses `psyche_before`, while route/psyche information also feeds historical
regression and provenance tools. The M24 browser contract says a compact
client payload is only a view; full trace must remain in local JSONL. A
truncated or browser-budgeted trace is not an acceptable disk fix.

The Web has two direct conversation-log readers:
`_latest_observatory_result` (backward history scan) and
`_latest_private_log_row` (strict latest-row read for graph receipt,
hydration and compute retirement). The latter authenticates **raw row
bytes** with the browser HMAC and must continue to reject incomplete,
nonprivate or changed rows rather than falling back to an older positive.
Several offline readers use direct `json.loads` (including
`planner_supervision_v76`, annotation candidate/draft and regression
builders, and M45–M52 audit/render tools). A new on-disk encoding without
strict, shared decoding across these consumers would silently turn a
storage saving into missing or false research evidence. Existing archived
rows and their hashes must stay unchanged.

## Next necessary scoped design gate

Prospectively specify **one reversible storage-format variable** for *new*
owner-only 0700-directory/0600-file private rows, with a version marker,
bounded lossless decode and integrity check; legacy plain rows remain
readable. Compare candidate trace encoding on a fixed isolated development
fixture before setting a size/CPU threshold. The design must map every
reader above, preserve the logical row exactly (including source, graph,
episode and compute item ID), keep the browser HMAC on raw persisted bytes,
and fail closed for unknown codec, corruption, over-limit expansion,
truncated latest row or unsafe file permissions. No lossy deletion or
conversion of old frozen logs is allowed.

After design review, a single implementation batch may use zero-model
50-turn isolated rows to compare bytes and CPU/reload latency, run affected
graph/annotation/receipt regressions and then one new isolated native Safari
turn for real product observation. This audit authorizes none of those code
changes or model calls yet. If the measured benefit is too small or any
consumer loses evidence, retain the negative result rather than weakening
the reader contract. Formal user DB, original dirty checkout and unrelated
`output/graduate_application_report/` remain out of scope.
