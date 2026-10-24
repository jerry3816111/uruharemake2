# M56 Blinded Execution Capsule and Separate Scorer · 2026-09-01

## Why the preflight is not yet executable

The frozen M56 preflight proves that the source packet contains no current future outcome, but the packet
still carries the complete authorized pre-cutoff history. Passing that same object directly to every
condition would let B1 or B2 see information reserved for B3–B5/Ours. The preflight also validates a run
manifest but does not yet enforce a complete seven-condition prediction matrix, seal its probabilities,
or prevent a changed submission from reaching the scorer.

This unit closes that execution-control gap without reading Uruha target content or running a model.

## Single attributable change

Materialize a capability-separated execution capsule:

1. a generation-side capsule that contains condition-specific, cutoff-bound views but no outcome key;
2. a complete prediction submission with exact probability and resource contracts;
3. an immutable commitment receipt over the complete submission;
4. a separate scorer that can open the private outcome key only after the receipt verifies.

The already frozen M54–M56 contracts, M55 human thresholds, baselines, model, prompts, data slots, success
gates, and results remain unchanged. Formal model execution remains forbidden.

## Information isolation

- B0 receives only candidate labels and pre-cutoff behavior counts.
- B1 receives the current event, labels, and minimal target identity, with zero history and no persona
  summary.
- B2 adds only the frozen public persona summary.
- B3 adds a deterministic top-four pre-cutoff retrieval.
- B4 prediction receives a separately generated summary artifact rather than raw full history. Summary
  construction is its own costed task for each distinct nonempty history snapshot.
- B5 and Ours receive byte-identical source-information objects. B5 applies structured-history direct
  prediction; Ours must additionally supply a pre-outcome fit artifact and actual state/transition trace.
  B5 is forbidden from seeing those mechanism artifacts.

Every view has a digest. B5/Ours source hashes must match for every sample.

## Submission and commitment

The exact task order is packet sample order followed by that sample's pre-frozen rotated condition order.
The submission must contain every sample-condition pair exactly once. Each row must bind its view hash,
use every frozen behavior label exactly once, sum to one, select the deterministic argmax, reference only
authorized history IDs, and provide complete measured resource telemetry. B0 must use zero calls; B1–B5
use one prediction call per sample, while Ours uses one matched semantic call per sample; B4 summary cost
is recorded separately.

Only a complete valid submission can create a commitment receipt. Scoring rejects any later byte change,
missing row, duplicate, changed packet, stale view, visible outcome, retry, fallback, resource mismatch, or
missing Ours mechanism provenance.

## Separate scoring

The scorer independently validates the packet, capsule, split report, outcome-key hash, submission, and
commitment receipt before joining by sample ID. It reports all seven condition metrics and the fixed B5
versus Ours paired comparison. Proper scores use the primary observed behavior as the one-hot target;
acceptable alternatives apply only to ranking and accuracy diagnostics.

Brier and NLL use 20,000 paired bootstrap draws. At 30 rows, sign-flip p-values use a frozen deterministic
20,000-draw Monte Carlo estimate because exact enumeration has more than one billion assignments; for 20
or fewer engineering rows, exact enumeration is retained. The p-value is descriptive because the frozen
M56 success gate is the joint upper-CI rule plus the Top-1 noninferiority and integrity/resource gates.

## Current boundary and acceptance

Only synthetic no-content fixtures may exercise the whole capsule and scorer now. Tests must prove that:

1. each condition sees exactly its allowed information;
2. B5 and Ours share the same source-information hash;
3. future/outcome fields cannot enter any generation view;
4. incomplete, duplicate, reordered, non-normalized, stale-view, wrong-argmax, unauthorized-evidence,
   retry/fallback, resource, and Ours-provenance attacks fail closed;
5. a submission cannot be scored before commitment or after any mutation;
6. a wrong private key or split hash fails closed;
7. the scorer's metrics match independently checkable hand calculations;
8. synthetic results always remain nonformal even if every numerical success gate happens to pass;
9. the graphical page makes the two locked compartments and current human-data blocker understandable.

Passing this unit is execution/scoring engineering readiness only. It is not a formal M56 run, a model
comparison, Uruha evidence, human-response-equation validity, private psychology, or production readiness.
