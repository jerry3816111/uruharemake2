# P4-B non-B real supervisor: prospective process-transition amendment

Status: **two same-model read-only reviews permit design commit only; no
source or live release from this file alone.** This amends only the *future
real-only* path described by
`p4_b_non_b_live_supervisor_exact_implementation_freeze_2026-10-26.md`.
It does not rewrite that historical freeze, V1–V5 fake receipts, the P4-B
question/gold, source-conditioned scoring rule, seven-call/no-retry cap, or
the T0+80/90 deadlines. The current public `supervise_once()` is still
fail-closed. A separate committed-source/patch review, bounded read-only
preflight and explicit live GO remain required before one real attempt.

## Blocking counterexample and one implementation variable

V5's H is a Python child, not the frozen Ollama binary. Its fake binding's
daemon PID is 101, whereas H is a separate real PID. Replacing H by `execve`
loses its H-specific readiness IPC and changes its frozen argv/binary
witness; forking Ollama *from* H moves listener ownership away from H and
leaves the daemon without S_H's initial witness. Thus V5 cannot be renamed
installed identity or extended to a positive V6 H attestation.

The real-only variable is **run-owned source/process identity observation**
for the frozen non-B protocol. The real operator must establish source bytes,
same-run daemon/runner process identity, readiness, work, post-store check
and physical stop without using caller-supplied hash-shaped booleans. It
must keep fake and live schemas distinct. This variable changes no input,
prompt, model settings, response parsing, outcome metric, baseline or B
authorization. Small synthetic children/files may test its control protocol,
but their PASS can never become an installed-source or live PASS.

## Real-only roles, FD and time ordering

P is a nonblocking watchdog. D durably journals the seven ordinal grants;
W owns the exact request, private loopback transport and raw responses; R
durably writes the final raw-free receipt; O performs blocking read-only
file/OS attestation. A is a held bootstrap which may make exactly one
controlled transition into Ollama `serve`. S_D/S_W/S_R/S_O/S_A and
S_runner are initially witnessed, independently stoppable signal helpers.
No fake H or V5 pipe graph participates in this real path.

Candidate IPC is two one-way pipes per 11 roles: **22 pipes / 44 endpoints
allocated before forks**, P retaining at most its one end per pipe after
each child's non-role FDs close. One CLOEXEC exec-status pipe, private 0600
logs and transient hash/listener FDs are additional and must be counted at
every allocation/close barrier. This 44-endpoint arithmetic is a proposed
topology, not a measured peak or a substitute for the actual macOS 256-FD
limit. Frames remain <=4096 bytes, canonical, length-prefixed, raw-free,
run/phase/sequence-bound; reuse a channel across ordinals with monotonic
state, rather than adding 12 pipes per ordinal. Before implementation,
prove that every success, blocked-hash, early abort, runner-loss, receipt
failure and cleanup path closes its inherited ends and stays below the
limit without raising it. The V5 252/256 sample is not a live FD guarantee.

Preparation may create/witness idle helpers, allocate IPC and select an
existing private model clone before T0; record that cost separately. T0 is
immediately before the first real source/model validation and daemon
startup. O performs exactly one pre-store validation plus both binary
hashes, then A may exec. The runner may appear during the frozen ordinal-4
render-only call; operations 5–7 wait for its independent identity witness.
Exactly one post-store validation must finish before T0+80 or the run
strictly fails. [80,90) is for revoked grants, exact-PID cleanup, exit/
port/shared-11434 proof and R receipt, not a late 4.4 GiB hash. Full store
pre+post costs at least 9,366,176,380 logical bytes plus binary hashes;
the B-only helper's four-store pattern is forbidden. Record actual counts,
logical bytes, CPU, wall, cold load, helper preparation, seven external
HTTP and any internal work left unknown. No model download or new clone.

## A: one explicit bootstrap-to-daemon transition

