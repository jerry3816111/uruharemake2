# M57.7 Auditable Participant Runtime Launcher — Prospective Plan

Date: 2026-09-05

Status: prospective freeze before implementation, before project-runtime provisioning and before any real participant launch

## Problem proof

M57.6 can safely recover a claimed participant capability, but only the hidden Codex desktop interpreter currently
contains its frozen authenticated-encryption backend. The default Python 3.14.2 and the project's ordinary Python
3.12.10 both report no `cryptography` distribution. The repository has no dependency lock, Python-version file,
project-owned runtime or participant launcher. A person therefore cannot start M57.6 from the repository alone, and a
future Codex runtime update could silently remove the only working path.

A temporary feasibility probe showed that the ordinary project Python 3.12.10 can create a copied venv and run the
unchanged M57.6 primitives after installing three macOS arm64 binary wheels whose names, versions and SHA-256 hashes
are now prospectively locked. The temporary runtime imported Scrypt and AES-GCM, and its two critical compiled binary
hashes matched the wheel contents. No runtime was added to the project by that probe.

## Single changed variable

Add a separately prepared, project-local, hash-locked and fail-closed participant runtime launcher. Do not change
M57.4 evidence semantics, M57.5 capability issuance/session semantics, M57.6 cryptography/recovery semantics, source
visibility, roles, ledgers, predictions, model execution, outcomes, scoring or formal authorization.

## Frozen lifecycle

1. `prepare` is an explicit setup operation before collection. It accepts no run, role, token or recovery secret. It
   verifies the exact base Python 3.12.10 executable and hash, builds a copied venv under the ignored project `.venv`
   directory, and installs only the three exact hash-locked binary wheels using pip `--require-hashes`.
2. Preparation may access the package index. It stages into a newly created directory and atomically publishes the
   runtime only after a child-process audit passes. Existing or partial final runtimes are never repaired or
   overwritten automatically.
3. A `0600` attestation binds the M57.7 contract and requirements hashes, exact base/runtime Python, platform,
   package versions, critical compiled-binary hashes, M57.6 frozen dependencies, smoke-test result and runtime path.
   The runtime directory is `0700`.
4. `audit` is read-only. It revalidates the M57.7 contract and all M57.6 frozen files, executes an isolated child audit
   in the prepared runtime, compares every attested field, validates the critical binary hashes, and reports ready
   only if all values match. Missing state, symlink/path escape, version drift, binary drift or attestation tamper
   fails closed.
5. `launch` accepts only run ID, role, M57.5 envelope path and port. It performs the complete audit before replacing
   itself with the prepared runtime and unchanged M57.6 `--serve-recoverable` command. Only after that replacement may
   M57.6 ask for the hidden TTY secret. Launch does not invoke pip, download, install, repair or take token/secret
   arguments, and it removes Python path injection variables from the child environment.
6. The launcher and dashboard may show hashes, versions, readiness and formal-evidence boundaries. They must not show
   or accept a participant recovery secret or M57.4 role token.

## Verification plan

- Problem: default/project/Codex interpreters and repository runtime inventory are preserved as prechange evidence.
- Contract: exact M57.6 freeze/config/module hashes, exact requirements hash, base interpreter and three wheel hashes.
- Provisioning: one explicit clean project-local preparation; no existing-runtime overwrite; missing/offline package
  failure cannot publish a ready runtime.
- Audit: fresh child process proves exact Python/packages/primitives/binaries; attestation, package, binary, path,
  interpreter and frozen-dependency drift each reject.
- Launch: public arguments contain no token/secret; audit precedes `execve`; launch performs zero pip/download/install
  calls and strips `PYTHONPATH`, `PYTHONHOME` and user-site injection.
- Functional: the launcher must start the unchanged M57.6 collector, survive a process stop/restart with the same
  hidden participant secret, and permit one isolated synthetic M57.4 form save.
- Compatibility: focused M57.7, adjacent M56.10 + M57–M57.7, then selected M1/M2/M6/V7/V9/M54–M57.7.
- Cost: report preparation network bytes/time separately from steady-state audit/launch time and local runtime bytes.
  Do not confuse setup cost with human labeling, model or production cost.
- Safari: a graphical operator page must make `prepare → attest → audit → hidden prompt → M57.6 recovery` visible and
  retain zero real-human/formal counts; an actual Safari collector save is required.

## Stop and claim boundary

M57.7 passes only if a normal repository command can use the independently prepared local runtime without the Codex
interpreter, runtime drift fails before secret input, launch contains no installation path, unchanged M57.6 recovery
works through Safari and all formal/outcome/model counts remain zero. If the copied venv cannot be made deterministic
from the locked wheels, retain M57.6's hidden-runtime limitation rather than accepting an unverified environment.

Even a pass is local to macOS 15 arm64 and the exact installed Python framework. It is not an offline source bundle,
cross-platform package, software-supply-chain audit, code-signing/notarization result, malicious same-account defense,
TLS, human identity proof, real component evidence, Equation V1 validation, LLM superiority, a solved human-response
equation, production readiness or M58 authorization.
