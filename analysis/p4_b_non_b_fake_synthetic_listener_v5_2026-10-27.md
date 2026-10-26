# P4-B non-B v5 synthetic listener: fake-only partial result (2026-10-27)

## Changed claim, not a live release

Committed v4 (`7160bbf`) had an O-owned, 23-byte synthetic pre-hash and
private-port vacancy proof before `W_GO`, but no daemon child or readiness
observation. The v5 prospective contract received separate read-only
assistant-agent review and was
committed at `c840886`, with the explicit opt-in boundary pinned at
`b1d4bcd`. Before source edits, the positive v5 test failed with
`TypeError`: `_supervise_fake_seven_once()` had no `fake_listener` argument.
The single new control-path variable is an independently supervised H child
owning an exact `127.0.0.1:{bound_daemon_port}` TCP LISTEN socket, observed
by the already witnessed O via H's per-process OS socket rows before W is
released. This is a *synthetic admission instant*, not installed Ollama,
model/source identity, or continuous readiness.

```text
D zero journal -> R zero-journal preflight -> phase-2 12-pipe allocation
 -> O v4 SHA + vacant-port proof -> H/S_H initial witness -> H LISTEN
 -> O independent H-owned TCP4 LISTEN + identity bracket -> H/R live
 -> W_GO -> seven injected opener calls -> H close + witnessed stop
 -> O existing injected final-port proof -> R 0600 receipt + normal exit
```

The public `supervise_once()` remains fail-closed. V5 is an explicit fake-only
opt-in requiring v4 prehash, v3 injected opener, v2 injected port observer,
and no legacy fake HTTP callback. H performs one local bind/listen and no
accept/connect/HTTP; the seven W responses are injected. V1–v4 behavior,
result/receipt schemas and failure-code allowlists remain separate. V5's
result and R receipt add ten fixed fields; the latter retains the first
pre-W cause even when later cleanup or R durability dominates the top-level
failure. `continuous_listener_proven=false` is permanent.

## Failure analysis and verification

- The first focused run had **32/33 pass**. On forced phase-2 FD failure, P
  closed D/W command pipes *before* witnessed cleanup, causing EOF/nonzero
  exits. V5 alone now defers those closes until the D/W cleanup transaction
  finishes; the test confirms witnessed D/W stop, zero grants/opener calls,
  preserved `phase2_fd_unavailable`, and a raw-free durable R failure receipt.
- Separate read-only source review found and prompted fixes for premature
  `h_initial_unavailable` attribution on a v4 pre-stage failure; accepting
  a late normal H/O/R exit as within the v5 cleanup deadline; leaving a
  late child unreaped after a failed timing verdict; and treating
  `ChildProcessError` as proof H/R remained live. V5 now separates deadline
  verdict from bounded late drain, and requires exact nonblocking
  `waitpid(..., WNOHANG)==0` for admission/later-grant liveness. Phase-2
  allocation attribution is confined to the allocation call.
- V5 focused fake tests: **60/60 passed in 33.22 s**. They include a
  H-owned LISTEN-before-W_GO positive; seven fake calls; V1–v4 schema
  isolation; partial FD allocation, bind collision, wrong owner/address/
  port/state, absent/extra/unterminated wire frames, raw-generation/PGID
  drift, H crashes/stalls, R death both before readiness and at admission,
  mid-run H loss, H cleanup identity drift/no signal, TERM ignored and
  uncertain KILL proof, late helper exit, canary isolation, and R durability
  failure. Rejected pre-W cases retain a zero-operation journal and no W_GO.
- Final eight-file affected regression on the final source/test state:
  **618/618 passed in 112.01 s** using
  this exact command:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -s -p no:cacheprovider test_p4_b_child_local_identity_fixture_v2_preflight.py test_p4_b_child_local_identity.py test_p4_b_isolated_ollama_identity_probe.py test_p4_b_non_b_usage_parity.py test_p4_b_private_zero_turn_operator.py test_p4_b_child_local_identity_sandbox_preflight.py test_p4_b_ps_free_identity_feasibility_probe.py test_p4_b_non_b_parity_live_operator.py
  ```

  `py_compile` and `git diff --check` passed. A separate read-only assistant
  agent gave **GO for this fake-only patch**, not for live release. This is
  same-model review, not independent human or cross-model evidence.

## Actual resource and evidence boundary

Positive-test `/dev/fd` barrier samples in P/O/H (soft FD limit 256) were:

| Process | Peak simultaneously observed FDs | Largest numeric FD |
|---|---:|---:|
| P | 252 | 251 |
| O | 15 | 250 |
| H | 12 | 24 |

These are sampled peaks, not continuous maxima. V5 allocates **135 pipes /
270 endpoints cumulatively** in two phases, never 270 simultaneous parent
endpoints; attempted positive topology is ten fake children. P's four-FD
headroom is narrow and must not be generalized to a real service. The
measured run did zero model calls/tokens, zero provider HTTP, zero Safari
Send, zero B Send and no production DB write. Test-suite wall time is not
product response latency or the frozen T0+90 physical-stop result.

Passing v5 proves only that this bounded synthetic listener/control path
can admit, reject, and clean up under its stated probes. O's final
two-port/11434 snapshot remains injected; the one-time psutil admission
does not prove the listener stayed open during all operations. Real Ollama
binary/argv/GGUF and model-store provenance, actual 4.4 GiB pre/post SHA,
real daemon/runner identities/readiness, provider transport, full fake
matrix, Safari/node-graph visual acceptance, T0+90 and human/model-quality
claims remain pending. Positive results still fix
`physical_stop_unproven=true`, `full_gate_pass=false`, and
`b_send_authorized=false`. No new graphical product page was built for this
supporting fake gate; existing runtime graph was not Safari-verified here.

The next necessary distinct gate is a **read-only source/model identity
inventory and prospective attestation design**, separate from readiness.
It must pin actual installed binary/argv/GGUF/model-store evidence and its
cost/failure branches before any fake extension or separately reviewed live
preflight. V5 cannot itself authorize real Ollama, Safari or B Send.
