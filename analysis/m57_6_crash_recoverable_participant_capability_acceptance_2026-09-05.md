# M57.6 Crash-Recoverable Participant Capability — Acceptance

Date: 2026-09-05

Decision: **PASS as a bounded local crash-recovery engineering milestone; real participants/evidence remain 0 and formal M57/M58 remain denied**

Single changed variable: add participant-secret-bound encrypted post-claim restart recovery to the M57.5 role
capability. The frozen M57.4 evidence semantics and M57.5 issuance, claim, token-surface and browser-session
semantics were not changed.

## Problem and prospective boundary

M57.5 correctly removed its bearer token from the role envelope after a one-time claim. That made accidental token
exposure smaller, but it also meant a collector process could not restart: an isolated prechange run accepted the
first start and rejected the next with `M57.5 role capability was already claimed; restart is unsupported`. Losing one
process could therefore invalidate a partially completed 30-row human collection even though its ledger remained
valid.

The regular project Python 3.12.10 and default Python did not provide authenticated encryption. The already-present
Codex desktop Python 3.12.14 did provide `cryptography==50.0.1`, including Scrypt and AES-GCM. The plan therefore
froze that exact existing backend for this local milestone. No dependency was installed, no cipher was invented, and
missing or changed crypto support remains a terminal refusal. This is deliberately not a general portability claim.

## What was implemented

The public collector command still accepts only run ID, role, envelope path and port. The participant supplies a
recovery secret through hidden terminal input: twice on first activation and once on restart. The secret is rejected
outside a real TTY and is not accepted through argv, an environment variable or a browser.

Before the unchanged M57.5 claim, M57.6 full-syncs random Scrypt and AES-GCM parameters, derives a 256-bit key using
Scrypt `N=32768, r=8, p=1`, and writes one `0600` encrypted capability vault. AES-GCM additional authenticated data
binds the run, role, participant pseudonym, M57.5 commitment and contract, original token hash, initial envelope hash
and crypto parameters. Only after the vault is durable may the M57.5 claim and envelope scrub run.

An activation commitment binds the exact encrypted vault to the exact M57.5 claim. A later process must provide the
same secret, authenticate and decrypt the vault, reproduce the committed token hash, revalidate that no outcome state
exists, and reuse the original M57.4 ledger. Wrong secrets and authenticated-ciphertext tampering produce the same
fail-closed error.

Three explicit interruption states are recoverable:

1. encrypted vault durable before the M57.5 claim;
2. M57.5 claim and spent envelope durable before M57.6 activation;
3. M57.5 claim receipt durable before envelope scrub, where only the exact hash-committed spent record may be rebuilt.

The browser receives a newly random host-only `HttpOnly; SameSite=Strict` cookie and a separate CSRF token. Neither
the role token nor recovery secret is placed in URL/history, HTML/form or cookie. Plain loopback HTTP remains non-TLS.

## Measurable result

- before: first post-claim restart accepted **0** times;
- after: a clean new process using the same participant secret restarted successfully and preserved the same vault
  file SHA and activation hash;
- first activation required two hidden secret prompts; restart required one;
- wrong secret, ciphertext tamper, role/path mismatch, missing/drifted crypto and an outcome-state race were rejected;
- all three frozen interruption states recovered without regenerating or weakening a capability;
- tested durable and browser surfaces contained **0 raw role-token occurrences** and **0 raw recovery-secret
  occurrences**;
- the restarted collector wrote one exact M57.4 coder revision and advanced to the next token-free sample;
- target-outcome access, model calls, real participants, formal evidence and M58 authority all remained **0**.

## Failures found before freeze

The implementation work retained and corrected six pre-freeze failures rather than hiding them:

1. the first implementation imported the M56.6 lock module, which does not own the required scoring lock; it now uses
   M56.9;
2. the first restarted HTTP test reused the M57.5 cookie-name parser, causing repeated 303 responses; M57.6 now reads
   its own cookie;
3. the rehearsal expected a nonexistent CSRF field in the M57.5 exchange result; surface scanning now uses the
   rendered body that actually contains it;
4. the first live-audit adapter assumed flat M57.5 count keys; it now reads the real nested `counts` structure;
5. a structurally malformed vault could reach key lookup during validation; validation now reports invalid state and
   the negative test preserves that behavior;
6. the first generic boolean contract check did not prove exact frozen sections; validation now compares exact
   contract objects.

Safari accessibility automation initially placed two form values in the wrong fields after accessibility indices
shifted. That invalid fill was not submitted. The fields were reset using a fresh screenshot and visual coordinates,
the exact three values were checked, and the form was submitted once. Safari reported 33 tabs before and 35 after;
there was no explicit new-tab action and the cause was not proven, so this milestone does not claim a stable tab
count. No tab was closed.

## Verification