The state machine is `BOOTSTRAP_HELD -> EXEC_ARMED -> DAEMON_BOUND ->
STOPPING -> EXIT_OBSERVED`. A is P's *direct* child, with a known parent
and a single PID/raw kernel start generation. A calls `setsid`, enters a
held bootstrap with private stdin/logs and no network, sends a bounded
initial frame, then waits. O and S_A independently record the initial
PID/raw-generation/PPID/PGID/executable/exact-argv witness; P must ACK that
and the completed pre-store check before giving A one exec grant. A uses a
frozen absolute Ollama binary/`serve` argv and exact private model, host and
no-cloud environment. Unknown/duplicate GO, environment or path mismatch,
failed pre-store, or no initial S_A witness means **no exec/W_GO/HTTP**.
All A-owned grant/proof pipe ends are closed after the one grant is consumed
and marked `FD_CLOEXEC` as a second barrier; all non-role pipe ends were
closed immediately after fork. Only explicitly permitted private stdio/log
FDs may survive `execve`. The exec-status pipe's close-on-exec EOF is the
sole controlled transition hint, never a success proof. An inherited
control endpoint, failed close/CLOEXEC check or runner inheritance of P's
control channel bars W_GO and forces cleanup; Ollama cannot speak the
parent's helper protocol.

The bootstrap-to-exec image change is the *only* allowed witness change:
PID, raw generation, PPID and PGID remain identical; OS executable, exact
argv and environment must become the pinned Ollama values, not merely a
version string. A CLOEXEC pipe EOF is only a transition hint; it is not
success, since death can also close the pipe. Before W_GO, require A still
an unreaped, live direct child, O's bracketing OS snapshot of the final
image, a match to the **same run's already completed pre-store validation**
and pinned daemon binary digest, and **A-owned** private TCP4 loopback
LISTEN; shared 11434 remains at its recorded owner. The W_GO check may
use bounded path/inode/metadata drift observations, but must not call
`_model_store` a third time or imply a third whole-store hash.
The pre-hash attestor must bind each opened binary's canonical path,
device/inode, size, modification/change times, file bytes SHA and close
metadata. O rechecks the no-follow path before granting exec; A itself
opens and `fstat`s that path against the pinned metadata immediately
before `execve(path)`, emits a bounded result, then closes the check FD.
After A's OS procargs observation, O compares the observed executable path
and its currently opened no-follow file metadata to the same pinned file
identity; the runner receives the same treatment before op5. A path-only
match is insufficient. This
is still **cooperative file-to-process conformance**, not a SHA of the
memory-loaded image: this Python has no `fexecve`/fd-based `execve`, and
path replacement between the last file check and process start is a
residual TOCTOU risk. Name receipt fields `installed_file_sha256` and
`observed_os_executable_path` separately, never `process_image_sha256`.
Any observed drift or unverifiable path/inode bridge is `REVIEW_REQUIRED`
and bars W_GO/op5; do not promote it to a strong binary-image claim.
Any unknown intermediate image, raw-generation/PGID/parent drift, foreign
listener, observer failure or deadline means no W_GO. A may have already
been execed on such a failure, so cleanup remains mandatory; do not report
zero process side effects merely because HTTP was withheld.

P must not reap a *still-live* A while S_A may signal it. A
`waitpid(A, WNOHANG)==(0,0)` result proves the direct child still live at
that instant. If WNOHANG instead returns its terminal PID, P records the
exit status, has reaped it and permanently forbids any later signal to that
PID. P serializes its waitpid/reap and S_A signal-grant state: it must
neither reap during an in-flight S_A transaction nor issue another signal
grant after a terminal waitpid. Once a signal grant is armed, P defers
further reaping until S_A's terminal transaction result is received. A
missing S_A ACK is not permission to reap or issue a second signal while
S_A may still be running; it leaves the fate unknown and the physical-stop
gate failed. If S_A is independently proven terminated with no possible
future signal, P may reap A for hygiene but cannot upgrade that failed
signal transaction into a witnessed stop. Death in the interval leaves an
unreaped child PID, preventing reuse. This repository's product-checks
Python lacks
`os.waitid`, so no source design may rely on Python `WNOWAIT`. If A exits
between a live observation and signal, P's exclusive unreaped-child
ownership prevents PID reuse, but the existing final-check→`kill` residual
race and cooperative-host limit must still be reported.

