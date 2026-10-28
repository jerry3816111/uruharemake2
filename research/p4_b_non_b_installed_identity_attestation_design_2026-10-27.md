# P4-B non-B installed-identity attestation: read-only inventory and prospective gate

Status (2026-10-27): **design only; NO-GO for real Ollama, model hashing, HTTP,
Safari, B Send, or a live-release claim.** This is the next dependency of the
existing P4-B non-B task, not a new M or a change to its question, gold,
baseline, generation parameters, seven-call cap, or T0+90 contract. Two
separate read-only assistant-agent reviews agreed with the *design boundary*
only; they are same-model reviews, not independent human evidence. The exact
live-supervisor freeze remains the higher-level execution contract.

## Before evidence and the decision it changes

At `3097ab9`, V5 has a Python H child with one synthetic loopback LISTEN.
O's per-process observation can prove H owned it **at admission**, but H
does not serve Ollama, accept HTTP, or load a GGUF; seven W results are
injected. V5's sampled P/O/H high-water FD observations are 252/15/12 with
P soft limit 256; these samples are not a continuous peak proof and show no
demonstrated margin for another resident pipe or child. Public
`supervise_once()` still fails with `process_supervisor_not_implemented`.
`_identity_process()` in the non-B operator checks *supplied* PID/hash-shaped
fields against frozen constants, and `_source_before_completion()` explicitly
does not establish full launch-argv or binary conformance. A ready listener
therefore cannot be promoted to installed-source identity.

Read-only local metadata on 2026-10-27 found the expected application paths
`/Applications/Ollama.app/Contents/Resources/ollama` and `llama-server` as
regular executable files of 49,401,984 and 14,749,408 bytes, respectively.
The shared model directory exists. **No current binary or private model bytes
were hashed, no private clone was validated, and no Ollama PID/argv/listener
was observed in this inventory.** Existence and size do not establish the
historical frozen SHA or a same-run process identity.

The older `p4_b_isolated_ollama_identity_probe.py` records frozen manifest,
five blob, GGUF/template/system and daemon/runner SHA expectations. Its
`_model_store()` checks a 0700 private clone, distinct inodes, six file
digests and manifest references, but its older `_process_identity()` uses
`ps` and lacks raw-generation binding. The B-only
`uruha_p4_b_child_local_identity.py` offers a stronger macOS
raw-generation→procargs→raw-generation snapshot, executable+argv digest and
loopback listener ownership; `uruha_p4_b_private_endpoint_binding.py` uses
those with a private model-store check. Neither is a drop-in non-B gate:

| Reuse trap | Observable consequence | Required decision |
|---|---|---|
| B `_inspect_live_identity()` invokes `_model_store()` twice | Calling it both pre and post would perform four whole-store validations, at least 18,732,352,760 logical bytes | Do not call it directly. Design one supervised pre and one supervised post store validation, exactly as frozen. |
| B `argv_digest` hashes `{executable, argv}`; non-B `_argv_hash` hashes only argv | Equal-looking SHA fields do not bind the same bytes | Give the run-bound OS digest a separately named, versioned field; never compare the two as though equivalent. |
| V5 H is synthetic Python | A listener owner and a matching injected hash do not imply Ollama | Keep synthetic and installed-identity verdicts separate; no `installed_identity_proven` in fake receipts. |
| V5 P sampled 252/256 open FDs | Another resident IPC channel could fail before source proof | First calculate maximum simultaneous demand at allocation/close barriers and sample success/abort paths; do not call V5 samples a continuous peak. Do not raise the OS limit. |

The exact live freeze budgets `_model_store()` at 4,683,088,190 logical bytes
per validation; precisely one pre plus one post means **at least
9,366,176,380 bytes**, plus executable hashes. Four validations are
forbidden without a prospective amendment. A historical *cached* B-only
four-validation microbenchmark was 9.301121 s; it excludes cold load,
daemon startup, HTTP, shutdown, Web and receipt. It cannot certify the
non-B T0+90 schedule. No new model I/O was spent for this design.

## Single next implementation variable and admissible evidence

The next source/test slice may change only the **provenance of the non-B
identity verdict**: from caller-supplied fields to a supervised, run-bound
observation of installed files and processes. It must not alter the frozen
question, answer, usage-delta rule, prompts, model options, seven external
HTTP operations, or existing V1–V5 fake result bytes. The operator, its
focused tests, this prospective design, a concise result and `CURRENT_TASK`
are the intended scoped files; any shared helper extraction requires a
separate behavior-equivalence review before source edits.

The live schema and order must keep three evidence classes distinct:

