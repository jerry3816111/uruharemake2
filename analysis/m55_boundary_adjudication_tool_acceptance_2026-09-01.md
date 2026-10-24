# M55 Explicit Boundary Adjudication + Record Assembly Acceptance · 2026-09-01

## Decision

**Adjudication-tool engineering gate: PASS. Human evidence gate: BLOCKED. M55: INCOMPLETE. M56: NOT AUTHORIZED.**

This checkpoint closes the software gap between two independent completed observations and one
contract-valid private temporal record. It does not create either person's labels and never treats
agreement, a synthetic fixture, or a software merge as human adjudication.

## Why this step was necessary

The preceding M55 boundary tool deliberately stopped at a text-free comparison. That protected
independence, but it also meant there was no legitimate way to turn two answers into the single record
required by the temporal compiler. Automatically averaging four times, selecting the majority label,
or merging two paraphrases would silently create a third answer that no human made.

The new tool therefore permits exactly three explicit decisions per paired slot:

1. accept coder A's complete observable record;
2. accept coder B's complete observable record;
3. manually resolve the event, X/cutoff/Y boundaries, public-observation labels, and paraphrases.

Even byte-identical pairs initialize with zero adjudicated entries and require a human submit.

## Implemented mechanism

- SHA-bound contract with seven frozen dependencies and seventeen adjudication-entry fields;
- canonical lexicographic coder A/B order so caller order cannot change provenance;
- a gitignored, atomically written private adjudication ledger;
- ledger-level hashes for both V9 ledgers and both boundary ledgers;
- per-row hashes for both V9 entries and both boundary entries;
- fail-closed validation of complete, distinct, same-kind source pairs;
- real V9 completeness and real init/serve gated by the genuine V7 reliability lock;
- accept-A/B records reconstructed entirely from the chosen coder, with no cross-coder fields;
- manual records checked against the frozen 22-field temporal-row contract;
- explicit rejection of automatic-average or text-merge request fields;
- reason, confidence, independent-review, no-auto-merge, and no-quote attestations;
- source hashes revalidated on every page load and before every save or export;
- HTTP 409 stop if a V9 or boundary source changes after the adjudication server starts;
- synthetic exports forced to `synthetic_engineering_only` and zero human coders;
- complete exports revalidated by `validate_record_pack_m55`;
- no model calls, sealed-future access, production-memory writes, M55 completion, or M56 authorization.

## Acceptance evidence

### Focused and compatibility tests

- focused adjudication suite: **9/9 passed**;
- M54 + V7 + V9 + all M55 suites: **69/69 passed**;
- Python compilation: PASS;
- contract validation: PASS;
- `git diff --check`: PASS before and after documentation freeze;
- contract hash: `9cb11cca6d75f85f488fbbbcd86054d0ecbe744f1cf5a9754c5c03112b1d3682`;
- synthetic record pack validated against the frozen temporal contract: PASS;
- model calls: 0;
- production-memory writes: 0;
- target-person content read or created: 0.

The tests cover zero-entry initialization, exact-pair non-acceptance, accept-A, accept-B, valid and
invalid manual resolution, bad chronology, missing reason and attestations, forbidden automatic merge,
incomplete or same-coder pairs, synthetic/real confusion, stale V9 and boundary hashes, token gating,
HTTP 409 fail-closed behavior, and synthetic zero-human export.

### Current real-data readiness

- pre-content readiness: true;
- V7 private ledgers: **0/18 and 0/18**;
- V9 independently reviewed Uruha events: **0/30**;
- real cutoff-to-future temporal rows: **0/30**;
- M55 complete: false;
- M56 authorized: false;
- blocker: `complete_two_independent_v7_18_slot_ledgers`;
- unchanged readiness hash: `137489976bd2b49cdf721849fed2444b90ab1640cbcc40eb39805c748f5927eb`.

### Safari graphical acceptance

Safari reused the existing M55 tab and remained at 28 tabs; no tab was opened or closed and no form
was submitted. Two local synthetic views were inspected:

1. The outsider graph showed the full M54 → V7 → V9 → X/cutoff/Y → adjudication → M55 → M56 chain,
   with M54 and the adjudication engineering tool marked PASS, real counts at zero, and M56 forbidden.
2. The private adjudication page showed retained Coder A/B context, relationship, behavior label,
   X/cutoff/Y times and paraphrases, the three explicit decision paths, manual fields, three required
   attestations, progress 0/2, and the final evidence-boundary statement.

Both pages fit the Safari viewport without horizontal overflow. The private page was also checked at
the bottom, where the submit control and M55/M56 non-authorization statement remained visible.

## Contribution to the candidate human-response equation

M54 defines what Equation V1 must consume and predict; the temporal contract defines a prospective
X/cutoff/Y row; the boundary tool lets two people independently measure it. This adjudication tool now
preserves their disagreement and makes one human-accountable final measurement possible. It improves
measurement provenance and prevents hidden software decisions from becoming equation ground truth.

It does not show that the proposed variables predict Uruha, correspond to private mental states, or
beat an LLM baseline. Those claims still require two real humans, 30 adjudicated real rows, a separately
frozen M56 protocol, fresh unseen-future generation, and later ablation/transfer/replication evidence.

## Exact continuation

1. Two distinct consenting humans independently complete the unchanged V7 18-slot pilot.
2. Run the frozen reliability analyzer; retain failure if temporal IoU or nominal alpha misses its gate.
3. Only after a genuine V7 pass, initialize both V9 and boundary collection sites.
4. After both people complete all 30 target slots, initialize this adjudication site.
5. Require one explicit human decision for every paired selected event and retain all disagreements.
6. Export and compile exactly 30 valid cutoff-to-future rows; keep M56 forbidden until its own protocol
   is frozen before model generation.

## Claim boundary

This is deterministic data-instrument, private-record assembly, and graphical UI evidence only. It is
not human reliability, real-person data, fresh model generation, full-pipeline readiness, production
authorization, persona equivalence, human understanding, or a solved human-brain equation.
