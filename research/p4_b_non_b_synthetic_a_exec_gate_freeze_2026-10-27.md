# P4-B non-B: prospective synthetic A exec/EOF gate

Status: design for the next **fake-only** source slice, not source or live
authorization. It follows the committed 11-role held-child topology at
`aef2a4e`. It leaves that exact marker, its receipt bytes, V1–V5, the seven
real operations, question/gold, B result and T0+80/90 gates unchanged.
Two same-model read-only design discussions recommended separating this
A transition from the runner topology; they are not independent human
approval. Exact-file review and a commit must precede new red tests/source.

## One variable and before evidence

The existing `synthetic_role_graph_probe_v1` proves A was initially held
with OS-witnessed control FDs and normally released. It **never executes**
the child; an FD_CLOEXEC flag alone does not show control endpoints disappear
at a real image transition. The new variable is A's one controlled held→exec
transition with an independently observed post-exec image and FD set. Do
not add runner discovery, listener, model hash, HTTP or product turns in
this slice.

Only a separate exact plain dict
`{"schema":"synthetic_a_exec_probe_v1","fault":null}` may enter this
diagnostic. The frozen fault enum is `null`, `missing_exec_grant`,
`duplicate_exec_grant`, `death_before_exec`, `close_status_without_exec`,
`wrong_exec_argv`, `retain_control_fd`. Reject subclasses, extra/missing
keys and unknown values through the existing public fail-closed error before
fork/callback/path access. Ignore caller `run_dir`, `model_root` and `clock`;
never read or write them. No production memory, Ollama, model file, TCP,
HTTP, Safari or B Send is authorized.

## Synthetic protocol and witnesses

Reuse the 11 direct P-child roles and 22 command/proof pipes plus the
existing CLOEXEC exec-status pipe. Add **one** separately counted private
stdin pipe, allocated before forks: 24 pipes/48 endpoints in this *new*
marker only. No role command/proof endpoint may become post-exec stdin.
The existing marker stays at 23 pipes/46 allocated endpoints. P must sample
open FDs after each allocation and fork-close barrier, report soft limit,
sampled max/min margin and final parent count; the prior 50/256 sample is
not a budget proof for this configuration. Never raise the FD limit.
After A forks, P closes its exec-status writer and private-stdin reader;
the other ten children close both private-stdin ends and the exec-status
writer as non-role FDs.
Otherwise status EOF and child FD-set evidence would be invalid.

All eleven initial frames and exact child FD sets must pass the previous
OS-backed witness before A is armed. In the new marker A's fd0 is replaced
by the private stdin read end before its initial frame; the original read
FD is closed. P checks this new fd0 pipe handle via libproc. A has only
fd0/1/2, its own command-read and proof-write ends, and the exec-status
write end; all other inherited ends close. The P-owned private stdin write
end stays open. A's initial PID/raw-generation/PPID/PGID and exact held
image/argv are recorded before one bounded, canonical exec grant.

The synthetic executable is the canonical absolute regular executable
resolved from the isolated product-checks `sys.executable` at runtime.
The frozen argv is exactly `[canonical_path, "-I", "-S", "-c",
"import os,sys;sys.exit(0 if os.read(0,1)==b'R' else 7)"]`.
This fixed no-network program blocks reading one byte from fd0 and exits 0
only for P's `R` release byte. The `wrong_exec_argv` fault appends exactly
`"unexpected"` after this code, leaving behavior otherwise unchanged.
Do not accept arbitrary caller code, shell, model path or target argv.
The exec environment is exactly `{}`; A consumes at most one
grant, closes role command/proof FDs, verifies exec-status writer CLOEXEC,
then calls `os.execve` exactly once. P may write one release byte only
after post-exec checks; no work/HTTP grant exists here.

