# M57.4 Independently Attributable Component-Evidence Collection and Quarantine Plan

Date: 2026-09-04

Status: prospective contract frozen before implementation and before any real component source view

Single changed variable: add the missing collection/quarantine path that turns three role-separated, pre-outcome human
ledgers into the exact frozen M57.2 evidence manifest. Do not change M56 samples, predictions, model, outcome, scoring,
M57 stage definitions, M57.2 manifest semantics, M57.3 result bridge or any statistical threshold.

## Why this is necessary

M57.2 validates a completed object, but it does not provide a way for two coders and a distinct adjudicator to create
that object independently. The only retained complete manifest is deliberately author-constructed. There are no
source-view receipts, private per-role ledgers, immutable seals, disagreement records or pre-outcome export barrier.
V7's existing 18-slot persona-source coder tool is useful precedent for human isolation, but it answers a different
question and does not satisfy the 30-row M57.2 component schema.

Without this milestone, a structurally valid manifest could hide who saw which source, whether coders worked
independently, when adjudication began, whether a record was revised after outcome access, or whether disagreements
were erased. That would make later component localization unauditable even if M57.3 were mechanically correct.

## Frozen workflow

1. Revalidate the existing M57.1 pre-outcome mode and confirm all M56 outcome-state artifacts are absent.
2. Initialize one immutable mode with exactly `coder_a`, `coder_b` and `adjudicator`, three distinct pseudonyms, real
   human attestations, random role tokens and exact upstream hashes. A clearly named internal synthetic initializer is
   allowed only for mechanics tests and can never export formal data.
3. Each coder receives only the current sample's permitted source and their own ledger. Opening a sample creates a
   server-timestamped source-view receipt. Saving appends a hashed revision containing one perception representation
   and one retrieval selection; no outcome, other coder record or private mental truth is present.
4. Each coder must cover all 30 samples and seal their own ledger. A seal binds the complete ledger hash. Nothing can
   be appended or edited after sealing.
5. The adjudicator cannot view coder records until both coder seals validate. For each sample, the adjudicator sees the
   two immutable contributions, records a resolution and basis, and supplies one source-bound observable state proxy.
   Perception and retrieval disagreement flags are computed from the coder payloads, not declared by the caller.
6. After 30 adjudications, the adjudicator ledger is sealed. Export occurs under the same per-run lock and again fails
   if any outcome-state artifact exists. It preserves raw ledgers privately and writes only the exact M57.2 manifest,
   using real formal data kind only for a real collection mode and engineering-only kind for a synthetic rehearsal.
7. Export does not run M57.2 predictions, read the outcome, write production memory or authorize M58.

## Acceptance tests frozen before implementation

- contract hashes and all five public signatures match the prospective specification;
- synthetic three-role rehearsal completes 60 coder entries, 30 adjudicator entries, 90 source views, 60 perception
  plus 60 retrieval contributions, 30 state proxies and 60 adjudications, then exports a manifest accepted only by the
  explicitly internal M57.2 engineering validator;
- public/real initialization rejects repeated pseudonyms, missing consent, model/synthetic participation attestations,
  unsafe run IDs and already-present outcome state;
- a role token cannot read or write another role, coders receive no cross-ledger context, and adjudication is denied
  before both coder seals;
- entry save without a source-view receipt, unknown or post-cutoff history ID, forbidden outcome key, private-state
  field, wrong source/sample and malformed payload all fail closed;
- partial ledgers cannot seal; sealed ledgers cannot mutate; changed ledger or seal hashes cannot export;
- any outcome-state artifact appearing before a view, save, seal or export blocks that operation;
- export cannot overwrite an existing manifest, cannot upgrade synthetic data to formal, and produces no model call,
  outcome access, production-memory write or external deployment;
- the page makes role isolation, 90-entry progress, disagreements, export boundary and the live 0-human status visible;
- focused, adjacent and selected regression suites pass after an implementation freeze hashes the new artifacts.

## Failure and decision rules

- If mutable-ledger crash safety fails, retain the failure and add an append-only journal in a new prospective version;
  do not silently weaken sealing.
- If the M57.2 validator rejects a mechanically exported synthetic manifest, fix only the collection-to-frozen-schema
  projection; do not change the frozen M57.2 validator or manifest contract.
- If identity independence cannot be established from real operator evidence, the collection remains structurally
  ready but non-authoritative. Never substitute Codex, an LLM, synthetic records or one person using three pseudonyms.
- If any outcome marker exists before export, preserve all private ledgers but deny export for that formal run; start a
  new preregistered run rather than backdating evidence.

## Cost scope

Measure local initialization, 90-entry synthetic save/seal/export wall time and durable artifact bytes across seven
isolated runs. These numbers cover Python validation, JSON hashing and full-sync writes only. They are not human labor,
model latency, energy, formal throughput or production-security measurements.

## Scientific boundary

Passing M57.4 would make future component evidence attributable and auditable at the application level. Random tokens,
pseudonyms and self-attestations still do not prove three physical humans against a malicious same-user operator;
external study oversight remains necessary. The milestone does not itself create human observations, infer private
states, validate Equation V1, show UruhaBrain beats a baseline, identify a causal component, solve the human-response
equation or authorize M58.
