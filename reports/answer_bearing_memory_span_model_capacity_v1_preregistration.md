# Answer-bearing memory span model-capacity V1 preregistration

## Question

The 4B model produced fully grounded structured output but preserved only 1/8 true
answer-bearing memories. This experiment changes only model size to test whether that
false-negative problem is capacity-related.

## Controlled comparison

| Variable | Values |
|---|---|
| Changed | Qwen3.5 0.8B, 2B, 4B, 9B |
| Fixed | Cases, interventions, prompt, tool schema, source validation, scores, thresholds, speakability, metrics |

The prior 4B result is reused exactly. The other installed models receive identical
requests.

## Compute-saving stages

1. Phase 1 runs target-only and target-removed conditions (16 decisions per new model).
2. A model survives only with 100% strict contracts, 100% grounded positive spans,
   zero target-removed selections, and at least 6/8 target-only safe outcomes.
3. Survivors then run intact and replacement conditions to complete all 32 decisions.

## Decision boundary

Only a model passing every final safety and recall gate is eligible. If several pass,
the smallest local model wins. A pass authorizes only a new disjoint holdout; it does
not authorize runtime or production.
