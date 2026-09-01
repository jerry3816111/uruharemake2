# M56.1 Pre-Outcome Equation Artifact Materialization · 2026-09-01

## Problem

The frozen M56 execution capsule requires the Ours condition to cite a fit artifact, a state snapshot,
and a transition trace.  Its engineering fixture currently proves only that three 64-character fields
exist.  Arbitrary placeholder hashes do not prove that an Equation V1 mechanism was actually
materialized before the target behavior became visible.

## Single attributable change

Add an outcome-blind overlay that turns the exact source-information object shared by B5 and Ours into
three content-addressed artifacts and binds them to the Ours generation request, submission commitment,
and separate scorer.  Do not modify the frozen M54, M55, or M56 files.

## Artifact semantics

1. **Fit artifact**: fit only an observable, Laplace-smoothed behavior prior and sparse observable
   behavior-to-behavior transition counts from history records whose `available_at` is no later than the
   current cutoff.  This is a small-data public-behavior parameter estimate, not a fit of private mental
   state.
2. **State snapshot**: materialize all nine frozen Equation V1 variables in their exact order.  Current
   input, history, observable context, structured behavior memory, and the declared person parameter are
   represented by typed values or digests.  Transient state, relationship, and goal/need remain
   `unavailable_not_inferred` when the M56 source object does not contain valid evidence.
3. **Transition trace**: compare consecutive pre-cutoff snapshots for the same target.  Record newly
   available history, behavior-count deltas, fit-size changes, and variable status/digest changes.  Never
   infer an unobserved psychological transition.

No artifact stores the current event paraphrase or history summary verbatim.  No current target outcome,
answer key, private-state truth, model output, or post-cutoff evidence may enter the bundle.

## Binding and commitment

- B5 and Ours source hashes must remain byte-identical.
- An Ours request replaces the capsule's required-artifact placeholders with the validated artifact
  payload for that sample; a B5 request can never receive it.
- A bound submission must cite the exact three content hashes.
- A new wrapper receipt binds both the frozen M56 submission receipt and the full artifact-bundle hash.
- The wrapper scorer must revalidate the bundle and wrapper receipt before delegating to the frozen
  separate scorer.

## Acceptance

- deterministic rebuilds produce identical fit/state/transition/bundle hashes;
- first sample with no history retains an empty fit and unknown private-state variables;
- a later sample uses only earlier history available before cutoff and shows an explicit transition;
- tampered content, stale hashes, placeholder hashes, post-cutoff history, forbidden outcome fields,
  non-monotonic history, B5 artifact injection, or submission/bundle mismatch fails closed;
- artifact materialization adds zero model calls, zero target-outcome access, and zero production-memory
  writes;
- the graphical page shows `same source -> fit -> state -> transition -> Ours request -> commitment`
  and the current human-data blocker in language understandable to a non-specialist;
- focused, selected compatibility, compile, and diff checks pass.

## Claim boundary and next dependency

Passing this unit proves that required Equation V1 inputs are real, inspectable, content-addressed
pre-outcome artifacts rather than arbitrary strings.  It does not prove that the fitted variables are
human cognition, that the semantic prediction is accurate, that Ours beats B5, or that formal M56 is
authorized.  Formal execution remains blocked by two distinct human V7 ledgers, the V9/M55 30-row data
chain, and a separately authorized real-data execution path.