1. **Expected reference**: pinned source tag `v0.34.4`, version, binary,
   manifest, GGUF, template and system SHA values from the frozen contract.
   This is an expectation, not a measurement of the currently installed app.
2. **Filesystem observation**: after T0 and before daemon launch, one
   supervised read-only full store validation plus exact daemon/runner file
   hashes, regular/single-link/private-clone and inode metadata. Pin file
   identity across open/read/close; replacement, symlink, hash mismatch,
   blocked read or missing proof must fail closed before W_GO. Repeat the
   store validation **once** after work, then compare the same private
   manifest/blob identities. A pre-only pass is not a final pass.
3. **Same-run process observation**: bracket each macOS PID with kernel raw
   generation; capture PPID/PGID, OS executable and *exact* argv, required
   private environment, resolved daemon/runner binary and `--model` GGUF
   path, and exact loopback LISTEN owner. The daemon must be the supervised
   child; the runner must be its child on a distinct private port. Recheck
   before both tokenizers, before completion, and at cleanup using the same
   initial identities. A callback-provided SHA, API version, old PID or
   free/ready port alone is never this class of evidence.

The first-run daemon may exist before the runner. Thus the pre-W_GO gate
can certify the pre-store and daemon only; it must not claim a runner that
has not started. The runner witness and frozen source-conditioned
branch/BOS/NumCtx/rendered-UTF8/token predicates become mandatory **before
ordinal 7**. After ordinal 7, post-store validation must complete inside
the T0+80 work window or strictly fail; T0+80..90 remains reserved for
witnessed stop, port proof and receipt. These are separate required verdicts.
A normal completion must not
retroactively make an earlier unsupported source predicate true.

All evidence crossing IPC is at most 4096 bytes per frame, canonical and
raw-free: `run_id`,
stage, initial/current PID raw generation and PGID, separately typed OS
executable+argv digest, canonical file identity/digests and logical byte
counts, exact port-owner observation digest, timing, and fixed failure
codes. No raw model bytes, process environment, rendered prompt, token IDs,
HTTP body or traceback locals belong in public IPC/receipt. Parent checks
the received proof against independently pinned expected values, not a
child-provided `passed` boolean. It must never call full SHA, `ps`, `lsof`,
or blocking receipt I/O synchronously on its watchdog loop.

The tagged-source→installed-binary link remains **cooperative conformance**:
matching historical SHA, observed version and required branch behavior do
not prove a reproducible build or code signature. The known same-helper
PID-final-check→`kill` reuse race also remains; do not claim adversarial
process isolation. The private clone is read-only and is not rebuilt here.

## Pre-source feasibility, controls, and stop rules

The real path must be separate from V5's 123+12 one-shot-pipe fake topology.
One prospective topology to review before a red test is a nonblocking parent
P with resident journal D, worker W, receipt R, attestor O, and bootstrap A;
initially witnessed signal helpers S_D/S_W/S_R/S_O/S_A plus S_runner wait
for commands or a later runner. At most two unidirectional pipes per role
would be 22 pipes/44 endpoints before forks for these 11 roles, with P
retaining only its end of each channel after fork; an exec-status pipe and
logs are additional, short-lived and must be counted. All channels are
bounded canonical frames with monotonic phase/sequence and one-use grants;
the seven ordinals do **not** each reserve twelve more pipes. This is a
candidate upper-budget calculation, **not** a measured peak, a source GO, or
permission to relax the existing durability/cleanup contract. The parent
must close every inherited non-role FD in children and keep blocking hash,
OS inspection, fsync and HTTP out of its event loop. If the candidate cannot
preserve frozen semantics, stop for design review rather than copy V5's
nearly exhausted topology into the live path.

The candidate A is a direct, unreaped P child which first waits as a
bootstrap under an initial PID/raw-generation/PGID/PPID/argv witness. Only
after the pre-store/binary proof and S_A initial ACK may it make one
explicit `execve` transition to the pinned Ollama `serve` binary with
private endpoint/model/cloud-disabled environment and 0600 logs. CLOEXEC
EOF alone is not success: require A still waitable, unchanged raw generation,
and O's fresh executable/exact argv/env/loopback-owner proof before W_GO.
Before a listener exists, an exact-PID stop can only rely on the still
waitable direct child plus its known bootstrap or fully observed post-exec
identity; a PID with an unknown intermediate image is *not* blindly
signaled and remains `physical_stop_unproven`. This pre-listener stop rule
and the authorized one-time exec identity transition require a reviewed
amendment to the existing exact freeze before source edits.

