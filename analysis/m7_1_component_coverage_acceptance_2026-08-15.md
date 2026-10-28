# M7 / M7.1 Ablation and Intervention — Frozen Diagnostic Acceptance

Date: 2026-08-15 (JST)

## Outcome

M7 establishes a probability-level diagnostic loop on the frozen M6 synthetic holdout. M7.1 then closes the two engineering gaps found by the first diagnostic: preference and habit are represented as independent variables, so all ten master-spec components can now be removed and measured separately.

This is not a new predictive result. M7.1 was implemented after inspecting M7 and uses the same eight synthetic holdout rows. Its valid claim is component identifiability and diagnostic completeness only.

## Frozen first M7 diagnostic

- Exact replay of the frozen M6 Ours probabilities: pass.
- Eight components evaluated; preference and habit honestly recorded as `not_identifiable`.
- 80 preregistered named interventions executed.
- 40 direct top-feature interventions executed; 40/40 changed the selected-label probability.
- Zero new model calls and zero utterance generation.

Important retained findings:

| Component removed | Δ Top-1 | Δ Brier | Δ NLL | Reading |
|---|---:|---:|---:|---|
| memory | -12.5 pp | +0.193 | +0.839 | removal harms |
| personality | -12.5 pp | +0.231 | +0.514 | removal harms |
| explicit state transition | -25.0 pp | +0.432 | +1.386 | removal harms strongly |
| LLM semantic interpretation | -25.0 pp | +0.282 | +1.461 | removal harms strongly |
| relationship | 0 pp | -0.072 | -0.070 | removal improves |
| temporal dynamics | +12.5 pp | -0.102 | -0.100 | removal improves |

Thus the diagnostic does not merely certify every proposed organ. It identifies the current T3 temporal update and relationship subvector as potentially noisy on this fixture.

## Preserved failure and controlled intervention

For `quiet_success::holdout`, the frozen system predicts `direct_rejection` with probability 0.775, while the synthetic future label is `acknowledge_then_continue` with probability 0.225. Under the preregistered `event.support = 1.0` intervention, the correct-label probability rises to 0.99995 and the selected behavior flips to the observed label.

This demonstrates that the error is inspectable and manipulable at the variable level. It does not prove the intervention value is the true hidden human state or authorize post-hoc correction of the M6 score.

## M7.1 component-coverage remediation

The remediation adds:

- Five explicit preference alignment variables computed from frozen observable event, state, and person parameters.
- Six habit-similarity variables computed against behavior centroids fitted only on the 24 training rows.
- A 28-feature diagnostic predictor: 17 frozen base features + 5 preference + 6 habit.

All 10/10 ablations change at least one probability metric. Preference and habit are now separately measurable. The full remediation score is Top-1 87.5%, Brier 0.248, and NLL 0.675, but these numbers are post-exposure diagnostics and are not predictive-lift evidence.

The negative evidence remains visible: removing temporal dynamics improves NLL by 0.220, removing relationship improves NLL by 0.116, and removing preference improves NLL by 0.014. Habit removal worsens NLL by 0.417. Goal removal changes NLL by only 0.0009. Component presence is therefore not equivalent to component usefulness.

## Acceptance boundary

Completed:

- 10/10 component-level ablations are executable and independently visible.
- Named probability interventions and direct explanation-faithfulness checks are reproducible.
- Positive, negligible, and harmful component effects are retained in one graphical lab.
- Immutable experiment/result locks bind both the first diagnostic and remediation.

Not established:

- causal truth about a human's private state;
- new unseen-domain predictive lift;
- stable benefit of every component;
- Uruha-specific human evidence;
- language, voice, or production behavior.

Raw remediation result: `analysis/m7_1_component_coverage_remediation_result.json`  
Result SHA-256: `24a0f0cfadf946d7a8ae55d27abe50fc3160c1ea6f8882fe621bc7b63cb0f45a`

The next dependency is M8: rolling-cutoff and multi-seed robustness, including a genuinely new semantic holdout that can test whether the transition and relationship failures recur rather than tuning them away.
