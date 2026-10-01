# M57.8 Participant-Confirmed Ledger Completion Acceptance

Date: 2026-09-06

Decision: **BOUNDED ENGINEERING PASS**. Formal M57 science remains denied.

## What changed

M57.8 changes exactly one operational variable: `participant_confirmed_token_free_complete_ledger_seal`.

Before M57.8, M57.4 could seal an exact complete role ledger through its internal API, but the M57.5/M57.6
participant browser exposed only `POST /save`. A participant could reach 30/30 and still could not inspect the exact
draft ledger or independently finalize it without giving the coordinator participant authority.

The participant page now displays completed unique samples, missing count, source views, revisions and the exact
draft-ledger hash. A separate CSRF-protected confirmation appears only at 30/30. Saving the thirtieth row leaves the
ledger open: automatic seals remain **0**. An explicit checkbox and confirmation POST create a durable intent, the
unchanged M57.4 ledger/seal schema and a separate M57.8 receipt. After completion the page is read-only.

The transaction revalidates outcome absence, run/role capability, all 30 entries and source views, revision content,
draft hash and any existing intent/seal/receipt while holding the existing one-host single-writer lock. Incomplete,
tampered, stale-hash, wrong-role, outcome-present and nonidentical replay paths fail closed. An identical interrupted
or completed transaction resumes without creating a different seal.

## Observable before and after

| Participant capability | Before | M57.8 |
|---|---:|---:|
| token-free progress summary | absent | present |
| exact 30/30 draft hash visible | absent | present |
| automatic seal after last save | 0 | **0** |
| explicit participant confirmation | absent | present |
| crash-resumable confirmation intent | absent | present |
| M57.4 seal plus participant receipt | internal API only | **browser path** |
| raw role token / recovery secret in tested browser or M57.8 durable state | 0 | **0** |

Contract validation passed with 8 frozen bindings and contract hash
`31bd3791f84c7853dbe582f4734d9253ea82d2dfa3c3563624d964e07c65316e`.

## Test evidence after implementation freeze

- focused M57.8 suite: **11/11 passed** in **217.24 s**;
- adjacent M56.10 + M57–M57.8 suite: **139/139 passed** in **454.05 s**;
- selected M1/M2/M6/V7/V9/M54–M57.8 compatibility suite: **463/463 passed** in **543.64 s**;
- Python compilation, JSON parsing, contract validation, rehearsal validation, implementation-freeze hashes and JPEG
  format/hash checks: PASS;
- all tested local services on ports 7934–7937 were stopped after acceptance.

The adjacent and selected suites ran concurrently. Their wall times are reported as execution evidence only and are
not a benchmark or production-throughput comparison.

## Safari functional and graphical acceptance

The final isolated run `m578-safari-final-no-human` used the normal repository launcher. The M57.7 project-runtime
audit passed before two hidden secret prompts; the project runtime was Python 3.12.10 with cryptography 50.0.1, and
collection-time download/install/repair calls remained zero.

Safari showed 30/30 and draft hash
`bbc8b0e8bdd47581a2446f26797e8cb079cdc1a7e2e123f443caafb92b9d8df9`, then required an explicit checkbox and
button. The resulting exact artifacts were:

- final M57.4 ledger hash: `dd9359f787cc34272256e6caa17d15259dd1e175a75fcac3d5ccdf45c45da286`;
- unchanged M57.4 seal hash: `30454411e97b5b997d0f9ace139e9d7cdb01fedc7486af7f66addb11d38f346e`;
- M57.8 completion receipt hash: `2d52fab701eaf9ad2e54f2d19615ca51e85af243c8b2af5c9d8486b393eb2798`.

The final page displayed the seal and receipt and contained no save or confirmation form. The graphical dashboard
loaded the frozen rehearsal and visibly showed
`SAVE → 30/30 → HASH PREVIEW → CONFIRM → INTENT → SEAL`, automatic seals **0**, explicit receipts **0 → 1**,
token/secret surfaces **0** and real component evidence **0/30**.

Final acceptance reused one existing M57.8 Safari tab: **38 → 38**, opened 0, closed 0. Across the whole UI-debug
session the count changed 37 → 38 because one stale accessibility index created an Open Codex tab; its modal was
cancelled and no tab was closed. The remaining local test tab is safe to close, but M57.8 did not close it.

Graphical evidence:

- `analysis/m57_8_safari_participant_ready_to_seal_2026-09-06.jpg`
- `analysis/m57_8_safari_participant_sealed_2026-09-06.jpg`
- `analysis/m57_8_safari_participant_completion_flow_2026-09-06.jpg`

## Retained failures and corrections

1. The first completion card was below the long per-sample form, so the confirmation controls were outside the
   captured viewport. It was moved directly under the source header and reaccepted.
2. The first wrapper still displayed the inherited M57.5 title. The title and visible milestone label were corrected
   to M57.8 and reaccepted.
3. One stale Safari accessibility index selected a different action and created an Open Codex tab. The modal was
   cancelled; fresh indices were used afterward and no tab was closed.
4. The first dashboard build measured seal count after explicit confirmation and therefore read 1. It failed closed.
   The metric was corrected to use the frozen pre-confirmation observation, and the rebuilt rehearsal validates 0.

These failures are implementation findings. They are not deleted or relabeled as formal participant evidence.

## Measured local synthetic cost

Three isolated 30-entry fixtures produced explicit completion transactions of
**0.293659–0.306211 s**, median **0.295989 s**. Fixture setup plus 30 synthetic entries took
**18.724178–18.861495 s**. The M57.8 intent and receipt added **1,800 bytes** per fixture.

These measurements exclude human completion time, 90 real entries, identity verification, model generation, target
outcomes, energy, TLS and production throughput.

## Preserved evidence boundary and limitation

Authoritative live state is unchanged: V7 is **0/18 evaluators + 0/18 coders**, real temporal rows **0/30**, real
component rows **0/30**, real participant completion receipts **0**, model calls **0**, target-outcome accesses **0**,
formal M56 results **0**, formal M57 results **0**, and M58 authorization **false**.

M57.8 proves that one isolated synthetic participant can use the attested token-free local Safari path to review an
exact complete ledger, explicitly authorize its finalization and obtain a crash-recoverable receipt. It does not prove
participant identity, label correctness, predictive value, Equation V1, LLM advantage, a solved human-response
equation, cross-platform or adversarial security, production readiness or external deployment.

One maintenance risk remains explicit: the M57.8 transaction constructs the exact frozen M57.4 seal schema inside the
already-held non-reentrant lock instead of calling the public M57.4 seal function. Hash bindings and parity tests cover
the frozen version, but any future M57.4 schema change requires an explicit M57.8 parity update.

## Next necessary unit

M57.9 should change only `adjudicator_confirmed_token_free_preoutcome_manifest_export`. M57.8 lets the adjudicator
complete and seal 30/30 in the browser, but the exact M57.2 pre-outcome manifest export still requires the internal
M57.4 API and raw adjudicator capability. The next prospective unit should expose a separate post-seal,
CSRF-protected adjudicator confirmation that exports the unchanged M57.4/M57.2 manifest under the same attested,
token-free, crash-safe boundary. It must preserve outcome absence and all formal-denial gates; synthetic export remains
engineering evidence only.
