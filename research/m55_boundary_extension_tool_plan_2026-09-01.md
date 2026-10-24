# M55 Two-Coder Boundary Extension Tool · 2026-09-01

## Single question

After V7 reliability passes and each human independently completes a frozen V9 event entry, can each
person separately mark the pre-cutoff input and later observable behavior without changing V9 or seeing
the other person's answer?

## One attributable change

Add one private companion ledger and local browser instrument for the four M55 temporal boundaries and
a newly written pre-cutoff-only input paraphrase. V7/V9 frozen artifacts, codebook, sampling slots,
thresholds, content, model, runtime, memory, and sealed future remain unchanged.

## Required separation

- each boundary ledger belongs to exactly one pseudonymous coder and binds that coder's own V9 entry by
  SHA-256;
- the other ledger is never loaded by the collection server;
- real initialization and serving remain fail-closed until the genuine V7 reliability lock exists;
- the V9 whole-event context paraphrase is not copied or prefilled as model input;
- cross-coder comparison is allowed only after both ledgers are complete and valid;
- comparison exposes hashes, counts, interval overlap, and cutoff differences, never either coder's
  paraphrase;
- disagreement is retained for explicit human adjudication; software cannot average timestamps or
  choose text automatically;
- synthetic fixtures test only the instrument and never count as a human result.

## Acceptance

1. Contract bindings, private-root ignore rule, and authorization boundaries validate.
2. Real ledger initialization and real server start fail while V7 reliability is absent.
3. Synthetic ledgers save independently and atomically; one server cannot address the other ledger.
4. Every saved entry is bound to the matching coder's current V9 entry digest.
5. Invalid ordering, whole-event-context reuse, raw/verbatim keys, mismatched coder/slot/source, stale
   V9 digest, and false attestations fail closed.
6. The comparison requires two complete, distinct ledgers and returns no text; exact and divergent
   synthetic cases are both preserved, with automatic merge and M56 authorization false.
7. A graphical demo shows two isolated lanes joining only after completion, then a disagreement lane
   and explicit adjudication gate.

## Claim boundary

Passing establishes collection-tool readiness only. Actual V7 and V9 human work, temporal-row
adjudication, M55 compilation, unseen-future generation, Equation V1 validity, and M56 comparison remain
future evidence.
