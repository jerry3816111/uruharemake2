# M57.9 Adjudicator-Confirmed Token-Free Manifest Export — Prospective Plan

Date: 2026-09-06

Status: prospective freeze before implementation and before any real participant collection or export

## Problem proof

M57.4 already builds and validates the exact frozen M57.2 component-evidence manifest from three complete sealed role
ledgers. M57.8 lets every participant, including the adjudicator, inspect 30/30 and explicitly seal in the token-free
browser. However, M57.8 exposes only `POST /save` and `POST /seal`; after the adjudicator seals, the page is read-only.
The remaining M57.4 export API accepts a raw adjudicator session token, so an engineer must regain participant
authority to finish the workflow.

## Single changed variable

Add one `adjudicator_confirmed_token_free_preoutcome_manifest_export` path. Do not change the M57.2 manifest, M57.4
ledger/seal/export schemas, M57.5 capability/session, M57.6 recovery/crypto, M57.7 runtime or M57.8 seal transaction.
Do not add model generation, outcome access, scoring, formal authorization or external deployment.

## Frozen behavior

1. Only the adjudicator can see an export panel, and only after all three M57.4 ledgers and seals plus the adjudicator's
   M57.8 completion receipt validate. Coder pages never expose export controls or another private ledger.
2. The panel previews the exact deterministic M57.2 manifest hash, 30 samples, 60 coder entries, 30 adjudicator entries,
   90 source views, all three seal hashes and the current data-kind boundary. It does not display raw private ledgers,
   role tokens or recovery secrets.
3. Export is never automatic after seal. A separate CSRF-protected checkbox submits only CSRF, the displayed manifest
   hash and the frozen confirmation value.
4. The transaction first acquires the existing one-host single-writer lock, revalidates outcome absence, adjudicator
   authority, all three ledgers/seals, M57.8 receipt and exact preview hash, and full-sync writes a `0600` M57.9 intent.
5. After releasing that non-reentrant lock, it delegates the unchanged public M57.4 export, which reacquires the lock
   and repeats its own complete pre-outcome validation. A final locked phase revalidates the exact manifest/export and
   writes a `0600` M57.9 receipt binding the intent, preview, three seals, M57.2 manifest and M57.4 export commitment.
6. A crash after intent or after M57.4 export resumes only for identical state. Preexisting export without M57.9 intent,
   stale preview, mutated ledger/seal/export, outcome appearance or nonidentical replay fails closed. A completed
   identical replay only revalidates existing artifacts.
7. After a completed export, the page shows the exact manifest, M57.4 export commitment and M57.9 receipt hashes and
   renders no export form. Raw token and recovery secret remain absent from argv, URL, form, HTML, cookie, receipt and
   durable M57.9 state.
8. Launch reuses the complete M57.7 project-runtime audit and M57.8 recovery/seal path before accepting a secret. No
   download, install or repair is allowed during collection/export.

## Verification

- Preserve the exact prechange gap probe.
- Contract and dependency hashes bind M57.2, M57.4 and the complete M57.8 freeze before implementation.
- Coder, incomplete adjudicator, unsealed adjudicator and adjudicator without a valid M57.8 receipt cannot preview or
  export. Finishing or sealing never automatically exports.
- A fully sealed synthetic three-role fixture shows the exact preview, then exports only after valid cookie + CSRF +
  explicit confirmation. The resulting manifest and export commitment must pass unchanged M57.2/M57.4 validation.
- Wrong CSRF, missing checkbox, token/secret form field, stale preview, preexisting unattributed export, outcome state,
  mutation and nonidentical recovery artifacts reject.
- Intent-only and export-without-receipt crashes resume with the same hashes and no duplicate manifest.
- Runtime audit precedes hidden input; public args remain run/role/envelope/port and collection-time installs remain 0.
- Run focused, adjacent M56.10 + M57–M57.9 and selected M1/M2/M6/V7/V9/M54–M57.9 suites.
- Perform isolated Safari adjudicator 30/30 sealed → explicit export and graphical acceptance without closing tabs;
  stop all services and retain exact disk evidence.

## Stop and claim boundary

M57.9 passes only if the adjudicator can independently preview and explicitly authorize the exact pre-outcome manifest
through the recoverable token-free browser, with crash-identical recovery and all stale/outcome states rejected.
Synthetic acceptance proves workflow mechanics only. It does not prove participant identity, label correctness,
predictive value, Equation V1, LLM superiority, a solved human-response equation, production security or M58 authority.
