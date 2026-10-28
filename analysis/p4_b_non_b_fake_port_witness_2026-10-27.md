# P4-B non-B fake port/11434 witness (2026-10-27)

Status: **GO only for a fake-only partial commit** after an independent,
read-only patch review. This is one unfinished clause of the existing exact
freeze, not a new M, the full fake matrix, or a live release. Public
`supervise_once()` remains fail-closed. There were **zero real HTTP, Ollama,
Safari or B Send actions** in this slice.

## Before, single change, observable result

Before this change, the committed v1 P+D/W/R seven-operation process loop
passed its synthetic positive check (1/1), but its result and R receipt had
no independent evidence that either private listener was vacant or that the
user's shared 11434 listener had stayed unchanged. A new opt-in v2 test was
red because the fake entry point had no `port_observe` argument. V1 remains
the default and retains its old result/receipt schemas and behavior.

The single mechanism added here is an **injected fake OS-only port witness**.
An independent O child and its exact-PID signal helper S_O are initially
witnessed after D's durable zero ACK and R's zero-journal preflight, but
before W GO. O checks the bound daemon private port vacant and records an
explicit shared-11434 baseline. W's validated ordinal-5 runner request
supplies only a candidate port; ordinal 6 must agree before O may perform
the final check. After D/W have been cleaned up, O checks both private
ports vacant and shared 11434 unchanged. `port_gate_proven` additionally
requires D/W reaped with proven stop states, O normal exit, and S_O normal
exit. The v2 R receipt records the same verdict and bounded hashes/codes.
Blocked or malformed observation leaves a separate R path to persist a
raw-free failure receipt. O's injected callback stdout/stderr are discarded
to `/dev/null` before any callback, not stored as a 0600 log.

One isolated positive synthetic run produced:

| Field | Value | Meaning |
|---|---:|---|
| v2 status / port gate | `fake_seven_process_pass` / `true` | All injected fake contracts passed. |
| reserved / granted / worker issued / fake on-wire | 7 / 7 / 7 / 7 | Durable seven-operation fake journal. |
| OS-only identity observations | 6 | Existing W injected observation count. |
| private ports / shared 11434 | vacant / unchanged | Injected pre/post snapshots, **not real lsof proof**. |
| R receipt | v2, 0600, durable proof | Independent raw-free result record. |
| physical / full gate / B Send | unproven / false / false | No live authority follows. |

The O proof and public projection contain only bound numeric ports, fixed
booleans and SHA digests. The injected listener SHA is a contract value;
it is **not** an independent real OS fingerprint. `on_wire=yes` here is
only the successful return of a fake callback, not network bytes.

## Verification and repairs

| Evidence | Result | Boundary |
|---|---:|---|
| V2 port tests | **30/30 passed** | Injected snapshots, fork/IPC, isolated temp run dirs. |
| Entire operator file | **237/237 passed** | Includes original v1 regressions. |
| Eight affected P4-B/parity/identity/operator files | **487/487 passed**, 52.40 s | No provider or browser. |
| `py_compile`; `git diff --check` | Pass | Syntax/whitespace only. |
| Independent read-only final patch review | **GO fake-only partial** | Not the full fake matrix or live GO. |

Negative controls now include pre occupied/unknown/fabricated runner, post
occupied daemon/runner, shared-11434 drift, wrong final port, op5/op6
runner-port disagreement, pre/post observer crash or block, O/S_O missing
initial or abnormal exit, S_O blocked fresh cleanup witness, duplicate,
partial and stale pre/final O proofs, raw extra-field and exception canaries,
and FD-cap refusal before journal/work. Initial O/S_O witness failures start
zero port callbacks. On blocked O or S_O the parent remains bounded and R
still attempts/writes a v2 failure receipt. The v2 receipt exposes only
O reaped/stop and S_O normal-exit status, **not** every signal transaction
code; do not infer full per-PID cleanup telemetry from it.

Red tests caught three real implementation defects before acceptance:
an observer could print raw material to inherited stdout/stderr; an S_O
fresh-witness stall could consume R's failure-receipt window; and an op6
runner-port mismatch or unproven D stop could leave the independent port
gate incorrectly marked true. O output isolation, a separate later v2 R
deadline, and stricter runner/D/W gate predicates fixed these cases. V1
deadlines and default API remain unchanged.

The fake layout reserves **123 pipes / 246 IPC endpoints** before work GO
and forks eight short-lived children (D/W/R/O and S_D/S_W/S_R/S_O). O briefly
opens one additional `/dev/null` descriptor after inherited unowned ends
are closed; lack of FD headroom fails closed. The 52.40-second suite time
is test wall time, **not product response latency**. Provider token and
paid-network cost for this slice are zero.

## Remaining decision boundary

This partial result does not prove real private-port vacancy, a real
11434 owner/generation/endpoint fingerprint, transport/proxy/redirect
isolation, all blocked hash/readiness/receipt-fsync/cleanup combinations,
installed daemon/runner/GGUF/source identity, T0+80/90 physical cleanup,
actual provider usage parity, Safari or B Send. O's stdio containment does
not establish raw-free output for every older child callback. The overall
result keeps `physical_stop_unproven=true`, `full_gate_pass=false`, and
`b_send_authorized=false`; failure or later passage of a lower-level fake
test cannot change that claim boundary.

Next necessary work remains within the same exact freeze: finish the
transport/proxy/redirect, blocked durability/readiness/cleanup and
source/model/runner identity fake matrix, review it independently, then
only consider a separate committed-source audit and read-only live
preflight. No frozen question/gold, formal DB, original dirty checkout or
unrelated `output/graduate_application_report/` was changed here.
