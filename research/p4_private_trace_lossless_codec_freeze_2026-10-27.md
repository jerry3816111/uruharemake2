# P4 private trace lossless codec: prospective design freeze

Status: design only. This is one product storage variable, not a new research M,
formal holdout, or permission to run the blocked P4-B real runner. Same-model
read-only review informed this freeze; it is not an independent human review.

## Before and reason to act

The existing isolated native-Safari D0–D10 private JSONL has 11 rows and
51,242,729 bytes (SHA-256
`1284bc9fc0d2eac1c2202c2d3f18fe84b0d1e8dadace1f4cdeee8adf6ce31529`).
Rows 1/6/11 are 1,151,988/5,338,909/6,716,958 bytes. On row 11,
`cognition_trace` is 6,485,316 bytes and its nested recent-turn traces are
4,574,844 bytes. A read-only UTF-8 JSON + zlib level 6 + base64 candidate
calculation predicts 9,133,562 bytes for those same 11 logical rows (82.2%
less), but has not tested any product writer/reader or new Safari turn. The
browser's latest-row limit is 16 MiB. These are exposed development rows,
not a fresh 50-turn trajectory or general performance claim. Exact provenance
and original single-row extrapolation are in
`analysis/p4_private_long_conversation_disk_trace_before_2026-10-27.md`.

## Single changed variable and disk contract

For **new** rows only, when the already-opened JSONL file and its parent have
the existing owner-only 0600/0700 checks, serialize the complete logical
record first. Replace only the on-disk `cognition_trace` JSON object with a
base64 string of its UTF-8 JSON bytes compressed with zlib level 6. Add one
top-level `cognition_trace_codec` descriptor containing an exact version
(`zlib-json-base64-v1`), original byte length, and SHA-256 of those bytes.
Preserve all other fields, full trace information, and the logical return
value of `_append_conversation_log`. Nonprivate legacy writer behavior remains
plain and does not add private episode/receipt fields. Never rewrite old
rows, frozen evidence, or their hashes.

Put encode/decode in a side-effect-free `uruha_web_log_codec.py`, rather than
importing Web runtime from offline scripts. A legacy row with a dict trace
and no descriptor decodes unchanged. Unknown version, descriptor/trace
mismatch, malformed or noncanonical base64, zlib error, missing stream EOF,
unused appended stream/trailing data, length or SHA mismatch, non-dict JSON,
or duplicate/invalid descriptor fields are explicit errors. Decode with a
streaming output bound of 16 MiB **before** JSON parse; inspect declared
uncompressed length first. A new private row whose full encoded bytes exceed
the current 16 MiB browser cap fails before append. If the trace cannot fit
the decode bound, fail closed rather than truncate or claim durable receipt.
Preexisting too-large plain rows retain existing behavior. No compressed
row is written to a nonprivate log.

The raw persisted row bytes remain the browser graph HMAC input. Decode only
after obtaining/verifying those bytes; `_latest_private_log_row` must reject a
corrupt or incomplete latest row without falling back to an earlier positive.
Its decoded logical record drives graph hydration and compute-ledger retirement.
`_latest_observatory_result` and active offline JSONL readers must use the
same strict decoder, never treat an encoded string as an empty trace. Historical
M45–M52 scripts may need a documented adapter rather than changing frozen
results; any newly supported path must be tested for old/new logical parity.

## Allowed implementation and prohibitions

Allowed: `uruha_web_log_codec.py`, `uruha_web_ui.py`, directly affected active
offline readers, their targeted tests, this plan, a bounded result report, and
`CURRENT_TASK.md`. A small shared reader adapter is allowed if it is the
least-invasive way to preserve the historical render/audit contracts. No
changes to cognitive decisions, model prompts, user memory, VRM, tools,
formal data or comparison baselines. Do not move or re-encode the 11-row
source log. No real Ollama, P4-B B Send, or formal DB access in this slice.

## Acceptance, failure and resources

Before source edits, record unchanged-source focused test behavior; then
implement one batch. Required contract tests: encoded/legacy logical equality
on nested Unicode data; encoded size and descriptor integrity; malformed
base64/zlib/hash/size/extra stream/unknown version/oversize fail closed;
nonprivate writer stays plain; private permissions, incomplete tail and raw
HMAC remain enforced. Product tests must cover graph reload, semantic episode,
compute receipt readback/retirement and annotation/planner readers for both
formats. Do not weaken existing assertions. Run targeted tests first, then
affected Web/reader regressions; avoid unrelated long generation suites.

Quantify encoded bytes and encode/decode CPU on a **separate isolated fixture**.
Engineering acceptance is ≥60% disk-byte reduction versus the exact same
uncompressed logical rows, full logical parity, zero missing evidence, and
≤1.0 s additional row-11 codec CPU on this local machine. This threshold is
for product engineering only, not a scientific effect or external machine
guarantee. Record 0 provider tokens and exact test runtime. After all code
contracts pass, a fresh isolated Web/Safari turn must show a natural Japanese
visible reply and a reloadable, matching graph without writing to formal DB;
until then, Safari/product acceptance is pending. A new 50-turn current-product
run needs a separate controller/journal design; the old D0–D10 is not one.

If a reader loses a field, a receipt retires without verified persistence, a
corrupt latest row is accepted, or benefit/CPU gate fails, retain the failure
as `REVIEW_REQUIRED`; at most two justified revisions, no lossy fallback or
retroactive threshold change. No lower-layer PASS licenses formal P3/M claims.
