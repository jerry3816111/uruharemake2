# M57.5 Separate Participant-Capability Issuance and Token-Surface Hardening — Acceptance

Date: 2026-09-05

Decision: **PASS as a bounded participant-launch engineering milestone; real participants/evidence remain 0 and formal M57/M58 remain denied**

Single changed variable: add a wrapper that separates the three M57.4 role capabilities and keeps the raw M57.4
bearer token out of coordinator-facing results, command arguments, browser URLs/history, HTML/forms and browser
cookies. The frozen M57.4 sources, ledgers, seals, adjudication, manifest projection and scientific meaning were not
changed.

## Problem and why this milestone is necessary

M57.4 stored only token hashes in durable run state, but its initializer returned all three raw role tokens to one
caller. Its direct demonstration collector also accepted a raw token through `--token`, a query string and a hidden
form field, then repeated it in redirect URLs. That was a valid mechanics harness, but not an acceptable handoff
surface for three separate study roles: one coordinator could accidentally retain every capability, and process lists,
browser history or page source could preserve bearer material.

M57.5 wraps the unchanged M57.4 operations. It does not claim that software can prove three human identities; it
reduces accidental capability co-location and browser exposure before a real operator recruits those humans.

## What was implemented

Before the unchanged M57.4 initializer is called, M57.5 full-syncs an immutable intent bound to the run, roster,
delivery root and frozen M57.4 implementation. An incomplete intent is terminal: the wrapper will not guess or
regenerate once-only M57.4 tokens for the same run.

The wrapper writes one capability envelope per role into three `0700` directories; each envelope is `0600`. The
central commitment and public receipt contain only role/pseudonym metadata, token hashes, envelope hashes and paths.
No raw role token is returned. A completed identical call performs validation-only replay.

Starting a role collector requires the run ID, role, envelope path and port—not the token. Under the existing per-run
lock, the server rechecks outcome absence, validates the exact envelope, writes a one-time claim receipt, replaces the
secret-bearing envelope with a spent record and retains the role token only in process memory. A second claim and a
restart after claim fail closed.

Safari uses an independent random host-only session cookie with `HttpOnly; SameSite=Strict` plus a separate random
CSRF token. The M57.4 role token is not the cookie or CSRF value and never appears in URLs, HTML or forms. Plain
loopback HTTP deliberately does not claim the cookie `Secure` flag or network TLS. Valid form writes still call the
unchanged M57.4 source-view and save functions.

## Isolated rehearsal and measurable change

One complete synthetic rehearsal demonstrated:

- before: one coordinator result exposed three raw tokens; token-bearing argv, URL and form paths existed;
- after: three separate private envelopes, zero raw tokens in public receipt, one one-time claim and a scrubbed
  envelope;
- first browser request returned a 303 cookie handshake; the valid CSRF-checked POST returned a token-free 303 next
  sample location;
- zero occurrences of the M57.4 role token across tested URL, redirect, response HTML, cookie and CSRF surfaces;
- one exact coder revision and one source view persisted through the unchanged M57.4 ledger;
- zero target-outcome access, zero model calls, no formal evidence and no M58 authority.

No fake real roster was used. All automated and Safari participants remained explicitly synthetic.

## Failure analysis and retained limitations

The first complete rehearsal reached the expected browser save but failed while measuring artifact paths: macOS
resolved the temporary root from `/var/...` to `/private/var/...`, so `relative_to` rejected two equivalent spellings.
The result was not saved. The path accounting now resolves both sides before comparison; no evidence or security rule
was relaxed.

Implementation review then found that the rehearsal used a duplicate already-claimed test server. That could let the
test diverge from production. The duplicate was removed before freeze; the saved rehearsal and tests now exercise the
same `_make_secure_collection_server` used by the public server.

Safari's first state capture occurred during the 303 navigation and temporarily showed the old dashboard tree beside
the new token-free address. A fresh state read showed the actual M57.5 page. Form fields were edited one at a time with
fresh accessibility indices, avoiding the stale-index error observed in M57.4.

M57.5 intentionally cannot restart a role server after the one-time claim: the raw token has been scrubbed and is only
in the stopped process memory. That is fail-closed but operationally costly for a 30-row human session. Persisting the
token in plaintext would undo the exposure reduction, so restart recovery is not silently added after freeze.

