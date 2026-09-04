# M57.6 Crash-Recoverable Participant Capability — Prospective Plan

Date: 2026-09-05

Status: prospective freeze before implementation and before any real participant recovery secret

## Problem proof

M57.5 correctly removes a claimed role token from its private envelope and keeps it only in the collector process.
An isolated prechange run showed that the first collector start succeeds and leaves a valid claimed issuance, while a
second start fails with `M57.5 role capability was already claimed; restart is unsupported`. For a 30-row human
collection, one process crash would therefore discard the only usable capability even though the evidence ledger is
still valid.

The normal project Python and default Python do not contain an authenticated-encryption package. The already-present
Codex desktop Python 3.12.14 contains `cryptography==50.0.1`, including Scrypt and AES-GCM. M57.6 will bind exactly to
that audited implementation for this local acceptance. It will fail closed elsewhere; it will not install a package,
write its own cipher, invoke an undocumented platform primitive or claim general runtime portability.

## Single changed variable

Add participant-secret-bound encrypted recovery for an already separated M57.5 role capability. Do not change source
visibility, coder/adjudicator roles, ledgers, seals, disagreements, manifest projection, model execution, outcomes,
scoring or formal authorization.

## Frozen state machine

1. The public collector command accepts only run ID, role, envelope path and port. It obtains a recovery secret twice
   from a real TTY on first activation and once on restart using hidden `getpass`; argv, environment variables and the
   browser are not secret inputs.
2. Before consuming the M57.5 envelope, write a full-sync intent containing random salt/nonce and exact frozen crypto
   parameters. Derive a 256-bit key using Scrypt (`N=32768, r=8, p=1`) and encrypt the M57.4 role token using AES-GCM.
3. AEAD additional authenticated data binds the run, role, participant pseudonym, M57.5 commitment and contract,
   token hash, initial envelope hash and crypto parameters. Full-sync the `0600` encrypted vault before calling the
   unchanged M57.5 claim operation.
4. After a valid claim and spent envelope, full-sync an activation commitment binding the exact vault and M57.5 claim.
   On restart, the same secret must decrypt the vault and reproduce the committed token hash before the collector can
   start. No secret or key is persisted or returned.
5. A vault-before-claim interruption resumes by decrypting the vault and completing the one-time M57.5 claim. A valid
   claim-before-activation interruption resumes by validating the spent envelope and writing the activation
   commitment. If the M57.5 claim receipt was durable but its spent-envelope write was interrupted, reconstruct only
   the exact already-committed spent record and verify its hash before completing the scrub.
6. Wrong secret, AEAD tamper, path/role mismatch, crypto version drift, outcome-state appearance, invalid claim/spent
   state, a spent envelope without a valid vault or changed frozen dependency fails closed. No plaintext backup or
   recovery override exists.
7. The browser receives only a new random host-only HttpOnly SameSite=Strict cookie and a separate CSRF token. Neither
   the M57.4 token nor recovery secret appears in URL/history, HTML, form or cookie. Plain loopback HTTP is not TLS.

## Verification plan

- Contract: exact public signatures, M57.5 frozen hashes, exact crypto version and no secret-bearing CLI field.
- Recovery: first activation, clean restart, vault-before-claim interruption, claim-before-activation interruption and
  exact claim-before-scrub completion.
- Negative: wrong secret, changed role/path, ciphertext/AAD tamper, crypto drift and outcome race all reject before a
  browser is served; state hashes remain unchanged for wrong-secret attempts.
- Surface: vault, intent, activation, public metadata, URL, HTML, form, cookie, CSRF and redirect contain zero tested
  raw role-token or recovery-secret occurrences.
- Functional: after a process-equivalent restart, one isolated synthetic Safari form submission must still write an
  exact unchanged M57.4 coder revision and advance to the next token-free sample.
- Compatibility: focused M57.6, adjacent M56.10 + M57–M57.6, then selected M1/M2/M6/V7/V9/M54–M57.6 suites.
- Cost: seven isolated encrypt→claim→restart→decrypt→one POST runs, reporting wall time and durable bytes. This is not
  human labor, full 90-entry throughput, model cost, energy or adversarial-security evidence.

## Stop and claim boundary

M57.6 passes only if every accepted-runtime recovery and negative-path gate passes, Safari demonstrates a real
post-restart save, no tested secret surface is created, no frozen dependency changes and outcome/model/formal counts
remain zero. Missing `cryptography==50.0.1` is a supported terminal refusal, not permission to weaken the design.

Even a pass establishes only local crash-recovery mechanics. It does not prove three physical humans, protect against
a malicious process sharing the macOS account, guarantee erasure of Python objects from RAM, provide TLS, create real
component evidence, validate a private mental state or Equation V1, show an LLM comparison advantage, solve a human
response equation or authorize M58.
