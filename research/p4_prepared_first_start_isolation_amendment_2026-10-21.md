# P4 C probe: prospective first-start isolation amendment

Status: **setup design only; zero C model or Safari turns**. This amendment
does not alter the already frozen C0–C9 inputs or conditional gold, the
retrospective actor product binary frozen at `852de83`, or prior B failures.
It is a prerequisite to test the C product without repeating B's observed
zero-turn external ONNX download attempt. No result is presumed.

## Before and single setup variable

`p4_local_fact_answer_authority_detached_control.py` delegates to
`p4_preference_fallback_detached_control.py`. The latter's first `start`
creates a private root **and immediately launches** its exact entrypoint.
`--reuse-runtime-root` only accepts an earlier run with same-PID ready and
planned-stop receipts. Thus there is no supported interval in which a fresh
controller-owned root can receive an independent official-SHA ONNX cache and
network-disabled prewarm before the very first server launch. B's first
zero-turn stderr actually attempted a download. The C plan requires the
opposite, so continuing without a lifecycle change would knowingly FAIL its
isolation gate.

**Only changed variable:** an additive, one-use `prepare` →
`start --prepared-runtime-root` first-start path in the existing exact-identity
controller. Prepared start is product-only and mutually exclusive with
`--reuse-runtime-root`. Default `start`, stopped-root reuse, PID/port/
HTTP readiness, planned stop, product entrypoint, model, DB, UI, C probes,
gold and cognitive code must stay unchanged. `prepare` creates a new
launcher-owned owner-0700 root, private layout and owner-0600 controller
receipt; it neither starts a process nor opens the model or network. The
prepared first-start path checks an immediate `uruha-product-*` child of the
resolved system temporary directory, the owner-0600 launcher manifest, and
a receipt binding canonical root, UID, exact patched entrypoint, port and
schema. It rejects symlinks, hardlinks, foreign ownership, non-private modes,
wrong receipt/entrypoint, previous run/current pointer, nonempty DB/logs,
stale run artifacts, consumed receipt, unsafe cache tree, missing/changed
archive, and absent or altered extracted model **before any `Popen`**.
The copied ONNX archive must be an independent inode,
link count 1, 83,178,821 bytes and SHA-256
`913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`.
The six extracted files must byte-match their members inside the verified
archive. Recheck cache privacy/content after preflight and calibration,
immediately before `Popen`. Prepared start claims the root atomically with
owner-0600 `O_EXCL` before preflight; a crash/failure leaves the claim and
requires a new root. This same-UID receipt is an audit invariant, **not** an
OS-level adversarial isolation guarantee.

This controller extension is a **harness/isolation correction**, not a new
cognitive improvement or a second experimental treatment. The only product
answer variable remains the source-bound actor gate frozen before C0.

## Frozen execution and evidence

1. Commit/push this amendment and current card, verify PR #435 head **before
   changing controller code**. Allowed implementation files are only
   `p4_preference_fallback_detached_control.py` and one new
   `test_p4_prepared_first_start_isolation.py`. No old controller tests,
   launcher, cognitive/product, C dataset or scoring thresholds may change.
2. Zero-model tests: prepare creates private root with no PID/current/run
   record; invalid path/receipt/current/consumed/unsafe cache cannot spawn;
   official private archive and extracted model allow exactly one first start
   through the same exact ENTRYPOINT; default and prior-run reuse remain
   unchanged. Include wrong entrypoint/receipt, cache mutation after prepare,
   nested symlink/hardlink, bad archive size/SHA, altered/missing extracted
   member, concurrent first-start claim, and stale run/current records. No
   `Popen` on any invalid case. Use mocked `Popen`/identity for product-free
   lifecycle contracts.
   Run focused tests and existing
   `test_p4_preference_fallback_detached_control.py`,
   `test_p4_reference_probe_evidence.py` and
   `test_p4_local_fact_answer_authority.py`; compile, Web build, diff check.
   A red test
   or changed default behavior is setup FAIL, not a reason to weaken identity.
3. Product-freeze both changed files by SHA, commit/push only allowed files,
   verify PR head **before** any zero-turn model or Safari run.
4. New 0700 root via exact local-fact controller `prepare`. Inspect 0600
   receipt and empty source/DB/log state. Copy the official host archive into
   only this isolated cache (never link it), check source and copy SHA,
   device/inode difference and private modes. Use a **fresh subprocess** with
   `HOME=<prepared root>` set before importing Chroma, assert its resolved
   ONNX `DOWNLOAD_PATH` equals the private cache, and disable Chroma's
   `httpx.stream` download entrypoint before embedding. Require finite
   1×384 embedding and private extracted `onnx/` files (config, model,
   special-token map, tokenizer configuration/data and vocabulary). This is
   not an OS-wide proof that all possible networking was disabled. Reject if
   any download is attempted.
   Then exact controller `start --prepared-runtime-root` in product mode,
   `verify-ready` with same final PID/loopback HTTP 200, inspect zero-turn
   stderr for **no** download attempt, `stop` with exact planned receipt.
   Zero-turn may create empty Chroma schemas: preserve those artifacts
   privately, verify no conversation/profile rows, and do not silently delete
   them or call T0 clean. Then explicitly initialize and preserve an empty
   T0 profile/source snapshot. Only then re-use that same
   root through the already validated stopped-run `--reuse-runtime-root` for
   one C Safari session. If zero-turn setup still tries network or cannot be
   verified, mark whole C isolation FAIL and do not conceal it.
5. Execute C0–C9 exactly once each in native Safari, 0 retries, with all
   previously frozen source, surface/graph/episode, natural Japanese,
   profile, ≤20 s, visual and full-cost gates. Missing native saved image or
   token ledger remains a FAIL/unknown as specified, even if actor turns
   improve. No formal DB, original dirty checkout, unrelated output or
   external deployment is in scope.

Resource ceiling: no model calls during controller/unit tests; one zero-turn
ready/stop rehearsal and one ten-turn C product run after frozen controller
code. No extra generation or exposed-C reruns to improve scores. A failure
before C0 remains a setup failure with preserved evidence; at most two
reasoned changes under a **new** reviewed freeze, otherwise
`REVIEW_REQUIRED`. This amendment gives no formal same-model comparison,
human preference rating, temporal holdout or whole UruhaBrain completion.
