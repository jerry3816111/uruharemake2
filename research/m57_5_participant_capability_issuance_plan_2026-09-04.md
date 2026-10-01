# M57.5 Separate Participant-Capability Issuance and Token-Surface Hardening Plan

Date: 2026-09-04

Status: prospective contract frozen before implementation and before any real capability issuance

Single changed variable: add a wrapper that separates delivery of the three M57.4 role capabilities and keeps the raw
M57.4 bearer token out of coordinator results, process arguments, browser URLs/history, HTML/forms and cookies. Do not
change the frozen M57.4 source, ledger, seal, adjudication or manifest semantics.

## Why this is necessary

M57.4 correctly stores only token hashes in its committed mode, but initialization returns all three raw tokens to one
caller. Its demonstration collector also accepts a token in the command line, query string and hidden form field, and
returns it in the next-page URL. Those choices were sufficient to exercise the frozen mechanics, but they create a
single coordinator capability and leave bearer material in process listings, browser history and page source.

M57.5 is not a new scientific variable. It is the smallest launch-surface dependency needed before asking separate
people to use M57.4. The old route remains frozen evidence of M57.4 mechanics; formal operators must use the new wrapper.

## Frozen workflow

1. Validate the M57.5 contract, run identifier, participant roster and a new absolute delivery path. Before calling
   M57.4, full-sync an issuance intent bound to the roster, path and exact M57.4 freeze. An intent without a complete
   commitment is terminal because M57.4 tokens are returned only once.
2. Call the unchanged M57.4 initializer internally. Write one secret-bearing envelope into each role's separate
   `0700` directory as a `0600` file. Full-sync the files/directories, then write a central commitment containing only
   pseudonyms, role-token hashes, envelope hashes and paths. The public result returns no raw token.
3. A role launches the M57.5 collector with run ID, role, envelope path and port. No token appears in argv. Under the
   existing per-run lock, validate the envelope against the commitment, recheck outcome absence, create an exclusive
   one-time claim receipt, remove the raw token from the envelope and retain it only in the server process memory.
4. The browser starts at `/`. The server establishes a random host-only `HttpOnly; SameSite=Strict` session cookie and
   redirects to a token-free sample URL. A separate random CSRF token is allowed in the form; the M57.4 role token is
   never rendered or stored in the browser. All writes still call unchanged M57.4 source-view/save functions.
5. A complete existing issuance may be revalidated without exposing tokens. Partial issuance, an intent without a
   commitment, a second claim, wrong role/path/hash, missing cookie/CSRF or any outcome-state marker fails closed.

## Acceptance tests frozen before implementation

- all frozen dependency hashes and three public signatures match the prospective contract;
- real/public initialization returns no raw role tokens, creates exactly three distinct envelopes with `0700/0600`
  modes and commits only hashes/metadata; a new non-symlink delivery root is required;
- complete identical replay is validation-only, while intent-only or partial issuance is terminal and never regenerates
  a token or overwrites an envelope;
- role/run/path/hash mismatch and a second claim fail; a successful claim writes one receipt, scrubs the raw token from
  the envelope and never returns it through a public response;
- command help has no token argument; the first browser response uses a host-only `HttpOnly; SameSite=Strict` session
  cookie, all URLs/locations/forms omit the role token, and no role token is used as the cookie or CSRF value;
- missing/wrong cookie and missing/wrong CSRF fail; a valid synthetic POST persists the exact M57.4 coder entry and
  redirects to the next token-free sample URL;
- coder/adjudicator gating, source-view requirements, post-cutoff rejection, outcome race denial and formal/synthetic
  boundaries remain those of frozen M57.4;
- focused, adjacent and selected regression suites pass; cost and Safari acceptance remain explicitly synthetic.

## Failure and decision rules

- If a crash occurs after intent but before the completed issuance commitment, retain the terminal state and require a
  new run ID. Do not regenerate capabilities for the same run.
- If a server dies after the one-time claim receipt, the role capability is intentionally unrecoverable in M57.5.
  Preserve completed ledger evidence and treat the run as operationally failed; a later recovery design must be a new
  prospective milestone, not a silent token backup.
- If browser compatibility requires putting the M57.4 token in a URL, form, local storage or ordinary cookie, fail the
  milestone rather than weaken the contract.
- If three physical identities cannot be externally audited, label the workflow structurally ready but non-authoritative.
  Never substitute one person, Codex, an LLM or synthetic entries for independent participants.

## Cost scope

Measure local issuance, claim, first cookie handshake and one source-view/save round trip across seven isolated
synthetic runs. Report durable bytes separately. These numbers exclude human labor, a 90-entry study, model calls,
target-outcome access, network TLS, energy and production deployment.

## Scientific and security boundary

M57.5 can reduce accidental bearer exposure and make role handoff less ambiguous. It does not protect secrets from a
malicious process or coordinator running as the same macOS user, prove physical identity, encrypt loopback HTTP, create
human labels, validate a component, validate Equation V1, prove UruhaBrain superiority, solve the human-response
equation or authorize M58.