- focused M57.6 after freeze: **14/14 passed** in 44.621 seconds;
- adjacent M56.10 + M57/M57.1/M57.2/M57.3/M57.4/M57.5/M57.6: **110/110 passed** in 225.008 seconds;
- selected M1/M2/M6/V7/V9/M54–M57.6 compatibility: **434/434 passed** in 300.78 seconds;
- the selected scope is the previous 420-test M57.5 set plus the 14 M57.6 tests, so the comparison is like-for-like;
- Python compilation, JSON parsing, frozen dependency hashes, saved rehearsal validation, screenshot format,
  dimensions and hashes, stopped local services and Git whitespace checks passed;
- the selected pytest run used the project's Python 3.12 test environment plus the already-present Codex-runtime
  site-packages so it could exercise both pytest and the exact frozen `cryptography==50.0.1` backend; no package was
  installed.

These are scoped engineering tests and one isolated Safari acceptance. They are not a complete-repository result,
real multi-person collection, security audit or support claim for other browsers or Python environments.

## Cost

Seven isolated encrypt→claim→restart→decrypt→cookie/CSRF→POST rehearsals all passed. Wall time was
**7.035195–7.267910 seconds**, median **7.119880 seconds**. Each run added exactly three M57.6 durable artifacts
totalling **3,649 bytes**; counting the M57.5 claim and scrubbed envelope, five affected artifacts totalled **4,956
bytes**.

This includes local validation, Scrypt/AES-GCM work, full-sync writes, two collector constructions and one loopback
form submission. It excludes human effort, 90 real entries, model execution, target outcomes, energy, TLS,
same-account adversarial testing and production throughput.

## Safari graphical and functional acceptance

The M57.6 dashboard visibly showed the six-stage path `TTY secret → Scrypt → AES-GCM vault → M57.5 claim → process
restart → M57.4 ledger`, the pre/post restart difference `0 → 1`, zero secret surfaces, one functional revision, V7
`0/18 + 0/18`, real component rows `0/30` and `FORMAL M57 DENIED`.

A first real local process was started with no secret in its command arguments, accepted two hidden prompts, created
the vault and activation, and was stopped. A second new process used the same command and one hidden prompt. Its vault
SHA and activation hash were identical to the first process. Safari then submitted one synthetic coder entry and
redirected from sample `forged-runner-no-human-01` to `forged-runner-no-human-02`. Disk inspection found one revision,
two source views, the exact visible form content, no role-token/recovery-secret field, zero outcome access and zero
model calls. Both local services were stopped. Evidence:

- `analysis/m57_6_safari_crash_recovery_acceptance_2026-09-05.json`;
- `analysis/m57_6_safari_crash_recovery_flow_2026-09-05.jpg`;
- `analysis/m57_6_safari_recovered_collector_2026-09-05.jpg`.

The current M57.6/M57.5 local test tab is safe to close, but no user tab was closed during acceptance.

## Contribution and remaining limits

M57.6 prevents an ordinary collector process crash from discarding the only capability for one independent coder or
adjudicator. That makes the future M57 human evidence workflow more usable while preserving its pre-outcome ordering,
role attribution, source provenance and original ledger. It advances the reliability of the falsification machinery;
it does not add predictive validity to the human-response equation itself.

The minimum 20-byte secret rule is only an input-length boundary, not proof of entropy. Python object memory cannot be
reliably zeroized. A malicious process under the same macOS account may read files or process memory. The exact
accepted crypto backend currently lives in a Codex-bundled interpreter, while the normal project interpreter cannot
run recovery. The M57.6 HTTP handler also mirrors the frozen M57.5 handler because M57.5 exposes only a claim-and-build
constructor; future parity maintenance is therefore a real engineering risk. There is no TLS or independent identity
proof.

Live V7 remains `0/18 + 0/18`, real temporal rows `0/30`, real component rows `0/30`, real recovery vaults `0`, formal
M56/M57 results `0` and M58 denied. M57.6 does not prove three physical humans, validate private emotion/intent,
validate Equation V1, show UruhaBrain beats a baseline, solve a human-response equation or establish production
security.

## Next necessary milestone

M57.7 should remove the hidden-interpreter operational dependency without changing M57.6 cryptography or evidence
semantics. The prospective single variable is an auditable, participant-facing runtime launcher that verifies a
project-owned locked environment and exact crypto artifact before accepting a secret, never downloads or installs at
collection time, and keeps secret/token material out of argv, logs and browser surfaces. It must prove that a fresh
participant launch and restart use the same attested runtime, fail closed on interpreter/dependency drift, preserve
M57.4–M57.6 hashes and formal denial, and provide a clear Safari/operator view. If a project-owned runtime cannot be
provided reproducibly without broad packaging changes, retain the exact Codex-runtime limitation rather than claiming
portability.