The runner is a later A child, potentially created during render-only
operation 4. S_runner must acquire its own initial raw-generation/parent/
PGID/executable/argv/GGUF/listener witness before operations 5–7. P cannot
`waitpid` that grandchild, so independent runner exit/port-vacancy proof
must be recorded separately from a claim that P reaped it. Whether this
meets the old cleanup wording is a **design-review question**, not a silent
weakened PASS. A failed initial runner witness forbids ordinal 7 and may
leave physical cleanup unproven. The T0+80/90 schedule, private ports and
shared 11434 invariance apply to this real path exactly as frozen.

### Isolated OS feasibility result (2026-10-27)

An added macOS synthetic grandchild test in
`test_p4_b_non_b_parity_live_operator.py` now exercises the *necessary OS
primitive*, not the candidate topology: `proc_listchildpids(A)` yielded the
one local child B; the kernel raw-generation witness identified B's parent
as A; P's `waitpid(B, WNOHANG)` correctly refused non-parent ownership;
`EVFILT_PROC/NOTE_EXIT` registered by P before release was absent while B
waited and delivered one exit event afterward. The first version failed
because this repository's `product_checks` Python has no `os.waitid`, even
though a different system Python did. The final test uses the already used
nonblocking `waitpid(A, WNOHANG)` only for its *direct, live* child and
provides test-only five-second child alarms plus bounded parent cleanup.
Focused final result **1/1 in 0.70 s**; final operator-file regression
**369/369 in 111.06 s**. No Ollama, private model bytes, HTTP, Safari or
B Send were used. This rules out one local API-availability objection but
does not prove enumeration completeness under races, a runner listener,
S_runner's initial witness, kqueue availability inside a future sandbox,
exact daemon identity, or T0+90. Those remain hard gates.

Before implementing the gate, a focused topology test must calculate maximum
simultaneous FD demand at every allocation/close barrier and record P's FD
samples under success **and** FD-allocation/blocked-hash/abort/receipt paths.
Target no more than the existing sampled envelope of 252/256, but do not call
those samples a continuous peak or a real Ollama FD guarantee. The design must
reuse or release phase-scoped channels, not append a resident pipe. The O/S_O
watchdog arrangement is a candidate for blocking hashes, but only a
measured phase diagram and initial/fresh witness tests can authorize it.
T0 starts before pre-hash/startup; new work stops by T0+80, exact witnessed
cleanup and raw-free durable receipt by T0+90. Count actual two store
validations, logical bytes, CPU, wall, cold-load/preparation separately,
and all helper/HTTP calls. Do not infer a 90-second bound from cached SHA.

Prospective controls: positive small synthetic files may prove **only** the
mechanical observation protocol, never installed Ollama; negative controls
must include wrong binary/argv digest form, wrong model path or blob, changed
inode/hash during read, symlink/extra blob, missing/changed daemon or runner
raw generation/PPID/PGID, wrong/foreign listener owner, missing runner before
ordinal 7, blocked hash and cleanup observer, stale/duplicate/late proof,
FD exhaustion, source branch/NumCtx/BOS mismatch, and post-store drift.
A **pre-W_GO** admission failure means zero W_GO and zero HTTP. If runner or
source identity fails after operations 1–6 but before ordinal 7, ordinal 7
is forbidden while previously issued operations and their `on_wire`/spent
records remain intact. Post-grant uncertainty keeps `on_wire=unknown`
where appropriate, never refunds a spent ordinal. Failure
receipt is required when R remains available, without hiding physical-stop
uncertainty. The original V5 fake suite and affected regressions must stay
green; a true live verdict requires separate committed-source review,
read-only live preflight, explicit GO and at most one frozen attempt.

Decision now: **GO for this source-only design and for a subsequent focused
real-supervisor topology review, then a focused red test of the public
fail-closed entry; NO-GO for an installed-identity PASS or live execution.**
Do not add a V6 fake H-identity flag: V5 test binding uses daemon PID 101,
while its actual H listener is a different forked Python PID. H itself sends
`h_initial/h_ready/h_stopped` and owns the synthetic port. Executing Ollama
in H would erase that IPC and change the initial argv/binary witness;
forking Ollama from H would move the port owner to a child with no initial
S_H witness. Neither is a valid one-variable extension of V5. The real
path needs an explicit launcher→daemon→runner parentage, initial and fresh
OS witnesses for each, and a different phase-scoped IPC/FD budget. Small
synthetic files/processes can test that new *protocol*, but a fake positive
must never set installed-identity or live-release PASS. If FD or cold T0+90
feasibility fails, keep `REVIEW_REQUIRED`
with the minimal measured counterexample; revise topology prospectively,
not by deleting SHA, relaxing the clock, adding HTTP calls or recasting a
synthetic fixture as a real model. Safari/node graph, character quality,
VRM, Function Calling and B Send are unchanged and remain outside this
supporting gate.