S_A's fresh signal check accepts only one of these phase-specific, fully
observed states at the same PID/raw-generation/PPID/PGID:

| Phase | Executable/argv | Private listener | Permitted action |
|---|---|---|---|
| Held or armed before exec | Exact held bootstrap | Independently vacant, no foreign owner | Exact PID TERM/KILL after fresh check; no W_GO. |
| Post-exec before readiness | Exact frozen Ollama image | Independently vacant, no foreign owner | Revoke grants; exact PID TERM/KILL after fresh check; no W_GO. |
| Bound work or work abort | Exact frozen Ollama image | A is sole owner | Revoke work, exact PID TERM; never a group signal. |
| Work lost readiness before TERM | Exact frozen Ollama image | Independently vacant, no foreign owner | Revoke work, record readiness failure; exact PID TERM/KILL after fresh check, never further HTTP. |
| Stopping after TERM | Same Ollama image | A-owned **or** independently vacant with no foreign owner | Exact PID KILL only if still live and freshly matched. |
| Unknown image/owner/observation | Any other state | Unknown or foreign | No blind signal; `physical_stop_unproven`, manual review. |

The vacant rows require a fresh independent exact-port observation and
the same initial PID/raw generation/PPID/PGID/executable/argv, not a
missing listener check or stale readiness snapshot. Unknown or foreign
ownership never authorizes a signal. This explicitly supersedes the old
real-path assumption that listener and argv/binary can remain
byte-identical from pre-exec through cleanup; the
old condition is impossible for a legitimate exec, and a daemon may close
its listener before it exits. The table does **not** authorize signaling an
unwitnessed PID or weaken the exact-run identity requirement. S_A must
bracket PGID and `os.kill(initial_pid, signal)` with fresh raw-generation
checks inside one bounded helper transaction, preserving the documented
PID-only syscall residual race. A blocked S_A observer or ineffective
TERM/KILL cannot yield a T0+90 physical-stop PASS.

## Runner: discovery, independent witness and exit—not P reap

