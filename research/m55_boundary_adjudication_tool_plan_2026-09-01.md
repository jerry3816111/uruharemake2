# M55 Explicit Boundary Adjudication + Record Assembly · 2026-09-01

## Single question

After two people independently finish the same V9 slots and their M55 prediction boundaries, can a
human explicitly resolve every pair into one private temporal record without software silently
averaging timestamps, selecting a label, merging text, or discarding the original disagreement?

## One attributable change

Add a separate adjudication ledger and local browser instrument. Each submit explicitly accepts coder
A, accepts coder B, or provides a manual resolution. The output record is then checked by the already
frozen M55 temporal-row contract. V7, V9, boundary collection, codebook, sampling frame, thresholds,
Equation V1, runtime, memory, model, prompt, and sealed future remain unchanged.

## Required behavior

- both V9 and both boundary ledgers must already be complete, valid, distinct, and the same data kind;
- no entry is created during initialization, even if the two coders are exactly identical;
- every entry preserves both source V9 and boundary-entry digests;
- accept-A and accept-B copy exactly the chosen complete observable record after a human submit;
- manual resolution must supply valid times, public-observation labels, bounded paraphrases, reason,
  confidence, and three attestations;
- stale source or boundary hashes stop the browser and export;
- synthetic export is forcibly `synthetic_engineering_only`, coder count zero, and cannot impersonate
  human review;
- real init/serve remains gated by the genuine V7 reliability lock;
- a complete export must pass `validate_record_pack_m55`, yet still leaves M56 unauthorized;
- source ledgers and adjudication records stay in separate gitignored private paths.

## Acceptance

1. Contract bindings and private-root ignore rule validate.
2. Real init/serve fail before V7 reliability.
3. Incomplete, same-coder, different-kind, stale, or mismatched source pairs fail closed.
4. Initialization creates zero adjudicated entries; exact pairs do not auto-pass.
5. Explicit accept-A and accept-B preserve the chosen full record exactly.
6. Manual resolution passes only with valid chronology, codebook values, reason, confidence, and
   attestations; disguised auto-average or forbidden raw/private keys fail.
7. Complete synthetic export passes the frozen temporal record-pack validator, reports zero human
   coders, performs zero model calls, and leaves M55/M56 false.
8. Token-gated browser QA shows both retained inputs and one explicit decision lane; outsider demo
   shows no private text and labels itself synthetic.

## Claim boundary

Passing proves only adjudication-tool and record-assembly readiness. It is not real inter-coder
agreement, target-person data, Equation V1 validity, unseen-future prediction, or model advantage.
