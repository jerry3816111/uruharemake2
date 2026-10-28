# M57.7 Auditable Participant Runtime Launcher — Acceptance

Date: 2026-09-05

Result: **PASS for the bounded macOS arm64 project-runtime and launcher claim.** This is an engineering-operability
result only. It creates no real human evidence, model result, target-outcome access, formal M57 result or M58 authority.

## Problem closed

Before M57.7, M57.6 recovery worked only through a hidden Codex-bundled Python. The default Python 3.14.2 and the
ordinary project Python 3.12.10 had no `cryptography`, and the repository had no lock, participant runtime or launcher.
The project-owned ready-runtime count was therefore **0**, and a repository user could not independently start the
frozen recovery path.

M57.7 adds one explicitly prepared local runtime and a fail-closed launcher. Preparation uses the project Python
3.12.10 and exactly three hash-locked wheels. Collection launch now audits the complete attestation before replacing
itself with that runtime and the unchanged M57.6 entrypoint. It neither invokes nor requires the Codex interpreter.
The project-owned ready-runtime count is now **1** on the tested machine.

## Single changed variable

Only `project_owned_attested_participant_runtime_launcher` changed. M57.4 evidence semantics, M57.5 participant
capability/session semantics, M57.6 Scrypt/AES-GCM recovery semantics, source visibility, role separation, ledgers,
predictions, outcomes, scoring and formal authorization remain unchanged.

The lifecycle is deliberately split:

1. `prepare` may access the network before collection and installs only the three exact `--require-hashes` wheels into
   a staging runtime. It accepts no run, role, token or recovery secret and never repairs or overwrites an existing
   runtime.
2. The staged runtime must pass its own child-process audit before atomic publication. A `0600` attestation binds the
   contract, requirements, base/runtime Python, platform, packages, critical compiled binaries and frozen M57.6 files.
3. `audit` is read-only and rejects missing state, symlink/path escape, attestation tamper, interpreter/package/binary
   drift and upstream freeze drift.
4. `launch` accepts only run ID, role, envelope path and port. It audits before any hidden prompt, strips Python path
   injection variables, then executes unchanged M57.6 with the prepared runtime. There is no collection-time install,
   download or repair path and no secret/token argument.

## Actual verification

- Focused M57.7 suite: **18/18 passed**.
- Adjacent M56.10 + M57–M57.7 suite: **128/128 passed** in **225.69 s**.
- Selected M1/M2/M6/V7/V9/M54–M57.7 compatibility suite: **452/452 passed** in **309.38 s**.
- Python compilation, all M57.7 JSON schemas, implementation-freeze file hashes, image hashes/dimensions and Git
  whitespace validation passed.
- Negative tests reject missing runtime, existing-runtime auto-repair, path escape, a symlink runtime root, attestation
  drift, base/runtime interpreter drift, package drift, critical compiled-binary drift and frozen M57.6 drift.
- Launch-spec tests prove the full audit is ready before execution, the unchanged M57.6 module/action are selected,
  `PYTHONPATH`/`PYTHONHOME` are absent, and role-token or recovery-secret arguments number **0**.

One first selected-suite command named two obsolete M56 test files and exited before collecting any test. It was an
invocation error, not a product failure. The corrected command used the repository's actual filenames and passed; the
failed command remains reported here rather than being hidden.

## Safari functional acceptance

Safari reused one existing local test tab (**36 → 36 tabs; 0 opened, 0 closed**). The normal repository launcher was
invoked from the default Python, audited the project runtime before the hidden prompt, started M57.6, stopped that
process, then started a clean second process with the same public command and participant secret. After reload, one
isolated synthetic coder form was saved through the recovered capability, advancing sample 01 to sample 02 and writing
one exact M57.4 revision.

The graphical dashboard visibly preserved the order
`PREPARE → HASH LOCK → ATTEST → AUDIT → HIDDEN PROMPT → COLLECT`, collection-time installs **0**, real component
rows **0/30**, and formal M57 denied. Both local services were stopped after acceptance; the reused test tab is safe to
close but was not closed.

Failures encountered before the final pass are retained as evidence: Python `-I` hid the repository module; an overly
narrow `PATH` omitted Homebrew Ollama and later `/usr/sbin`; removing `HOME` caused Ollama to panic; Safari accessibility
indices shifted while filling the synthetic form; and one stale Safari index briefly displayed Start Page. The final
launcher uses `-E -s`, a fixed minimal tool path and the existing `HOME`; only one form was submitted, disk content was
checked, the same Safari tab was restored, and the tab count stayed unchanged.

## Measured local cost

- One-time exact wheel transfer: **4,243,044 bytes**.
- One-time project-runtime preparation: **3.349842 s**.
- Prepared runtime size: **26,073,907 bytes**.
- Seven read-only audits: **0.290234–0.293445 s**, median **0.291446 s**.
- Collection-time download/install/repair calls: **0**.

These numbers exclude the required three humans, 90 real component entries, model generation, outcome collection,
energy, offline wheel mirroring, other platforms, code signing/notarization, TLS and production throughput.

## Evidence and claim boundary

The live external-evidence state is unchanged: V7 qualified slots **0/18 evaluators + 0/18 coders**, real temporal rows
**0/30**, real component rows **0/30**, target-outcome accesses **0**, model calls **0**, formal M56 results **0**,
formal M57 results **0**, and M58 authorization **false**.

This pass proves one repository-owned, exact-hash, fail-closed participant runtime on the tested macOS 15 arm64 host
can launch and restart unchanged M57.6 without the hidden Codex interpreter. It does **not** prove offline installation,
cross-platform portability, wheel-source trust, a supply-chain audit, code signing, malicious same-account resistance,
TLS, independent human identity, label validity, Equation V1, LLM advantage, a solved human-response equation or
production readiness.

## Next necessary unit

M57.8 should change only participant-confirmed ledger completion. M57.4 already has a complete-ledger seal primitive,
but the M57.5/M57.6 token-free browser exposes only `POST /save`; a participant who finishes all 30 unique samples has
no browser action to inspect completion and seal their own ledger. M57.8 should add an explicit, CSRF-protected,
token-free confirmation step that calls the unchanged M57.4 seal only at 30/30, fails closed for incomplete, mutated,
wrong-role, outcome-present or repeated-nonidentical state, and preserves the formal-evidence boundary.