After ordinal 4, W pauses before operations 5–7. O brackets A's raw
generation around two bounded `proc_listchildpids(A_pid)` enumerations.
Every returned PID is independently bracketing-observed using the existing
macOS raw-generation/procargs helper; unknown, extra, truncated, duplicate,
drifting or zero children fail closed. Exactly one child must match the
frozen runner executable and full argv, PPID=A, its own initial PGID
(which may differ from A's), `--model` pointing to the verified private
GGUF, private 127.0.0.1 host/port, flags and A-owned
model/source relation. An independent sole-owner listener check must show
that exact runner PID on the distinct runner port. Neither an old PID nor
`pgrep`/`ps` strings alone are authority. No extra HTTP is allowed merely
to discover the runner.

The already witnessed S_runner independently reacquires the *same* initial
PID/raw-generation/PPID/PGID/executable/argv/model/listener witness and
registers `EVFILT_PROC/NOTE_EXIT` before op5; raw generation is rechecked
after registration. Registration error, permission denial, ESRCH, early
exit or any mismatch bars op5–7. A cleanup event counts only when its
`ident` is the witnessed runner PID, `filter` is `EVFILT_PROC`, `fflags`
contains `NOTE_EXIT`, and `EV_ERROR` is absent; unrelated or malformed
events cannot fill the exit receipt. O and W recheck the identical runner
before both tokenizer calls and before the sole completion grant. Source
branch/BOS/context/truncation predicates and two equal tokenizer lists
remain mandatory before ordinal 7, as in the old exact freeze. This
admission proof does not establish continuous readiness across HTTP calls.

S_runner's cleanup signal uses the same fixed exact-PID/fresh identity
discipline. The final runner proof requires a registered NOTE_EXIT event,
disappearance of the original raw-generation PID, runner private-port
vacancy with no foreign owner, daemon stop and unchanged shared 11434.
Like A, a runner that closes its listener before TERM/KILL may still be
signaled only after a fresh match of its original PID/raw generation,
PPID/PGID/executable/argv/model path **and** an independently vacant port
with no foreign owner; losing readiness revokes further HTTP and is not a
successful-work state. O and S_runner must remain alive through the
T0+87–89 exit/port proof and must not be included in an earlier generic
"remaining helpers" stop. Stopping an observer cannot itself prove the
daemon or runner exited.

The bounded [87,89) phase must finish the exit/port/shared-11434 proof
**while O and S_runner are alive**, then request their normal shutdown and
nonblocking-reap those direct helper children (and their signal helpers)
before the [89,90) final R receipt phase. If proof or helper exit misses
that barrier, R may still durably record a failure when available, but a
T0+90 physical-stop PASS is forbidden. R and its signal helper remain
reserved until after that final receipt. No observer may be counted as
stopped merely because its IPC channel closed.

P is **not** the runner's parent and cannot `waitpid`/reap it. Receipt must
therefore distinguish `runner_exit_observed=true` from
`runner_reaped_by_parent=not_applicable`; never write a fake `reaped=true`.
This is a prospective correction to the real-path reap wording, subject to
design review: if NOTE_EXIT plus absence/port proof is not accepted as
physical-stop evidence, the live gate stays `REVIEW_REQUIRED`. Missing
NOTE_EXIT, a zombie/unknown child, or a still-owned port also leaves
`physical_stop_unproven=true` rather than guessing from one observation.

The local no-Ollama feasibility probe on 2026-10-27 passed 1/1 focused and
369/369 operator-file tests: libproc listed one synthetic A child B, raw
generation tied B to A, P's non-parent waitpid refused B, and a kqueue
registered before release received NOTE_EXIT. The first probe had exposed
the unavailable `os.waitid` in the project Python. These observations do
**not** test a sandboxed real runner, port/model identity, S_runner or
T0+90. The probe asserted event PID and `NOTE_EXIT`, but not the proposed
full filter/`EV_ERROR` check; that remains for focused protocol controls.
Its only authorization is to proceed with design review.

## First source slice: isolated role-graph preflight, not live admission

Before source change, public `supervise_once()` always raises
`process_supervisor_not_implemented`; V5's 252/256 sampled parent FD count
belongs to a different fake graph. The first implementation slice changes
only **the real-path role/IPC topology**, before identity, exec or work.
The public opt-in is the exact plain dict
`{"schema":"synthetic_role_graph_probe_v1","fault":null}`. Source must
require `type(effects) is dict`, exact keys, exact schema and a fixed fault
enum. The only fault values are `null`, `pipe_allocation_after_7`,
`omit_o_initial_ack` and `retain_o_nonrole_fd`. All other effects retain
the public fail-closed error and zero callbacks. The dict is a request
for a permanently fake diagnostic, **not** an identity or live authority.
The probe must not read or write caller-supplied `run_dir` or `model_root`;
tests assert both paths remain absent or byte-equal. It must not spawn
Ollama, `exec` A, open a network socket, send W_GO or HTTP,
read model bytes, write production memory, or produce a live verdict.

The probe allocates the candidate 22 control pipes / 44 endpoints plus one
separately counted exec-status pipe before forking, recording the expected
pipe handles/FD identities while P still owns both ends. It forks exactly the
eleven direct P children D/W/R/O/A/S_D/S_W/S_R/S_O/S_A/S_runner in fixed
order. Each child closes every non-role inherited endpoint immediately,
retains only its command/proof ends, sets role and exec-status controls
`FD_CLOEXEC`, and sends one canonical <=4096-byte initial PID/raw-generation/
PPID/PGID/role frame. P must independently reacquire each child's initial
raw generation and parentage before considering the graph prepared. For
this isolated synthetic probe, P also brackets two macOS
`proc_pidinfo(PROC_PIDLISTFDS)` snapshots of each idle child with raw
generation, then compares the exact allowed FD number/type/pipe identity
set for stdio, the role's two control ends and A's exec-status end.
`proc_pidfdinfo(PROC_PIDFDPIPEINFO)` may supply pipe handles and the
`PROC_FP_CLEXEC` flag. Missing permission, full/truncated buffer,
unexpected FD, changed generation/set or failed CLOEXEC check fails
closed; a child's ACK cannot certify its own FD closure. These APIs are
only locally feasible so far, not yet proven for all eleven children.
In the future live path O/S_O must perform blocking OS inspection rather
than place it on P's watchdog loop. A
remains **held**; merely checking CLOEXEC flags is not an exec/EOF proof.
P samples its actual open-FD count at each allocation and fork-close
barrier, with named phase, soft limit and minimum observed margin; the
`/dev/fd` enumeration's own transient FD is counted. Samples are not a
continuous process-wide peak or proof of a future daemon/runner load.

The positive result is `schema=fake_role_graph_preflight_v1`,
`status=fake_topology_partial`, exact 11 initially witnessed and normally
released with ACK, exit status zero and P exact `waitpid` for every direct
child, 22 control pipes and 44 endpoints, one
extra exec-status pipe, ordered FD samples, `work_grants=0`, `http_calls=0`,
`model_bytes_read=0`, `a_exec_observed=false`, and permanently
`installed_identity_proven=false`, `physical_stop_unproven=true`,
`full_gate_pass=false`, `b_send_authorized=false`. It is a test-only
mechanical witness, not a 0600 live receipt. No raw data or caller-supplied
`passed` boolean may control the verdict.

Required negative controls: pipe allocation fails before fork with all
allocated ends closed and no child; one role omits initial ACK, yielding
zero work grants, bounded exact-owned-child cleanup and a fake failure;
O deliberately retains A's not-yet-forked command-read pipe endpoint,
which must be detected by the OS FD
set rather than accepted from a well-shaped ACK. The parent must retain
direct waitable ownership until cleanup; a test-only child alarm, emergency
exact-PID signal, missing normal release ACK or nonzero exit can only
produce fake failure, never positive fake topology. Resource/failure
observations must be recorded without normalizing away the initial red
failure. After this slice, a separate A synthetic exec/EOF and runner
topology gate is still necessary before installed identity source or live
preflight. Success of this slice alone never authorizes real Ollama, model
SHA, HTTP, Safari or B Send.

## Required red/negative controls and release boundary

After this exact amendment is reviewed/committed, the next source step is
one focused red test against public `supervise_once()` using explicit
small-file/synthetic-process effects. It must fail now because public
entry is closed; later a mechanical-protocol test may pass only under a
distinct fake schema with installed/live flags false. Do not change V1–V5
bytes. Allowed eventual source files are the non-B operator and its
focused test; this prospective amendment, a concise result and
`CURRENT_TASK` are documentation scope. A new shared helper or change to
B-only product binding needs a separate behavior-equivalence amendment.

Controls must cover missing/duplicate exec grant, A death versus CLOEXEC
EOF, unknown post-exec image, A pre-listener stop, A-owned→vacant listener
before readiness or during work, A-owned→vacant listener after TERM,
foreign listener, P premature reap or in-flight signal/reap overlap,
missing/stale S_A, blocked source hash/OS observer, unchanged raw
generation with altered argv, runner
zero/multiple/unknown children, truncation/race during enumeration,
S_runner kqueue denial/early exit, op5–7 refusal, blocked cleanup witness,
NOTE_EXIT absent or wrong ident/filter/flags, early O/S_runner stop,
runner close-before-exit, raw canary, FD-allocation exhaustion, model pre/post
drift, and late cleanup/receipt. They must retain already spent ordinals
and `on_wire=unknown` where delivery is uncertain. Proof frames are
canonical, <=4096 B, raw-free; R remains durable and independently
witnessed. A positive fake probe is not a true binary/model attestation.

Design/patch review may reject this topology. If any exact-transition,
runner-exit, FD or T0+90 predicate cannot be proven under the frozen
resources, preserve the counterexample as `REVIEW_REQUIRED`; do not add a
hidden HTTP call, a fourth model hash, retry, weaker baseline, new fake
PASS label, or B Send. Real model/provider/Safari/node graph/human-quality
results remain pending until their own distinct evidence layers pass.
