# M57.8 Participant-Confirmed Ledger Completion — Prospective Plan

Date: 2026-09-05

Status: prospective freeze before implementation and before any real participant collection

## Problem proof

M57.4 already refuses to seal an incomplete role ledger and creates an exact hash-bound seal. M57.5 and M57.6 make
the browser token-free and recoverable, while M57.7 supplies an attested project runtime. However, their browser server
only exposes `POST /save`. Even after 30 unique entries, the participant cannot see a completion summary, explicitly
confirm that this is the ledger they intend to finalize, or seal it without an internal API and raw role token.

This is not merely cosmetic: two participant seals are the gate that releases adjudication, and the adjudicator seal
is the gate for pre-outcome manifest export. Letting a coordinator act on behalf of the participants would weaken the
role boundary established in M57.4–M57.7.

## Single changed variable

Add one `participant_confirmed_token_free_complete_ledger_seal` path. Do not change M57.4 evidence fields, validation,
source visibility or final seal schema; M57.5 issuance/session, M57.6 recovery/crypto and M57.7 runtime attestation also
remain frozen. Do not add model generation, outcome access, scoring, formal authorization or external deployment.

## Frozen behavior

1. The participant page shows completed unique samples, source-view count, revision count, missing count and current
   ledger hash. It never shows another private coder ledger, a role token or recovery secret.
2. Before 30/30, no active seal form is rendered and `POST /seal` fails closed. Saving the thirtieth entry does not
   automatically seal; the participant must make a separate explicit confirmation.
3. At exactly 30/30, the page renders a CSRF-protected checkbox and confirmation button. The form submits only CSRF,
   the exact displayed draft ledger hash and the frozen confirmation phrase.
4. Seal execution revalidates run, role, authorization, outcome absence, all 30 unique source views/entries, order,
   every revision and the expected draft hash while holding the existing M56 single-writer lock.
5. A `0600` intent is durably written before mutating the ledger. The unchanged M57.4 ledger/seal schema is then
   produced, followed by a `0600` M57.8 completion receipt binding the intent, final ledger and M57.4 seal hashes.
6. A crash after intent or after the M57.4 seal can resume only when the submitted confirmation and all hashes are
   identical. A different replay, ledger mutation, role/path mismatch, outcome appearance or invalid existing seal
   fails closed. A completed identical replay only revalidates existing artifacts.
7. After sealing, the browser shows a final read-only receipt and no save/seal form. The raw token and recovery secret
   remain absent from argv, URL, form, HTML, cookie, receipt and durable M57.8 state.
8. A separate M57.8 launch command must reuse the full M57.7 project-runtime audit before executing the M57.8 server;
   it cannot download, install or repair during collection.

## Verification

- Prechange probe preserves the exact missing browser action.
- Contract and dependency hashes bind M57.4–M57.7 before implementation.
- Incomplete 0/30 and 29/30 ledgers cannot render an active confirmation or seal through direct/API/browser calls.
- A complete 30/30 synthetic ledger remains open after the last save, displays its draft hash, then seals only after
  an explicit valid cookie + CSRF + confirmation POST.
- Wrong CSRF, missing checkbox, unexpected token/secret field, stale draft hash, wrong role, mutated ledger, outcome
  presence and invalid/nonidentical recovery artifacts reject.
- Identical post-crash/post-completion replay validates the same M57.4 seal and M57.8 receipt without a second seal.
- Both coder roles must seal before the unchanged adjudicator path becomes accessible; an adjudicator can likewise
  complete and explicitly seal without an internal token surface.
- M57.7 runtime audit precedes launch; public args remain run/role/envelope/port and collection installs remain zero.
- Run focused, adjacent M56.10 + M57–M57.8 and selected M1/M2/M6/V7/V9/M54–M57.8 compatibility suites.
- Perform an isolated Safari 30/30 completion display and explicit seal. Preserve tab count, stop services and retain
  screenshots plus exact disk evidence. Synthetic data must stay under ignored local roots.

## Stop and claim boundary

M57.8 passes only if a participant can independently inspect, explicitly confirm and seal an exact complete ledger in
the token-free recoverable browser, with stale/mutated/incomplete state rejected under the single-writer boundary.
Synthetic acceptance proves workflow mechanics only. It does not prove participant identity, label correctness,
predictive value, Equation V1, LLM superiority, a solved human-response equation, production security or M58 authority.
