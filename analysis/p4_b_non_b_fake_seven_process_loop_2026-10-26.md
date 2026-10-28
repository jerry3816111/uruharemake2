# P4-B non-B seven-operation fake process loop (2026-10-26)

Status: **GO only for a fake-only partial commit** after independent read-only
patch review. This is neither the full exact-freeze fake matrix nor a live
operator release. Public `supervise_once()` still fails closed; there were
zero real HTTP/model calls, Safari actions or B Sends.

## Before, change and visible example

Before `909c725`, `worker_once()` could complete seven injected operations
and six injected OS observations in one process, while the P+D/W/R supervised
topology stopped at a durable op1 grant and W-received ACK. It had no
process-backed op2–7, no W fake transport gate, and no durable per-call
`worker_issued`/`on_wire` result. A new positive process-loop test was first
red with the seven-operation entry missing.

The one changed mechanism is a **fake-only, one-use process-backed
grant/issue/result loop**. An initially witnessed resident D owns the
single-use journal; W reuses the existing `worker_once()` seven-call/six-
observation implementation; R writes a separate 0600 result receipt. For
each ordinal, W requests a raw-free spec, D commits and reads back the
grant, W validates its own URL/payload/nonce at a one-use fake transport
gate, D commits and reads back W's issue-entry, W invokes the sole injected
fake callback, and D commits and reads back the fake transport success.
Operation 7 spends its completion attempt before the grant reaches W. A
missing proof, lost ACK, crash or uncertain callback never refunds an
attempt or permits the next ordinal. Child-to-parent grant-affecting replies
have one bounded frame plus EOF; all 226 pipe endpoints are actually reserved
before work GO and unowned inherited ends are closed. A final positive fake
result requires D/W normal exit, signal-helper normal exit, and R's durable
receipt proof. It always retains `physical_stop_unproven=true` and
`full_gate_pass=false`.

In the positive synthetic case, `journal.json` contains ordinals **1–7**,
`reserved=granted=worker_issued=7`, seven fake `on_wire=yes` entries and
`completion_attempt_spent=1`. W reports **7** external injected operations
and **6** OS-only observation stages. The 0600 receipt repeats those counts,
binds the final journal SHA and records the fake-only status. A raw response
canary is absent from the public result and receipt. `on_wire=yes` here is
only evidence that the injected fake callback returned a bounded successful
result; it does **not** prove real network bytes or runner generation.

## Verification, failures and cost

| Evidence | Result | Claim boundary |
|---|---:|---|
| New `-k fake_seven` tests | **37/37 passed**, 13.55 s | Synthetic fork/IPC/journal only. |
| Entire operator file | **207/207 passed**, 41.07 s | Includes 170 pre-existing tests. |
| Seven affected parity/identity/operator files | **435/435 passed**, 42.22 s | No real provider or browser. |
| `py_compile`; `git diff --check` | Pass | Source hygiene only. |
| Independent final read-only patch review | **GO fake-only partial commit** | Explicitly not full fake matrix/live GO. |

Negative controls cover D crashes after reserve/issue/wire, op7 ACK loss
after durable spend, blocked fake callback at **every ordinal 1–7**,
pre-op7 source failure (six operations and unspent completion), W-local
grant tampering, lost result ACK, duplicate child frame, FD reservation
failure, existing-run refusal, R initial-witness failure, blocked D commit,
S_D/S_W/S_R nonzero exits, raw exception/IPC/summary canaries, restrictive
umask and parent/W reused-FD sentinels. Review caught three defects before
GO: an injected exception could leak raw text through a public failure code;
an abnormal signal-helper exit could leave a seven-op false positive; and
numeric FD double-close could close a later reused descriptor. These were
fixed and covered by regression tests. Exact 0600 journal mode now uses
`fchmod` and regular-file/mode readback, not just `open(..., 0600)`.

The fake topology reserves **113 pipes / 226 endpoints** and forks six
ephemeral children (D, W, R, S_D, S_W, S_R). The measured 13.55/41.07/42.22
seconds above are test-suite wall times, **not** model latency or production
cost. Provider token and paid-network cost for this slice are **zero**.
No actual T0+90 stop or SHA/CPU cost measurement can be inferred from it.

## Remaining gates

The exact freeze's remaining fake matrix is **not complete**: private daemon/
runner port vacancy and unchanged shared 11434, actual proxy/redirect and
loopback transport isolation, blocked hash/readiness/cleanup-witness/receipt
fsync combinations, and source/model/runner identity still need their
appropriate evidence. The installed Ollama source/binary/GGUF, true HTTP
wire behavior, T0+80/90 physical cleanup, real usage parity, Safari and B
Send all remain **NO-GO**. The previous final-check-to-`os.kill` PID-reuse
residual also remains. No frozen question/gold, formal DB, original dirty
checkout or unrelated `output/graduate_application_report/` was modified.

Next: complete the remaining fake port/transport/cleanup matrix under the
same exact freeze, with independent review. Only after full fake acceptance,
scoped committed-source audit and read-only live preflight may a separate
live-release decision be considered. This fake slice is a safety and
traceability prerequisite, not evidence that the full human-response
equation, Uruha persona quality or P4 product is complete.
