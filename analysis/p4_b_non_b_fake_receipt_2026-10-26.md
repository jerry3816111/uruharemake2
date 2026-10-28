# P4-B non-B prewitnessed fake receipt: partial result (2026-10-26)

Status: **GO only for a fake-process partial commit**, independently
reviewed under the existing exact implementation freeze. It is not a live
supervisor, provider-parity result, P4-B pass, Safari acceptance or B Send
authority. Public `supervise_once()` still fails closed.

## Before and single attributable change

The previous P+D/W+S_D/S_W op1 probe could prove a zero journal ACK, an op1
durable grant and W receipt, and could stop blocked synthetic D/W children.
It had **no independent durable failure/result receipt**. This slice adds
prestarted, initially witnessed R(receipt) and S_R(exact-PID signal helper)
before D's work GO. D still exclusively creates the 0700 run directory.
After D's zero ACK but before W GO or any op1 reservation, R independently
verifies that directory contains only the canonical 0600 zero journal and
sends one bounded ACK. Existing receipt/intent, changed journal, missing
ACK or blocked preflight is terminal and cannot reach W/op1.

R remains idle through D/W cleanup. P then sends one bounded, canonical,
raw-free snapshot; R alone creates `receipt.json` with `O_EXCL` and mode
0600, fsyncs file and directory, reads back exact bytes, and sends a
one-shot proof. P sets `receipt_durable_proven=true` only after valid
frame+EOF, matching hash/byte length and R's exact normal `waitpid` exit.
If R blocks, S_R can issue witness-gated TERM/KILL; only matching actual
signal-exit status is a witnessed stop. R's self-alarm does not prove stop.
The on-disk snapshot explicitly predates R/S_R final reap and permanently
says `physical_stop_unproven=true`/`full_gate_pass=false`.

## Evidence and cost

| Check | Observed result | Boundary |
|---|---:|---|
| New fake receipt controls | **17/17 passed**; first 9 were red before source change | Synthetic process and filesystem controls only. |
| All fake split controls | **50/50 passed, 19.79 s** | No worker HTTP. |
| Seven adjacent parity/identity/operator files | **391/391 passed, 28.48 s** | Test wall time, not product latency. |
| Existing receipt / changed zero journal / lost or blocked preflight | W/op1 not authorized; prior bytes retained | No refund/resume or parent filesystem scan. |
| Blocked receipt fsync/readback, lost command/proof, R nonzero exit, ineffective signal, raw canary | No false receipt proof; fixed failure code | File may exist but remains unproven and single-use. |
| Blocked D with ineffective signal | Bounded **failure receipt** still persisted in the synthetic window | Not a real T0+90 guarantee. |
| Independent read-only patch audit | **GO only fake partial** | No live-release authority. |
| `py_compile`; `git diff --check` | Pass; clean | Source hygiene only. |

Receipt failure downgrades the top-level result to
`fake_partial_split_unproven` / `receipt_unavailable_review_required`, while
independently proved W-receipt fields remain intact. There were **zero**
real HTTP/model calls, Web turns, Safari actions or B Sends. Formal/private
DB, original dirty checkout and unrelated `output/graduate_application_report/`
were not touched. `physical_stop_unproven=true` and `full_gate_pass=false`
remain fixed even on the positive fake path. No graph/Safari visual check is
authorized for this isolated protocol slice.

The final-check-to-`os.kill` PID-reuse residual remains. R may crash after
preflight; then no receipt can be proved and the run fails closed. Missing
real argv/binary/listener/source/model identity, op2–7 transport, private
port and shared-11434 proofs, actual T0+80/90 deadlines and provider usage
parity prevent any live claim. The next necessary gate is the remaining
seven-operation fake transport/source/port matrix and independent review,
then committed-source audit and read-only preflight before a separate live
release decision.
