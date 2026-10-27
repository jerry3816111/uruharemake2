# P4-B non-B synthetic runner direct-Bash acceptance (2026-10-27)

Decision: **PASS for the isolated fake-only runner lifecycle gate; real/live NO-GO**.
This is a short-lived `/bin/bash` → `/bin/cat` OS-process instrument, not
an Ollama run, an installed-runner identity proof, a physical-stop proof,
or a product/Safari acceptance. The prior `/bin/sh` integrated failure
remains in `analysis/p4_b_non_b_synthetic_runner_image_transition_review_required_2026-10-27.md`.

## Before, versioned correction and one gate

- Accepted native A v2 `b170a8a` proved A's direct `/bin/cat` exec but no
  runner. The runner freeze `9213150` specified 11 P children, 25 pipes/50
  endpoints, O's double OS enumeration, S_runner's independent re-observation
  and real `NOTE_EXIT`, staged zero-byte release, six named faults and an
  unresolved early-A-death orphan window. Red contract `83e31a7` had eight
  intended public-stub failures and four zero-fork invalid passes.
- The first runner source WIP failed before O/S_runner because `/bin/sh`
  briefly remained the OS image after CLOEXEC EOF. The 30/30 immediate
  `/bin/sh` observations, 30/30 later `/bin/bash` observations, 5/5
  cross-checks and the old source failure are retained in `89713a8`.
- Prospective design `8276616` changed only the synthetic A target/argv0 to
  direct `/bin/bash`; frozen scripts and runner witnesses were not weakened.
  Test-only commit `f985d18` changed the two expected argv0 assertions.
  With the committed pre-source operator loaded in memory (the dirty WIP
  was not mistaken for public HEAD), the new tests still gave **8 intended
  stub failures / 4 invalid passes / 404 deselected** in 2.24 s. Each red
  was `process_supervisor_not_implemented`.

## Implemented mechanism and review correction

The exact fake marker now constructs the fixed shell and private fd0/fd3
channels after initial 11-role OS/FD attestation. P waits for zero-data
CLOEXEC EOF but accepts only two complete postexec `/bin/bash` image,
argv, raw-generation and FD/pipe-handle maps. P's bounded spawn-presence
check is not O's evidence. O independently enumerates A's child twice and
attests the single `/bin/cat`; S_runner independently reacquires its identity,
owns a real kqueue FD, registers `EVFILT_PROC/NOTE_EXIT` before release and
observes the matching event. P's `waitpid` must reject the non-child runner.
Only then does P close the runner writer with zero bytes, require runner
disappearance while A remains held, close A's hold writer, and normally
reap all 11 direct children. Public result flags remain permanently fake.

Same-model read-only patch review found a blocking false-green: any
`ProbeError` had counted as runner disappearance. A second pass found
that comparing the full `(pid, ppid, start_sec, start_usec)` tuple could
call a *live reparented* runner gone merely because PPID changed. Both
were corrected before acceptance: the stable identity is PID plus start
sec/usec; when libproc cannot report it, only the kernel's exact
`kill(pid, 0) → ESRCH` proves absence. A live/permission-unknown PID
fails closed. Parent-side test observation uses the same strict rule;
seven focused branches cover live observation errors, ESRCH/EPERM,
reparenting and PID reuse. Review then gave GO **only for fake-only source**,
not an independent human review.

## Final verification and cost

| Evidence | Result | Boundary |
|---|---:|---|
| Runner-focused tests after both review fixes | 19/19 pass | Positive, six named faults, four invalid shapes, seven disappearance branches |
| Final direct positive repetitions | 30/30 pass | Each 11/11 normal direct reaps, runner exit observed, fake flags remain false |
| Six direct fault probes | 6/6 fixed refusal codes; FD count restored 6/6 | All below 0.3 s; no positive receipt |
| Affected operator file, `pytest -q -s -p no:cacheprovider` | 423/423 pass in 135.84 s | Selected operator file, not full repository suite |
| Positive probe cost | median 0.211 s; max 0.289 s; sampled minimum FD margin 202 | 30 local fake processes; not model or product latency |
| Model/HTTP/Safari/real data | 0 calls / 0 requests / not run / not read | No fresh-model, Web, browser or formal result |

Compile and `git diff --check` passed. The six direct fault codes in frozen
order were `fake_runner_child_count_invalid` (early exit and duplicate),
`fake_runner_o_witness_mismatch`, `fake_runner_watch_unregistered`,
`fake_runner_exit_event_invalid`, and `fake_runner_fd_witness_unavailable`.
The focused tests additionally require parent-side actual OS image/FD
snapshots, simultaneous duplicate children, hold-pipe inheritance and
S_runner kqueue-denial injection; returned booleans alone do not pass them.

## Claim boundary and next dependency

This proves a bounded, cooperative macOS synthetic runner protocol can
exercise O discovery, S_runner kernel-event watching and staged exit
without a fake parent reap. It adds **no measured improvement** to the
user-visible Japanese reply, memory graph, VRM, Function Calling, same-model
LLM comparison or the candidate human-response equation. No new graphical
page or Safari turn was authorized for this fake-only support gate; those
acceptance layers remain pending rather than being inferred from tests.

The freeze's early-A-death/orphan window is still unresolved: if A forks
a runner and dies before any observer identifies it, the present protocol
cannot prove that unknown descendant was stopped. No such instance was
observed in these positives, which does **not** eliminate the window.
Real installed Ollama/model/port ownership, seven-call/no-retry work,
T0+90 physical stop, Safari and B Send require separate prospective design,
controls and evidence. The next necessary item is a source-reviewed
containment/witness design for that orphan window before any live attempt;
do not relabel this fake PASS as physical-stop authorization.