The status pipe must produce **zero-data EOF**, but EOF is only a hint:
child death or a manual close produces the same observation. While A is
still P's unreaped direct child, require `waitpid(A,WNOHANG)==(0,0)`,
the same raw PID/start generation, PPID and PGID bracketing two post-exec
OS process observations, and exact new executable/full argv. Reacquire
the post-exec FD set twice under raw-generation brackets; both exact maps
must agree. It must contain only expected stdio FDs, with fd0's private
pipe handle unchanged and fd1/fd2 type and (if pipe) handle unchanged from
the initial witness, and **no** role command/proof or exec-status pipe
handle/FD. Missing OS permission, truncated FD list, changed generation/FD
set, unknown image,
unexpected FD or failed CLOEXEC is a fake failure. Only then may P send
the release byte, receive A exit 0 by exact waitpid, normally release and
reap the other ten direct children, and return
`schema=fake_a_exec_preflight_v1,status=fake_transition_partial`.
Permanent flags remain `installed_identity_proven=false`,
`physical_stop_unproven=true`, `full_gate_pass=false`,
`b_send_authorized=false`; `work_grants=http_calls=model_bytes_read=0`.
The result may say `synthetic_exec_observed=true` only after all these
witnesses, never merely after EOF. A normal exit does not prove real
Ollama was stopped.

The source call count of one `os.execve` plus one P grant is a controlled
cooperative-program claim, not proof that an adversarial process could not
perform a transient unobserved exec. File path/OS procargs observation is
not a memory-loaded-image SHA. No claim of a real installed Ollama binary,
runner or T0+90 physical stop follows.

## Fail-closed controls and acceptance order

- `missing_exec_grant`: A remains held; no EOF-success, release, work or
  positive receipt. Deadline and exact owned-child cleanup are required.
- `duplicate_exec_grant`: the P grant state rejects the second attempted
  issue. Even if the first was delivered, no positive result is permitted;
  cleanup must account for any synthetic image already started.
- `death_before_exec`: EOF occurs through A death; live/process-image check
  rejects it. If the WNOHANG check reaps A, record that terminal status and
  forbid any cleanup signal or second reap of the PID. No fake transition PASS.
- `close_status_without_exec`: A closes the writer but remains held; OS
  procargs remains the held image and rejection cannot rely on EOF alone.
- `wrong_exec_argv`: a harmless, bounded target with one altered argv item
  remains alive long enough for OS observation; exact argv mismatch fails.
- `retain_control_fd`: deliberately clear CLOEXEC on one A role control
  endpoint **only after the eleven initial OS FD witnesses pass**, then
  leave it open across exec; post-exec OS FD set rejects the extra pipe
  even if status EOF and argv are correct.

All faults must preserve zero model/HTTP/work grants, bounded exact-owned
PID cleanup, no parent FD leak and no leaked direct child. An emergency
alarm or signal is test hygiene and never counts as normal positive exit.
Use the inherited five-second parent observation deadline and a child
eight-second absolute alarm backstop, with at most the existing per-child
0.20+0.20+0.60-second bounded cleanup sequence; the whole negative probe
must finish within 25 seconds. An alarm timer may survive exec while its
handler is reset, so any alarm-triggered target death is a fault, not a
normal exit or proof of physical stop.
The test first goes red against the public exact marker and proves the
failure is `process_supervisor_not_implemented`, not an OS setup failure.
After review, source may edit only `p4_b_non_b_parity_live_operator.py` and
its focused test; result and `CURRENT_TASK.md` may be added after measured
checks. First run focused positive/negative/invalid-marker tests, then the
affected operator file. Any FD/procargs/cleanup counterexample is retained
as `REVIEW_REQUIRED`; do not weaken witness conditions or convert the old
held-only fake PASS into an exec PASS.

The next **separate** gate, only after this one, is an A-postexec synthetic
runner lifecycle with exact child enumeration, S_runner independent
`NOTE_EXIT` registration/event fields and non-parent waitpid boundary.
It must not borrow this A gate as proof of runner or live readiness.
