# P4-B non-B synthetic A exec amendment: native v2

Status: prospective **fake-only** design amendment. This is not a retroactive
PASS of `synthetic_a_exec_probe_v1`, not a live Ollama authorization, and not
an amendment to V1–V5, B, or T0+80/90. The Python v1 freeze at `31f7e5a`,
the red contract at `b58fe6e`, and its retained counterexample at `07880dc`
remain immutable evidence. A same-model read-only reviewer suggested this
amendment; that is not independent human approval. Commit and review this
design before changing the red contract or operator source.

## Why this change is necessary and what is held fixed

The strengthened v1 WIP saw transient extra VNODE FDs in 17/30 direct
invocations. After a diagnostic delay outside source, the framework Python
image/argv0 differed from the frozen canonical path in 30/30 observations.
Changing only the target is insufficient: isolated `/bin/cat` and
`/usr/bin/grep` trials obtained two *immediate* exact stdio-only FD maps in
only 4/10 trials each. Those are development feasibility probes, not
acceptance rates. V1 therefore stays `REVIEW_REQUIRED` and fail-closed.

The single versioned engineering change for v2 is the **synthetic A
post-exec witness contract**: a fixed native target plus bounded, active
startup observation. These are coupled corrections to a failed fixture;
v2 cannot isolate their individual causal contributions and makes no such
claim.
Keep the 11 direct roles, 22 command/proof pipes, one exec-status pipe, one
private stdin pipe (24 pipes/48 endpoints), initial OS FD/process witnesses,
one P exec grant, empty target environment, 5-second parent deadline,
8-second child alarm backstop, six frozen fault meanings, exact owned-PID
cleanup, zero work/model/HTTP grants, and permanent live/B refusal. No
runner, listener, model bytes, T0+90 physical stop, Safari, or product turn
belongs in this slice. Caller paths and clock remain unused.

## Exact v2 target and release

The only accepted marker **for this diagnostic** is an exact plain dict with exactly
`{"schema":"synthetic_a_exec_probe_v2","fault":null}` or one of the existing
six exact fault strings. All other marker shapes fail before fork, path
access, or callback. The v1 marker must explicitly refuse with
`process_supervisor_not_implemented` and zero forks; do not silently route
it to v2. The old red commit and failure report preserve v1's history.
Prospectively replace the v1 success/fault expectations with seven explicit
v1 fail-closed/zero-fork checks; retain its four invalid-marker checks.
This makes accidental v1 acceptance fail the current suite rather than
hiding the frozen counterexample behind an expected-failure mark.

Resolve the fixed `/bin/cat` to itself and require an absolute regular
executable at that exact path. A invokes `os.execve("/bin/cat",
("/bin/cat",), {})` once. It blocks on the preallocated private stdin pipe;
P writes **zero** bytes. Only after all post-exec witnesses pass does P
close its private stdin writer to cause cat EOF and exact normal exit 0.
No role control endpoint is reused as stdin. The `wrong_exec_argv` fault
appends exactly `"-"`, leaving cat able to wait for stdin but forcing an
exact argv mismatch. The target does not contact network or model paths.
An isolated read-only feasibility probe saw exact native image/argv/FD0
handle with normal exit in 17/17 trials; this is not the v2 acceptance.

The result schema is `fake_a_exec_preflight_v2` and status remains
`fake_transition_partial`. Report sampled parent FD phases, max/min margin,
11 normal reaps, 24/48 allocation, and a bounded raw-free observation
summary. `synthetic_exec_observed=true` requires the full witness; EOF or
child exit alone never sets it. Permanent flags:
`installed_identity_proven=false`, `physical_stop_unproven=true`,
`full_gate_pass=false`, `b_send_authorized=false`,
`work_grants=http_calls=model_bytes_read=0`.

## Bounded active OS witness

Start observation **immediately** after zero-data CLOEXEC status EOF; do
not insert a fixed startup sleep. EOF is only a hint. Before each attempt,
require A is still the unreaped direct child with `waitpid(WNOHANG)==(0,0)`.
Each attempt reacquires raw PID/start generation, PPID, PGID, OS procargs
image/argv, full libproc FD number/type list and every pipe handle/flag,
then brackets them with another raw generation/identity observation. A
truncated FD list, missing permission, identity drift, child death, known
wrong image/argv, missing/wrong stdio type or handle, unexpected extra PIPE
(including any role control/status handle), or extra FD of a type other
than VNODE(type 1) fails **immediately**. A procargs parse error or other
observation error is also immediate failure; only the exact
`ProbeError("procargs_unavailable")` exception may be recorded as pending,
while FD and
identity checks still run. This does not turn an unavailable image into
evidence of a correct one.

An attempt with otherwise correct identity, image/argv and stdio but only
transient extra VNODE FDs is recorded, not accepted. Actively reacquire
until **two consecutive complete** attempts have exact `/bin/cat` image,
exact one-item argv, the same expected raw generation/PPID/PGID, and
exact stdio-only FD/type/**pipe-handle** maps. Make the first attempt
immediately after EOF, then space **all** later attempt starts at least
10 ms apart, including after transient/pending results; thus the two
complete acquisitions are also separated. A pending/transient attempt
resets the consecutive count. This is an active sampling cadence, not a
preselected startup sleep after which unexplained FDs are ignored.
Stay within the original five-second absolute deadline and at most 512
attempts. If two complete samples are unavailable, fail and clean up;
never turn timeout into PASS. After the second complete sample, recheck
live status and exact identity before closing stdin. Record **every**
attempt in a bounded raw-free ledger (at most 512 rows) with elapsed
milliseconds, image availability/match category, FD extra-type counts,
identity/liveness match booleans and exact/transient/fail classification;
do not retain raw argv, FD handles or source text. Aggregate attempt count,
procargs-unavailable count, transient-VNODE count/max, exact samples and
elapsed milliseconds from that ledger. A negative test must
show persistent extra VNODE never passes, and an injected extra PIPE/control
handle fails immediately rather than being polled away.

These samples show a stable observed post-exec state, not continuous
absence of FDs between samples, an unobserved extra exec, or loaded binary
SHA identity. They cannot authorize the real Ollama gate.

## Faults, tests, and stopping rule

Keep six v1 fault meanings in v2: missing grant; duplicate grant; death
before exec; status writer close without exec; wrong argv; inherited role
control FD. Each must fail with a fixed fake code, no positive receipt,
bounded cleanup/no leaked direct child/no parent FD leak, and no work,
HTTP, or model access. `wrong_exec_argv` and `retain_control_fd` must be
rejected by OS witness even when EOF occurs. Normal positive execution
requires 11/11 exact normal reaps; emergency cleanup is never a positive
reap. Invalid marker variants and v1 marker must fork zero children.

Acceptance order: (1) commit this design; (2) update the focused test-only
contract with v2 positive, six faults, invalid markers, v1 refusal and
transient/persistent/extra-pipe observation negatives; demonstrate expected
red against the public stub before source change; (3) adapt only
`p4_b_non_b_parity_live_operator.py`; (4) focused tests, repeated positive
probe for stability, affected operator tests, diff review and exact PR head
check. Do not rerun unrelated long suites. If image, FD, or cleanup
counterexample persists after at most one bounded v2 correction batch,
retain `REVIEW_REQUIRED` with the smallest counterexample and stop before
runner or live work. A green fake-only v2 still leaves runner discovery,
installed binary/model identity, physical T0+90 stop, Web graph and Safari
as separate pending gates.
