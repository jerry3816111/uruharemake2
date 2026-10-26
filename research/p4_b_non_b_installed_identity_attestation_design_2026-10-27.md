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
topology/red-test phase; NO-GO for an installed-identity PASS or live
execution.** If FD or cold T0+90 feasibility fails, keep `REVIEW_REQUIRED`
with the minimal measured counterexample; revise topology prospectively,
not by deleting SHA, relaxing the clock, adding HTTP calls or recasting a
synthetic fixture as a real model. Safari/node graph, character quality,
VRM, Function Calling and B Send are unchanged and remain outside this
supporting gate.
