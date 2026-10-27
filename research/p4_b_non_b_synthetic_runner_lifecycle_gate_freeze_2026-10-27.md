# P4-B non-B: prospective synthetic runner lifecycle gate

Status: **design only**, new fake-only marker; no source, red contract, real
Ollama call, HTTP, model bytes, Safari or B Send is authorized by this file.
It follows the accepted native A exec v2 `b170a8a` without changing its
marker/result. The real-path requirements at
`research/p4_b_non_b_real_supervisor_transition_freeze_2026-10-27.md`
§Runner require **O** to enumerate A's child twice and **S_runner** to
independently reobserve/register `NOTE_EXIT`; P-only watching is insufficient.
This fake gate tests those mechanisms without borrowing real identity,
listener, model or T0+90 claims.

## Before evidence and one variable

- The committed A v2 `synthetic_a_exec_probe_v2` result has 11/11 direct
  normal reaps but **zero runner-specific fields**. `/bin/cat` cannot spawn
  a runner. The existing local grandchild test performs libproc enumeration,
  non-parent waitpid and kqueue watching in P itself; it neither connects
  to the public 11-role supervisor nor exercises O/S_runner.
- Isolated short-lived, no-Ollama feasibility probes found 5/5 a fixed
  `/bin/sh -c '/bin/cat <&0 3<&- & wait; read _ <&3; exit 0'` process with
  exactly one `/bin/cat` child, shell OS executable `/bin/bash` and exact
  `/bin/sh -c` argv. With private fd0 and fd3 pipes, A had stable
  `{0,1,2,3}`, child cat `{0,1,2}`, and runner fd0 shared the expected
  pipe handle. Closing fd0's writer ended cat while A stayed live; closing
  fd3's writer then ended A with exit 0. A transient fd10 was seen after
  runner exit, so instantaneous FD counts are not proof of a stable state.
  An independent forked watcher received exact `NOTE_EXIT` 3/3 while P's
  `waitpid(runner,WNOHANG)` was rejected 3/3. These are **feasibility**, not
  integrated acceptance; the first libproc probe mistakenly treated a
  PID-count return as bytes and is not included in those rates.

The single versioned engineering variable is the integrated **A-postexec
runner lifecycle witness**: fixed native shell creates one cat child, O
discovers it, S_runner independently witnesses and watches it, and P
admits release/exit only after both roles' evidence. The changed target,
extra hold pipe and two role behaviors are coupled requirements; this
gate cannot attribute an effect to one of them individually. No changes
to the seven real operations, V1–V5, question/gold, B comparison, port or
model thresholds are allowed. Before code, review this exact file and
commit it. Allowed implementation files after a separate red-test commit:
`p4_b_non_b_parity_live_operator.py`, its focused test, then result report
and `CURRENT_TASK.md`.

## Exact isolated topology and target

The only accepted marker for this diagnostic is an exact plain dict
`{"schema":"synthetic_runner_lifecycle_probe_v1","fault":null}` or one
frozen fault below. Reject subclasses and extra/missing marker keys before
fork, caller-path access or callback invocation. Like the existing fake
markers, ignore `run_dir`, `model_root` and `clock`: do not read, call or
write them. Keep the existing 11
direct P-child roles and 22 role command/proof pipes, existing A exec-status
and runner-release stdin pipes, plus **one** new private A-hold pipe:
25 pipes/50 allocated endpoints. P's soft FD limit is observed/sampled
after allocations and fork-close barriers; never raise it. The v2 24/48
resource sample cannot be reused as this gate's measured margin.

After the initial eleven OS-backed held frames, A receives one exec grant.
For `fault=null`, the fixed target is regular executable `/bin/sh` invoked with exactly
`("/bin/sh", "-c", "/bin/cat <&0 3<&- & wait; read _ <&3; exit 0")`
and empty environment. All command/proof/status role endpoints close
across exec. A's fd0 is the private runner-release read end; its fd3 is
the separate private A-hold read end, intentionally inheritable. The cat
child explicitly closes fd3 and must have only expected stdio FDs. The
status pipe's zero-data CLOEXEC EOF is only a transition hint. The
host-bound OS image for `/bin/sh` was `/bin/bash`; require exact
`/bin/bash` image and the full frozen argv, not a false `/bin/sh` image
assumption. A later host whose OS image differs must fail closed and be
reviewed prospectively, not silently substituted.

