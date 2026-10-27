# P4 private long-conversation trace storage: read-only before audit

Status: **problem and dependencies located; no storage code, codec acceptance,
new Safari turn, or product improvement yet**. This is independent
of the P4-B real runner containment NO-GO. It serves the local-PC long-chat
and reloadable node-graph product requirement; it is not a new research M.

## Same-day correction: existing multi-turn product evidence

The single-row extrapolation below was insufficient to decide priority.
After that first audit, a read-only check found the existing 2026-10-21
**real isolated Safari D0–D10 log** (not formal user data) still present in
its owner-only root. Its 11-row file is **51,242,729 bytes**, and its SHA-256
matches the frozen report's
`1284bc9fc0d2eac1c2202c2d3f18fe84b0d1e8dadace1f4cdeee8adf6ce31529`
(`analysis/p4_current_decision_ack_fresh_product_probe_result_2026-10-21.md`).
No dialogue text was printed. Byte lengths of rows 1, 6 and 11 are
1,151,988 / 5,338,909 / 6,716,958. Their `cognition_trace` JSON sizes are
1,033,817 / 5,150,405 / 6,485,316 bytes. By row 11,
`runtime_state.recent_turn_traces` alone is 4,574,844 bytes; the snapshot
duplicates bounded recent traces into each new row. This is a measured
11-turn growth pattern, **not proof of what a fresh 50-turn run would do**.

A read-only fixed candidate calculation (UTF-8 trace JSON, zlib level 6,
base64, version/length/SHA envelope; no writes) gave an estimated total of
**9,133,562 bytes** for those exact 11 logical rows, versus 51,242,729 raw
bytes: about **82.2% smaller**. The row-11 trace by itself compressed from
6,485,316 to 643,804 zlib bytes before base64/envelope. This is development
sample feasibility only: no codec is implemented, no new row has been written,
and decode correctness, CPU, browser graph and offline readers are untested.
It does make the storage-format gate materially more justified than the
earlier 1 MB/turn extrapolation. The browser latest-row hard cap is 16 MiB;
the observed 6.72 MB final row has not crossed it, but accumulated traces
could make future rows fail closed. Do not silently relabel this as a
50-turn or production failure.

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
  RAM. It did **not** compress the append-only private JSONL. The initial
  audit had no representative raw row; the same-day correction above adds
  the existing isolated 11-turn size and a read-only codec estimate.

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
