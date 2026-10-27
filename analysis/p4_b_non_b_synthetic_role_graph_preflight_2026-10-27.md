# P4-B non-B: isolated synthetic role-graph preflight

Scope: the first source slice of
`research/p4_b_non_b_real_supervisor_transition_freeze_2026-10-27.md`.
This is a mechanical, fake-only process/FD experiment, not a live Ollama
admission, installed-source attestation, product turn, or B Send release.

## Before, intervention, and result

- Before: the public `supervise_once()` rejected every effects object with
  `process_supervisor_not_implemented`. The committed exact-marker contract
  at `7410e46` had four intended failures and four invalid-marker passes;
  the four failures were this stub, not an import or OS permission error.
- Single change: the exact plain-dict marker
  `{"schema":"synthetic_role_graph_probe_v1","fault":null}` now enters a
  held-child topology probe. All other effects still fail closed. Caller
  `run_dir`, `model_root`, and `clock` are unused by this probe.
- The probe allocates 22 role control pipes / 44 endpoints and one additional
  exec-status pipe. It forks 11 direct children: D, W, R, O, A, S_D, S_W,
  S_R, S_O, S_A, S_runner. A is held and never execs. Each child keeps only
  its role control ends, plus A's exec-status end. The parent independently
  brackets two macOS `PROC_PIDLISTFDS` snapshots with raw process generation
  and checks `PROC_PIDFDPIPEINFO` pipe handles/CLOEXEC. Child ACK alone cannot certify
  closure. Normal release requires each ACK, exit 0, and parent `waitpid`.
- Three failures are exercised independently: eighth pipe allocation after
  seven successful allocations; O missing its initial ACK; and O retaining
  A's non-role command-read FD. The last is rejected by the OS FD-set
  witness despite a well-shaped child ACK. All failures have zero work
  grants, and cleanup must reap each direct child and close parent FDs.

## Measured evidence

| Check | Result and boundary |
|---|---|
| Focused exact marker, three faults, invalid markers and old public fail-closed | 9/9 passed, 368 deselected, 5.83 s after the final test-assertion strengthening. |
| Full affected operator file | 377/377 passed, 115.84 s on the same source, before test-only assertion strengthening; changed focused tests were rerun afterward. |
| One direct positive invocation | 11 initial roles, 11 normal reaps; 22/44 control pipes/endpoints plus one exec pipe; 36 named FD samples; before/after parent FD count 4/4. |
| FD resource sample | Maximum sampled parent FD count 50, soft limit 256, minimum observed margin 206. This is not a continuous peak or a future daemon/runner budget. |
| Actual model/network/product cost | 0 model bytes, 0 HTTP calls, 0 work grants, 0 Ollama exec, 0 Safari turns, 0 model tokens, 0 production memory writes. |

The final test strengthening did not change the frozen research data or
source behavior: it asserts the exact 36 allocation/fork-close/cleanup
sample order, the computed sampled margin, and the fault-specific error
codes. `git diff --check` is clean. Two same-model read-only reviews found
no blocking mismatch for **fake-only source**; they are not independent
human evaluation. The direct invocation returns
`schema=fake_role_graph_preflight_v1`, `status=fake_topology_partial`,
`installed_identity_proven=false`, `physical_stop_unproven=true`,
`full_gate_pass=false`, and `b_send_authorized=false`.

## Failure analysis and next gate

The original red failure was absence of this public diagnostic path.
The negative controls now fail for the intended mechanical reasons instead
of accidentally reaching the old stub. This establishes one bounded
resource/process topology and an OS-backed initial FD witness only.
It does **not** test A's one-time exec/CLOEXEC EOF, installed binary/model
identity, actual runner discovery/exit, continuous FD ownership, source
pre/post hashes, T0+90 physical stop, seven real HTTP operations, visible
node graph, Safari behavior, or felt-understanding quality. No diagram or
Safari acceptance is newly claimed for this support slice.

The next necessary gate is separately frozen synthetic A exec/EOF plus
runner topology and its negative controls, before any installed-source or
live preflight. The real path must remain NO-GO unless its own source,
model, process, deadline and cleanup evidence passes; no result here may
authorize B Send.