## Verification

- focused M57.5: **11/11 passed** in 20.71 seconds;
- adjacent M56.10 + M57/M57.1/M57.2/M57.3/M57.4/M57.5: **96/96 passed** in 188.60 seconds;
- selected M1/M2/M6/V7/V9/M54–M57.5 compatibility: **420/420 passed** in 273.55 seconds;
- Python compilation, JSON parsing, frozen dependency hashes, saved rehearsal validation, JPEG format/hash/dimensions,
  stopped local services, freeze hashes and Git whitespace checks passed;
- malformed/repeated roster behavior remains frozen in M57.4; M57.5 tests add path/symlink, intent-only crash,
  role/path/hash mismatch, tamper, second claim, outcome race, cookie, CSRF and raw-token-form rejection;
- no M57.4 frozen file or historical scorer, model, sample, answer, score, statistic, threshold or result was edited.

These are selected tests and synthetic launch mechanics. They do not prove a complete repository, a real multi-person
collection, browser support beyond the tested Safari path or production security.

## Cost

Seven isolated issuance→claim→cookie handshake→one coder POST runs measured median **4.601486 seconds**, range
**4.586087–4.638623 seconds**. Six M57.5 durable artifacts totaled exactly **5,587 bytes** per run. All rehearsals
passed; no raw token surfaced, no formal evidence was created and M58 remained denied.

The measurement covers local Python validation, three private envelope writes, one claim/scrub, one loopback browser
round trip, hashing and full-sync barriers. It excludes human labor, 90-entry completion, model execution, target
outcome access, energy, TLS and adversarial same-user security.

## Safari graphical and functional acceptance

Safari reused the existing M57.4 test tab and loaded `http://127.0.0.1:7928/dashboard`. The page visibly contrasted
the old all-token/URL path with three envelopes, one-time claim, local cookie+CSRF and the unchanged M57.4 ledger. It
retained `REAL PARTICIPANT CAPABILITIES 0`, `FORMAL M57 DENIED`, V7 `0/18 + 0/18`, real rows `0/30`, token-surface
hits `0`, outcome/model `0/0` and M58 denied.

The functional isolated run entered `http://127.0.0.1:7929/` and settled at a URL containing only
`sample=forged-runner-no-human-01`. Coder A saw the permitted source and its own fields, but no other coder or target
outcome. After one corrected synthetic submission, Safari redirected to the second token-free sample. The spent
envelope and claim receipt contained no role token; the ledger held exactly one revision and two source views, with
the exact visible form values and zero outcome/model access. Safari stayed **35 → 35** tabs, with no tab created or
closed. Both local servers were stopped; the M57.5 test tab is safe to close. Evidence:

- `analysis/m57_5_safari_participant_capability_acceptance_2026-09-04.json`;
- `analysis/m57_5_safari_capability_flow_2026-09-04.jpg`;
- `analysis/m57_5_safari_secure_collector_2026-09-04.jpg`.

## Contribution to the human-response-equation goal

M57.5 makes the already-built falsification workflow safer to hand to different human roles. It reduces the chance
that one coordinator or browser artifact accidentally collapses the independent-coder boundary that a future M57
causal localization depends on. This improves experimental operability and provenance, not the equation's predictive
validity.

It still does **not** prove three physical humans, protect against a malicious process under the same macOS account,
provide TLS, create component labels, validate private emotion/intent, identify a Uruha component, validate Equation
V1, show UruhaBrain beats a baseline or solve a human-response equation. Live V7 remains `0/18 + 0/18`, real temporal
rows `0/30`, real M57 component rows `0/30`, formal M56/M57 results `0` and M58 denied.

## Next necessary milestone

M57.6 should address crash-recoverable participant-owned sessions without reintroducing plaintext tokens. Before any
implementation, it must prove the current post-claim restart failure, audit whether an existing authenticated-encryption
dependency is available, and prospectively freeze a design in which a participant-supplied recovery secret enters via
an interactive non-argv channel, is never persisted, and encrypts the active role capability. Restart must require the
same participant secret, preserve claim/ledger/outcome boundaries and add no browser token surface. If no suitable
audited primitive is available, retain M57.5's terminal failure instead of inventing cryptography. This still cannot
replace external identity oversight or authorize M58.