Before any runner release, require A still be P's unreaped direct child
with its original raw PID/start generation, PPID and PGID. Use the v2
active, bounded two-complete-snapshot discipline for this **new** target:
exact shell image/argv and stdio-plus-fd3 type/pipe handles, no role
control/status handles; startup VNODE/procargs-unavailable may be recorded
but cannot count as exact. Unexpected PIPE, identity drift, known wrong
image/argv, truncated FD list or timeout fails. A full post-exit FD map
is not a gate because the shell can transiently open fd10 while handling
`wait`; instead require later A liveness/identity and its exact final
normal exit.

## O discovery, S_runner watcher, and release order

Once A is postexec-live, P uses an active **spawn-presence gate** under
the same original five-second deadline: first OS check immediately,
then bounded reacquisitions at least 10 ms apart while no child exists.
Record each attempt as a raw-free count/identity category. On the normal
path, two or more children, a wrong image/PPID/generation, a truncated
list or A drift fails immediately; one exact live cat permits the O
grant but is not accepted as O's evidence. The duplicate-runner
negative variant is the sole exception: P must first establish two
live exact cats before O grant so O itself can reject the two-child
condition; this branch can never PASS. A fixed sleep or P-only
preliminary enumeration may not replace O. O then receives a single
bounded enumeration grant. O
brackets **two** `proc_listchildpids(A)` reads with A's raw generation,
rejects truncated/duplicate/zero/multiple/drifting results, and obtains
the unique runner's raw generation, PPID=A, PGID, exact OS `/bin/cat`
image/full argv and exact stdio-only FD/pipe-handle map. O sends a bounded
frame; P validates its structure and performs an independent OS spot-check
before relaying the witnessed identity to S_runner. A frame or child-PID
self-report is not OS authority. The Python/libproc API returns a **PID
count**, not byte count; tests must exercise that contract.

S_runner remains a separate, initially witnessed P child. It must
independently reacquire A and runner raw generations, PPID/PGID,
image/argv and expected fd0 handle; it cannot merely echo O's frame. It
registers `EVFILT_PROC/NOTE_EXIT` for that exact runner before P closes
the runner-release writer, checks raw generation again and sends a
bounded registration frame. P requires a real S_runner kqueue FD of OS
type 5 plus an exact registration frame; P's own kqueue does not substitute
for S_runner's. P calls `waitpid(runner,WNOHANG)` and must get
`ChildProcessError`: the runner is A's child, not P's.

Only then may P close the runner-release writer (zero bytes). The cat
must exit. S_runner's event frame must contain the original runner PID,
`filter=EVFILT_PROC`, `fflags` containing `NOTE_EXIT`, and no `EV_ERROR`;
unrelated or malformed fields cannot fill the receipt. This is a
cooperative, source-reviewed S_runner kernel-event path, not a proof
against a malicious helper fabricating the same correct-looking fields. O and
S_runner independently verify disappearance of the **original raw
generation** and no remaining child of still-live A under the deadline;
P checks their bounded reports and may OS spot-check. This is exit
observation, never P reap. `runner_reaped_by_parent` must be
`not_applicable`. Keep O and S_runner alive until these proofs finish.
Then P closes the A-hold writer, observes A's exact normal exit 0 and
reaps A; only then normally release/reap O, S_runner and all other direct
roles. A normal positive result needs 11/11 direct normal reaps and a
real S_runner event. Emergency signals or channel EOF never count.

The return is `schema=fake_runner_lifecycle_preflight_v1`,
`status=fake_runner_partial`, measured FD samples/soft-limit margin,
bounded raw-free O/S event and exit summaries, `runner_exit_observed=true`,
`runner_reaped_by_parent=not_applicable`, and permanent
`installed_identity_proven=false`, `physical_stop_unproven=true`,
`full_gate_pass=false`, `b_send_authorized=false`,
`work_grants=http_calls=model_bytes_read=0`. Do not return raw child PID,
source text, pipe handles or private dialogue in a public receipt.

