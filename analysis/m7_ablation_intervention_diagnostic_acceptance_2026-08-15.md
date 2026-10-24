# M7 Ablation and Intervention — First Frozen Diagnostic

Date: 2026-08-15 (JST)

## Outcome

The first M7 diagnostic run is mechanically complete but **full component coverage is not complete**. Eight components represented in frozen M6 were reproducibly removed, 80 named interventions and 40 explanation-faithfulness interventions were executed with zero model calls, and the M6 probabilities replayed exactly. Preference and habit do not have independent M6 features, so both are reported `not_identifiable` instead of receiving fabricated proxy scores.

## Component ablations

Delta is ablated minus full. Positive Brier/NLL is worse; negative is better.

| Removed component | Top-1 delta | Brier delta | NLL delta | Finding |
|---|---:|---:|---:|---|
| Memory | -12.5 pp | +0.193 | +0.839 | Helpful on this fixture. |
| Emotion-like state | 0 pp | +0.054 | +0.117 | Helps probability quality, not Top-1. |
| Personality parameters | -12.5 pp | +0.231 | +0.514 | Helpful on this fixture. |
| Relationship state | 0 pp | **-0.072** | **-0.070** | Removal improves proper scores; likely redundant/noisy. |
| Preference/value | — | — | — | `not_identifiable` in M6. |
| Goal-like task focus | 0 pp | +0.050 | +0.092 | Helps probability quality, not Top-1. |
| Habit prior | — | — | — | `not_identifiable` in M6. |
| Temporal dynamics (replace with T0 previous state) | **+12.5 pp** | **-0.102** | **-0.100** | Removal improves all primary metrics. |
| Explicit transitioned-state group | -25.0 pp | +0.432 | +1.386 | State group as a whole is useful. |
| LLM semantic event features | -25.0 pp | +0.282 | +1.461 | Current event perception is useful despite noise. |

The important negative result is that the explicit state group helps, but the current **T3 temporal update** hurts relative to using the previous state while retaining direct event/memory/person features. This is consistent with M5's finding that T3 is much worse than T2 because Qwen event-feature error propagates into the state transition.

## Quiet-success causal diagnosis

Frozen M6 predicted `direct_rejection` with 0.775 instead of the synthetic target `acknowledge_then_continue` with 0.225. The preregistered `event.support = 1.0` intervention, propagated through the T3 transition, changes the result to:

- `acknowledge_then_continue`: 0.99995;
- original `direct_rejection`: 0.00003;
- delta correct-label probability: +0.77487.

This does not prove what a human internally felt. It proves that, inside the frozen computational graph, the support feature causally controls this error. The correct remediation target is the observable-event/support pathway and its transition interaction, not a post-hoc Japanese reply rule.

## Explanation faithfulness

For each of eight holdouts, the five largest non-bias features in the selected-label logit were intervened on. All 40/40 interventions changed the selected-label probability beyond `1e-8`, giving a nonzero-effect rate of 100%. The explanations are therefore faithful to this frozen model graph at the tested perturbation points; they are not causal claims about a human mind.

## Boundary and required remediation

- Engineering diagnostic: PASS.
- Diagnostic hypotheses: 3/3 pass.
- Full master-spec component coverage: FAIL/INCOMPLETE.
- Formal target-person claim: false.
- Model calls: 0.
- Language realization: false.

Raw result: `analysis/m7_ablation_intervention_diagnostic_first_result.json`  
SHA-256: `563bd366dfe930f4afca7b5773e8d7b1cce7aa0872a781a2dddf6fbc552caf23`

M7.1 must add independently represented preference/value and habit-prior features under a new predictor/remediation ID, then repeat all ten component ablations. It must preserve the first M7 result and may not claim fresh predictive lift on the already exposed M5/M6 holdouts.
