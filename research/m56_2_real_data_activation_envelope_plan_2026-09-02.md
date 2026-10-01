# M56.2 Formal Real-Data Activation Envelope · 2026-09-02

## Problem

M56 now has a frozen fair-comparison protocol, condition-separated generation capsule, separate scorer,
and content-addressed Equation V1 artifacts.  Those components deliberately accept only synthetic
engineering inputs.  A future caller must not be able to turn a caller-supplied `readiness=true`, a copied
fixture hash, a Git-tracked outcome file, or a stale model/hardware description into a formal M56 run.

## Single attributable change

Add one fail-closed activation envelope between the completed M55 private data chain and any real M56
model call.  It may authorize exactly one whole formal run only after it independently re-reads the live
human gate, validates the private 30-row temporal result, re-splits prediction data from the outcome key,
revalidates all frozen dependencies, captures the local model/hardware artifact, and binds the resulting
prediction capsule plus Equation artifacts into a short-lived receipt.

This unit does not change M54, M55, M56, or M56.1 frozen files.  It does not call a model, inspect a target
answer during generation, create a score, or weaken the two-human gate.

## Required compartments

The only permitted formal execution root is the Git-ignored
`analysis/local_m56_formal_execution_v1/<run-id>/`.  It has non-overlapping directories:

- `generation/`: prediction packet, condition capsule, run manifest, and pre-outcome Equation artifacts;
- `commitments/`: activation request, receipt, and later prediction commitment;
- `scoring/`: private outcome key and later score input;
- `telemetry/`: measured CPU time, prompt/completion tokens, latency, and peak memory.

The activation receipt contains hashes, not target answers or private paths.  A generation request may
receive the receipt and generation-side artifacts only.  The scoring directory is never part of a model
request.

## Live authorization gates

1. Contract and every frozen dependency hash validate at the moment of activation.
2. The standard V7 ledgers are complete, the frozen reliability result passes, and the standard V9
   result reports two human coders and 30 independently reviewed events.
3. The supplied private M55 result validates as 30 real-public-observation cutoff-to-future rows with
   zero future leakage and at least two independent coders.
4. The prediction/outcome split validates, the outcome key exists only in `scoring/`, and generation-side
   artifacts contain no outcome keys.
5. The local `qwen3.5:9b` manifest SHA-256, Ollama version, OS, machine architecture, CPU and memory are
   captured.  All model conditions bind to that one artifact and one hardware fingerprint.
6. The formal capsule is complete for all 30 × 7 condition tasks; B5/Ours source hashes match; the real
   Equation bundle contains 30 fit/state/transition triplets and retains unknown variables rather than
   fabricating private state.
7. The activation request binds the dataset, packet, outcome-key hash, manifest, capsule, Equation bundle,
   frozen dependency set, private layout, and runtime snapshot.
8. The receipt is short-lived and single-use.  Consuming it is an atomic state transition that authorizes
   the one no-retry formal run, not scoring or a scientific claim.

## Acceptance before human data exists

- the current machine produces a deterministic blocked audit with V7 `0/18 + 0/18`, V9 `0/30`, real rows
  `0/30`, formal model calls `0`, target-outcome access `0`, and no receipt;
- no public API accepts caller-supplied readiness as a substitute for the live audit;
- synthetic packets, forged real packets, stale dependency hashes, wrong model artifact, non-private
  paths, outcome material in generation, expired/modified receipts, or double consumption fail closed;
- a synthetic rehearsal may exercise layout and hash plumbing but has a different schema and can never
  produce a formal receipt;
- focused and compatibility tests pass, and the graphical page makes the denied-now/authorized-later
  boundary understandable without exposing private content.

## Claim boundary

Passing M56.2 proves only that formal execution now has a machine-checkable activation boundary and a
prepared real-data path.  While the human gate is incomplete, the correct result is denial.  It is not an
M56 model run, real-person prediction evidence, Equation V1 validity, Ours superiority, private mental
truth, a solved human-brain equation, full-pipeline readiness, or production readiness.
