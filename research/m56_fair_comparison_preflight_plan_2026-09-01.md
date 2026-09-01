# M56 Blinded Same-Model Fair-Comparison Preflight · 2026-09-01

## Why this can be frozen before M55 human data

M56 must not be designed after seeing which condition wins. The comparison conditions, strongest
control, model settings, information boundaries, token rules, primary metrics, success gate, and
failure policy can all be fixed while V7/V9/M55 real counts are still zero. This reduces researcher
degrees of freedom without opening target media or running a model.

## Single attributable change

Add only a fail-closed execution-preflight contract and a blinded packet/outcome-key splitter. Existing
M1–M55 artifacts, baselines, Equation V1, prompts, models, memory, runtime, human thresholds, sampling
slots, and sealed sources remain unchanged. This unit performs zero prediction calls.

## Formal comparison

- B0 remains a deterministic frequency floor and is exempt from the same-model rule.
- B1–B5 and Ours use the same frozen `qwen3.5:9b` artifact, hardware snapshot, decoding options, input
  and output token ceilings, and probability schema.
- B1–B4 are required floors with prospectively declared information differences.
- The confirmatory contrast is fixed as `B5_STRUCTURED_HISTORY` versus `OURS_HYBRID`; a weaker
  baseline cannot replace B5 after results.
- B5 and Ours receive the same source pre-cutoff information. B5 asks the model to predict directly
  from structured history; Ours uses a matched semantic call followed by explicit Equation V1
  memory/state/transition calculation.
- Every upstream Ours call and the B4 summary-build cost are included. Actual tokens, latency, peak
  memory, failures, and warmup are reported rather than hidden.

## Outcome isolation

The coordinator will split a valid M55 temporal dataset into:

1. a prediction packet made only from `build_model_input` views;
2. a separate private outcome key;
3. a split report containing only hashes and counts.

The generation process receives only item 1. It must commit all seven-condition probability rows by
canonical SHA-256 before a separate scorer may load item 2. Any outcome field in the packet, missing
row, retry, fallback, or source/hash change invalidates the run.

## Evidence and decision rule

The two co-primary paired outcomes are Ours-minus-B5 multiclass Brier and NLL. A positive result needs
both effects to favor Ours and both paired-bootstrap 95% upper bounds below zero, while Ours Top-1 is
not more than five percentage points below B5. This is an intersection rule: one attractive metric
cannot rescue the other. ECE is descriptive only at n=30. All B0–B5 results, proper scores, ranking
metrics, errors, costs, and leakage checks remain visible.

If the primary B5/Ours actual prompt-token difference exceeds 5%, a separately declared exact-token
matched sensitivity analysis must directionally replicate before the primary claim is accepted. The
main result is never silently replaced by that sensitivity run.

## Current authorization boundary

The live M55 audit still reports V7 0/18 + 0/18, V9 0/30, real temporal rows 0/30, M55 incomplete,
and M56 forbidden. Therefore this unit may validate only contract structure and synthetic no-content
fixtures. It may not open Uruha target outcomes, run B0–B5/Ours, create a model result, or change the
M55 gate.

## Acceptance

1. Every dependency hash and all seven condition definitions validate.
2. B5 is immutably the primary control and Ours the system condition.
3. Current live preflight stays unauthorized while M55 is incomplete.
4. Synthetic splitting emits a valid prediction packet, separate outcome key, and hash-only report.
5. The prediction packet contains none of the frozen outcome keys or values.
6. Real-shaped data cannot split or execute without a genuine M55 completion report.
7. Run-manifest validation rejects model, hardware, decoding, budget, sample, condition, retry, or
   outcome-unseen mismatches; B0 is handled as the declared deterministic exception.
8. The graphical preflight explains information visibility, blinding, resource parity, decision rule,
   current zero human rows, and M56 prohibition without private text.

## Claim boundary

Passing is protocol and execution-instrument readiness only. It does not show that Ours beats B5,
predicts Uruha, estimates private psychology, transfers to another person, or solves a human equation.