## Fail-closed controls, cleanup, and acceptance

The frozen fault enum is `null`, `runner_exited_before_enumeration`, `duplicate_runner`,
`o_wrong_runner_pid`, `watch_registration_missing`, `wrong_exit_event`,
`retain_private_hold_fd_in_runner`. The normal/null target keeps the
**only positive** exact script above. `runner_exited_before_enumeration`
uses that same script but closes the runner-release writer after A's
exact shell witness and before O grant. P must first OS-confirm a
**unique live `/bin/cat` child under the same A** with raw generation,
then close the writer and confirm that original generation is gone
while A remains held on fd3. Only then may O be granted enumeration
and reject zero children; a cat that never spawned or exited early for
another reason cannot make this negative test green.

Only two negative faults use different, fixed literal scripts; neither
can ever produce a positive result. `duplicate_runner` uses exactly
`/bin/cat <&0 3<&- & /bin/cat <&0 3<&- & wait; read _ <&3; exit 0`.
Before O grant, two `/bin/cat` children must be OS-confirmed live
simultaneously, both with exact stdio-only FDs; O rejects two.
`retain_private_hold_fd_in_runner` uses exactly
`/bin/cat <&0 & wait; read _ <&3; exit 0`; its one cat must be
OS-confirmed to inherit fd3 with the private A-hold pipe handle, and O
rejects the runner FD leak. Each negative variant's A OS `/bin/bash`
image **and its own exact `/bin/sh -c` argv** must be verified before
the named downstream fault is checked, or an earlier normal-argv
mismatch would make a false-green negative test. The normal script
and its acceptance are never altered or relaxed. Isolated short-lived
probes found duplicate two-live-child behavior 3/3 and inherited fd3
handle 3/3; closing both private writers ended A normally in all six.
These are feasibility observations, not integrated acceptance.

Zero/duplicate runner must fail O's exact
enumeration; wrong O PID must fail independent OS/S_runner match; missing
registration must not close runner stdin as a positive release; wrong
event ident/filter/fflags or `EV_ERROR` must not fill exit proof; retained
hold-pipe inheritance must fail the runner OS FD map. No fault may yield a positive receipt,
work/HTTP/model grant, or leaked direct P child. The test-only variants
must force the named condition rather than allowing an unrelated early
failure to make every negative test green. In particular, the duplicate
runner fault must hold **two live cat children simultaneously** and obtain
OS evidence of both before granting O enumeration; merely launching them
in sequence does not test multi-child rejection. Exact fixed failure codes are
required in the red contract before source.

On any failure, P first closes both private writers, bounds every owned
direct-child cleanup, and verifies known runner generation disappeared.
If a known runner persists, any S_runner signal is only to the freshly
matched exact PID, never a group/blind signal; P cannot waitpid/reap it.
No emergency signal counts toward the positive 11/11. Keep the 5-second
parent observation deadline, 8-second child alarm backstop and <25-second
negative test bound, with no retry or arbitrary fixed sleep to hide
transient observations. If the kernel/host does not expose a reliable
event, full FD map or cleanup witness, return a fixed fake failure and
retain `REVIEW_REQUIRED`; do not weaken the gate.

There is an unresolved **early-A-death/orphan window** if A forks a
runner but dies before any observer can identify it. A shell PID receipt
pipe would not solve that window and would add authority confusion. This
fake gate must not claim to prove cleanup in that case, and any observed
instance is a NO-GO requiring stronger supervision design before live
authorization. It also does not prove true Ollama runner bytes/model,
listener ownership/port vacancy, physical T0+90 stop or production safety.

Acceptance order: test-only red v1 marker/positive/six faults/invalid
shapes and exact OS controls against the public stub; then source;
focused normal/negative tests; repeat isolated normal probes; affected
operator regression with `-s` to preserve the 256-FD test envelope;
independent same-model patch review; diff/cost/failure report; scoped
commit/push/PR exact-head check. The red test must not read formal data,
start Ollama or mutate the production DB. After this gate, real installed
Ollama/model/port/T0+90 and Safari remain separate pending evidence.
