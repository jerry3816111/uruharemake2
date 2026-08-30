# M5 State Transition — Frozen First-Generation Acceptance

Date: 2026-08-15 (JST)

## Outcome

M5 passes its preregistered **synthetic mechanism** contract. It implements and compares four state-transition families under one common interface:

`next_state = transition(previous_state, current_event, retrieved_memories, person_parameters)`

This is not evidence of a person's true private state, not a behavior-prediction result, and not an Uruha or real-person claim.

## Frozen design

- 40 distinct event texts: 24 train, 8 dev, 8 holdout.
- Six state dimensions: arousal, irritation, caution, task focus, relationship tension, uncertainty.
- T0: previous state is copied unchanged.
- T1: disclosed, hand-designed weighted update.
- T2: ridge-linear transition fitted from structured fixture features.
- T3: the same learned family, but observable event features are first extracted from event text by local `qwen3.5:9b`.
- T3's prompt cannot see next-state labels, outcomes, private thoughts, identity, or behavior labels.
- No per-row retry and no row fallback.
- Ridge alpha is chosen using dev RMSE only; holdout is used for final comparison.

Frozen experiment lock: `configs/m5_state_transition_lock.json`  
Lock SHA-256: `bf18d809572adeebca70837da3c4f59a977890215d08d077997a062a87ae1c50`

## Actual holdout results

| Family | Holdout RMSE ↓ | MAE ↓ | Direction accuracy ↑ | Interpretation |
|---|---:|---:|---:|---|
| T0 static | 0.1264 | 0.1009 | 14.6% | Previous state alone misses most disclosed changes. |
| T1 weighted | 0.0420 | 0.0369 | 77.1% | Hand-designed mechanism captures much of the synthetic equation. |
| T2 learned linear | **0.0042** | **0.0034** | **100.0%** | Best match to this disclosed linear synthetic oracle. |
| T3 hybrid | 0.0576 | 0.0410 | 70.8% | Beats static, but loses to T1 and T2 because text-to-feature extraction is noisy. |

Selected ridge alpha: T2 = 0.001; T3 = 0.1.

## Preserved negative result

T3 is not the winner. Its holdout event-feature MAE is 0.2294. The largest per-feature errors are repetition (0.3675), support (0.2950), and technical failure (0.2625). This bottleneck is retained in the raw result and graphical lab instead of being hidden or tuned away after holdout inspection.

This result supports a narrower engineering conclusion: an explicit state-transition layer can be learned and audited when the input features are reliable; the current LLM perception layer is not yet reliable enough to preserve T2-level accuracy.

## Resource evidence

- Actual local model: `qwen3.5:9b`.
- Model calls: 40.
- Prompt tokens: 6,121.
- Completion tokens: 2,493.
- Total tokens: 8,614.
- Accumulated local inference latency: 178.76 seconds.
- Raw response text and SHA-256 are retained for every call.

Raw result: `analysis/m5_state_transition_synthetic_first_generation_raw.json`  
Result SHA-256: `61abb11677eedcd9c3824a9a14767b346396bc5b7770d3841a7fdbf5933f1a0c`

## Verification evidence

- M5 core and graphical contract tests: 12/12 pass (7 core/fixture + 1 lab + 4 frozen-result tests).
- Scoped M1–M5 regression before result-test addition: 49/49 pass.
- M2, M3, M4, and M5 frozen input/lock validation: all exit 0 with zero lock mismatch.
- Web graphical lab exposes all eight holdout events and all four predicted state vectors.

## Gate clarification

In the raw JSON, `gate_checks.behavior_prediction_performed: true` and `language_generation_performed: true` mean the **absence requirements passed**. Every trace itself records both `behavior_prediction_performed: false` and `language_generation_performed: false`. The naming is retained because the experiment code and result were already frozen; the graphical lab explains the intended meaning.

## Honest boundary and next dependency

M5 establishes an inspectable state-transition mechanism on author-designed synthetic targets. It does not establish that the state variables correspond to a real person's private state or that the transition improves real-world behavior prediction. M6 must add a frozen `HumanState → behavior probability distribution` predictor with proper calibration and temporal holdout, while preserving the transition ablations.
